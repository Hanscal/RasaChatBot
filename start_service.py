# -*- coding: utf-8 -*-

"""
@Time    : 2022/3/25 8:35 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import time

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
        路径：/ai
        请求方式：GET、POST
        请求参数：content
    :return: response rasa响应数据
    """
    b0 = time.time()
    response = ''
    if request.method == 'POST':
        data_json = request.get_json(force=True)
        message_input = data_json['message']
        user_name = data_json.get('user_name','hanscal')
        response = requestRasabotServer(user_name, message_input)
    print('total costs {:.2f}s'.format(time.time() - b0))
    return json.dumps({"response":response},ensure_ascii=False)


@app.route('/live_assistant_ui', methods=['GET','POST'])
def live_assistant_ui():
    """
    前端调用接口
        路径：/ai
        请求方式：GET、POST
        请求参数：content
    :return: response rasa响应数据
    """
    if request.method == 'POST':
        b0 = time.time()
        question = request.form["question"]
        print(question)
        answer = requestRasabotServer(question, 'hanscal')
        answer = eval(answer)
        if answer and isinstance(answer, list):
            answer = answer[0]['text']
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


if __name__ == '__main__':
    # 初始化日志引擎
    fh = logging.FileHandler(encoding='utf-8', mode='a', filename='./log/live_assistant.log')
    logging.basicConfig(
        handlers=[fh],
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%a, %d %b %Y %H:%M:%S',
    )

    # 启动服务，开启多线程、debug模式
    # 浏览器访问http://127.0.0.1:8088/ai?content="你好"
    app.run(
        host='0.0.0.0',
        port=8088,
        threaded=True,
        debug=False
    )