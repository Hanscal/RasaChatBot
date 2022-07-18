# -*- coding: utf-8 -*-

"""
@Time    : 2022/7/14 6:11 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import re
import os
import pymysql

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
            return ques  # none
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
