# -*- coding: utf-8 -*-

"""
@Time    : 2022/7/14 6:11 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import re
import os
import pymysql
import logging
from collections import defaultdict
from typing import Text, Dict, Any, List
from rasa_sdk.knowledge_base.storage import KnowledgeBase
from neo4j import GraphDatabase

file_root = os.path.dirname(__file__)

class NormalizeName(object):
    def __init__(self):
        self.name_map = {"{}号链接".format(i): str(i) for i in range(1, 200)}

    @staticmethod
    def ch2digits(chinese):
        numerals = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
                    '十': 10, '百': 100, '千': 1000}
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

    def run(self, ques):
        # todo object_name is list type
        if not ques:
            return []  # none
        if isinstance(ques, list):
            # 取最后一个product
            ques_new = []
            ques_in_kb = []
            for que in ques:
                if re.search('\d+号[链]?[接]?.*', str(que)):
                    ques_t = str(re.search('(\d+)号[链]?[接]?.*', str(que)).group(1)) + "号链接"
                    que = self.name_map[ques_t] if ques_t in self.name_map else str(re.search('(\d+)号[链]?[接]?.*', str(que)).group(1))
                    ques_in_kb.append(que)
                    flag = True
                elif re.search('[一二三四五六七八九十百千]+号', str(que)):
                    ques_t = str(self.ch2digits(re.search('([一二三四五六七八九十百千]+)号[链]?[接]?.*', str(que)).group(1))) + "号链接"
                    que = self.name_map[ques_t] if ques_t in self.name_map else str(re.search('(\d+)号[链]?[接]?.*', str(que)).group(1))
                    ques_in_kb.append(que)
                    flag = True
                else:
                    flag = False
                # todo 对商品名的归一化成链接号
                if not flag and que in self.name_map:
                    que = self.name_map[que]
                    ques_in_kb.append(que)
                else:
                    ques_new.append(que)
            ques_new.extend(ques_in_kb)
            ques = ques_new
        print("ques",ques)
        return ques


class RetrieveProduct(object):
    def __init__(self, MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE):
        self.user = MYSQL_USER
        self.pw = MYSQL_PASSWORD
        self.port = MYSQL_PORT
        self.host = MYSQL_HOST
        self.db = MYSQL_DATABASE

    def get_prod_names(self, shop_name):
        p = os.path.join(file_root, '../data/dict/{}_name.txt'.format(shop_name))
        if os.path.exists(p):
            prod_names = [i.strip().split(' ')[0] for i in open(p, mode='r', encoding='utf-8').readlines() if i]
            prod_names = sorted(self.prod_names, key=len)[::-1]  # 按照字符长度从长到短排序
        else:
            prod_names = []
        return prod_names

    def retrieve_prod_name(self, prod_names, name):
        """根据识别出来的name去name库中查找最相似的，并且超过阈值才放回，否则放回原值"""
        if name in prod_names:
            return name
        pattern = re.compile('.*' + name + '.*')
        for i in prod_names:
            candidate = pattern.search(i)
            name = candidate.group()
        return name

    def get_conn(self):
        db = pymysql.connect(user=self.user, password=self.pw, database=self.db, host=self.host, port=self.port)
        cursor = db.cursor(pymysql.cursors.DictCursor)
        return db, cursor

    def get_shop_list(self, shop_name_spell):
        dict = {}
        db, cursor = self.get_conn()
        sql_bid = "select b_id from shop_list where name_spell = %s"
        sql_links = "select prod_id, link from product_links where b_id = %s"
        cursor.execute(sql_bid, (shop_name_spell))
        result = cursor.fetchone()
        if result:
            b_id = result['b_id']
            cursor.execute(sql_links, (b_id))
            results = cursor.fetchall()
            for i in results:
                id = i['prod_id']
                link = i['link']
                dict[link] = id
                # {'1': "3", "2": '4', "5": '15', '6': "16", '7': "17", '8': '18'}
        return dict

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
    import sys

    sys.path.append('.')
    from RasaChatBot.actions.action_config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

    kb = Neo4jKnowledgeBase(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)  # 测试代码，根据情况修改
    loop = asyncio.get_event_loop()

    result = loop.run_until_complete(kb.get_objects("Planet_product", [], 5))
    print(result)

    result = loop.run_until_complete(kb.get_objects("Planet_product", [{"name": "name", "value": "防脱固发洗发水"}], 5))
    print(result)

    result = loop.run_until_complete(
        kb.get_objects(
            "Planet_product",
            [{"name": "name", "value": "防脱固发洗发水"}, {"name": "name", "value": "氨基酸保湿护发洗发水"}],
            5,
        )
    )
    print(result)

    result = loop.run_until_complete(kb.get_object("Planet_product", "1"))
    print('id=1', result)

    result = loop.run_until_complete(kb.get_object("Planet_product", None))
    print(result)

    result = loop.run_until_complete(kb.get_object("Planet_product", "防脱固发洗发水"))
    print(result)

    result = loop.run_until_complete(kb.get_attributes_of_object("Planet_product"))
    print(result)

    loop.close()