#!/usr/bin/env python
# -*- coding:utf-8 -*-
from collections import defaultdict
import re

class DFAFilter():

    '''Filter Messages from keywords

    Use DFA to keep algorithm perform constantly

    >>> f = DFAFilter()
    >>> f.add("sexy")
    >>> f.filter("hello sexy baby")
    hello **** baby
    '''

    def __init__(self):
        self.keyword_chains = {}
        self.delimit = '\x00'

    def add(self, keyword):
        if not isinstance(keyword, str):
            keyword = keyword.decode('utf-8')
        keyword = keyword.lower()
        chars = keyword.strip()
        if not chars:
            return
        level = self.keyword_chains
        for i in range(len(chars)):
            if chars[i] in level:
                level = level[chars[i]]
            else:
                if not isinstance(level, dict):
                    break
                for j in range(i, len(chars)):
                    level[chars[j]] = {}
                    last_level, last_char = level, chars[j]
                    level = level[chars[j]]
                last_level[last_char] = {self.delimit: 0}
                break
        if i == len(chars) - 1:
            level[self.delimit] = 0

    def parse(self, path):
        with open(path,encoding='utf-8') as f:
            for keyword in f:
                self.add(keyword.strip()) #strip() 去除首尾空格

    def filter(self, message, repl="*"):
        if not isinstance(message, str):
            message = message.decode('utf-8')
        message = message.lower()
        ret = []
        start = 0
        while start < len(message):
            level = self.keyword_chains
            step_ins = 0
            for char in message[start:]:
                if char in level:
                    step_ins += 1
                    if self.delimit not in level[char]:
                        level = level[char]
                    else:
                        ret.append(repl * step_ins)
                        start += step_ins - 1
                        break
                else:
                    ret.append(message[start])
                    break
            else:
                ret.append(message[start])
            start += 1

        return ''.join(ret)


if __name__ == "__main__":
    gfw = DFAFilter()
    gfw.parse("keywords2")
    # 输入的句子
    sentence = "售假人民币,我操"
    # 进行过滤
    filted = gfw.filter(sentence, "*")
    # 如果未过滤，则返回句子
    if sentence != filted:
        print(filted) #句中有敏感词

    print(gfw.filter("然后，市长在婚礼上唱春天在哪里。", "*"))
    print(gfw.filter("你好，请问这件衣服多少钱？", "*"))
    print(gfw.filter("法轮功，邪教", "*"))
    print(gfw.filter("使用针孔摄像机，偷拍他人隐私是违法行为", "*"))


