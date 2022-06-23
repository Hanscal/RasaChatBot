# -*- coding: utf-8 -*-

"""
@Time    : 2022/6/23 3:12 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""

import os
import jieba
import numpy as np
import random

from transformers import pipeline

file_root = os.path.dirname(__file__)

class BertAugmentor(object):
    def __init__(self, model_dir, beam_size=3):  # bert-base-chinese
        self.beam_size = beam_size
        self.model = pipeline('fill-mask', model=model_dir, top_k=beam_size)
        self.mask_token = self.model.tokenizer.mask_token

    def gen_sen(self, query, num_mask):
        '''{'sequence': ,'score' }'''
        tops = self.model(query)[0] if num_mask > 1 else self.model(query)
        num_mask -= 1
        while num_mask:
            qs = [x['sequence'] for x in tops]
            new_tops = self.model(qs)[0] if num_mask > 1 else self.model(qs)
            cur_tops = []
            for q, q_preds in zip(tops, new_tops):
                pre_score = q['score']
                for each in q_preds:
                    each['cur_score'] = each['score']
                    each['score'] = pre_score * each['score']
                    cur_tops.append(each)
            tops = sorted(cur_tops, key=lambda x: x['score'], reverse=True)[:self.beam_size]
            num_mask -= 1
        return tops

    def word_replacement(self, query, n):
        # 随机替换：通过随机mask掉词语，预测可能的值。
        out_arr = []
        seg_list = jieba.cut(query, cut_all=False)
        seg_list = [x for x in seg_list]
        set_index = [i for i, _ in enumerate(seg_list)]
        # 随机采样n个index，进行替换
        replace_index = random.sample(set_index, min(n, len(set_index)))
        for cur_index in replace_index:
            new_query = seg_list.copy()
            word_len = len(new_query[cur_index])
            new_word = [self.mask_token] * word_len
            new_query[cur_index] = ''.join(new_word)
            gen_qs = self.gen_sen(''.join(new_query), word_len)
            out_arr.extend(gen_qs)
        out_arr = sorted(out_arr, key=lambda x: x['score'], reverse=True)[:n]
        return [''.join([y for i, y in enumerate(x['sequence']) if i % 2 == 0]) for x in out_arr]

    def word_insertion(self, query, n):
        # 随机插入：通过随机插入mask，预测可能的词语
        out_arr = []
        seg_list = jieba.cut(query, cut_all=False)
        seg_list = [x for x in seg_list]
        # 随机采样n个index，进行插入
        set_index = [0] + [i + 1 for i, _ in enumerate(seg_list)]
        insert_index = random.sample(set_index, min(n, len(set_index)))
        # return insert_index
        # 随机在词语之间插入[MASK]
        for cur_index in insert_index:
            new_query = seg_list.copy()
            # 随机insert n 个字符, 1<=n<=3
            insert_num = np.random.randint(1, 4)
            for _ in range(insert_num):
                new_query.insert(cur_index, self.mask_token)
            gen_qs = self.gen_sen(''.join(new_query), insert_num)
            out_arr.extend(gen_qs)
        out_arr = sorted(out_arr, key=lambda x: x['score'], reverse=True)[:n]
        return [''.join([y for i, y in enumerate(x['sequence']) if i % 2 == 0]) for x in out_arr]

    def augment(self, query, num_aug=9):
        num_new_per_technique = int(num_aug / 2) + 1
        # 随机替换
        augmented_sentences = self.word_replacement(query, num_new_per_technique)
        # 随机插入
        augmented_sentences += self.word_insertion(query, num_new_per_technique)
        augmented_sentences = [i for i in augmented_sentences if not i.startswith('[')]
        return augmented_sentences


class BartAugmentor(object):
    def __init__(self, model_dir, beam_size=3): # fnlp/bart-base-chinese
        from transformers import BertTokenizer, BartForConditionalGeneration, Text2TextGenerationPipeline
        tokenizer = BertTokenizer.from_pretrained(model_dir)
        model = BartForConditionalGeneration.from_pretrained(model_dir)
        self.model = Text2TextGenerationPipeline(model, tokenizer)
        self.beam_size = beam_size
        self.mask_token = self.model.tokenizer.mask_token

    def gen_sen(self, query):
        '''{'sequence': ,'score' }'''
        tops = self.model(query)
        return tops

    def word_replacement(self, query, n):
        # 随机替换：通过随机mask掉词语，预测可能的值。
        out_arr = []
        seg_list = jieba.cut(query, cut_all=False)
        seg_list = [x for x in seg_list]
        set_index = [i for i, _ in enumerate(seg_list)]
        # 随机采样n个index，进行替换
        replace_index = random.sample(set_index, min(n, len(set_index)))
        for cur_index in replace_index:
            new_query = seg_list.copy()
            new_word = [self.mask_token]
            new_query[cur_index] = ''.join(new_word)
            gen_qs = self.gen_sen(''.join(new_query))
            out_arr.extend(gen_qs)
        return [''.join([y for i, y in enumerate(x['generated_text']) if i % 2 == 0]) for x in out_arr]

    def word_insertion(self, query, n):
        # 随机插入：通过随机插入mask，预测可能的词语
        out_arr = []
        seg_list = jieba.cut(query, cut_all=False)
        seg_list = [x for x in seg_list]
        # 随机采样n个index，进行插入
        set_index = [0] + [i + 1 for i, _ in enumerate(seg_list)]
        insert_index = random.sample(set_index, min(n, len(set_index)))
        # return insert_index
        # 随机在词语之间插入[MASK]
        for cur_index in insert_index:
            new_query = seg_list.copy()
            # 随机insert n 个字符, 1<=n<=3
            new_query.insert(cur_index, self.mask_token)
            gen_qs = self.gen_sen(''.join(new_query))
            out_arr.extend(gen_qs)
        return [''.join([y for i, y in enumerate(x['generated_text']) if i % 2 == 0]) for x in out_arr]

    def augment(self, query, num_aug=9):
        num_new_per_technique = int(num_aug / 2) + 1
        # 随机替换
        augmented_sentences = self.word_replacement(query, num_new_per_technique)
        # 随机插入
        augmented_sentences += self.word_insertion(query, num_new_per_technique)
        augmented_sentences = [i for i in augmented_sentences if not i.startswith('[')]
        return augmented_sentences


if __name__ == "__main__":
    # bert 模型下载地址，中文bert下载链接：https://github.com/InsaneLife/ChineseNLPCorpus#%E9%A2%84%E8%AE%AD%E7%BB%83%E8%AF%8D%E5%90%91%E9%87%8For%E6%A8%A1%E5%9E%8B
    s = '帮我查一下航班信息'
    bart_base_path = os.path.join(file_root, '../model/bart-base-chinese')
    bert_base_path = os.path.join(file_root, '../model/chinese-roberta-wwm-ext')
    model = BartAugmentor(model_dir=bart_base_path)
    res = model.augment(s)

    model = BertAugmentor(model_dir=bert_base_path)
    res1 = model.augment(s)
    res.extend(res1)
    print(set(res))