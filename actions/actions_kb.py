# -*- coding: utf-8 -*-

"""
@Time    : 2022/3/23 8:14 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""

import os
from neo4j import GraphDatabase
from typing import Any, Dict, List, Text

from rasa_sdk import utils
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.knowledge_base.storage import KnowledgeBase
from rasa_sdk.knowledge_base.actions import ActionQueryKnowledgeBase
from collections import defaultdict

file_root = os.path.dirname(__file__)


class EnToZh:
    def __init__(self):
        self.data = {
            "song": "歌曲",
            "album": "专辑",
            "singer": "歌手",
            "birthday": "生日",
            "gender": "性别"
                    }

    def __call__(self, key):
        return self.data.get(key, key)


class MyKnowledgeBaseAction(ActionQueryKnowledgeBase):
    def name(self) -> Text:
        return "action_response_query"

    def __init__(self):
        print("using Neo4jKnowledgeBase")
        knowledge_base = Neo4jKnowledgeBase(uri="bolt://113.31.111.86:48087", user="neo4j", password="CHneo4j")  # 根据情况修改
        super().__init__(knowledge_base)

        self.en_to_zh = EnToZh()

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

            if utils.call_potential_coroutine(
                self.knowledge_base.get_representation_function_of_object
            ):
                repr_function = await self.knowledge_base.get_representation_function_of_object(
                    object_type
                )
            else:
                repr_function = self.knowledge_base.get_representation_function_of_object(
                    object_type
                )

            for i, obj in enumerate(objects, 1):
                dispatcher.utter_message(text=f"{i}: {repr_function(obj)}")
        else:
            dispatcher.utter_message(
                text="我没找到任何{}.".format(self.en_to_zh(object_type))
            )

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
                text="{}的{}是{}。".format(
                    self.en_to_zh(object_name),
                    self.en_to_zh(attribute_name),
                    self.en_to_zh(attribute_value),
                )
            )
        else:
            dispatcher.utter_message(
                text="没有找到{}的{}。".format(
                    self.en_to_zh(object_name), self.en_to_zh(attribute_name)
                )
            )



class Neo4jKnowledgeBase(KnowledgeBase):
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)

        self.representation_attribute = defaultdict(lambda: "name")

        self.relation_attributes = {
            "Singer": {},
            "Album": {},
            "Song": {"singer": "SUNG_BY", "album": "INCLUDED_IN"},
        }

        super().__init__()

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
        with self._driver.session() as session:
            result = session.write_transaction(
                self._do_get_attributes_of_object, object_type
            )

        result = result + list(self.relation_attributes[object_type].keys())

        return result

    def _do_get_attributes_of_object(self, tx, object_type) -> List[Text]:
        query = "MATCH (o:{object_type}) RETURN o LIMIT 1".format(
            object_type=object_type
        )
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
            result = session.write_transaction(
                self._do_get_objects, object_type, attributions, relations, limit
            )

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

            query = (
                basic_query + " " + where_clause + " RETURN o LIMIT {}".format(limit)
            )

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
        if isinstance(object_identifier,str) and object_identifier.isdigit():
            object_identifier = int(object_identifier)
        else:
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


if __name__ == "__main__":
    import asyncio

    kb = Neo4jKnowledgeBase(uri="bolt://113.31.111.86:48087", user="neo4j", password="CHneo4j")   # 测试代码，根据情况修改
    loop = asyncio.get_event_loop()

    result = loop.run_until_complete(kb.get_objects("singer", [], 5))
    print(result)

    result = loop.run_until_complete(
        kb.get_objects("singer", [{"name": "name", "value": "周杰伦"}], 5)
    )
    print(result)

    result = loop.run_until_complete(
        kb.get_objects(
            "song",
            [{"name": "name", "value": "晴天"}, {"name": "album", "value": "叶惠美"}],
            5,
        )
    )
    print(result)

    result = loop.run_until_complete(kb.get_object("singer", "0"))
    print('id=0',result)

    result = loop.run_until_complete(kb.get_object("singer", "周杰伦"))
    print(result)

    result = loop.run_until_complete(kb.get_object("song", "晴天"))
    print(result)

    result = loop.run_until_complete(kb.get_attributes_of_object("singer"))
    print(result)

    result = loop.run_until_complete(kb.get_attributes_of_object("song"))
    print(result)

    loop.close()