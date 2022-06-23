# coding: utf-8
"""
@env: python3, pytorch>=1.7.1, transformers==4.2.0
@author: hua.cai@unidt.com
@date: 10/06/2022
"""
import os
import random
import sys
import time
import json
import logging
import torch
import numpy as np
from transformers import BertModel, BertTokenizer
sys.path.append('.')
from augment.language_model_generate import BartAugmentor, BertAugmentor
from augment.baidu_translate import Translator
from flask import Flask, request
from flask_cors import CORS

#MODEL_NAME = './model/bert-base-chinese'
#BERT-Base, Chinese: Chinese Simplified and Traditional, 12-layer, 768-hidden, 12-heads, 110M parameters
file_root = os.path.dirname(__file__)

# 初始化日志引擎
def get_logger(logger_name, log_file, level=logging.INFO):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s',
                                  datefmt='%a, %d %b %Y %H:%M:%S')
    fh = logging.FileHandler(encoding='utf-8', mode='a', filename=log_file)
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(logging.DEBUG)
    logger = logging.getLogger(logger_name)
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.setLevel(level)
    return logger

log_dir = os.path.join(os.path.join(file_root, 'log'))
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logger = get_logger('embedding', os.path.join(log_dir,'embedding_service.log'))

app = Flask(__name__)
CORS(app, supports_credentials=True)

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class BuildModel(object):
    def __init__(self):
        self.model_path = os.path.join(file_root, 'model/chinese-roberta-wwm-ext')

        self.POOLING = 'first_last_avg'
        # POOLING = 'last_avg'
        # POOLING = 'last2avg'
        self.USE_WHITENING = True
        self.N_COMPONENTS = 64
        self.MAX_LENGTH = 64

        self.tokenizer = BertTokenizer.from_pretrained(self.model_path)
        self.model = BertModel.from_pretrained(self.model_path)
        self.model = self.model.to(DEVICE)


    def sents_to_vecs(self, sentences, batch_size=32):
        with torch.no_grad():
            vecs = []
            input_is_string = False
            if isinstance(sentences, str) or not hasattr(sentences, '__len__'):
                sentences = [sentences]
                input_is_string = True
            i = 0
            iter_num = len(sentences)//batch_size if not len(sentences) % batch_size else len(sentences)//batch_size+1
            for sents in range(iter_num):
                sents = sentences[i*batch_size:batch_size*(i+1)]
                inputs = self.tokenizer(sents, return_tensors="pt", padding=True, truncation=True,  max_length=self.MAX_LENGTH)
                inputs['input_ids'] = inputs['input_ids'].to(DEVICE)
                inputs['token_type_ids'] = inputs['token_type_ids'].to(DEVICE)
                inputs['attention_mask'] = inputs['attention_mask'].to(DEVICE)

                hidden_states = self.model(**inputs, return_dict=True, output_hidden_states=True).hidden_states

                if self.POOLING == 'first_last_avg':
                    output_hidden_state = (hidden_states[-1] + hidden_states[1]).mean(dim=1)
                elif self.POOLING == 'last_avg':
                    output_hidden_state = (hidden_states[-1]).mean(dim=1)
                elif self.POOLING == 'last2avg':
                    output_hidden_state = (hidden_states[-1] + hidden_states[-2]).mean(dim=1)
                else:
                    raise Exception("unknown pooling {}".format(self.POOLING))
                i += 1
                all_embeddings = [emb.cpu().numpy() for emb in output_hidden_state]
                if input_is_string:
                    all_embeddings = all_embeddings[0]
                vecs.extend(all_embeddings)
            assert len(sentences) == len(vecs)
        return np.asarray(vecs) if vecs else []


    def compute_kernel_bias(self, vecs, n_components):
        """计算kernel和bias
        最后的变换：y = (x + bias).dot(kernel)
        """
        vecs = np.concatenate(vecs, axis=0)
        mu = vecs.mean(axis=0, keepdims=True)
        cov = np.cov(vecs.T)
        u, s, vh = np.linalg.svd(cov)
        W = np.dot(u, np.diag(s**0.5))
        W = np.linalg.inv(W.T)
        W = W[:, :n_components]
        return W, -mu


    def transform_and_normalize(self, vecs, kernel=None, bias=None):
        """应用变换，然后标准化
        """
        if not (kernel is None or bias is None):
            vecs = (vecs + bias).dot(kernel)
        return vecs / (vecs**2).sum(axis=1, keepdims=True)**0.5


    def normalize(self, vecs):
        """标准化
        """
        return vecs / (vecs**2).sum(axis=1, keepdims=True)**0.5


    def generate_parameter(self, z):
        sents = [str(it) for it in z['question']]
        vecs = self.sents_to_vecs(sents)
        print("Compute kernel and bias.")
        kernel, bias = self.compute_kernel_bias([vecs], n_components=self.N_COMPONENTS)
        vecs = self.transform_and_normalize(vecs, kernel, bias)
        print("Save...")
        np.save('kernal.npy',kernel)
        np.save('bias.npy',bias)
        np.save('vecs.npy',vecs)

        """
        vecs = transform_and_normalize(vecs, kernel, bias)
        print(vecs.shape)
        np.save('vecs.npy',vecs)
        """

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

bm = BuildModel()

@app.route('/get_sentence_embedding',methods=['POST'])
def get_sentence_embedding():
    b0 = time.time()
    response = []
    if request.method == 'POST':
        data_json = request.get_json(force=True)
        sents = data_json['sentences']
        response = bm.sents_to_vecs(sents)
    else:
        logger.error("only support post method!")
    logger.info('total costs {:.2f}s'.format(time.time() - b0))
    return json.dumps({"embeddings": response}, cls=NumpyEncoder)


@app.route('/get_normalized_sentence_embedding',methods=['POST'])
def get_normalized_sentence_embedding():
    b0 = time.time()
    response = []
    if request.method == 'POST':
        data_json = request.get_json(force=True)
        sents = data_json['sentences']
        vecs = bm.sents_to_vecs(sents)
        response = bm.normalize(vecs)
    else:
        logger.error("only support post method!")
    logger.info('total costs {:.2f}s'.format(time.time() - b0))
    return json.dumps({"embeddings": response}, cls=NumpyEncoder)


berta = BertAugmentor(model_dir=os.path.join(file_root, 'model/chinese-roberta-wwm-ext'))
barta = BartAugmentor(model_dir=os.path.join(file_root, 'model/bart-base-chinese'))
bdta = Translator()

@app.route('/data_augment',methods=['POST'])
def data_augment():
    b0 = time.time()
    res_all = []
    num = 0
    if request.method == 'POST':
        data_json = request.get_json(force=True)
        sent = data_json['sentence']
        num = int(data_json['aug_number'])
        method = data_json.get('method','generate') # method可以为generate和translate
        try:
            if method == "translate":
                sent0 = bdta.back_translate(sent, nums=num)
                if len(sent0) < 25:
                    num_half = int(num) // 2
                    sents1 = berta.augment(sent, num_half)
                    sents2 = barta.augment(sent, num_half)
                    res_all.extend(sents1)
                    res_all.extend(sents2)
            else:
                num_half = int(num) // 2
                sents1 = berta.augment(sent, num_half)
                sents2 = barta.augment(sent, num_half)
                res_all.extend(sents1)
                res_all.extend(sents2)
        except Exception as e:
            logger.info("data augment error: {}".format(e))
        res_all = list(set(res_all))
        random.shuffle(res_all)
    else:
        logger.error("only support post method!")
    logger.info('total costs {:.2f}s'.format(time.time() - b0))
    return json.dumps({"aug_sentences": res_all[:num]},ensure_ascii=False)


if __name__ == "__main__":
    # sents = ['你好','你提供什么功能','发什么快递']
    # vecs = direct_embedding(sents)
    # print(vecs)
    # 启动服务，开启多线程模式
    app.run(
        host='0.0.0.0',
        port=8068,
        threaded=True,
        debug=False
    )

