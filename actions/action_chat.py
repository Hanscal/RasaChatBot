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


chat_url = "http://113.31.111.86:48001/chat_ai"  # 需要根据情况修改

jokes = json.load(open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data/kb/jokes.json')))

def get_chitchat_response(user_name, text_in):
    response = requests.post(url=chat_url, data=json.dumps({"event_title": text_in, "user_name": user_name}))
    response = response.json()["response"]
    return response

def get_jokes():
    joke_dict = random.choice(jokes)
    joke = joke_dict['content']
    return joke

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
            message = get_jokes()
        else:
            message = get_chitchat_response(user_name, text)
        print("闲聊:", message)
        if message is not None:
            dispatcher.utter_message(message)
        else:
            dispatcher.utter_template('utter_ask_rephrase', tracker, silent_fail=True)
        return [UserUtteranceReverted()]