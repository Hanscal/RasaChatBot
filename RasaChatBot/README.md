
# 创建项目一般步骤
1. 初始化项目(rasa init);  
2. 准备NLU数据(data/nlu.yml);  
3. 配置NLU模型(config.yml--pipline)。  
4. 准备故事数据(data/stories.yml);  
5. 定义领域(domain.yml);  
6. 配置rasa core模型(config.yml--policies)；  
7. 训练模型；  
8. 测试机器人； 

# 项目快速启动
1. rasa data validate [对标注数据进行检查]  
2. rasa train (train both nlu and core) [同时训练NLU模块和Core模块]  
3. rasa run actions (optional) if you redefined actions [如果没有定义actions，这个步骤可以跳过]  
4. rasa run --cors "*" --enable-api [使得可以通过web和api来访问服务] 
5. python start_service.py [启动服务]  

**下面两个步骤可能在debug或评估时会用到**
1. rasa shell (interactive with chat bot) [与训练的机器人交互，debug的时候使用]  
2. rasa evaluate markers all out.csv (evaluate chat bot) [评估部分，前期可略过]

## 训练模型参数介绍 
```
用法: rasa train [-h] [-v] [-vv] [--quiet] [--data DATA [DATA ...]]
                  [-c CONFIG] [-d DOMAIN] [--out OUT]
                  [--augmentation AUGMENTATION] [--debug-plots]
                  [--dump-stories] [--fixed-model-name FIXED_MODEL_NAME]
                  [--force]
                  {core,nlu} ...

位置参数:
{core,nlu}
    core        使用你的故事训练Rasa Core模型
    nlu         使用你的NLU数据训练Rasa NLU模型

可选参数:
 -h, --help     显示帮助消息并退出。
 --data DATA [DATA ...]
                Core和NLU数据文件的路径。(默认：['data'])
 -c CONFIG, --config CONFIG
                机器人的策略和NLU管道配置。(默认：config.yml)
 -d DOMAIN, --domain DOMAIN
                域规范(yml文件)。(默认：domain.yml)
 --out OUT      存储模型的目录。(默认：models)
 --augmentation AUGMENTATION
                在训练期间使用多少数据扩充。(默认值：50)
 --debug-plots  如果启用，将创建展示检查点( checkpoints)和它们在文件(`story_blocks_connections.html`)中的故事块之间的联系的图表。(默认：False)
 --dump-stories 如果启用，将展开的故事保存到文件中。(默认：False)
 --fixed-model-name FIXED_MODEL_NAME
                如果设置，则模型文件/目录的名称将为设置为给定的名称。(默认：None)
 --force        即使数据没有改变，也强制进行模型训练。(默认值：False)

Python日志选项:
 -v, --verbose  详细输出。将日志记录级别设置为INFO。(默认：None)
 -vv, --debug   打印大量的调试语句。设置日志记录级别为 DEBUG。(默认：None)
 --quiet        将日志记录级别设置为WARNING。(默认：None)   
```

## 启动服务参数介绍  
```
用法: rasa run [-h] [-v] [-vv] [--quiet] [-m MODEL] [--log-file LOG_FILE]
                [--endpoints ENDPOINTS] [-p PORT] [-t AUTH_TOKEN]
                [--cors [CORS [CORS ...]]] [--enable-api]
                [--remote-storage REMOTE_STORAGE] [--credentials CREDENTIALS]
                [--connector CONNECTOR] [--jwt-secret JWT_SECRET]
                [--jwt-method JWT_METHOD]
                {actions} ... [model-as-positional-argument]

位置参数:  
 {actions}
    actions     运行操作服务(action server)。
 model-as-positional-argument
                已训练的Rasa模型的路径。如果目录指定，它将使用目录中的最新的模型。(默认：None)

可选参数:
 -h, --help     显示帮助消息并退出。
 -m MODEL, --model MODEL
                已训练的Rasa模型的路径。如果目录指定，它将使用目录中的最新的模型。(默认：None)     
 --log-file LOG_FILE
                将日志存储在指定文件中。(默认：None)       
 --endpoints ENDPOINTS
                模型服务和连接器的配置文件为yml文件。(默认：None)

Python日志选项:
 -v, --verbose  详细输出。将日志记录级别设置为INFO。(默认：None)
 -vv, --debug   打印大量的调试语句。设置日志记录级别为 DEBUG。(默认：None)
 --quiet        将日志记录级别设置为WARNING。(默认：None) 

服务设置:
 -p PORT, --port PORT
                用于运行服务的端口。(默认值：5005)   
 -t AUTH_TOKEN, --auth-token AUTH_TOKEN
                启用基于令牌的身份验证，请求需要提供可被接受的令牌。(默认：None)
  --cors [CORS [CORS ...]]
                为传递的来源启用CORS。使用`*`将所有来源添加到白名单。(默认：None)
 --enable-api
                除输入渠道外，还启动Web服务API渠道。(默认值：False)
 --remote-storage REMOTE_STORAGE
                设置Rasa模型所在的远程存储位置，例如在AWS上。(默认：None)

渠道(Channels):
 --credentials CREDENTIALS
               连接器的身份验证凭据为yml文件。(默认：None)
 --connector CONNECTOR
                连接的服务。 (默认: None)

JWT身份验证:
 --jwt-secret JWT_SECRET
                非对称JWT方法的公钥或对称方法的共享机密。还请确保使用 --jwt-method 选择签名方法，否则这个参数将被忽略。(默认：None)
--jwt-method JWT_METHOD
                用于JWT的认证负载签名的方法。(默认：HS256)
``` 
