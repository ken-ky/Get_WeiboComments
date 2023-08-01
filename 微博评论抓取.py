import json
import os
import re
import time
from jsonpath import jsonpath
import requests
import pandas as pd
import datetime
from bs4 import BeautifulSoup


# 将新浪微博时间转换作标准格式
def trans_time(v_str):
    # 转换GMT到标准格式
    GMT_FORMAT = '%a %b %d %H:%M:%S +0800 %Y'
    timeArray = datetime.datetime.strptime(v_str, GMT_FORMAT)
    ret_time = timeArray.strftime('%Y-%m-%d %H:%M:%S')
    return ret_time


# 请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Mobile Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-encoding": "gzip, deflate, br",
}

# cookie
cookies = '''ALF=1692107211; SUB=_2A25JsvAqDeRhGeBO7lcW9S3Iwj-IHXVrXJBirDV6PUJbkdCOLUrWkW1NRf6whRBDNroUOM2t-BHLW6ZYM07gqWhP; _T_WM=82729770584; WEIBOCN_FROM=1110006030; MLOGIN=1; XSRF-TOKEN=cfc187; mweibo_short_token=0ed0069bfe; M_WEIBOCN_PARAMS=oid%3D4924553476441688%26luicode%3D20000061%26lfid%3D4924553476441688%26uicode%3D20000061%26fid%3D4924553476441688'''


# cookie transfer
def convert_cookie(co_str):
    cookies = dict([i.split("=", 1) for i in co_str.split(';')])
    return cookies


# 爬取相关代码：其中mid和id是相同的
def fetch_web(url, header, cookie):
    response = requests.get(url=url, headers=header, cookies=cookie)
    response.encoding = response.apparent_encoding
    time.sleep(3)  # 加上3s的延时防止被反爬
    return response.text


# 获取二级评论
def get_second(cid, header, cookie):
    data = []
    max_id = 0
    max_id_type = 0
    dr = re.compile(r'<[^>]+>')
    url = 'https://m.weibo.cn/comments/hotFlowChild?cid={}&max_id={}&max_id_type={}'
    while True:
        response = fetch_web(url.format(cid, max_id, max_id_type), header, cookie)
        content = json.loads(response)
        comments = content['data']
        for i in comments:
            text_data = i['text']
            text_data = dr.sub('', text_data)
            if text_data != '':
                li = [trans_time(i['created_at']), text_data]
                data.append(li)
                # print(text_data)
                # print(trans_time(i['created_at']))
        max_id = content['max_id']
        max_id_type = content['max_id_type']
        if max_id == 0:  # if max_id==0, fetching has finished.
            break
    return data


# 获取一级评论
def get_first(mid, header, cookie):
    data = []
    max_id = 0
    max_id_type = 0
    dr = re.compile(r'<[^>]+>')
    url = 'https://m.weibo.cn/comments/hotflow?id={}&mid={}&max_id={}&max_id_type={}'
    while True:
        response = fetch_web(url.format(mid, mid, max_id, max_id_type), header, cookie)
        content = json.loads(response)
        max_id = content['data']['max_id']
        max_id_type = content['data']['max_id_type']
        text_list = content['data']['data']
        for text in text_list:
            text_data = text['text']
            text_data = dr.sub('', text_data)
            # print(trans_time(text['created_at']))
            if text_data != '':
                li = [trans_time(text['created_at']), text_data]
                data.append(li)
            total_number = text['total_number']
            if int(total_number) != 0:  # 如果有二级评论就去获取二级评论。
                data += get_second(text['id'], header, cookie)
            # print(text_data)
        if int(max_id) == 0:  # 如果max_id==0表明评论已经抓取完毕了
            break
    return data


if __name__ == '__main__':
    mid = ["4924553476441688"]
    for id in mid:
        print(get_first(id, headers, convert_cookie(cookies)))  # 爬取一级评论
