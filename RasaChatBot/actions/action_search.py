# -*- coding: utf-8 -*-

"""
@Time    : 2022/3/31 8:39 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import re
import time
import urllib.request
from urllib.parse import quote_plus
from lxml import etree
import json

class ZhidaoChatbot:
    def __init__(self):
        return

    '''获取搜索页'''
    def get_html(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/600.5.17 (KHTML, like Gecko) Version/8.0.5 Safari/600.5.17"}
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req).read().decode('utf-8')
        return html


    '''采集问答首页'''
    def collect_urls(self, url):
        html = self.get_html(url)
        selector = etree.HTML(html)
        pairs = []
        # questions = [i.xpath('string(.)').replace('搜狗问问','').replace('搜狗', '').replace('-','').replace('\r','').replace('\n','') for i in selector.xpath('//div[@class="results"]/div[@class="vrwrap"]')]
        # links = ['https://wenwen.sogou.com/' + i.xpath('./a/@href') for i in selector.xpath('//div[@class="results"]/div[@class="vrwrap"]')]
        for i in selector.xpath('//div[@class="results"]/div[@class="vrwrap"]'):
            try:
                q_tmp = i.xpath('./div/h3/a')[0].xpath('string(.)').replace('搜狗问问','').replace('搜狗', '').replace('-','').replace('\r','').replace('\n','')
                l_tmp = 'https://www.sogou.com/'+ i.xpath('./div/h3/a/@href')[0]
                pairs.append((q_tmp, l_tmp))
            except:
                print("not links, passed", i)
        return pairs[:2]

    '''采集答案'''
    def parser_answer(self, url):
        html = self.get_html(url)
        # get q_id
        pattern = re.compile(r'.*(q[0-9]{3,13}.htm).*')
        match = re.match(pattern, html)
        if match:
            url_re = 'https://wenwen.sogou.com/z/'+match.group(1)
            html_re = self.get_html(url_re)
            selector = etree.HTML(html_re)
            answers = [i.xpath('string(.)').replace('\u3000','').replace('\n', '').replace('\xa0', '').replace(' ', '。').replace('\r', '') for i in selector.xpath('//pre')]
            answers = [i for i in answers if '?' not in i and '？' not in i and len(set(i)) > 2 and '为什么' not in i]
            answer_dict = {answer:len(answer) for answer in answers}
            answers = [i[0] for i in sorted(answer_dict.items(), key=lambda asd:asd[1])]  # 将短答案排在最前面
            return answers
        return []

    '''收集答案'''
    def collect_answers(self, url):
        answers_all = []
        url_pairs = self.collect_urls(url)
        for question, answer_url in url_pairs:
            answers = self.parser_answer(answer_url)
            answers_all += answers
        answer_dict = {answer:len(answer) for answer in answers_all}

        best_answers = [i[0] for i in sorted(answer_dict.items(), key=lambda asd:asd[1])][:5]  # 将短答案排在前面
        return best_answers

    '''扩展问句'''
    def expand_question(self, question):
        url = 'https://wenwenfeedapi.sogou.com/sgapi/related/web/search?key=' + quote_plus(question) + \
        "_=1648739885791&_traceId=e3a0ad3615a74e55ac67af2f0b83d34e:2&c_tk=bdbd4b9f"
        data = json.loads(self.get_html(url))
        others = data["data"]
        return others

    '''问答'''
    def qa_main(self, question):
        url = 'https://www.sogou.com/sogou?query='+quote_plus(question) +'&ie=utf8&s_from=result_up&insite=wenwen.sogou.com'
        answers = self.collect_answers(url)
        other_questions = self.expand_question(question)
        return answers, other_questions

    '''问答'''
    def qa_new(self, question):
        url = 'https://www.sogou.com/sogou?query=' + quote_plus(question) + '&ie=utf8&insite=wenwen.sogou.com&pid=sogou-wsse-a9e18cb5dd9d3ab4&rcer='
        answers = self.collect_answers(url)
        return answers

'''测试'''
def test(question):
    handler = ZhidaoChatbot()
    b0 = time.time()
    answers = handler.qa_new(question)
    print("answer cost {:.2f}s".format(time.time() - b0))
    sim_questions = handler.expand_question(question)
    print("sim question cost {:.2f}s".format(time.time() - b0))
    print('回答:', answers)
    print('你可能还想问:', sim_questions)
    print('*******'*6)

if __name__ == '__main__':
    test("太阳有多大")
