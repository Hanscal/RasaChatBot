# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/15 11:16 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import os
import logging

proj_root = os.path.dirname(os.path.dirname(__file__))

# 初始化日志引擎
def get_logger(logger_name, log_file, level=logging.INFO):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s',
                                  datefmt='%a, %d %b %Y %H:%M:%S')
    fh = logging.FileHandler(encoding='utf-8', mode='a', filename=log_file)
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(logging.DEBUG)
    logger = logging.getLogger(logger_name)
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.setLevel(level)
    return logger


# 评论数据和回复数据交互库
MYSQL_HOST = '113.31.111.86'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'rasa@unidt'
MYSQL_PORT = 48036

MYSQL_DATABASE = 'vc'


# 其他额外设置
base_tag_map = {'intent':'打招呼'}