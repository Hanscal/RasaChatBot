# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/15 11:11 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""

import pymysql
from datetime import datetime

from config.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

"""数据库相关"""
class LiveDB(object):
    def __init__(self):
        pass

    def get_conn(self):
        db = pymysql.connect(user=MYSQL_USER,password=MYSQL_PASSWORD,database=MYSQL_DATABASE,host=MYSQL_HOST,port=MYSQL_PORT)
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