# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/17 5:30 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import uuid
from flask_login import UserMixin
# from werkzeug.security import generate_password_hash

users = [
    {'id':'planet', 'shopname':'planet', 'username': 'Tom', 'password': '111111'},
    {'id':'yunjing', 'shopname':'yunjing', 'username': 'Michael', 'password': '123456'}
]

class User(UserMixin):
    """用户类"""

    def __init__(self, user):
        self.shopname = user.get('shopname')
        self.username = user.get("username")
        self.password_hash = user.get("password")
        self.id = user.get("id")

    def verify_password(self, password):
        """密码验证"""
        if self.password_hash is None:
            return False
        return self.password_hash==password

    def get_id(self):
        """获取用户ID"""
        return self.id

    @staticmethod
    def get(user_id):
        """根据用户ID获取用户实体，为 login_user 方法提供支持"""
        if not user_id:
            return None
        for user in users:
            if user.get('id') == user_id:
                return User(user)
        return None

def create_user(shop_name, password):
    """创建一个用户"""
    user = {
        "name": shop_name,
        "password": password,
        "id": uuid.uuid4()
        # "password": generate_password_hash(password),
        # "id": uuid.uuid4()
    }
    users.append(user)

def query_user(user_id):
    for user in users:
        if user_id == user['id']:
            return user
