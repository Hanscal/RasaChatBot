# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/17 7:06 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import requests
import json

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