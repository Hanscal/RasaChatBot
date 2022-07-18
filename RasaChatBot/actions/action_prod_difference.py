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
from collections import defaultdict
from typing import Text, Dict, Any, List
from rasa_sdk import utils
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.knowledge_base.storage import KnowledgeBase
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

from neo4j import GraphDatabase
import sys
sys.path.append('.')
from .action_config import shop_list, attribute_url
from .action_config import EnToZh
from .action_config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from .prod_kb_utils import NormalizeName

# default neo4j account should be user="neo4j", password="neo4j"
# from py2neo import Graph
# graph = Graph(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)

name_norm = NormalizeName()

class MyKnowledgeBaseAction(ActionQueryKnowledgeBase):
    def name(self) -> Text:
        return "action_product_difference"

    def __init__(self):
        knowledge_base = Neo4jKnowledgeBase(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)  # 根据情况修改
        super().__init__(knowledge_base)
        self.en_to_zh = EnToZh()
        self.shop_list_link = shop_list

    # 只 query 产品属性
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

    # 只 query 产品属性
    def utter_product_difference(
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
        attr_list = ['通量','流速','纯水流量','废水比','颜色','总净水量','出水口','specification','effect']
        diff_text = ''
        for name, (value1, value2) in zip(attribute_name, attribute_value):
            value1, value2 = str(value1).strip('。.,，\n'), str(value2).strip('。.,，\n')
            if name == "intro":
                # 先求公共最长连续子序列，判断相似度，如果相似度高，则不用这个属性
                sim = Levenshtein.ratio(value1, value2)
                if sim < 0.85:
                    diff_text = "({}){}; 而({}){}。".format(self.en_to_zh(object_name[0]), value1, self.en_to_zh(object_name[1]), value2)
                    break
            else:
                if attribute_name and len(attribute_name) == 1:
                    
                elif attribute_name and len(attribute_name) <= 3:
                    if value1 != value2:
                        diff_text += "{}的{}是{}; 而{}的{}是{}。".format(self.en_to_zh(object_name[0]), self.en_to_zh(name), value1, self.en_to_zh(object_name[1]), self.en_to_zh(name), value2)
                elif name in random.sample(attr_list, 3):
                    diff_text += "{}的{}是{}; 而{}的{}是{}。".format(self.en_to_zh(object_name[0]), self.en_to_zh(name), value1, self.en_to_zh(object_name[1]), self.en_to_zh(name), value2)
        if diff_text:
            dispatcher.utter_message(text="{}与{}的区别是：{}".format(self.en_to_zh(object_name[0]), self.en_to_zh(object_name[1]), diff_text))
        else:
            dispatcher.utter_message(response="utter_rephrase")

    async def _query_difference(
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
        if object_name and len(object_name) >= 2:
            object_name = object_name[-2:] # 如果大于2个产品，取最后两个
        elif object_name and len(object_name) == 1:
            object_name_last = tracker.slots['knowledge_base_last_object'] # str
            if object_name_last:
                object_name.append(object_name_last)

        # 如果存在的商品少于两个，则退出查询
        if not object_name or len(object_name) < 2:
            dispatcher.utter_message(response="utter_rephrase")
            return [SlotSet(SLOT_MENTION, None), SlotSet(SLOT_ATTRIBUTE, None)]

        object_name_new = []
        # todo 建立映射关系
        self.shop_list_link.update({shop_id:{}})
        for obj_name in object_name:
            if obj_name in self.shop_list_link[shop_id]:
                obj_name = self.shop_list_link[shop_id][obj_name]
            # todo 测试
            if obj_name in [str(i) for i in range(19, 200)]:
                obj_name = random.choice([str(i) for i in range(1,19)])
            object_name_new.append(obj_name)
        object_name = object_name_new  # 将值赋给object_name
        # todo 对商品名进行实体链接

        logging.info("object_name, attribute: {},{}".format(object_name, attribute))

        prod1 = object_name[0]
        # 通过任意一个商品拿到属性值
        object_of_interest1 = await utils.call_potential_coroutine(self.knowledge_base.get_object(object_type, prod1))
        logging.info("objects interest {}, object_name {}".format(object_of_interest1, prod1))
        prod2 = object_name[1]
        object_of_interest2 = await utils.call_potential_coroutine(self.knowledge_base.get_object(object_type, prod2))
        logging.info("objects interest {}, object_name {}".format(object_of_interest2, prod2))

        # 任何一个商品查询不到，则退出查询
        if not object_of_interest1 or not object_of_interest2:
            dispatcher.utter_message(response="utter_rephrase")
            return [SlotSet(SLOT_MENTION, None), SlotSet(SLOT_ATTRIBUTE, None)]

        prod_diff_key = []
        prod_diff_value = []
        # 如果有商品和属性
        if attribute and object_name:
            if attribute not in object_of_interest1:
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
            # 如果链接后属性在库的交集里
            if attribute in (set(object_of_interest1.keys()) & set(object_of_interest2.keys())):
                value1 = object_of_interest1[attribute]
                value2 = object_of_interest2[attribute]
                prod_diff_key.append(attribute)
                prod_diff_value.append((value1, value2))

        if not prod_diff_key:
            # 如果只有商品, 同一个商家中的属性都有
            for key in (set(object_of_interest1.keys()) & set(object_of_interest2.keys())):
                value1 = object_of_interest1[key]
                value2 = object_of_interest2[key]
                if value1 != value2:
                    prod_diff_key.append(key)
                    prod_diff_value.append((value1, value2))

        object_repr_func = await utils.call_potential_coroutine(self.knowledge_base.get_representation_function_of_object(object_type))

        object_representation1 = object_repr_func(object_of_interest1)
        object_representation2 = object_repr_func(object_of_interest2)  # 保存最后一个提到的产品

        key_attribute = await utils.call_potential_coroutine(self.knowledge_base.get_key_attribute_of_object(object_type))
        object_identifier = object_of_interest2[key_attribute]

        await utils.call_potential_coroutine(self.utter_product_difference(dispatcher, [object_representation1, object_representation2], prod_diff_key, prod_diff_value))

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

        return await self._query_difference(dispatcher, shop_id+'_product', attribute, tracker)  # object_type默认product


class Neo4jKnowledgeBase(KnowledgeBase):
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)

        self.representation_attribute = defaultdict(lambda: "name")
        self.relation_attributes = defaultdict(lambda: {})
        self.key_attribute = defaultdict(lambda: "id")
        self.representation_function = defaultdict(lambda: lambda obj: obj["name"])

        super(Neo4jKnowledgeBase, self).__init__()

    def close(self):
        self._driver.close()

    @staticmethod
    def _dict_to_cypher(data):
        pieces = []
        for k, v in data.items():
            piece = "{}: '{}'".format(k, v)
            pieces.append(piece)

        join_piece = ", ".join(pieces)

        return "{" + join_piece + "}"

    async def get_attributes_of_object(self, object_type: Text) -> List[Text]:
        # transformer for query
        object_type = object_type.capitalize()

        result = self.do_get_attributes_of_object(object_type)

        return result

    def do_get_attributes_of_object(self, object_type) -> List[Text]:
        # import pdb;pdb.set_trace()
        with self._driver.session() as session:
            result = session.write_transaction(self._do_get_attributes_of_object, object_type)

        result = result + list(self.relation_attributes[object_type].keys())

        return result

    def _do_get_attributes_of_object(self, tx, object_type) -> List[Text]:
        query = "MATCH (o:{object_type}) RETURN o LIMIT 1".format(object_type=object_type)
        print(query)
        logging.info(query)
        result = tx.run(query,)

        record = result.single()

        if record:
            return list(record[0].keys())

        return []

    async def get_representation_attribute_of_object(self, object_type: Text) -> Text:
        """
        Returns a lamdba function that takes the object and returns a string
        representation of it.
        Args:
            object_type: the object type
        Returns: lamdba function
        """
        return self.representation_attribute[object_type]

    def do_get_objects(
        self,
        object_type: Text,
        attributions: Dict[Text, Text],
        relations: Dict[Text, Text],
        limit: int,
    ):
        with self._driver.session() as session:
            result = session.write_transaction(self._do_get_objects, object_type, attributions, relations, limit)

        return result

    def do_get_object(
        self,
        object_type: Text,
        object_identifier: Text,
        key_attribute: Text,
        representation_attribute: Text,
    ):
        with self._driver.session() as session:
            result = session.write_transaction(
                self._do_get_object,
                object_type,
                object_identifier,
                key_attribute,
                representation_attribute,
                self.relation_attributes[object_type],
            )

        return result

    @classmethod
    def _do_get_objects(self,
        tx,
        object_type: Text,
        attributions: Dict[Text, Text],
        relations: Dict[Text, Text],
        limit: int,
    ):
        print("<_do_get_objects>: ", object_type, attributions, relations, limit)
        logging.info("<_do_get_objects>: {} {} {} {}".format(object_type, attributions, relations, limit))
        if not relations:
            # attr only, simple case
            query = "MATCH (o:{object_type} {attrs}) RETURN o LIMIT {limit}".format(
                object_type=object_type,
                attrs=self._dict_to_cypher(attributions),
                limit=limit,
            )
            print(query)
            logging.info(query)
            result = tx.run(query,)

            return [dict(record["o"].items()) for record in result]
        else:
            basic_query = "MATCH (o:{object_type} {attrs})".format(
                object_type=object_type,
                attrs=self._dict_to_cypher(attributions),
                limit=limit,
            )

            sub_queries = []
            for k, v in relations.items():
                sub_query = "MATCH (o)-[:{}]->({{name: '{}'}})".format(k, v)

            where_clause = "WHERE EXISTS { " + sub_query + " }"
            for sub_query in sub_queries[1:]:
                where_clause = "WHERE EXISTS { " + sub_query + " " + where_clause + " }"

            query = (basic_query + " " + where_clause + " RETURN o LIMIT {}".format(limit))

            print(query)
            logging.info(query)
            result = tx.run(query,)

            return [dict(record["o"].items()) for record in result]

    @staticmethod
    def _do_get_object(
        tx,
        object_type: Text,
        object_identifier: Text,
        key_attribute: Text,
        representation_attribute: Text,
        relation: Dict[Text, Text],
    ):
        print("<_do_get_object>: ", object_type, object_identifier, key_attribute, representation_attribute, relation)
        logging.info("<_do_get_object>: {}, {}, {}, {}, {}".format(object_type, object_identifier, key_attribute, representation_attribute, relation))
        # preprocess attr value
        # if isinstance(object_identifier,str) and object_identifier.isdigit():
        #     object_identifier = int(object_identifier)
        # else:
        #     object_identifier = '"{}"'.format(object_identifier)
        object_identifier = '"{}"'.format(object_identifier)

        # try match key first
        query = "MATCH (o:{object_type} {{{key}:{value}}}) RETURN o, ID(o)".format(
            object_type=object_type, key=key_attribute, value=object_identifier
        )
        print(query)
        logging.info(query)
        result = tx.run(query,)
        record = result.single()
        if record:
            attr_dict = dict(record[0].items())
            oid = record[1]
        else:
            # try to match representation attribute
            query = "MATCH (o:{object_type} {{{key}:{value}}}) RETURN o, ID(o)".format(
                object_type=object_type,
                key=representation_attribute,
                value=object_identifier,
            )
            print(query)
            logging.info(query)
            result = tx.run(query,)
            record = result.single()
            if record:
                attr_dict = dict(record[0].items())
                oid = record[1]
            else:
                # finally, failed
                attr_dict = None

        if attr_dict is None:
            return None

        relation_attr = {}
        for k, v in relation.items():
            query = "MATCH (o)-[:{}]->(t) WHERE ID(o)={} RETURN t.name".format(v, oid)
            print(query)
            logging.info(query)
            result = tx.run(query)
            record = result.single()
            if record:
                attr = record[0]
            else:
                attr = None

            relation_attr[k] = attr

        return {**attr_dict, **relation_attr}

    async def get_objects(
        self, object_type: Text, attributes: List[Dict[Text, Text]], limit: int = 5
    ) -> List[Dict[Text, Any]]:
        """
        Query the knowledge base for objects of the given type. Restrict the objects
        by the provided attributes, if any attributes are given.
        Args:
            object_type: the object type
            attributes: list of attributes
            limit: maximum number of objects to return
        Returns: list of objects
        """
        print("get_objects", object_type, attributes, limit)
        logging.info("get_objects type:{}, attr:{}, limit:{}".format(object_type, attributes, limit))
        # convert attributes to dict
        attrs = {}
        for a in attributes:
            attrs[a["name"]] = a["value"]

        # transformer for query
        object_type = object_type.capitalize()

        # split into attrs and relations
        attrs_filter = {}
        relations_filter = {}
        relation = self.relation_attributes[object_type]
        for k, v in attrs.items():
            if k in relation:
                relations_filter[relation[k]] = v
            else:
                attrs_filter[k] = v

        result = self.do_get_objects(object_type, attrs_filter, relations_filter, limit)

        return result

    async def get_object(
        self, object_type: Text, object_identifier: Text
    ) -> Dict[Text, Any]:
        """
        Returns the object of the given type that matches the given object identifier.
        Args:
            object_type: the object type
            object_identifier: value of the key attribute or the string
            representation of the object
        Returns: the object of interest
        """
        # transformer for query
        object_type = object_type.capitalize()
        logging.info("get object -> object type: {}".format(object_type))
        result = self.do_get_object(
            object_type,
            object_identifier,
            await self.get_key_attribute_of_object(object_type),
            await self.get_representation_attribute_of_object(object_type),
        )

        return result

if __name__ == '__main__':
    import asyncio

    kb = Neo4jKnowledgeBase(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)  # 测试代码，根据情况修改
    loop = asyncio.get_event_loop()


    result = loop.run_until_complete(kb.get_object("Planet_product", "1"))
    print('id=1', result)

    result = loop.run_until_complete(kb.get_object("Planet_product", None))
    print(result)

    result = loop.run_until_complete(kb.get_object("Qinyuan_product", "前置过滤器"))
    print(result)

    result = loop.run_until_complete(kb.get_attributes_of_object("Planet_product"))
    print(result)

    loop.close()