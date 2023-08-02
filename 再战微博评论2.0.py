import datetime
import requests
import re
import os
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def trans_time(v_str):
    GMT_FORMAT = '%a %b %d %H:%M:%S +0800 %Y'
    timeArray = datetime.datetime.strptime(v_str, GMT_FORMAT)
    ret_time = timeArray.strftime('%Y-%m-%d %H:%M:%S')
    return ret_time


def get_since_id(session, user_id, l_id, contain_id, since_id):
    topic_url = 'https://m.weibo.cn/api/container/getIndex?uid={}&luicode=10000011&lfid={}&type=uid&value={}&containerid={}'.format(
        user_id, l_id, user_id, contain_id)
    topic_url += '&since_id=' + str(since_id)
    try:
        time.sleep(1)
        result = session.get(topic_url, timeout=40)
        json = result.json()
        items = json.get('data').get('cardlistInfo')
        if items is not None:
            min_since_id = items['since_id']
        else:
            min_since_id = '404'
        return min_since_id
    except (requests.ConnectionError, requests.Timeout) as e:
        print('Error since_id:', str(e))
        return '404'


def get_page(session, user_id, l_id, contain_id, since_id=''):
    li = []
    url = 'https://m.weibo.cn/api/container/getIndex?uid={}&luicode=10000011&lfid={}&type=uid&value={}&containerid={}'.format(
        user_id, l_id, user_id, contain_id)
    url += '&since_id={}'.format(since_id)
    try:
        time.sleep(1)
        result = session.get(url, timeout=60)
        if result.status_code == 200:
            li.append(result.json())
    except (requests.ConnectionError, requests.Timeout) as e:
        print('Error get pages:', str(e))
    return li


def get_user_name(session, user_id, contain_id):
    url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value={}&containerid={}'.format(user_id, contain_id)
    try:
        result = session.get(url, timeout=30)
        json = result.json()
        user_name = json['data']['cards'][1]['mblog']['user']['screen_name']
        return user_name
    except (requests.ConnectionError, requests.Timeout) as e:
        print('Error get id:', str(e))


def save_file(filename, text):
    folder = os.path.exists('../cache')
    if not folder:
        os.mkdir('../cache')
    with open('./cache/{}.txt'.format(filename), 'w', encoding='utf-8') as file:
        # line = 'time,text'
        # file.write(line + '\n')
        for row in text:
            line = ','.join(str(item) for item in row)
            file.write(line + '\n')
    print(filename + '数据已保存')


def get_data(session, min_id, user_id, l_id, contain_id, time_counter):
    li = []
    last_time = ''
    last_month = 0
    temp_month = 0
    rest_month = 0

    text = ''
    timing = ''
    length = 0

    while rest_month <= time_counter and min_id != '404':
        min_id = get_since_id(session, user_id, l_id, contain_id, min_id)
        if min_id == '404':
            break
        page = get_page(session, user_id, l_id, contain_id, min_id)[0]['data']['cards']

        for sentence in page:
            text = sentence['mblog']['text']
            timing = sentence['mblog']['created_at']

            dr = re.compile(r'<[^>]+>|转发微博|分享图片|\s|\n')
            text = dr.sub('', text)
            length = len(text)

            if 1 < length <= 50:
                if last_time == '' and text != '':
                    last_time = trans_time(timing)
                    last_month = int(last_time[5:7])

                if text != '':
                    temp_month = int(trans_time(timing)[5:7])
                    li.append([text])

        if temp_month != 0:
            rest_month = (last_month - temp_month + 12) % 12

    return li, trans_time(timing)[:11].replace('-', '') + last_time[:11].replace('-', '')


def crawl_data(user_id, l_id, contain_id, time_counter, headers):
    session = requests.Session()
    session.headers = headers

    min_since_id = ''
    text_data = []
    time_s = ''

    text_data, time_s = get_data(session, min_since_id, user_id, l_id, contain_id, time_counter)
    print('选取微博条数：' + str(len(text_data)))
    save_file(get_user_name(session, user_id, contain_id) + '_' + time_s, text_data[::-1])


if __name__ == '__main__':
    headers = {
        "User-Agent": UserAgent().random,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-encoding": "gzip, deflate, br",
    }

    uid = [
        '1648007681',
        '7768333203',
        '7263656476',
        '5747294735',
        '6932417793',
        '7814874451',
        '7834152181',
        '5530609542',
        '7131618371',
        '7836765553',
        '7817327840',
        '6113301440',
        '3225444910',
        '7478209878',
        '7714886755'
    ]
    l_fid = ['107603{}'.format(i) for i in uid]
    container_id = ['107603{}'.format(i) for i in uid]

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(crawl_data, uid[i], l_fid[i], container_id[i], 4, headers) for i in range(len(uid))]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print('Error data:', e)
