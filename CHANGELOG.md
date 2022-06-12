<h1 align="center"><a href="https://github.com/Hanscal/RasaChatBot" target="_blank">RasaChatBot</a></h1>


<p align="center">
  <a href="https://github.com/Hanscal/RasaChatBot/stargazers"><img alt="star" src="https://img.shields.io/github/stars/Hanscal/RasaChatBot.svg?label=Stars&style=social"/></a>
  <a href="https://github.com/Hanscal/RasaChatBot/network/members"><img alt="star" src="https://img.shields.io/github/forks/Hanscal/RasaChatBot.svg?label=Fork&style=social"/></a>
  <a href="https://github.com/Hanscal/RasaChatBot/watchers"><img alt="star" src="https://img.shields.io/github/watchers/Hanscal/RasaChatBot.svg?label=Watch&style=social"/></a>
  
</p>

# OverView
**一个基于Rasa3.0+的中文对话机器人, 一方面支持知识问答，另一方面支持智能闲聊**

# v1.0.0
20220610  
此版本对应于平台版本为 v100

## 简介

- 利用RASA实现了FQA基本框架的搭建；
- 在直播领域通用问题中的问答进行功能支持。
- 对于置信度比较低的问题采用闲聊进行回答，支持多人闲聊。

## 组件

- 新增: 新增对`templates/index.yml`中web界面访问的支持
- 新增: 新增对`data/nlu.yml`中FQA中问题意图识别的支持
- 新增: 新增对`data/responses.yml`中FQA回答的支持

## 主要变更

* 实现web聊天界面--20220327
* 实现闲聊功能API接入--20220325
* 实现neo4j知识库功能接入--20220318


## api和web测试
**api请求**
```python
import json
import requests
url = "http://113.31.111.86:48088/live_assistant_api"
response = requests.post(url=url, data=json.dumps({"user_name":"hanscal","message":"你好"}))
print(response.json())
```

**web测试**  
* 在浏览器中输入网址`http://113.31.111.86:48088/live_assistant_ui`  
![聊天界面](static/img/chatmessage.png)