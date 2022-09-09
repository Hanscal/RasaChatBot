import copy
import json
import time

import requests

# API Key
API_KEY = "uy9jpgMbL3Igb3Lm4ib9GPrf"
SECRET_KEY = "NKCSc2aTswGRrq3tZgCULrP7PVdWSOHj"
AppID = "27253768"
ROBOT_ID = "S74474"
post_data = {
    "version": "3.0",
    "service_id": ROBOT_ID,
    "session_id": "",
    "log_id": "77585210",
    "request": {"terminal_id": "88888", "query": ""},
}

headers = {"content-type": "application/json"}


def get_access_token():
    """  
    :return: 获取包涵有效access_token的url 
    先前url不会失效，access_token有效期三十天
    """
    host = "https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={}&client_secret={}".format(
        API_KEY, SECRET_KEY
    )
    response = requests.get(host)
    access_token = response.json()["access_token"]
    url = (
        "https://aip.baidubce.com/rpc/2.0/unit/service/v3/chat?access_token="
        + access_token
    )
    return url


global url
session_id_dict = {}
url = get_access_token()
t0 = time.time()


def chitchat_api(user_name, text_in, url=url, time_out=300):
    """  
    :param user_name: 用户id 形式product_id:user_id
    :param text_in: 自然语言文本
    :return:  json格式响应数据
    """
    global t0
    global session_id_dict
    t1 = time.time()
    if t1 - t0 > time_out:
        t0 = t1
        session_id_dict = {}
    # user_id = user_name.split(":")[-1]s
    session_id = session_id_dict.get(user_name, "")
    # print(session_id)
    data_json = copy.deepcopy(post_data)
    data_json["session_id"] = session_id
    data_json["request"]["query"] = text_in
    # data_json['skill_ids'] =  ["1229108"]
    tmp = requests.post(url, data=json.dumps(data_json), headers=headers)
    answer = tmp.json()
    if not answer.get("result", {}).get("responses", []):
        url = get_access_token()
        tmp = requests.post(url, data=json.dumps(data_json), headers=headers)
        answer = tmp.json()
        try:
            response = answer["result"]["responses"][0]["actions"][0]["say"]
            session_id = answer["result"]["session_id"]
            # print(session_id)
            if user_id not in session_id_dict:
                session_id_dict[user_id] = session_id
        except:
            response = ""
    else:
        if answer["result"]["responses"][0]["actions"] and answer["result"]["responses"][0]["actions"][0]["say"]:
            response = answer["result"]["responses"][0]["actions"][0]["say"]
            session_id = answer["result"]["session_id"]
            # print(session_id)
            if user_name not in session_id_dict:
                session_id_dict[user_name] = session_id
        else:
            response = ""
    return {"response": response}
    # return json.dumps({"response": response},ensure_ascii=False)