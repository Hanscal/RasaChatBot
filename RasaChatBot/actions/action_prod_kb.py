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
from action_config import shop_list, attribute_url
from action_config import EnToZh
from action_config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from action_config import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE
from prod_kb_utils import NormalizeName, RetrieveProduct, Neo4jKnowledgeBase

# default neo4j account should be user="neo4j", password="neo4j"
# from py2neo import Graph
# graph = Graph(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)

name_norm = NormalizeName()
ret_prod = RetrieveProduct(MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE)

class MyKnowledgeBaseAction(ActionQueryKnowledgeBase):
    def name(self) -> Text:
        return "action_query_prod_knowledge_base"

    def __init__(self):
        knowledge_base = Neo4jKnowledgeBase(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)  # 根据情况修改
        super().__init__(knowledge_base)
        self.en_to_zh = EnToZh()
        self.shop_list_link = {}

    # 只 query 产品属性
    async def utter_objects(
        self,
        dispatcher: CollectingDispatcher,
        object_type: Text,
        objects: List[Dict[Text, Any]],
    ) -> None:
        """
        Utters a response to the user that lists all found objects.
        Args:
            dispatcher: the dispatcher
            object_type: the object type
            objects: the list of objects
        """
        if objects:
            dispatcher.utter_message(text="找到下列{}:".format(self.en_to_zh(object_type)))

            if utils.call_potential_coroutine(self.knowledge_base.get_representation_function_of_object):
                repr_function = await self.knowledge_base.get_representation_function_of_object(object_type)
            else:
                repr_function = self.knowledge_base.get_representation_function_of_object(object_type)

            for i, obj in enumerate(objects, 1):
                dispatcher.utter_message(text=f"{i}: {repr_function(obj)}")
        else:
            dispatcher.utter_message(text="我没找到任何{}.".format(self.en_to_zh(object_type)))

    async def _query_objects(
        self, dispatcher: CollectingDispatcher, object_type: Text, tracker: Tracker
    ) -> List[Dict]:
        """
        Queries the knowledge base for objects of the requested object type and
        outputs those to the user. The objects are filtered by any attribute the
        user mentioned in the request.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker

        Returns: list of slots
        """
        object_attributes = await utils.call_potential_coroutine(self.knowledge_base.get_attributes_of_object(object_type))

        # get all set attribute slots of the object type to be able to filter the
        # list of objects
        attributes = get_attribute_slots(tracker, object_attributes)
        # query the knowledge base
        objects = await utils.call_potential_coroutine(self.knowledge_base.get_objects(object_type, attributes))

        await utils.call_potential_coroutine(self.utter_objects(dispatcher, object_type, objects))

        if not objects:
            return reset_attribute_slots(tracker, object_attributes)

        key_attribute = await utils.call_potential_coroutine(self.knowledge_base.get_key_attribute_of_object(object_type))

        last_object = None if len(objects) > 1 else objects[0][key_attribute]

        user_id = tracker.sender_id
        shop_id = user_id.split(':')[0]
        # 在run函数中已经确保一定是在这个shop_list里面
        object_type_wo_shop = object_type[len(shop_id):].lstrip('_')  # 这里有问题，需要将shop name 去除
        slots = [
            SlotSet(SLOT_OBJECT_TYPE, object_type_wo_shop),
            SlotSet(SLOT_MENTION, None),
            SlotSet(SLOT_ATTRIBUTE, None),
            SlotSet(SLOT_LAST_OBJECT, last_object),
            SlotSet(SLOT_LAST_OBJECT_TYPE, object_type_wo_shop),
            SlotSet(SLOT_LISTED_OBJECTS, list(map(lambda e: e[key_attribute], objects))),
        ]

        return slots + reset_attribute_slots(tracker, object_attributes)

    def utter_attribute_value(
        self,
        dispatcher: CollectingDispatcher,
        object_name: Text,
        attribute_name: Text,
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
        if attribute_value:
            dispatcher.utter_message(
                text="{}的{}是：{}".format(self.en_to_zh(object_name), self.en_to_zh(attribute_name),self.en_to_zh(attribute_value)).replace('\n','')
            )
        else:
            dispatcher.utter_message(text="没有找到{}的{}".format(self.en_to_zh(object_name), self.en_to_zh(attribute_name)))

    async def _query_attribute(
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
        # logging.info('mapping, mention {}, {}'.format(self.knowledge_base.ordinal_mention_mapping, self.use_last_object_mention))
        object_name = get_object_name(tracker,self.knowledge_base.ordinal_mention_mapping,self.use_last_object_mention)
        user_id = tracker.sender_id
        shop_id = user_id.split(':')[0]
        # todo 对链接号进行映射
        object_name = name_norm.run(object_name)  # 返回的是list, 或者none
        if object_name:
            object_name = object_name[-1]  # 取最后一个object_name
        # todo 商品链接映射
        self.shop_list_link = shop_list.get(shop_id, {})
        if object_name in self.shop_list_link:
            object_name = self.shop_list_link[object_name]

        # todo 测试
        if object_name in [str(i) for i in range(19, 200)]:
            object_name = random.choice([str(i) for i in range(1,19)])
        # todo 对商品名进行实体链接

        logging.info("object_name, attribute: {},{}".format(object_name, attribute))
        if not object_name or not attribute:
            dispatcher.utter_message(response="utter_rephrase")
            return [SlotSet(SLOT_MENTION, None), SlotSet(SLOT_ATTRIBUTE, None)]

        # logging.info("slots {}".format(tracker.slots))
        object_of_interest = await utils.call_potential_coroutine(self.knowledge_base.get_object(object_type, object_name))
        logging.info("objects interest {}, object_name {}".format(object_of_interest, object_name))
        if attribute not in object_of_interest:
            # 如果不在映射库中，调用服务
            msg = tracker.latest_message['text'] +' ' + attribute
            try:
                res = requests.post(attribute_url, data=json.dumps({"msg":msg}))
                res = res.json()
                conf = res['confidence']
                if float(conf) > 0.7:
                    attribute = res['name']
            except Exception as e:
                print("post attribute service error: {}".format(e))

        if not object_of_interest or attribute not in object_of_interest:
            dispatcher.utter_message(response="utter_rephrase")
            return [SlotSet(SLOT_MENTION, None), SlotSet(SLOT_ATTRIBUTE, None)]
        # logging.info("{} {}".format(object_of_interest, attribute))
        value = object_of_interest[attribute]

        object_repr_func = await utils.call_potential_coroutine(self.knowledge_base.get_representation_function_of_object(object_type))

        object_representation = object_repr_func(object_of_interest)

        # 通过id来记录上次提到的商品
        key_attribute = await utils.call_potential_coroutine(self.knowledge_base.get_key_attribute_of_object(object_type))

        object_identifier = object_of_interest[key_attribute]
        # logging.info("object identifier {}, key_attirbute {}".format(object_identifier, key_attribute))
        await utils.call_potential_coroutine(self.utter_attribute_value(dispatcher, object_representation, attribute, value))

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
        last_object_type = tracker.get_slot(SLOT_LAST_OBJECT_TYPE)
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
        new_request = object_type != last_object_type

        # 进入这个函数说明就是查询产品的
        # if not object_type:
        #     # object type always needs to be set as this is needed to query the
        #     # knowledge base
        #     dispatcher.utter_message(response="utter_ask_rephrase")
        #     return []
        print("product action",object_type, attribute)
        logging.info("product， attribute： {} {}".format(object_type, attribute))
        if attribute and object_type:
            return await self._query_attribute(dispatcher, shop_id+'_'+object_type, attribute, tracker)
        # elif not attribute or new_request:
        #     return await self._query_objects(dispatcher, shop_id+'_'+object_type, tracker)
        elif attribute:
            return await self._query_attribute(dispatcher, shop_id+'_product', attribute, tracker)  # object_type默认product

        dispatcher.utter_message(response="utter_ask_rephrase")
        return []
