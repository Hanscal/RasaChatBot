# -*- coding: utf-8 -*-

"""
@Time    : 2022/4/14 9:14 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import json
import random
import logging
import requests
import Levenshtein

from typing import Text, Dict, Any, List
from rasa_sdk import utils
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.knowledge_base.actions import ActionQueryKnowledgeBase

from rasa_sdk.events import SlotSet
from rasa_sdk.knowledge_base.utils import (
    SLOT_OBJECT_TYPE,
    SLOT_LAST_OBJECT_TYPE,
    SLOT_ATTRIBUTE,
    reset_attribute_slots,
    SLOT_MENTION,
    SLOT_LAST_OBJECT,
    SLOT_LISTED_OBJECTS,
    get_object_name,
    get_attribute_slots,
)


import sys
sys.path.append('.')
from .action_config import shop_list, attr_list, attribute_url
from .action_config import EnToZh
from .action_config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from .action_config import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE
from .prod_kb_utils import NormalizeName, RetrieveProduct, Neo4jKnowledgeBase

# default neo4j account should be user="neo4j", password="neo4j"
# from py2neo import Graph
# graph = Graph(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)

name_norm = NormalizeName()
ret_prod = RetrieveProduct(MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE)

class MyKnowledgeBaseAction(ActionQueryKnowledgeBase):
    def name(self) -> Text:
        return "action_product_recommendation"

    def __init__(self):
        knowledge_base = Neo4jKnowledgeBase(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)  # 根据情况修改
        super().__init__(knowledge_base)
        self.en_to_zh = EnToZh()
        self.shop_list_link = {}
        self.attr_list_link = []

    # 只 query 产品属性
    def utter_product_recommendation(
            self,
            dispatcher: CollectingDispatcher,
            object_name: List,
            attribute_name: List,
            attribute_value: List,
    ) -> None:
        """
        Utters a response that informs the user about the attribute value of the
        attribute of interest.
        Args:
            dispatcher: the dispatcher
            object_name: the name of the object
            attribute_name: the name of the attribute
            attribute_value: the value of the attribute
        """
        diff_text = []
        logging.info("utter: object_name, attribute: {},{}".format(object_name, attribute_name))
        flag = False
        for name, (value1, value2) in zip(attribute_name, attribute_value):
            value1, value2 = str(value1).strip('。.,，\n'), str(value2).strip('。.,，\n')
            if name == "intro":
                # 先求公共最长连续子序列，判断相似度，如果相似度高，则不用这个属性
                sim = Levenshtein.ratio(value1, value2)
                if sim < 0.85:
                    diff_text = ["({}){}; 而({}){}。".format(self.en_to_zh(object_name[0]), value1, self.en_to_zh(object_name[1]), value2)]
                    break
            else:
                if len(attribute_name) == 1:
                    if value1 != value2:
                        diff_text = ["{}的{}是{}; 而{}的{}是{}。".format(self.en_to_zh(object_name[0]), self.en_to_zh(name), value1, self.en_to_zh(object_name[1]), self.en_to_zh(name), value2)]
                    else:
                        flag = True
                        diff_text = ["{}和{}的{}没有区别。".format(self.en_to_zh(object_name[0]), self.en_to_zh(object_name[1]), self.en_to_zh(name))]
                elif name in self.attr_list_link:
                    if value1 != value2:
                        diff_text.append("{}的{}是{}; 而{}的{}是{}。".format(self.en_to_zh(object_name[0]), self.en_to_zh(name), value1, self.en_to_zh(object_name[1]), self.en_to_zh(name), value2))
        if diff_text:
            if len(diff_text) > 3:
                diff_text = random.sample(diff_text, 3)
            if flag:
                dispatcher.utter_message(text = ''.join(diff_text))
            else:
                dispatcher.utter_message(text="{}与{}的区别是：{}".format(self.en_to_zh(object_name[0]), self.en_to_zh(object_name[1]), ''.join(diff_text)))
        else:
            dispatcher.utter_message(response="utter_rephrase")

    async def _query_recommendation(
        self,
        dispatcher: CollectingDispatcher,
        object_type: Text,
        attribute: Text,
        tracker: Tracker,
    ) -> List[Dict]:
        """
        Queries the knowledge base for the value of the requested attribute of the
        mentioned object and outputs it to the user.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker

        Returns: list of slots
        """
        # import pdb;pdb.set_trace()
        # logging.info('mapping, mention {}, {}'.format(self.knowledge_base.ordinal_mention_mapping, self.use_last_object_mention))
        object_name = get_object_name(tracker,self.knowledge_base.ordinal_mention_mapping,self.use_last_object_mention)
        user_id = tracker.sender_id
        shop_id = user_id.split(':')[0]
        # todo 对链接号进行映射
        object_name = name_norm.run(object_name) # 得到list

        object_name_new = []
        # todo 建立映射关系
        self.shop_list_link = shop_list.get(shop_id, {})
        self.attr_list_link = attr_list.get(shop_id, [])
        for obj_name in object_name:
            if obj_name in self.shop_list_link:
                obj_name = self.shop_list_link[obj_name]
            # todo 测试
            if obj_name in [str(i) for i in range(19, 200)]:
                obj_name = random.choice([str(i) for i in range(1,19)])
            object_name_new.append(obj_name)
        object_name = object_name_new  # 将值赋给object_name
        # todo 对商品名进行实体链接

        logging.info("object_name, attribute: {},{}".format(object_name, attribute))

        object_of_interest_list = []
        # 返回25个产品的key,value list，格式为[{'name': 'KRL5003', 'id': '1'...},{'name': 'KRL5006', 'id': '2'...},...]
        all_prod_names = await utils.call_potential_coroutine(self.knowledge_base.get_objects(object_type, attributes=[], limit=25))
        prod_names = [i['name'] for i in all_prod_names]
        prod_ids = [i['id'] for i in all_prod_names]
        # 如果有产品，则取他们的交集，考虑name和id
        product_exist_flag = False
        if object_name:
            name_union = set(object_name) & set(prod_names)
            id_union = set(object_name) & set(prod_ids)
            object_name_union = name_union | id_union
            object_name = list(object_name_union)
            product_exist_flag = True if object_name else False
        else:
            object_name = prod_names
        for prod in object_name:
            # 通过商品拿到属性值
            object_of_interest_ = await utils.call_potential_coroutine(self.knowledge_base.get_object(object_type, prod))
            object_of_interest_list.append(object_of_interest_)
            logging.info("objects interest {}, object_name {}".format(object_of_interest_, prod))

        # 如果没有属性，或者一个商品也没有返回，则退出查询
        if not attribute or not object_of_interest_list:
            dispatcher.utter_message(response="utter_rephrase")
            return [SlotSet(SLOT_MENTION, None), SlotSet(SLOT_ATTRIBUTE, None)]

        # 如果有属性和商品
        for item in object_of_interest_list:
            # 得到产品的属性keys
            if attribute not in item.keys():
                # 如果不在映射库中，调用服务
                msg = tracker.latest_message['text'] +' ' + attribute
                try:
                    res = requests.post(attribute_url, data=json.dumps({"msg":msg}))
                    res = res.json()
                    conf = res['confidence']
                    if float(conf) > 0.7:
                        attribute = res['name']  # attribute归一化
                        break
                except Exception as e:
                    print("post attribute service error: {}".format(e))

        # 根据object_name和属性写逻辑，需要根据attribute去object_of_interest_list
        if attribute == '规格':
            pass
        elif attribute == '使用人数':
            pass
        elif attribute == '流量':
            pass
        elif attribute == '安装方式':
            pass
        else:
            dispatcher.utter_message(response="utter_rephrase")
            return [SlotSet(SLOT_MENTION, None), SlotSet(SLOT_ATTRIBUTE, None)]

        key_attribute = await utils.call_potential_coroutine(self.knowledge_base.get_key_attribute_of_object(object_type))
        object_identifier = object_of_interest_list[-1][key_attribute] if product_exist_flag else None

        await utils.call_potential_coroutine(self.utter_product_recommendation(dispatcher, object_of_interest_list))

        # 在run函数中已经确保一定是在这个shop_list里面
        object_type_wo_shop = object_type[len(shop_id):].lstrip('_')  # 这里有问题，需要将shop name 去除
        slots = [
            SlotSet(SLOT_OBJECT_TYPE, object_type_wo_shop),
            SlotSet(SLOT_ATTRIBUTE, None),
            SlotSet(SLOT_MENTION, None),
            SlotSet(SLOT_LAST_OBJECT, object_identifier),
            SlotSet(SLOT_LAST_OBJECT_TYPE, object_type_wo_shop),
        ]

        return slots

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: "DomainDict",
    ) -> List[Dict[Text, Any]]:
        """
        Executes this action. If the user ask a question about an attribute,
        the knowledge base is queried for that attribute. Otherwise, if no
        attribute was detected in the request or the user is talking about a new
        object type, multiple objects of the requested type are returned from the
        knowledge base.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker
            domain: the domain

        Returns: list of slots

        """
        # import pdb;pdb.set_trace()
        object_type = tracker.get_slot(SLOT_OBJECT_TYPE)
        attribute = tracker.get_slot(SLOT_ATTRIBUTE)
        user_id = tracker.sender_id
        shop_id = user_id.split(':')[0]
        if shop_id not in shop_list:
            print('请检查直播商店名是否正确')
            logging.info('请检查直播商店名是否正确')
            dispatcher.utter_message(response="utter_ask_rephrase")
            return []

        # 对需要查询的字典进行指定更新
        self.en_to_zh.update(shop_name=shop_id)
        print("product action",object_type, attribute)
        logging.info("product， attribute： {} {}".format(object_type, attribute))

        return await self._query_recommendation(dispatcher, shop_id+'_product', attribute, tracker)  # object_type默认product

if __name__ == '__main__':
    object_of_interest_list = [{"name":"KRL5006","id":"1","sf":""},{"name":"KRL5006","id":"1","sf":""}]
