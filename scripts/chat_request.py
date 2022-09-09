# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/17 7:06 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import os
import re

import requests
import json
import uuid
from config.config import get_logger, proj_root
from config.config import RASA_HOST, RASA_PORT
logger = get_logger('live', os.path.join(proj_root, 'log/live_assistant.log'))

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
    rasaUrl = "http://{0}:{1}/webhooks/rest/webhook".format(RASA_HOST, RASA_PORT)
    response = {}
    logger.info("params {}".format(params))
    try:
        response = requests.post(rasaUrl, data=json.dumps(params), headers={'Content-Type': 'application/json'})
        response = response.text.encode('utf-8').decode("unicode-escape")
    except Exception as e:
        logger.error("requestRasabotServer error:{}!".format(e))
    return response

def requestRasabot(url, params, method='post'):
    """
        访问rasa服务，所有服务都可以从这个接口进入，请求参数不同
    :param url: 相对路由
    :param params: 请求参数
    :param method: 请求方式
    :return:  json格式响应数据
    """
    rasaUrl = "http://{0}:{1}/{2}".format(RASA_HOST, RASA_PORT, url)
    response = ''
    print(rasaUrl)
    logger.info("params {}".format(params))
    try:
        if method == 'post':
            # print(98645)
            response = requests.post(rasaUrl, data=json.dumps(params), headers={'Content-Type': 'application/json'})
            # print(6434)
            response = response.text
            # print(484)
        elif method == 'get':
            response = requests.get(rasaUrl, headers={'Content-Type': 'application/json'})
            response = response.text
        response = response.encode('utf-8').decode("unicode-escape")
    except Exception as e:
        logger.error("requestRasabot service error:{}!".format(e))
    return response

def requestServerbot(data_json):
    response = ''
    intent_name = None
    intent_confidence = None
    entities = []
    message_input = data_json['message']
    # nlu部分
    message_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, message_input))
    try:
        # print(234)
        nlu_response = requestRasabot(url='model/parse', params={'text': message_input.replace(' ',''), "message_id": message_id}, method='post')
        nlu_response = json.loads(nlu_response)
        print(645)
        intent = nlu_response.get('intent', {})
        intent_name = intent.get('name', None)
        if intent_name == 'faq':
            # print(456)
            intent_name = nlu_response.get('response_selector', {}).get("default", {}).get("response", {}).get("intent_response_key", 'faq')
        intent_confidence = intent.get('confidence', None)
        # print(8946)
        logger.info("intent name: {}".format(intent_name))
        entity_tmp = nlu_response.get('entities', [])
        # print(345)
        entities = [{"name": ent['entity'], "value": ent['value'], "confidence": round(ent['confidence_entity'], 2), "pos":(ent['start'],ent['end'])} for ent in entity_tmp]
    except Exception as e:
        logger.info("nlu request error: {}".format(e))
    # response部分
    user_name = data_json.get('user_name', 'hanscal')
    shop_name = data_json.get('shop_name', '')
    input_name = shop_name + ':' + user_name
    # print(456)
    try:
        response = requestRasabotServer(input_name, message_input)
    except Exception as e:
        logger.info("response server request error: {}".format(e))
    try:
        response = eval(response)
    except Exception as e:
        logger.info("can't eval response:{}, {}".format(response, e))
    if response and isinstance(response, list):
        response = '\n'.join([i['text'] for i in response])
    return entities, intent_confidence, intent_name, response
