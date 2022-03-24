# OverView
**一个基于Rasa3.0+的中文对话机器人, 一方面支持知识问答，另一方面支持智能闲聊**

# 创建项目一般步骤
1. 初始化项目(rasa init);  
2. 准备NLU数据(data/nlu.yml);  
3. 配置NLU模型。  
4. 准备故事数据(data/stories.yml);  
5. 定义领域(domain.yml);  
6. 配置rasa core模型；  
7. 训练模型；  
8. 测试机器人； 

# 项目快速启动
1. rasa data validate [对标注数据进行检查]  

        用法: rasa data validate [-h] [-v] [-vv] [--quiet] [-d DOMAIN] [--data DATA]
        
        可选参数: 
         -h, --help     显示帮助消息并退出。
         -d DOMAIN, --domain DOMAIN
                        域规范(yml文件)。(默认:domain.yml)
        --data DATA     包含Rasa数据的文件或目录。(默认:data)  
        
        Python日志选项:
         -v, --verbose  详细输出。将日志记录级别设置为INFO。(默认:None)
         -vv, --debug   打印大量的调试语句。设置日志记录级别为 DEBUG。(默认:None)
         --quiet        将日志记录级别设置为WARNING。(默认:None)

2. rasa train (train both nlu and core) [同时训练NLU模块和Core模块]  
3. rasa run actions (optional) if you redefined actions [如果没有定义actions，这个步骤可以跳过]  
4. rasa run -m models --endpoints endpoints.yml (run the rasa bot) [或者直接运行rasa run]   
5. rasa shell (interactive with chat bot) [与训练的机器人交互]  
6. rasa evaluate markers all out.csv (evaluate chat bot) [评估部分，前期可略过]

## 学习资料
1. [官方文档](https://rasa.com/blog/what-s-ahead-in-rasa-open-source-3-0/)
2. [YouTube官方视频](https://www.youtube.com/channel/UCJ0V6493mLvqdiVwOKWBODQ)
3. [快速入门讲解英文](https://www.youtube.com/watch?v=PfYBXidENlg)
4. [快速入门项目中文](https://github.com/Chinese-NLP-book/rasa_chinese_book_code)

# CHANGELOG
* 实现闲聊功能API接入--20220325
* 实现neo4j知识库功能接入--20220318


## 下一步工作 
### Entity
1. 对于明确的实体进行定义，并且作出有针对性的回答。
 
### Action
1. 进行数据校验, 和数据交互，采用MySQL存储FQA数据，通过接口实现功能分离；  
2. 与数据库(Neo4j)进行交互，更多的实体和关系属性定义. 

### Tokenizer
1. 自定义分词器，实现实体边界的覆盖；

### Interactive Learning
1. 交互式学习，提供反馈并修正错误；

### Deploy
1. 模型部署与负载均衡；
2. 服务访问方式。
