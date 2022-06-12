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
* 实现自定义tokenizer，解决实体边界冲突--20220523  
* 实现训练数据、回复、故事从库中的自动生成--20220610

## 学习资料
1. [官方文档](https://rasa.com/blog/what-s-ahead-in-rasa-open-source-3-0/)
2. [YouTube官方视频](https://www.youtube.com/channel/UCJ0V6493mLvqdiVwOKWBODQ)
3. [快速入门讲解英文](https://www.youtube.com/watch?v=PfYBXidENlg)
4. [快速入门项目中文](https://github.com/Chinese-NLP-book/rasa_chinese_book_code)


## 下一步工作 
### Entity
1. 对于明确的实体进行定义，并且作出有针对性的回答。
2. 对于定义的商品属性进行映射或者正则匹配，以在库中进行准确查找。
 
### Action
1. 进行数据校验, 和数据交互，采用MySQL存储FQA数据，通过接口实现功能分离；  
2. 与数据库(Neo4j)进行交互，更多的实体和关系属性定义. 

### NLU
1. 自定义NLU组件，以JointBERT替换DIET组件；
2. 对训练数据自动进行数据增强处理。

### Interactive Learning
1. 交互式学习，提供反馈并修正错误；
2. RASA-X 1.1进行集成；

### Deploy
1. 模型部署与负载均衡，使用docker-compose对容器自动编排和管理；
2. 服务访问方式。

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