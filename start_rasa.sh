# 首先需要启动两个容器，一个是neo4j服务，一个是redis服务
## neo4j启动命令，注意端口映射[如果已经启动服务，跳过该步骤]
docker run --publish=7474:7474 --publish=7687:7687 --volume=$HOME/Documents/neo4j/data:/data neo4j:latest
## redis启动命令，注意端口映射[如果已经启动服务，跳过该步骤]
docker run -d -p 6379:6379 --name docker-redis redis:6.2.5

# 启动actions
## 设置worker数量，根据需要可在服务器上设置成5
export ACTION_SERVER_SANIC_WORKERS=1
nohup rasa run actions &> log/rasa_actions.log &

# 启动rasa
## 设置worker数量，根据需要可在服务器上设置成5
export SANIC_WORKERS=1
## 解决客户端和rasa服务器跨域问题
nohup rasa run --cors "*" --enable-api &> log/rasa_server.log &

# 启动webserver,有两个路由服务，一个是api接口，一个是ui接口
nohup python start_service.py &> log/live_assistant_server.log &
