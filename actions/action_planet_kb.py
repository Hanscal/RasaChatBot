# -*- coding: utf-8 -*-

"""
@Time    : 2022/4/14 9:14 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""

import os
import random
import re
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
from py2neo import Graph
from markdownify import markdownify as md


file_root = os.path.dirname(__file__)
p = os.path.join(file_root, '../data/dict/planet.txt')
disease_names = [i.strip().split(' ')[0] for i in open(p, 'r', encoding='UTF-8').readlines()]
# default neo4j account should be user="neo4j", password="neo4j"
graph = Graph(uri="bolt://113.31.111.86:48087", user="neo4j", password="CHneo4j")


def retrieve_prod_name(name):
    names = []
    name = '.*' + '.*'.join(list(name)) + '.*'
    pattern = re.compile(name)
    for i in disease_names:
        candidate = pattern.search(i)
        if candidate:
            names.append(candidate.group())
    return names


# class ActionEcho(Action):
#     def name(self) -> Text:
#         return "action_echo"
#
#     def run(self,
#             dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]):
#         user_say = "You said: " + tracker.latest_message['text']
#         dispatcher.utter_message(user_say)
#         return []
#
#
# class ActionDonKnow(Action):
#     def name(self) -> Text:
#         return "action_donknow"
#
#     def run(self,
#             dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]):
#         dispatcher.utter_template("utter_donknow", tracker)
#         # dispatcher.utter_template("utter_howcanhelp", tracker)
#         dispatcher.utter_message(md("您可以这样向我提问: <br/>头痛怎么办<br/>\
#                                       什么人容易头痛<br/>\
#                                       头痛吃什么药<br/>\
#                                       头痛能治吗<br/>\
#                                       头痛属于什么科<br/>\
#                                       头孢地尼分散片用途<br/>\
#                                       如何防止头痛<br/>\
#                                       头痛要治多久<br/>\
#                                       糖尿病有什么并发症<br/>\
#                                       糖尿病有什么症状"))
#         return []
#
#
# class ActionProdIntro(Action):
#     def name(self) -> Text:
#         return "action_prod_intro"
#
#     def run(self,
#             dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]):
#
#         prod = tracker.get_slot("prod")  # 这是产品的名字
#
#         possible_prod = retrieve_prod_name(prod)
#         # todo 从user_id中得到shop_id
#         shop = 'planet'
#         # if len(possible_diseases) == 1 or sure == "true":
#         if prod or len(possible_prod) == 1:
#             a = graph.run("match (a:$shop {name: $prod}) return a", shop=shop, prod=prod).data()[0]['a']
#             if "intro" in a:
#                 intro = a['intro']
#                 template = "{0}的简介：{1}"
#                 retmsg = template.format(prod, intro)
#             else:
#                 retmsg = prod + "暂无简介"
#             dispatcher.utter_message(retmsg)
#         elif len(possible_prod) > 1:
#             retmsg = '找到这几款产品：{}。你需要哪一款呢？'.format('，'.join(possible_prod))
#             dispatcher.utter_message(retmsg)
#         else:
#             dispatcher.utter_message("知识库中暂无与 {0} 产品相关的记录".format(prod))
#         return []


class EnToZh:
    def __init__(self):
        self.data = {
            "product":"产品",
            "name": "产品名",
            "intro": "介绍",
            "price": "原价",
            "arrive_price": "优惠价",
            "specification": "规格",
            "ingredient":"成分",
            "smell":"气味",
            "effect":"功效",
            "people":"适用人群",
            "expiration":"保质期",
            "package":"包装",
            "place":"生产地",
            "brand":"品牌",
            "氨基酸保湿护发洗发水": "氨基酸保湿护发洗发水(1号链接)",
            "防脱固发洗发水": "防脱固发洗发水(2号链接)",
            "丝润双萃分层喷雾": "丝润双萃分层喷雾(3号链接)",
            "柔润闪耀鎏沙精华液": "柔润闪耀鎏沙精华液(4号链接)"
                     }

    def __call__(self, key):
        return self.data.get(key, key)


class MyKnowledgeBaseAction(ActionQueryKnowledgeBase):
    def name(self) -> Text:
        return "action_prod_response_query"

    def __init__(self):
        knowledge_base = Neo4jKnowledgeBase(uri="bolt://113.31.111.86:48087", user="neo4j", password="CHneo4j")  # 根据情况修改
        super().__init__(knowledge_base)
        self.en_to_zh = EnToZh()

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
        object_attributes = await utils.call_potential_coroutine(
            self.knowledge_base.get_attributes_of_object(object_type)
        )

        # get all set attribute slots of the object type to be able to filter the
        # list of objects
        attributes = get_attribute_slots(tracker, object_attributes)
        # query the knowledge base
        objects = await utils.call_potential_coroutine(
            self.knowledge_base.get_objects(object_type, attributes)
        )

        await utils.call_potential_coroutine(
            self.utter_objects(dispatcher, object_type, objects)
        )

        if not objects:
            return reset_attribute_slots(tracker, object_attributes)

        key_attribute = await utils.call_potential_coroutine(
            self.knowledge_base.get_key_attribute_of_object(object_type)
        )

        last_object = None if len(objects) > 1 else objects[0][key_attribute]

        slots = [
            SlotSet(SLOT_OBJECT_TYPE, object_type),
            SlotSet(SLOT_MENTION, None),
            SlotSet(SLOT_ATTRIBUTE, None),
            SlotSet(SLOT_LAST_OBJECT, last_object),
            SlotSet(SLOT_LAST_OBJECT_TYPE, object_type),
            SlotSet(
                SLOT_LISTED_OBJECTS, list(map(lambda e: e[key_attribute], objects))
            ),
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
                text="{}的{}是：{}".format(self.en_to_zh(object_name), self.en_to_zh(attribute_name),self.en_to_zh(attribute_value))
            )
        else:
            dispatcher.utter_message(
                text="没有找到{}的{}".format(self.en_to_zh(object_name), self.en_to_zh(attribute_name))
            )

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
        # import pdb;pdb.set_trace()
        object_name = get_object_name(tracker,self.knowledge_base.ordinal_mention_mapping,self.use_last_object_mention)

        if not object_name or not attribute:
            dispatcher.utter_message(response="utter_ask_rephrase")
            return [SlotSet(SLOT_MENTION, None)]

        object_of_interest = await utils.call_potential_coroutine(self.knowledge_base.get_object(object_type, object_name))

        if not object_of_interest or attribute not in object_of_interest:
            dispatcher.utter_message(response="utter_ask_rephrase")
            return [SlotSet(SLOT_MENTION, None)]

        value = object_of_interest[attribute]

        object_repr_func = await utils.call_potential_coroutine(self.knowledge_base.get_representation_function_of_object(object_type))

        object_representation = object_repr_func(object_of_interest)

        key_attribute = await utils.call_potential_coroutine(self.knowledge_base.get_key_attribute_of_object(object_type))

        object_identifier = object_of_interest[key_attribute]

        await utils.call_potential_coroutine(
            self.utter_attribute_value(
                dispatcher, object_representation, attribute, value
            )
        )

        slots = [
            SlotSet(SLOT_OBJECT_TYPE, object_type),
            SlotSet(SLOT_ATTRIBUTE, None),
            SlotSet(SLOT_MENTION, None),
            SlotSet(SLOT_LAST_OBJECT, object_identifier),
            SlotSet(SLOT_LAST_OBJECT_TYPE, object_type),
        ]

        return slots


class Neo4jKnowledgeBase(KnowledgeBase):
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)

        self.representation_attribute = defaultdict(lambda: "name")
        self.relation_attributes = {"Product": {}}

        self.ordinal_mention_mapping = {
            "1": lambda l: l[0],
            "2": lambda l: l[1],
            "3": lambda l: l[2],
            "4": lambda l: l[3],
            "5": lambda l: l[4],
            "6": lambda l: l[5],
            "7": lambda l: l[6],
            "8": lambda l: l[7],
            "9": lambda l: l[8],
            "10": lambda l: l[9],
            "ANY": lambda l: random.choice(l),
            "LAST": lambda l: l[-1],
        }

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
        # if object_type in ['氨基酸保湿护发洗发水','防脱固发洗发水','丝润双萃分层喷雾', '柔润闪耀鎏沙精华液']:
        #     query = "MATCH (o:{object_type} {{name:{value}}}) RETURN o LIMIT 1".format(object_type='product', value=object_type )
        # else:

        query = "MATCH (o:{object_type}) RETURN o LIMIT 1".format(object_type=object_type)
        print(query)
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
        if not relations:
            # attr only, simple case
            query = "MATCH (o:{object_type} {attrs}) RETURN o LIMIT {limit}".format(
                object_type=object_type,
                attrs=self._dict_to_cypher(attributions),
                limit=limit,
            )
            print(query)
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

        result = self.do_get_object(
            object_type,
            object_identifier,
            await self.get_key_attribute_of_object(object_type),
            await self.get_representation_attribute_of_object(object_type),
        )

        return result

if __name__ == '__main__':
    import asyncio

    kb = Neo4jKnowledgeBase(uri="bolt://113.31.111.86:48087", user="neo4j", password="CHneo4j")  # 测试代码，根据情况修改
    loop = asyncio.get_event_loop()

    result = loop.run_until_complete(kb.get_objects("planet", [], 5))
    print(result)

    result = loop.run_until_complete(
        kb.get_objects("planet", [{"name": "name", "value": "防脱固发洗发水"}], 5)
    )
    print(result)

    result = loop.run_until_complete(
        kb.get_objects(
            "planet",
            [{"name": "name", "value": "防脱固发洗发水"}, {"name": "name", "value": "氨基酸保湿护发洗发水"}],
            5,
        )
    )
    print(result)

    result = loop.run_until_complete(kb.get_object("planet", "12"))
    print('id=0', result)

    result = loop.run_until_complete(kb.get_object("planet", "氨基酸保湿护发洗发水"))
    print(result)

    result = loop.run_until_complete(kb.get_object("planet", "防脱固发洗发水"))
    print(result)

    result = loop.run_until_complete(kb.get_attributes_of_object("planet"))
    print(result)

    loop.close()