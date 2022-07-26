# -*- coding: utf-8 -*-

"""
@Time    : 2022/4/14 9:14 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import json
import random
import logging
import re
import requests
from functools import reduce

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

    @staticmethod
    def normalize_num_people(query: Text):
        """
        适用人数推荐类query中人数提取

        Args:
            que: tracker.latest_message['text'] or attribute

        Returns: 适用人数
        """
        numerals = {'两': '2', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6'}
        if re.search('(\d)[个人/口/人].*', query):
            return str(re.search('(\d)[个人/口/人].*', query).group(1))
        elif re.search('([两/二/三/四/五/六])[个人/口/人].*', query):
            return numerals[re.search('([两二三四五六])[个人/口/人].*', query).group(1)[-1]]
        elif re.search('([一家/家用的/家庭]+).*', query):
            return '家庭'
        else:
            return '无'

    @staticmethod
    def get_intent_value(tracker: Tracker):
        """
        nlu意图识别attribute_entity提取

        Args:
            tracker: the tracker

        Returns: list of entities
        """
        entity_list = []
        latest_mess = tracker.latest_message
        for entity_dict in latest_mess['entities']:
            if entity_dict['entity'] == 'attribute':
                entity_tmp = latest_mess['text'][entity_dict['start']:entity_dict['end']]
                entity_list.append(entity_tmp)
        return entity_list

    # 只 query 产品属性
    def utter_product_recommendation(
            self,
            dispatcher: CollectingDispatcher,
            object_name: List,
            attribute_name: List,
            attribute_value: Text,
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

        logging.info("utter: object_name, attribute: {},{}".format(object_name, attribute_name))
        if attribute_value:
            dispatcher.utter_message(text=attribute_value)
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
        text = ''
        if attribute == '产品尺寸':
            prod_attr_lst = [
                (object['name'], reduce(lambda x, y: float(x) * float(y), object['产品尺寸'].split('mm')[0].split('*'))) for
                object in
                object_of_interest_list if '产品尺寸' in object]
            prod_attr_lst = sorted(prod_attr_lst, key=lambda x: x[1], reverse=True)  # 根据属性值来排序
            max_attr_value = prod_attr_lst[0][1]
            prod_attr_dict_lst = [{'name': item[0], attribute: item[1]} for item in prod_attr_lst if
                                  item[1] == max_attr_value]
            if len(prod_attr_dict_lst) == 1:
                text = "咱们店里现在正在售卖的产品中体积最小巧的一款是{}".format(prod_attr_dict_lst[0]['name'])
            elif len(prod_attr_dict_lst) == 2:
                dispatcher.utter_message(
                    "咱们店里现在正在售卖的产品中体积最小巧的两款是{}和{}".format(prod_attr_dict_lst[0]['name'], prod_attr_dict_lst[1]['name']))
            else:
                prod_attr_dict_lst = random.sample(prod_attr_dict_lst, 3)
                text = "咱们店里现在正在售卖的产品中体积最小巧的一款是 " + ' '.join([prod_attr['name'] for prod_attr in prod_attr_dict_lst])

            await utils.call_potential_coroutine(self.utter_product_recommendation(dispatcher, object_name, object_of_interest_list, text))

        elif attribute == '适用人数':
            # 规范query中使用人数
            query_num_people = self.normalize_num_people(tracker.latest_message['text'])
            object_of_suitable_for_num_people_list = []
            for obj in object_of_interest_list:
                if '适用人数' in obj:
                    if query_num_people in obj['适用人数']:
                        object_of_suitable_for_num_people_list.append(obj['name'])

            if len(object_of_suitable_for_num_people_list) > 3:
                object_of_suitable_for_num_people_list = random.sample(object_of_suitable_for_num_people_list, 3)
                if query_num_people != '家庭':
                    text = '适合{}个人使用的产品有{}'.format(query_num_people, ','.join(object_of_suitable_for_num_people_list))
                else:
                    text = '适合{}使用的产品有{}'.format(query_num_people, ','.join(object_of_suitable_for_num_people_list))

            elif len(object_of_suitable_for_num_people_list) > 0:
                if query_num_people != '家庭':
                    text = '适合{}个人使用的产品有{}'.format(query_num_people, ','.join(object_of_suitable_for_num_people_list))
                else:
                    text = '适合{}使用的产品有{}'.format(query_num_people, ','.join(object_of_suitable_for_num_people_list))

            await utils.call_potential_coroutine(self.utter_product_recommendation(dispatcher, object_name, object_of_interest_list, text))

        elif attribute == '纯水流量':
            prod_attr_lst = [(object['name'], float(object[attribute].strip('L/min'))) for object in object_of_interest_list if attribute in object]
            prod_attr_lst = sorted(prod_attr_lst, key=lambda x: x[1], reverse=True)  # 根据属性值来排序
            max_attr_value = prod_attr_lst[0][1]
            prod_attr_dict_lst = [{'name': item[0], attribute: item[1]} for item in prod_attr_lst if item[1] == max_attr_value]
            if len(prod_attr_dict_lst) == 1:
                text = "咱们店里现在正在卖的流速最快的一款是{}".format(prod_attr_dict_lst[0]['name'])
            elif len(prod_attr_dict_lst) == 2:
                text = "咱们店里现在正在卖的流速最快的两款是{}和{}".format(prod_attr_dict_lst[0]['name'], prod_attr_dict_lst[1]['name'])
            else:
                object_name_rand3 = random.sample(prod_attr_dict_lst, 3)
                text = "咱们店里现在正在卖的流速最快的几款是 " + ' '.join([prod_attr['name'] for prod_attr in object_name_rand3])

            await utils.call_potential_coroutine(self.utter_product_recommendation(dispatcher, object_name, object_of_interest_list, text))

        elif attribute == '出水口':
            # 规范query中单出水口
            query_outlet = re.search('([单/双][通道/水口/出水]?).*', tracker.latest_message['text']).group(1)[0]
            object_of_outlet_list = []
            for obj in object_of_interest_list:
                if '出水口' in obj:
                    if query_outlet in obj['出水口']:
                        object_of_outlet_list.append(obj['name'])

            if len(object_of_outlet_list) > 3:
                object_of_outlet_list = random.sample(object_of_outlet_list, 3)
                text = '有{}出水通道的产品有{}'.format(query_outlet, ','.join(object_of_outlet_list))
            elif len(object_of_outlet_list) > 0:
                text = '有{}出水通道的产品有{}'.format(query_outlet, ','.join(object_of_outlet_list))

            await utils.call_potential_coroutine(self.utter_product_recommendation(dispatcher, object_name, object_of_interest_list, text))

        elif attribute == '安装方式':
            await utils.call_potential_coroutine(self.utter_product_recommendation(dispatcher, object_name, object_of_interest_list, text))

        else:
            dispatcher.utter_message(response="utter_rephrase")
            return [SlotSet(SLOT_MENTION, None), SlotSet(SLOT_ATTRIBUTE, None)]

        key_attribute = await utils.call_potential_coroutine(self.knowledge_base.get_key_attribute_of_object(object_type))
        object_identifier = object_of_interest_list[-1][key_attribute] if product_exist_flag else None

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
