# 可以同时训练nlu、core两个组件, (指定config，domain, data路径，下述是默认文件和路径)
rasa train -c config.yml -d domain.yml --data data

# 可以单独训练nlu模块
rasa train nlu -c config.yml -d domain.yml --data data

