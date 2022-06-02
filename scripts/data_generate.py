# -*- coding: utf-8 -*-

"""
@Time    : 2022/5/24 11:26 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import os
import yaml
from scripts.mysql_opt import LiveDB
from config.config import inherit_tag_path, action_list_path
from collections import OrderedDict

def save_ordered_dict_to_yaml(data, save_path, stream=None, Dumper=yaml.SafeDumper, object_pairs_hook=OrderedDict, **kwds):
    class OrderedDumper(Dumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items())

    OrderedDumper.add_representer(object_pairs_hook, _dict_representer)
    with open(save_path, 'w') as file:
        file.write(yaml.dump(data, stream, OrderedDumper, allow_unicode=True, **kwds))
    return yaml.dump(data, stream, OrderedDumper, **kwds)


def read_yaml_to_ordered_dict(yaml_path, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    with open(yaml_path) as stream:
        dict_value = yaml.load(stream, OrderedLoader)
        return dict_value

class DataGenerator(object):
    def __init__(self):
        self.nlu_dir = os.path.join(os.path.dirname(__file__), '../data/nlu/')
        self.response_dir = os.path.join(os.path.dirname(__file__), '../data/responses/')
        self.story_dir = os.path.join(os.path.dirname(__file__), '../data/stories/')

    def clear_yml(self, datadir_list, tags=['nlu.yml', 'responses.yml', 'stories.yml']):
        """
        对目录中yaml文件进行清理
        :param datadir: 需要清理yml文件所在的目录
        :type datadir: list
        :return: 清除的文件名列表
        """
        res = []
        for dir in datadir_list:
            for file in os.listdir(dir):
                if file.rsplit('_')[-1] in tags:
                    file_path = os.path.join(dir, file)
                    os.remove(file_path)
                    res.append(file_path)
        return res

    def generate_nlu_data(self, savedir, shop_name):
        """
        对不同的商户生成相应的nlu训练数据，并且继承base数据库中的一些问题
        :param savedir: 需要保存的路径
        :param shop_name: 商户名
        :return: 生成文件名列表
        """
        base_tag = read_yaml_to_ordered_dict(inherit_tag_path)
        db = LiveDB()
        res = []
        for table_name, v in base_tag.items():
            if not table_name.startswith('question'):
                continue
            for intent_en in v:
                data = []
                if isinstance(intent_en,dict):
                    data = db.get_base_question(table_name, intent_en)
                elif isinstance(intent_en, list):
                    intent_en_dict = {k:"" for k in intent_en}
                    data = db.get_base_question(table_name, intent_en_dict)
                elif isinstance(intent_en, str):
                    data = db.get_base_question(table_name, {intent_en:''})
                res.extend(data)

        # 产生faq yml
        faq, prod, other = OrderedDict(), OrderedDict(), OrderedDict()
        faq["version"]="3.0"
        faq["nlu"] = []
        prod["version"]="3.0"
        prod["nlu"] = []
        prod['synonym'] = []
        other["version"] = "3.0"
        other["nlu"] = []
        for i in res:
            if 'faq/' in i['intent']:
                faq_value = OrderedDict()
                faq_value['intent'] = i['intent']
                faq_value['examples'] = '\n'+'\n'.join(['- '+ item.strip('\n ​') for item in i['examples']])
                faq['nlu'].append(faq_value)
            elif 'query_prod_knowledge_base' in i['intent']:
                prod_value = OrderedDict()
                prod_value['intent'] = i['intent']
                prod_value['examples'] = '\n'+'\n'.join(['- '+ item.strip('\n ​') for item in i['examples']])
                prod['nlu'].append(prod_value)
                for attr in i['synonym']:
                    if 'list_product' == attr['attribute']:
                        continue
                    attr_value = OrderedDict()
                    attr_value['synonym'] = attr['attribute']
                    attr_value['examples'] = '\n'+'\n'.join(['- '+ item.strip('\n ​') for item in attr['examples']])
                    prod['synonym'].append(attr_value)
            else:
                intent_value = OrderedDict()
                intent_value['intent'] = i['intent']
                intent_value['examples'] = '\n'+'\n'.join(['- '+ item.strip('\n ​') for item in i['examples']])
                other['nlu'].append(intent_value)

        faq_path = os.path.join(savedir, shop_name+"_faq_nlu.yml")
        prod_path = os.path.join(savedir, shop_name+"_prod_nlu.yml")
        other_path = os.path.join(savedir, shop_name+"_nlu.yml")
        save_ordered_dict_to_yaml(faq, faq_path)
        save_ordered_dict_to_yaml(prod, prod_path)
        save_ordered_dict_to_yaml(other, other_path)
        return res


    def generate_response_data(self, savedir, shop_name):
        """
        对不同的商户生成相应的回答，并且继承base数据库中的一些答案
        :param savedir:
        :type savedir: str
        :param shop_name:
        :type shop_name: str
        :param inherit_tag:
        :type inherit_tag: dict
        :return:
        :rtype: list
        """
        base_tag = read_yaml_to_ordered_dict(inherit_tag_path)
        db = LiveDB()
        res = []
        for table_name, v in base_tag.items():
            if not table_name.startswith('response'):
                continue
            for intent_en, intent_en_dict in v.items():
                # 看是否有text这个key，如果有则用text里面的内容，不需要去查找数据库
                text = intent_en_dict.get('text', []) if intent_en_dict else []
                if text:
                    data = [{'intent': 'utter_{}'.format(intent_en), "text": text}]
                else:
                    data = db.get_base_response(table_name, {intent_en:intent_en_dict})
                res.extend(data)

        # 产生faq yml
        faq, other = OrderedDict(), OrderedDict()
        faq["version"] = "3.0"
        faq["responses"] = OrderedDict()
        other["version"] = "3.0"
        other["responses"] = OrderedDict()
        for i in res:
            if 'utter_faq/' in i['intent']:
                faq['responses'][i['intent']]=[{"text": item} for item in i['text']]

            else:
                other['responses'][i['intent']]=[{"text": item} for item in i['text']]

        faq_path = os.path.join(savedir, shop_name + "_faq_responses.yml")
        other_path = os.path.join(savedir, shop_name + "_responses.yml")
        save_ordered_dict_to_yaml(faq, faq_path)
        save_ordered_dict_to_yaml(other, other_path)
        return res

    def generate_stories(self, intent_info, savedir, shop_name):
        """
        根据商家的nlu的数据生成domain文件
        :param savedir:
        :param shop_name:
        :param inherit_tag:
        :return:
        """
        action_dict = read_yaml_to_ordered_dict(action_list_path)
        # 产生story yml
        story = OrderedDict()
        story["version"] = "3.0"
        story["stories"] = []
        for i in intent_info:
            intent = i['intent']
            # faq已经在rules.yml中涵盖了
            if intent.startswith('faq'):
                continue
            story_value = OrderedDict()
            story_value['story'] = 'say '+intent
            step_value = OrderedDict()
            # 部分action会复写相应的utter方法
            if "action_"+intent in action_dict['actions']:
                step_value['intent'] = intent
                step_value['action'] = "action_"+intent
            else:
                step_value['intent'] = intent
                step_value['action'] = "utter_" + intent
            story_value['steps'] = step_value
            story['stories'].append(story_value)
        story_path = os.path.join(savedir, shop_name + "_stories.yml")
        save_ordered_dict_to_yaml(story, story_path)


    def generate_domain(self, intent_info, savedir, shop_name=''):
        """
        根据商家的nlu的数据生成domain文件
        :param savedir:
        :param shop_name:
        :param inherit_tag:
        :return:
        """
        """session_config:
      session_expiration_time: 60
      carry_over_slots_to_new_session: false"""
        action_dict = read_yaml_to_ordered_dict(action_list_path)
        # 产生domain yml
        domain = OrderedDict()
        domain["version"] = "3.0"
        domain["session_config"] = OrderedDict([("session_expiration_time",60),("carry_over_slots_to_new_session",False)])
        domain['intents'] = []
        domain['entities'] = action_dict['entities']
        domain['slots'] = action_dict['slots']
        domain['actions'] = []
        domain['actions'].extend(action_dict['actions'])
        for i in intent_info:
            intent = i['intent']
            # faq已经在rules.yml中涵盖了
            if intent in action_dict['intent'] or intent.startswith('faq'):
                continue
            domain['intents'].append(intent)
        domain['intents'] = list(set(domain['intents']))
        domain['intents'].extend(action_dict['intent'])
        domain_path = os.path.join(savedir, shop_name + "_domain.yml")
        save_ordered_dict_to_yaml(domain, domain_path)

    def generate(self, shop_name):
        # 清除对应的yaml文件
        ymls = self.clear_yml(datadir_list=[self.nlu_dir, self.response_dir, self.story_dir])
        # # 生成nlu训练数据
        res = self.generate_nlu_data(savedir=self.nlu_dir, shop_name=shop_name)
        # # 生成response文件
        self.generate_response_data(savedir=self.response_dir, shop_name=shop_name)
        self.generate_stories(res, savedir=self.story_dir, shop_name=shop_name)
        self.generate_domain(res, savedir=os.path.join(os.path.dirname(__file__), '../'), shop_name=shop_name)

if __name__ == '__main__':
    # 读取yml文件
    # file_path = os.path.join(os.path.dirname(__file__),'../data/nlu/chitchat_base_nlu.yml')
    # read_yaml_to_ordered_dict(file_path)
    dg = DataGenerator()
    dg.generate('planet')

