# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/18 5:29 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import json
import requests

def synthesize_audio(text):
    """念出昵称和打招呼话术"""
    audio_url = "http://113.31.111.86:19034/synthesize_single"
    dic = {"task_id": "sitong",
           "text": text,
           "speech_control": 1.0,
           "volume_control": 100}
    res = requests.post(audio_url, data=json.dumps(dic))
    response = res.json()['data']
    return response

def get_personality(nickname):
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

    text_list = []
    url = "http://113.31.111.86:19068/personality"
    dic = {"nickname": nickname}
    res = requests.post(url, data=json.dumps(dic))
    result_dic = res.json()

    if result_dic['msg'] == 'success':
        personality = result_dic['result']
        for key in personality.keys():
            if abs(personality[key]) == 1:
                text_list.extend(text_dic[key])
    return text_list

def get_nlu_theme(text):
    """定时轮询数据库中数据，返回分类结果"""
    url = "http://113.31.111.86:48088/nlu_parse_api"
    dic = {"message": text}
    res = requests.post(url, data=json.dumps(dic))
    result_dic = res.json()
    return result_dic

if __name__ == '__main__':
    res = get_nlu_theme('你好')