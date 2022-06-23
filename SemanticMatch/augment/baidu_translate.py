# -*- coding: utf-8 -*-

"""
@Time    : 2022/6/23 3:42 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""

# -*- coding: utf-8 -*-

"""
@Time    : 2022/3/1 9:35 上午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
#回译

from urllib.parse import quote
import http.client
import hashlib
import urllib
import random
import json
import time

class Translator(object):
    def translate(self, q, src_lang, tgt_lang):
        """请求百度通用翻译API，详细请看 https://api.fanyi.baidu.com/doc/21
        :param q:
        :param src_lang:
        :param tgt_lang:
        :return:
        """
        appid = '20220302001105912'  # Fill in your AppID
        secretKey = 'Gpginf0ryq4tRXBEgGyD'  # Fill in your key

        httpClient = None
        myurl = '/api/trans/vip/translate'

        salt = random.randint(0, 4000)
        sign = appid + q + str(salt) + secretKey
        sign = hashlib.md5(sign.encode()).hexdigest()
        myurl = '/api/trans/vip/translate' + '?appid=' + appid + '&q=' + urllib.parse.quote(
            q) + '&from=' + src_lang + '&to=' + tgt_lang + '&salt=' + str(salt) + '&sign=' + sign

        try:
            httpClient = http.client.HTTPConnection('api.fanyi.baidu.com')
            httpClient.request('GET', myurl)
            # response is HTTPResponse object
            response = httpClient.getresponse()
            result_all = response.read().decode("utf-8")
            result = json.loads(result_all)

            return result

        except Exception as e:
            print(e)
        finally:
            if httpClient:
                httpClient.close()

    def back_translate(self, text, nums=25, src_lang="zh"):
        """
        :param q: 文本
        :param src_lang: 原始语言
        :param tgt_lang: 目前语言
        :return: 回译后的文本
        """
        lan_list = "en,jp,kor,fra,spa,th,ara,ru,pt,de,it,el,nl,pl,bul,est,dan,fin,cs,rom,slo,swe,hu,cht,vie".split(",")
        res = []
        nums = nums if nums < 25 else 25
        for tgt_lang in random.sample(lan_list,nums):
            time.sleep(1.5)
            try:
                trans_result = self.translate(text, src_lang, tgt_lang).get('trans_result',[])
                en = trans_result[0]['dst'] if trans_result else ''
                if en:
                    time.sleep(1.5)
                    trans_result_en = self.translate(en, tgt_lang, src_lang).get('trans_result',[])
                    target = trans_result_en[0]['dst'] if trans_result_en else ''
                    if target:
                        res.append(target)
            except Exception as e:
                print("back translate error: {}".format(e))
        return list(set(res))


if __name__ == '__main__':
    t = Translator()
    res = t.back_translate('帮我查一下航班信息', nums=20, src_lang='zh')
    print("back_translate", res)