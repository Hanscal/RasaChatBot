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
    logger.info("params {}".format(params))
    try:
        if method == 'post':
            response = requests.post(rasaUrl, data=json.dumps(params), headers={'Content-Type': 'application/json'})
            response = response.text
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
        nlu_response = requestRasabot(url='model/parse', params={'text': message_input, "message_id": message_id}, method='post')
        nlu_response = json.loads(nlu_response)
        intent = nlu_response.get('intent', {})
        intent_name = intent.get('name', None)
        if intent_name == 'faq':
            intent_name = nlu_response.get('response_selector', {}).get("default", {}).get("response", {}).get("intent_response_key", 'faq')
        intent_confidence = intent.get('confidence', None)
        logger.info("intent name: {}".format(intent_name))
        entity_tmp = nlu_response.get('entities', [])
        entities = [{"name": ent['entity'], "value": ent['value'], "confidence": ent['confidence_entity'], "pos":(ent['start'],ent['end'])} for ent in entity_tmp]
    except Exception as e:
        logger.info("nlu request error: {}".format(e))
    # 根据nlu对response进行扩展
    if intent_name == "query_prod_knowledge_base":
        offset = 0
        for i in entities:
            if i["name"] == 'product' and not str(i['value']).isdigit():
                # 对商品名进行归一化
                prod_replace = name_normalize(i['value'])
                message_input = message_input[:i['pos'][0]+offset] + prod_replace + message_input[i['pos'][1]+offset:]
                offset = len(prod_replace) - len(str(i['value']))
    # response部分
    user_name = data_json.get('user_name', 'hanscal')
    shop_name = data_json.get('shop_name', '')
    input_name = shop_name + ':' + user_name
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

def name_normalize(ques):
    def ch2digits(chinese):
        numerals = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '百': 100,
                    '千': 1000}
        total = 0
        r = 1
        for i in range(len(chinese) - 1, -1, -1):
            # 倒序取
            val = numerals.get(chinese[i])
            if val >= 10 and i == 0:
                if val > r:
                    r = val
                    total += val
                else:
                    r = r * val
            elif val >= 10:
                if val > r:
                    r = val
                else:
                    r = r * val
            else:
                total += r * val
        return total

    if re.search('\d+号[链]?[接]?.*', str(ques)):
        ques = str(re.search('(\d+)号[链]?[接]?.*', str(ques)).group(1))+"号链接"
    elif re.search('[一二三四五六七八九十百千]+号', str(ques)):
        ques = str(ch2digits(re.search('([一二三四五六七八九十百千]+)号[链]?[接]?.*', str(ques)).group(1))) + "号链接"
    # todo 对商品名的归一化成链接号
    return ques