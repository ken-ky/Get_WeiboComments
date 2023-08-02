import datetime
import requests
import re
import os
from fake_useragent import UserAgent


# 将新浪微博时间转换作标准格式
def trans_time(v_str):
    # 转换GMT到标准格式
    GMT_FORMAT = '%a %b %d %H:%M:%S +0800 %Y'
    timeArray = datetime.datetime.strptime(v_str, GMT_FORMAT)
    ret_time = timeArray.strftime('%Y-%m-%d %H:%M:%S')
    return ret_time


# 获取since_id进行翻页
def get_since_id(header, user_id, l_id, contain_id, since_id):
    global min_since_id
    topic_url = 'https://m.weibo.cn/api/container/getIndex?uid={}&luicode=10000011&lfid={}&type=uid&value={}&containerid={}'.format(
        user_id, l_id, user_id, contain_id)
    topic_url += '&since_id=' + str(since_id)
    # print(topic_url)
    result = requests.get(topic_url, headers=header)
    json = result.json()
    items = json.get('data').get('cardlistInfo')
    # print(items)
    if items is not None:
        min_since_id = items['since_id']
    else:
        # 设置末页结束条件
        min_since_id = '404'
    return min_since_id


# 获取每一页的内容
def get_page(header, user_id, l_id, contain_id, since_id=''):
    li = []
    url = 'https://m.weibo.cn/api/container/getIndex?uid={}&luicode=10000011&lfid={}&type=uid&value={}&containerid={}'.format(
        user_id, l_id, user_id, contain_id)
    url += '&since_id={}'.format(since_id)
    # print(url)
    result = requests.get(url, headers=header)
    try:
        if result.status_code == 200:
            li.append(result.json())
            # print(result.text)
    except requests.ConnectionError as e:
        print('Error', e.args)
    return li


# 1. 获取用户id
def get_user_name(header, user_id, contain_id):
    url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value={}&containerid={}'.format(user_id, contain_id)
    result = requests.get(url, headers=header)
    json = result.json()
    user_name = json['data']['cards'][1]['mblog']['user']['screen_name']
    return user_name


# 数据获取函数：将二级列表升级，区分月份
def get_data(header, min_id, user_id, l_id, contain_id, time_counter):
    # 数据记录器
    li = []

    # 记录每个月的数据
    per_month = []

    # 记录月份时间序列
    month_id = []

    # timer system
    last_time = ''
    last_month = 0
    temp_month = 0  # 临时条件时间（因为微博是按时间顺序分配js的created_at）
    rest_month = 0  # 相隔月份数

    # 尝试事先声明的变量，减少重复回收和声明空间
    text = ''
    timing = ''
    length = 0
    page = []
    while rest_month <= time_counter and min_id != '404':
        min_id = get_since_id(header, user_id, l_id, contain_id, min_id)
        # print(min_since_id)
        page = get_page(header, user_id, l_id, contain_id, min_id)[0]['data']['cards']
        # print(page)
        for sentence in page:
            text = sentence['mblog']['text']
            timing = sentence['mblog']['created_at']

            dr = re.compile(r'<[^>]+>|转发微博|分享图片|\s|\n')
            text = dr.sub('', text)
            length = len(text)
            # print(length)

            # 确保文本长度小于50
            if 1 < length <= 50:
                if last_time == '' and text != '':
                    last_time = trans_time(timing)
                    # print(last_time)
                    last_month = int(last_time[5:7])

                    # 记录首个分片时间（截止时间）
                    month_id.append(last_time[:7])
                    # print(month_id)

                if text != '':
                    # print(text)
                    temp_month = int(trans_time(timing)[5:7])

                    if int(month_id[-1][5:]) != temp_month:
                        li.append(per_month)
                        month_id.append(trans_time(timing)[:7])
                        # print(month_id)
                        per_month = []

                    # per_month.append([temp_month, text])
                    per_month.append([text])

        # 将时间月份差转换为约瑟夫问题
        if temp_month != 0:  # 防止同一月份导致
            rest_month = (last_month - temp_month + 12) % 12

    if len(per_month) != 0:
        li.append(per_month)

    # print(li)
    # print(timing)
    # print(month_id)
    return li[::-1], month_id[::-1]  # 倒转使其按照先后顺序，之后截取真正在时间范围的数据


# 2. 保存为文本文件
def save_file(filename, text):
    path = filename[:-8]
    # print(path)
    folder = os.path.exists('./' + path)
    if not folder:
        os.mkdir('./' + path)
    with open('./{}/{}.txt'.format(path, filename), 'w', encoding='utf-8') as file:
        for row in text:
            line = ','.join(str(item) for item in row)
            file.write(line + '\n')
    print(filename + '数据已保存')


if __name__ == '__main__':
    headers = {
        "User-Agent": UserAgent().random,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-encoding": "gzip, deflate, br",
    }

    min_since_id = ''

    uid = ['1648007681']
    l_fid = ['107603{}'.format(i) for i in uid]
    container_id = ['107603{}'.format(i) for i in uid]

    text_data, month = get_data(headers, min_since_id, uid[0], l_fid[0], container_id[0], 4)
    # print(len(text_data))
    # print(len(month))

    if len(month) > len(text_data):
        month = month[1:]
    for i in range(len(month)):
        save_file(get_user_name(headers, uid[0], container_id[0]) + '_' + month[i], text_data[i])
