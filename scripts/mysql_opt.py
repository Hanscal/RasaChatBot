# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/15 11:11 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import re

import pymysql
from datetime import datetime

from config.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
from config.config import MYSQL_KNOWLEDGE_DATABASE

"""数据库相关"""
class LiveDB(object):
    def __init__(self):
        pass

    def get_conn(self,host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD, port=MYSQL_PORT, database=MYSQL_DATABASE):
        db = pymysql.connect(user=user,password=password,database=database,host=host,port=port)
        cursor = db.cursor(pymysql.cursors.DictCursor)
        return db,cursor

    def detect_recent_response(self, b_id, theme=None):
        db, cursor = self.get_conn()
        if theme == None:
            sql = "SELECT * FROM live_responses WHERE b_id='%s' ORDER BY present_time DESC" % (b_id)
            duration = 60*0  # 2 分钟内不回答第二次
            """去除该限制"""
        elif theme == "欢迎":
            sql = "SELECT * FROM live_responses WHERE b_id='%s' ORDER BY present_time DESC" % (b_id)
            duration = 0 #允许重复欢迎观众进入直播间
        else:
            sql = "SELECT * FROM live_responses WHERE b_id='%s' AND theme='%s' ORDER BY present_time DESC" % (b_id, theme)
            duration = 60*1  # 1 分钟内不回答第二次同一主题

        cursor.execute(sql)
        dat = cursor.fetchall()
        if len(dat) > 0:
            present_time = dat[0]['present_time']
            # date = datetime.strptime(present_time, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            diff = now - present_time
            if diff.seconds > duration:
                return False
            else:
                return True
        else:
            return False

    def get_base_question(self, table_name, intent_en:dict):
        db, cursor = self.get_conn(database=MYSQL_KNOWLEDGE_DATABASE)
        res = []
        if "faq" in intent_en:
            # faq中的second_label_en是一个list
            second_label_list = intent_en['faq'].get('second_label_en',[])
            for second_label_en in second_label_list:
                sql = "SELECT * FROM %s WHERE second_label_en='%s'" % (table_name, second_label_en)
                cursor.execute(sql)
                dat = cursor.fetchall()
                tmp = {'intent':'faq/{}'.format(second_label_en),"examples":[]}
                for d in dat:
                    if d['question']:
                        tmp['examples'].append(d['question'])
                res.append(tmp)

        elif "query_prod_knowledge_base" in intent_en:
            attribute_en_list = intent_en['query_prod_knowledge_base'].get("attribute_en",[])
            tmp = {'intent': 'query_prod_knowledge_base', "examples": [], "synonym":[]}
            patt = re.compile(r'.*\[(.*)\]\(attribute\)')
            for attribute_en in attribute_en_list:
                sql = "SELECT * FROM %s WHERE attribute_en='%s'" % (table_name, attribute_en)
                cursor.execute(sql)
                dat = cursor.fetchall()
                synonym = {"attribute": attribute_en, "examples":[]}
                syn_set = set()
                for d in dat:
                    if d['question']:
                        tmp['examples'].extend([d['question']])
                        # 得到question中的synonym
                        match = re.match(patt, d['question'])
                        if match:
                            syn_set.add(match.group(1))

                synonym['examples'] = list(syn_set)
                tmp['synonym'].append(synonym)
            res.append(tmp)


        else:
            intent_list = list(intent_en.keys())
            for intent in intent_list:
                sql = "SELECT * FROM %s WHERE intent_en='%s'" % (table_name, intent)
                cursor.execute(sql)
                dat = cursor.fetchall()
                tmp = {'intent': intent, "examples": []}
                for d in dat:
                    if d['question']:
                        tmp['examples'].append(d['question'])
                res.append(tmp)
        return res

    def get_base_response(self, table_name, intent_en:dict):
        db, cursor = self.get_conn(database=MYSQL_KNOWLEDGE_DATABASE)
        res = []
        if "faq" in intent_en:
            # faq中的second_label_en是一个list
            second_label_list = intent_en['faq'].get('second_label_en',[])
            for second_label_en in second_label_list:
                sql = "SELECT * FROM %s WHERE second_label_en='%s'" % (table_name, second_label_en)
                cursor.execute(sql)
                dat = cursor.fetchall()
                tmp = {'intent':'utter_faq/{}'.format(second_label_en),"text":[]}
                for d in dat:
                    if d['response']:
                        tmp['text'].append(d['response'])
                res.append(tmp)

        else:
            intent_list = list(intent_en.keys())
            for intent in intent_list:
                sql = "SELECT * FROM %s WHERE intent_en='%s'" % (table_name, intent)
                cursor.execute(sql)
                dat = cursor.fetchall()
                tmp = {'intent': "utter_{}".format(intent), "text": []}
                for d in dat:
                    if d['response']:
                        tmp['text'].append(d['response'])
                res.append(tmp)
        return res