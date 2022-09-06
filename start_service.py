# -*- coding: utf-8 -*-

"""
@Time    : 2022/3/25 8:35 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import os
import time
import uuid
import json

from flask import Flask, request, redirect, url_for, render_template, flash, session
from flask_cors import CORS
from flask_wtf import FlaskForm
from flask_login import LoginManager, login_user, logout_user, login_required
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

from scripts.user_model import User, query_user
from scripts.chat_request import requestServerbot, requestRasabot
from scripts.external_service import know_similarity, request_chitchat

# from config.config import get_logger, proj_root
# logger = get_logger('live', os.path.join(proj_root, 'log/live_assistant.log'))

# 改成unidt log
from config.config import UniLog, proj_root
logger = UniLog('live service', os.path.join(proj_root, 'log/live_assistant.log'))


app = Flask(__name__,template_folder='templates',static_folder='static')
CORS(app, supports_credentials=True)
app.secret_key = '1234567'

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = '请登录'
login_manager.init_app(app)


@app.route('/live_assistant_api', methods=['POST'])
def live_assistant_api():
    """
    前端调用接口
        路径：/live_assistant_api
        请求方式：POST
        请求参数：user_name, shop_name, message
    :return: response rasa响应数据
    """
    b0 = time.time()
    response = ''
    intent_name = None
    intent_confidence = None
    entities = []
    if request.method == 'POST':
        data_json = request.get_json(force=True)
        entities, intent_confidence, intent_name, response = requestServerbot(data_json)
        intent_confidence = round(intent_confidence, 2) if intent_confidence is not None else intent_confidence
    else:
        logger.error("only support post method!")
    logger.info("response: {}".format(response))
    logger.info('total costs {:.2f}s'.format(time.time() - b0), model_name='live_assistant_api')
    return json.dumps({"response":response, "intent":{"name":intent_name, "confidence":intent_confidence}, "entities":entities},ensure_ascii=False)


@app.route('/nlu_parse_api', methods=['POST'])
def nlu_parse_api():
    """
    前端调用接口
        路径：/nlu_parse_api
        请求方式：POST
        请求参数：user_name, shop_name, message
    :return: response rasa响应数据
    """
    b0 = time.time()
    response = {}
    if request.method == 'POST':
        data_json = request.get_json(force=True)
        message_input = data_json['message']
        message_id = str(uuid.uuid5(uuid.NAMESPACE_DNS,message_input))
        response = requestRasabot(url='model/parse', params={'text':message_input, "message_id":message_id}, method='post')
        response = json.loads(response)
    else:
        logger.error("only support post method!")
    logger.info('total costs {:.2f}s'.format(time.time() - b0), model_name='nlu_parser')
    return json.dumps({"response":response},ensure_ascii=False)


@app.route('/rasa_parse_api', methods=['POST'])
def rasa_parse_api():
    """
    前端调用接口
        路径：/rasa_parse_api
        请求方式：POST
        请求参数：url, params, method
    :return: response rasa响应数据
    """
    b0 = time.time()
    response = ''
    if request.method == 'POST':
        data_json = request.get_json(force=True)
        url = data_json['url']
        params = data_json.get('params',{})
        method = data_json.get('method','post')
        response = requestRasabot(url, params, method)
    else:
        logger.info("only support post method!")
    logger.info("response: {}".format(response))
    logger.info('total costs {:.2f}s'.format(time.time() - b0))
    return json.dumps({"response":response},ensure_ascii=False)


@app.route('/live_assistant_ui', methods=['GET','POST'])
@login_required
def live_assistant_ui():
    """
    前端调用接口
        路径：/ai
        请求方式：GET、POST
        请求参数：question
    :return: response rasa响应数据
    """
    shop_name = session.get('shopname','')
    user_name = session.get('username','')
    username = "登录用户: "+user_name+" ("+shop_name+")" if shop_name and user_name else None
    if not user_name:
        logger.info('用户登录失效，请重新登录！')
        return redirect(url_for('login'))
    if request.method == 'POST':
        b0 = time.time()
        question = request.form["question"]
        data_json = {"message":question,"user_name":user_name,"shop_name":shop_name}
        shop_name_map = {"yunjing":"10010", 'qinyuan':"10012", "planet":"10007"}
        faq_dict = know_similarity(text=question,b_id=shop_name_map.get(shop_name.lower(), '0'))
        faq_confidence = faq_dict['confidence']
        if faq_confidence > 0.88:
            link = faq_dict['link']
            if link:
                answer = str(link)
            else:
                answer = faq_dict['answer']
        else:
            # entities, intent_confidence, intent_name, answer = requestServerbot(data_json)
            res_dic = request_chitchat(user_name, shop_name, question)
            answer = str(res_dic.get('response',''))

        # intent_confidence = round(intent_confidence, 2) if intent_confidence is not None else intent_confidence
        logger.info("response: {}".format(answer))
        logger.info('total costs {:.2f}s'.format(time.time() - b0), model_name='live_assistant_ui')
        # answer = str({"response":answer,"intent":{"name":intent_name, "confidence":intent_confidence}, "entities":entities, "faq_match":faq_dict})
        return json.dumps({'answer': answer},ensure_ascii=False)

    return render_template("chat.html", username=username)

@app.route('/')
def index():
    return redirect(url_for('login'))

# 用户登录控制
class LoginForm(FlaskForm):
    """登录表单类"""
    shopname = StringField('商铺名', validators=[DataRequired()])
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == "POST":
        shop_name = request.form["shopname"]
        user_name = request.form["username"]
        password = request.form["password"]
        user_info = query_user(shop_name)  # 从用户数据中查找用户记录
        if user_info is None:
            emsg = "用户名或密码密码有误"
        else:
            user = User(user_info)  # 构建用户实体
            if user.verify_password(password):  # 校验密码
                login_user(user)  # 创建用户 Session
                session['shopname'] = user.shopname
                session['username'] = user_name
                return redirect(request.args.get('next') or url_for('live_assistant_ui'))  # request.args.get('next') or
            else:
                emsg = "用户名或密码密码有误"
        flash(message=emsg)
        logger.error(emsg)
    return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # 启动服务，开启多线程模式
    app.run(
        host='0.0.0.0',
        port=8088,
        threaded=True,
        debug=False
    )