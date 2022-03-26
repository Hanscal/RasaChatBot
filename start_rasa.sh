# 首先需要启动两个容器，一个是neo4j服务，一个是redis服务
## neo4j启动命令，注意端口映射
docker run --publish=7474:7474 --publish=7687:7687 --volume=$HOME/Documents/neo4j/data:/data neo4j:latest
## redis启动命令，注意端口映射
docker run -d -p 6379:6379 --name docker-redis redis:6.2.5

# 启动actions
## 设置worker数量
export ACTION_SERVER_SANIC_WORKERS=1
rasa run actions # &> log/rasa_actions.log

# 启动rasa
## 设置worker数量
export SANIC_WORKERS=1
## 解决客户端和rasa服务器跨域问题
rasa run --cors "*" # &> log/rasa_server.log

# 启动webserver
python start_service.py # &> log/live_assistant_server.log

# 启动web界面可以测试
python -m http.server 8089