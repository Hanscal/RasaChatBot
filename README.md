# OverView
**一个基于Rasa3.0+的中文对话机器人, 一方面支持知识问答，另一方面支持智能闲聊**

# procedure
1. 初始化项目(rasa init);  
2. 准备NLU数据(data/nlu.yml);  
3. 配置NLU模型。  
4. 准备故事数据(data/stories.yml);  
5. 定义领域(domain.yml);  
6. 配置rasa core模型；  
7. 训练模型；  
8. 测试机器人； 

# main procedure
1. rasa data validate

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

2. rasa train (train both nlu and core)  
3. rasa run actions (optional) if you redefined actions, 
4. rasa run -m models --endpoints endpoints.yml (run the rasa bot)  
5. rasa shell (interactive with chat bot)
6. rasa evaluate markers all out.csv (evaluate chat bot) 


## TODO 
###  Action
1. 进行数据校验, 和数据交互，采用MySQL存储FQA数据，通过接口实现功能分离；  
2. 采用Py2Neo与数据库(Neo4j)进行交互. 

### Tokenizer
1. 自定义分词器，实现实体边界的覆盖；

### Interactive Learning
1. 交互式学习，提供反馈并修正错误；

### Deploy
1. 模型部署与负载均衡；
2. 服务访问方式。
