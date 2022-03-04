# OverView
**一个基于Rasa3.0+的中文对话机器人, 一方面支持知识问答，另一方面支持智能闲聊**

# training procedure
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
3. rasa run -m models --endpoints endpoints.yml (run the rasa bot)  
4. rasa shell (interactive with chat bot)
5. rasa evaluate markers all out.csv (evaluate chat bot) 

## 模块化
Action - Rasa NLU - Rasa Core - Web Server

## Rasa NLU
使用自然语言理解进行意图识别和实体提取
### Example:
rquest(part)
`"张青红的生日什么时候"`

response
```json
{
  "intent": "view_defendant_data",
  "entities": {
    "defendant" : "张青红",
    "item" : "生日"
  }
}
```
### Pipeline
假设我们在config文件中这样设置pipeline`"pipeline": ["Component A", "Component B", "Last Component"]`

### Training


## Rasa Core
用于对话管理

### Pipeline
1. Rasa_Core首先接收到信息, 将信息传递给`Interpreter`, `Interpreter`将信息打包为一个字典(`dict`), 这个`dict`包括原始信息(`original text`), 意图(`intent`)的找到的所有实体(`entities`)
2. `Tracker`保持对话的状态.
3. `Policy` 接收到当前`Tracker`的状态
4. `Policy`选择执行哪个动作(`Action`)
5. 被选中的`Action`同时被`Tracker`记录
6. `Action`执行后产生回应

### Training


### Interactive Learning

在交互式学习模式下, 我们可以为Bot对话提供反馈. 这是一个非常强有力的方式去检测Bot能做什么, 同时也是修改错误最简单的方式. 基于机器学习的对话的有点就在于当bot不知道如何回答或者回答错误时, 我们可以及时的反馈给bot. 有些人称这种方式为Software 2.0


### Action
进行数据校验, 和数据交互. 
采用Py2Neo与数据库(Neo4j)进行交互. 
