# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/14 2:32 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""

import tornado.web
import tornado.ioloop
import json
import uuid
import random

import requests
import os
from datetime import datetime
from unidt_log import logger

from scripts.mysql_opt import LiveDB


live_db = LiveDB()



sql1 = "insert into danmu(b_id,room_name,room_id,room_type,user_id,live_id,content,publish_time,publisher_nick,label,date) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
sql2 = "insert into danmu(b_id,room_name,room_id,room_type,user_id,live_id,content,publish_time,publisher_nick,label,date,version) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"

class KnowSendHandler(tornado.web.RequestHandler):

    def post(self, *args):
        self.set_header('Content-Type', 'application/json')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'Content-Type')
        self.set_header('Access-Control-Allow-Methods', 'POST')

        try:

            params = self.request.body
            jstr = params.decode('utf-8')
            js = json.loads(jstr)

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

            db,cursor = live_db.get_conn()
            if version:
                try:
                    cursor.execute(sql2, (b_id,room_name,room_id,room_type,user_id,live_id,content,publish_time,publisher_nick,label,now,version))
                except Exception as e:
                    print(e)
                    db.rollback()
                    logger.error("know_send comment insertion error", model_name="None", prod_name="数字人评论互动")
                else:
                    db.commit()
                    logger.info("know_send comment inserted", model_name="None")
            else:
                try:
                    cursor.execute(sql1, (b_id,room_name,room_id,room_type,user_id,live_id,content,publish_time,publisher_nick,label,now))
                except Exception as e:
                    print(e)
                    db.rollback()
                    logger.error("know_send comment insertion error", model_name="None", prod_name="数字人评论互动")
                else:
                    db.commit()
                    logger.info("know_send comment inserted", model_name="None")

            cursor.close()
            db.close()

            ret = {'code': '200'}
        except Exception as e:
            print(e)
            ret = {'code': '400'}
            logger.error("know_send comment insertion error", model_name="None", prod_name="数字人评论互动")

        self.write(json.dumps(ret, ensure_ascii=False))


class KnowOpenHandler(tornado.web.RequestHandler):
    """
    记录打开知识库时发送给嘉道的爬虫请求
    """
    def post(self, *args):
        self.set_header('Content-Type', 'application/json')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'Content-Type')
        self.set_header('Access-Control-Allow-Methods', 'POST')

        params = self.request.body
        jstr = params.decode('utf-8')

        ret = {
            "code": "200"
        }
        logger.info("know_open request received", model_name="None")

        resp = json.dumps(ret, ensure_ascii=False)
        with open('know_open_log.txt', 'a') as f:
            f.write(str(datetime.now()) + '|' + jstr + '|' + resp + '\n')
        self.write(resp)




text_dic = {'O': ["嗨！抓住你了，猜猜我和主播还有什么技能？多发评论有彩蛋哟",
                  "欢迎你！我猜你是小姐姐，猜对了的话，要给我点小红心哟，不许抵赖！咩！"],
            'C': ["你好呀！有问题可以发在评论中，多利和主播会努力回答的！",
                  "欢迎进入直播间。多利隔着屏幕就看出你是个靠谱的人，巧了 ，我也是。咩！"],
            'E': ["你来啦？我看你骨骼清奇颇有领袖气质，快帮我转发分享吧家人。",
                  "恭喜你！发现了我们这个宝藏直播间！大家一起欢迎他！呜呼"],
            'A': ["你好咩？多利嗅出了你是个温柔的人，想用软敷敷的羊毛蹭蹭你。",
                  "欢迎进来，好心人，可以帮我点点右边小红心吗？多利手太短了，够不着。"],
            'N': ["欢迎进到直播间。多利发现你是个内心细腻的人，没说错吧？",
                  "欢迎进入直播间，最近生活是不是有些焦虑？多来直播间放松一下吧。"]}

class TagFetchHandler(tornado.web.RequestHandler):
    """
    前端每3秒循环调用此接口
    """
    def post(self, *args):
        self.set_header('Content-Type', 'application/json')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'Content-Type')
        self.set_header('Access-Control-Allow-Methods', 'POST')

        params = self.request.body
        jstr = params.decode('utf-8')
        js = json.loads(jstr)
        try:
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
                logger.info("tag_fetch no answerable comment", model_name="None")
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
                        print(e)
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
                        text_list = []

                        url = "http://113.31.111.86:19068/personality"
                        dic = {"nickname": h}
                        res = requests.post(url, data=json.dumps(dic))
                        result_dic = res.json()

                        if result_dic['msg'] == 'success':
                            personality = result_dic['result']
                            for key in personality.keys():
                                if abs(personality[key]) == 1:
                                    text_list.extend(text_dic[key])

                        if len(text_list) > 0:
                            text = h + random.choice(text_list)
                            """念出昵称和打招呼话术"""
                            audio_url = "http://113.31.111.86:19034/synthesize_single"
                            dic = {"task_id": "sitong",
                                   "text": text,
                                   "speech_control": 1.0,
                                   "volume_control": 100}
                            res = requests.post(audio_url, data=json.dumps(dic))
                            response = res.json()['data']

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
                    logger.info("tag_fetch no answerable comment", model_name="None")

                cursor.close()
                db.close()
        except Exception as e:
            print(e)
            ret = {'code': '400'}
            logger.error("tag_fetch comment response error", model_name="None", prod_name="430版本数字人评论互动")
        resp = json.dumps(ret, ensure_ascii=False)
        with open('log.txt', 'a') as f:
            f.write(str(datetime.now()) + '|' + jstr + '|' + resp + '\n')
        self.write(resp)



def get_app():
    return tornado.web.Application([(r'/know_send',KnowSendHandler),(r'/know_fetch',KnowFetchHandler),
                                    (r'/know_get',KnowGetHandler),(r'/know_direct',KnowDirectHandler),
                                    (r'/know_fetch_room',KnowFetchRoomHandler),(r'/know_open',KnowOpenHandler),
                                    (r'/tag_fetch',TagFetchHandler)],
                                   static_path=os.path.join(os.getcwd(), '../static'))
