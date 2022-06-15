# -*- coding: utf-8 -*-

"""
@Time    : 2022/3/24 10:13 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import re
import os
import json
import random
import requests

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker, events
from rasa_sdk.events import UserUtteranceReverted
from rasa_sdk.executor import CollectingDispatcher

shop_list = ['yunjing', 'planet']
file_root = os.path.dirname(__file__)


class ChitChatKnowledge(object):
    def __init__(self):
        self.chitchat_response = json.load(open(os.path.join(file_root, 'kb/chitchat_response.json'), mode='r'))
        self.jokes = json.load(open(os.path.join(file_root, 'kb/jokes.json'), mode='r'))

    def get_personality(self, nickname):
        """
        return：
        {'result': {'O': -1, 'C': 0, 'E': -1, 'A': 0, 'N': -1}, 'msg': 'success', 'code': 200}
        """
        url = "http://113.31.111.86:19068/personality"
        dic = {"nickname":nickname}
        res_final = None
        try:
            rest = requests.post(url,data=json.dumps(dic))
            rest = rest.json().get('result', {})
            res = []
            for k,v in rest.items():
                if str(int(v)) == '1':
                    res.append(k)
            if res:
                res_key = random.choice(res)
                res_list = self.chitchat_response['utter_greet'].get(res_key, [])
                res_final = random.choice(res_list) if res_list else None

        except Exception as e:
            print('get personality error!',e)

        return res_final

    def get_chitchat_response(self, user_name, text_in):
        chat_url = "http://113.31.111.86:48001/chat_ai"  # 需要根据情况修改
        response = requests.post(url=chat_url, data=json.dumps({"event_title": text_in, "user_name": user_name}))
        response = response.json()["response"]
        return response

    def get_jokes(self):
        joke_dict = random.choice(self.jokes)
        joke = joke_dict['content']
        return joke

chitkb = ChitChatKnowledge()

class ActionAnswerGreet(Action):
    """Executes the fallback action and goes back to the previous state
    of the dialogue"""

    def name(self):
        return 'action_greet'

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]):

        user_name = tracker.sender_id
        shop_name = user_name.split(':')[0]
        nickname = user_name[len(shop_name):] if shop_name in shop_list else user_name
        print("user_name",nickname)
        message = chitkb.get_personality(nickname)
        if message is not None and random.randint(1,10) < 9: # 设定80的概率
            dispatcher.utter_message(message)
        else:
            dispatcher.utter_message(response='utter_greet')
        return [UserUtteranceReverted()]

class ActionDefaultFallback(Action):
    """Executes the fallback action and goes back to the previous state
    of the dialogue"""

    def name(self):
        return 'action_default_fallback'

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]):

        # 访问API(闲聊)
        user_name = tracker.sender_id
        print("user_name",user_name)
        text = tracker.latest_message.get('text')
        pattern = re.compile(r'[^不别].*(笑话)|[^不别].*(玩笑)')
        match = re.search(pattern, text)
        if match:
            message = chitkb.get_jokes()
        else:
            message = chitkb.get_chitchat_response(user_name, text)
        print("闲聊:", message)
        if message is not None:
            dispatcher.utter_message(message)
        else:
            dispatcher.utter_template('utter_rephrase', tracker, silent_fail=True)
        return [UserUtteranceReverted()]


if __name__ == '__main__':
    res = chitkb.get_personality('多朵朵')
    print(res)