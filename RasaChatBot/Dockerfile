FROM rasa/rasa:3.0.4-full
# 这是最小镜像，和自己的需要的lib依赖有关系，需要问题时可以参考注释部分。
# 权限不足时打开
USER root

COPY . /app
WORKDIR /app
# 有gcc缺失时可以打开
#RUN apt-get install -y gcc
# 有requirement依赖时可以打开
#RUN pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple

# 指定暴露端口
EXPOSE 5005

ENTRYPOINT ["rasa"]
CMD ["run", "--enable-api", "--cors", "*"]