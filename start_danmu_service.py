# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/14 2:32 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import json
import os
import random
from datetime import datetime

from flask import Flask, request
from flask_cors import CORS

from scripts.mysql_opt import LiveDB
from scripts.external_service import synthesize_audio, get_personality
from config.config import get_logger, proj_root
logger = get_logger('danmu', os.path.join(proj_root, '../log/live_danmu.log'))

app = Flask(__name__,template_folder='templates',static_folder='static')
CORS(app, supports_credentials=True)

live_db = LiveDB()

@app.route('/know_send', methods=['POST'])
def know_send():
    """
    前端调用接口将评论数据插入到数据库
        路径：/know_send
        请求方式：POST
        请求参数：b_id, room_name, room_id, room_type, user_id, live_id, content, publish_time, publisher_nick\
        label, version
    :return: 响应数据状态 200为成功，400为不成功
    """
    ret = {'code': '400'}
    if request.method == 'POST':
        try:
            js = request.get_json(force=True)
            b_id = js.get('b_id')
            room_name = js.get('room_name')
            room_id = js.get('room_id')
            room_type = js.get('room_type')
            user_id = js.get('user_id')
            live_id = js.get('live_id')
            content = js.get('content')
            publish_time = js.get('publish_time')
            publisher_nick = js.get('publisher_nick')
            label = js.get('label')
            now = datetime.now()
            version = js.get('version')
            db, cursor = live_db.get_conn()
            if version:
                try:
                    sql2 = "insert into danmu(b_id,room_name,room_id,room_type,user_id,live_id,content,publish_time,publisher_nick,label,date,version) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    cursor.execute(sql2, (b_id,room_name,room_id,room_type,user_id,live_id,content,publish_time,publisher_nick,label,now,version))
                except Exception as e:
                    logger.error(e)
                    db.rollback()
                    logger.error("know_send comment insertion error")
                else:
                    db.commit()
                    logger.info("know_send comment inserted")
            else:
                try:
                    sql1 = "insert into danmu(b_id,room_name,room_id,room_type,user_id,live_id,content,publish_time,publisher_nick,label,date) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    cursor.execute(sql1, (b_id,room_name,room_id,room_type,user_id,live_id,content,publish_time,publisher_nick,label,now))
                except Exception as e:
                    logger.error(e)
                    db.rollback()
                    logger.error("know_send comment insertion error")
                else:
                    db.commit()
                    logger.info("know_send comment inserted")

            cursor.close()
            db.close()

            ret = {'code': '200'}
        except Exception as e:
            logger.error(e)
            logger.info("know_send comment insertion error")
    return json.dumps(ret, ensure_ascii=False)


@app.route('/know_open', methods=['POST'])
def know_open():
    """
    记录打开知识库时发送给嘉道的爬虫请求
        路径：/know_open
        请求方式：POST
        请求参数：b_id, room_name, room_id, room_type, user_id, live_id, content, publish_time, publisher_nick\
        label, version
    :return: 响应数据状态 200为成功，400为不成功
    """
    ret = {'code': '400', "msg":"请求方法必须为POST！"}
    if request.method == 'POST':
        params = request.get_json(force=True)
        jstr = str(params)
        ret = {"code": "200", "msg":"know_open request received"}

        logger.info("know_open request received")
        logger.info("know_open_log:"+str(datetime.now()) + '|' + jstr + '|' + str(ret) + '\n')
    return json.dumps(ret, ensure_ascii=False)


@app.route('/tag_fetch', methods=['POST'])
def tag_fetch():
    """
    记录打开知识库时发送给嘉道的爬虫请求
        路径：/tag_fetch
        请求方式：POST
        请求参数：b_id, room_type
    :return: 响应数据状态 200为成功，400为不成功
    """
    ret = {'code': '400', "msg":"请求方法必须为POST！"}
    jstr = ''
    if request.method == 'POST':
        try:
            js = request.get_json(force=True)
            jstr = str(js)
            bid = js.get('b_id')
            room_type = js.get('room_type')

            now = datetime.now()
            recent_response_detected = live_db.detect_recent_response(bid)
            """符合规则返回False，否则返回True。已去除回答间隔2分钟的限制"""
            if recent_response_detected:
                ret = {
                    "code": "200",
                    "task_list": []
                }
                logger.info("tag_fetch no answerable comment")
            else:
                sql_cha = "select uid,video_id,confidence,date,theme,link,content,answer,publisher_nick" \
                          " from danmu where answerable=1 and b_id={} and room_type={} and version != 1" \
                          " and is_published=0".format(bid,room_type)
                sql_update = "update danmu set is_published=1 where uid={}"
                db, cursor = live_db.get_conn()
                cursor.execute(sql_cha)
                dat = cursor.fetchall()
                l = []
                for it in dat:
                    uid = it['uid']
                    confidence = it['confidence']
                    content = it['content']
                    answer = it['answer']
                    link = it['link']
                    publisher_nick = it['publisher_nick']
                    try:
                        cursor.execute(sql_update.format(uid))
                    except Exception as e:
                        logger.info(e)
                        db.rollback()
                    else:
                        db.commit()

                    try:
                        q = now - it['date']
                    except:
                        continue

                    if q.seconds > 300:
                        """5分钟以外的评论不理会"""
                        continue

                    theme = it['theme']
                    recent_response_theme_detected = live_db.detect_recent_response(bid, theme=theme)
                    if recent_response_theme_detected:
                        """1分钟之内不发同一类型，欢迎类型除外"""
                        continue

                    if theme == '产品讲解' and len(str(link)) > 0:
                        #识别出了评论要求讲解的产品链接号
                        l.append((theme, confidence, uid, content, answer, link, publisher_nick))
                    else:
                        l.append((theme, confidence, uid, content, answer, '', publisher_nick))

                if len(l) > 0:
                    l.sort(key=lambda t: t[1]) #按照置信度从低到高排序
                    b, c, d, e, f, g, h = l[-1]  # theme, confidence, uid, content, answer, link, publisher_nick
                    if b == '欢迎':
                        #返回小挂件所需的wav
                        text_list = get_personality(nickname=h)

                        if len(text_list) > 0:
                            text = h + random.choice(text_list)
                            """念出昵称和打招呼话术"""
                            response = synthesize_audio(text)
                            audio_url = response['speech_url']
                            duration = response['duration']

                            ret = {
                                "code": "200",
                                "task_list": [{
                                    "b_id": bid,
                                    "tag": "欢迎",
                                    "room_type": room_type,
                                    "image_id": "1",
                                    "content": e,
                                    "answer": text,
                                    "type": "wav",
                                    "audio_url": audio_url,
                                    "duration": duration,
                                    "progress": "100",
                                    "create_time": str(now),
                                    "has_link": "0",
                                    "link": "",
                                    "publisher_nick": str(h)
                                }]
                            }
                            logger.info("tag_fetch comment responded by audio", model_name="None")
                    else:
                        #返回标签值
                        if g == '':
                            ret = {
                                "code": "200",
                                "task_list": [{
                                    "b_id": bid,
                                    "tag": b,
                                    "room_type": room_type,
                                    "image_id": "1",
                                    "content": e,
                                    "answer": str(f),
                                    "type": "mp4",
                                    "audio_id": "0",
                                    "progress": "100",
                                    "create_time": str(now),
                                    "has_link":"0",
                                    "link":"",
                                    "publisher_nick": str(h)
                                }]
                            }
                            logger.info("tag_fetch comment responded", model_name="None")

                        else:
                            ret = {
                                "code": "200",
                                "task_list": [{
                                    "b_id": bid,
                                    "tag": b,
                                    "room_type": room_type,
                                    "image_id": "1",
                                    "content": e,
                                    "answer": str(f),
                                    "type": "mp4",
                                    "audio_id": "0",
                                    "progress": "100",
                                    "create_time": str(now),
                                    "has_link": "1",
                                    "link": str(g),
                                    "publisher_nick": str(h)
                                }]
                            }
                            logger.info("tag_fetch comment responded", model_name="None")
                else:
                    ret = {
                        "code": "200",
                        "task_list": []
                    }
                    logger.info("tag_fetch no answerable comment")

                cursor.close()
                db.close()
        except Exception as e:
            logger.error(e)
            logger.error("tag_fetch comment response error")
        resp = json.dumps(ret, ensure_ascii=False)
        logger.info("know_fetch_log:"+str(datetime.now()) + '|' + jstr + '|' + resp + '\n')
        return resp

if __name__ == '__main__':
    # 启动服务，开启多线程模式
    app.run(
        host='0.0.0.0',
        port=8089,
        threaded=True,
        debug=False
    )