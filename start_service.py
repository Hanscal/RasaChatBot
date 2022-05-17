# -*- coding: utf-8 -*-

"""
@Time    : 2022/3/25 8:35 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import time
import uuid
from flask import Flask, render_template
from flask import request
from flask_cors import CORS
import requests
import json
import logging

app = Flask(__name__,template_folder='templates',static_folder='static')
CORS(app, supports_credentials=True)

@app.route('/live_assistant_api', methods=['POST'])
def live_assistant_api():
    """
    前端调用接口
        路径：/live_assistant_api
        请求方式：POST
        请求参数：user_name, shop_name, message
    :return: response rasa响应数据
    """
    b0 = time.time()
    response = ''
    if request.method == 'POST':
        data_json = request.get_json(force=True)
        message_input = data_json['message']
        user_name = data_json.get('user_name','hanscal')
        shop_name = data_json.get('shop_name','')
        input_name = shop_name+':'+user_name
        response = requestRasabotServer(input_name, message_input)
        response = eval(response)
        if response and isinstance(response, list):
            response = '\n'.join([i['text'] for i in response])
    else:
        logging.info("only support post method!")
    print("response: ", response)
    print('total costs {:.2f}s'.format(time.time() - b0))
    return json.dumps({"response":response},ensure_ascii=False)


@app.route('/nlu_parse_api', methods=['POST'])
def nlu_parse_api():
    """
    前端调用接口
        路径：/nlu_parse_api
        请求方式：POST
        请求参数：user_name, shop_name, message
    :return: response rasa响应数据
    """
    b0 = time.time()
    intent_name = None
    intent_confidence = None
    if request.method == 'POST':
        data_json = request.get_json(force=True)
        message_input = data_json['message']
        message_id = str(uuid.uuid5(uuid.NAMESPACE_DNS,message_input))
        response = requestRasabot(url='model/parse', params={'text':message_input, "message_id":message_id}, method='post')
        intent = response.get('intent',{})
        intent_name = intent.get('name',None)
        intent_confidence = intent.get('confidence', None)
    else:
        logging.info("only support post method!")
    print("response: ", response)
    print('total costs {:.2f}s'.format(time.time() - b0))
    return json.dumps({"response":{'intent_name':intent_name, 'intent_confidence':intent_confidence}},ensure_ascii=False)

@app.route('/rasa_parse_api', methods=['POST'])
def rasa_parse_api():
    """
    前端调用接口
        路径：/rasa_parse_api
        请求方式：POST
        请求参数：url, params, method
    :return: response rasa响应数据
    """
    b0 = time.time()
    response = ''
    if request.method == 'POST':
        data_json = request.get_json(force=True)
        url = data_json['url']
        params = data_json.get('params',{})
        method = data_json.get('method','post')
        response = requestRasabot(url, params, method)
    else:
        logging.info("only support post method!")
    print("response: ", response)
    print('total costs {:.2f}s'.format(time.time() - b0))
    return json.dumps({"response":response},ensure_ascii=False)

@app.route('/live_assistant_ui', methods=['GET','POST'])
def live_assistant_ui():
    """
    前端调用接口
        路径：/ai
        请求方式：GET、POST
        请求参数：question
    :return: response rasa响应数据
    """
    if request.method == 'POST':
        b0 = time.time()
        question = request.form["question"]
        answer = requestRasabotServer('planet:hanscal', question)  # 默认地球主义的展示
        answer = eval(answer)
        if answer and isinstance(answer, list):
            answer = '\n'.join([i['text'] for i in answer])
        print("response: ", answer)
        print('total costs {:.2f}s'.format(time.time() - b0))
        return json.dumps({'answer': answer},ensure_ascii=False)

    return render_template("index.html")


def requestRasabotServer(userid, content):
    """
        访问rasa服务
    :param userid: 用户id
    :param content: 自然语言文本
    :return:  json格式响应数据
    """
    params = {'sender': userid, 'message': content}
    # rasa使用rest channel
    # https://rasa.com/docs/rasa/user-guide/connectors/your-own-website/#rest-channels
    # POST /webhooks/rest/webhook
    rasaUrl = "http://{0}:{1}/webhooks/rest/webhook".format('0.0.0.0', '5005')

    response = requests.post(rasaUrl, data=json.dumps(params), headers={'Content-Type': 'application/json'})
    response = response.text.encode('utf-8').decode("unicode-escape")
    return response

def requestRasabot(url, params, method='post'):
    """
        访问rasa服务
    :param url: 相对路由
    :param content: params是请求参数
    :param method: 请求方式
    :return:  json格式响应数据
    """
    rasaUrl = "http://{0}:{1}/{2}".format('0.0.0.0', '5005', url)
    response = ''
    if method == 'post':
        response = requests.post(rasaUrl, data=json.dumps(params), headers={'Content-Type': 'application/json'})
        response = response.text
    elif method == 'get':
        response = requests.get(rasaUrl, headers={'Content-Type': 'application/json'})
        response = response.text
    response = response.encode('utf-8').decode("unicode-escape")
    return response

if __name__ == '__main__':
    # 初始化日志引擎
    fh = logging.FileHandler(encoding='utf-8', mode='a', filename='./log/live_assistant.log')
    logging.basicConfig(
        handlers=[fh],
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%a, %d %b %Y %H:%M:%S',
    )

    # 启动服务，开启多线程模式
    app.run(
        host='0.0.0.0',
        port=8088,
        threaded=True,
        debug=False
    )