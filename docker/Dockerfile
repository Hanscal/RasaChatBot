FROM hanscal/py3

# maintainer info
MAINTAINER caihua "hua.cai@unidt.com"

RUN apt-get update && apt-get install -y libgl1-mesa-glx vim

RUN mkdir /root/RasaChatBot

# 指定工作路径
WORKDIR /root/RasaChatBot

# Copy the current directory contents into the container at /article_search
COPY / .

# Install any needed packages specified in requirements.txt
COPY ./docker/requirements-web.txt ./
RUN pip3 install --upgrade pip -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
RUN pip3 install -r requirements-web.txt -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com

# Define environment variable
#环境变量硬编码及时区
ENV TZ=Asia/Shanghai
RUN apt-get update \
    && apt-get install -y locales \
    && locale-gen zh_CN.UTF-8 \
    && update-locale LANG=zh_CN.UTF-8 LANGUAGE=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8
    && apt-get install tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && dpkg-reconfigure --frontend noninteractive tzdata

ENV LANG zh_CN.UTF-8
ENV LANGUAGE zh_CN.UTF-8
ENV LC_ALL zh_CN.UTF-8
#RUN localedef -c -f UTF-8 -i zh_CN zh_CN.utf8

# RUN python setup.py build_ext && rm ./setup.py

# 指定暴露端口
EXPOSE 8088

# Run app.py when the container launche
# CMD ["python", "article_search_service.py"]