# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/24 11:26 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""

def clear_yml(datadir, pattern):
    """
    对目录中文件按照正则方式递归清理
    :param datadir: 需要清理yml文件所在的目录
    :param pattern: 正则表达式pattern
    :return: 清除的文件名列表
    """
    pass

def generate_nlu_data(savedir, shop_name, inherit_tag):
    """
    对不同的商户生成相应的nlu训练数据，并且继承base数据库中的一些问题
    :param savedir: 需要保存的路径
    :param shop_name: 商户名
    :param inherit_tag: 需要继承的问题tag
    :return: 生成文件名列表
    """
    pass

def generate_response_data(savedir, shop_name, inherit_tag):
    """

    :param savedir:
    :param shop_name:
    :param inherit_tag:
    :return:
    """
    pass

def generate_domain(external_info, shop_name, inherit_tag):
    """
    根据商家的nlu的数据生成domain文件
    :param savedir:
    :param shop_name:
    :param inherit_tag:
    :return:
    """
    pass
