import datetime
import requests
import re
import os
import time
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed


class WeiboCommentCrawler:
    __default_headers = {
        "User-Agent": UserAgent().random,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-encoding": "gzip, deflate, br",
    }

    def __init__(self) -> None:
        pass

    # 将新浪微博时间转换作标准格式
    @staticmethod
    def __trans_time(v_str):
        # 转换GMT到标准格式
        GMT_FORMAT = '%a %b %d %H:%M:%S +0800 %Y'
        timeArray = datetime.datetime.strptime(v_str, GMT_FORMAT)
        ret_time = timeArray.strftime('%Y-%m-%d %H:%M:%S')
        return ret_time

    # 获取since_id用于翻页操作
    @classmethod
    def get_since_id(self, session, user_id, l_id, contain_id, since_id):
        topic_url = f'https://m.weibo.cn/api/container/getIndex?uid={user_id}&luicode=10000011&lfid={l_id}&type=uid&value={user_id}&containerid={contain_id}&since_id={since_id}'
        # print(topic_url)

        try:
            time.sleep(1)
            result = session.get(topic_url, timeout=40)
            json = result.json()
            items = json.get('data').get('cardlistInfo')
            # print(items)

            if items is not None:
                min_since_id = items['since_id']
            else:
                min_since_id = '404'
            return min_since_id

        except (requests.ConnectionError, requests.Timeout) as e:
            print('Error since_id:', str(e))
            return '404'  # 防止因为最后一页无法获取下一个since_id的情况

    # 获取每一页的内容
    @classmethod
    def get_page(self, session, user_id, l_id, contain_id, since_id=''):
        li = []
        url = f'https://m.weibo.cn/api/container/getIndex?uid={user_id}&luicode=10000011&lfid={l_id}&type=uid&value={user_id}&containerid={contain_id}&since_id={since_id}'
        # print(url)

        try:
            time.sleep(1)
            result = session.get(url, timeout=60)
            if result.status_code == 200:
                li.append(result.json())
                # print(result.text)
        except (requests.ConnectionError, requests.Timeout) as e:
            print('Error get pages:', str(e))
        return li

    # ==================================对外接口=========================================
    # 1. 获取用户id
    @classmethod
    def get_user_name(self, session, user_id, contain_id):
        url = f'https://m.weibo.cn/api/container/getIndex?type=uid&value={user_id}&containerid={contain_id}'

        try:
            result = session.get(url, timeout=30)
            json = result.json()
            user_name = json['data']['cards'][1]['mblog']['user']['screen_name']
            return user_name
        except (requests.ConnectionError, requests.Timeout) as e:
            print('Error get id:', str(e))

    # 2. 进行数据筛选和生成数据列表
    @classmethod
    def get_data(self, session, min_id, user_id, l_id, contain_id, time_counter):
        # data record
        li = []

        # timer system
        last_time = ''
        last_month = 0
        temp_month = 0  # 临时条件时间（因为微博是按时间顺序分配js的created_at）
        rest_month = 0  # 相隔月份数

        # 尝试事先声明的变量，减少重复回收和声明空间
        text = ''
        timing = ''
        length = 0

        while rest_month <= time_counter and min_id != '404':
            min_id = self.get_since_id(session, user_id, l_id, contain_id, min_id)
            # print(min_since_id)
            if min_id == '404':
                break
            page = self.get_page(session, user_id, l_id, contain_id, min_id)[0]['data']['cards']
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
                        last_time = self.__trans_time(timing)
                        # print(last_time)
                        last_month = int(last_time[5:7])

                    if text != '':
                        temp_month = int(self.__trans_time(timing)[5:7])
                        # li.append([self.__trans_time(timing), text])  # 暂时不需要时间
                        li.append([text])

            # 将月份差值转换作约瑟夫问题，确保最大间隔
            if temp_month != 0:
                rest_month = (last_month - temp_month + 12) % 12
        # print(li)
        # print(timing)
        return li, self.__trans_time(timing)[:11].replace('-', '') + last_time[:11].replace('-', '')

    # 3.保存为文本文件
    @staticmethod
    def save_file(filename, text):
        folder = os.path.exists('./cache')
        if not folder:
            os.mkdir('./cache')
        with open(f'./cache/{filename}.txt', 'w', encoding='utf-8') as file:
            # 这里暂时不需要标签
            # line = 'time,text'
            # file.write(line + '\n')
            for row in text:
                line = ','.join(str(item) for item in row)
                file.write(line + '\n')
        print(f'{filename}数据已保存')

    # 4.集成函数一：将数据按所需格式保存[使用上述函数 1, 2, 3]

    # headers：HTTP请求头，包含了请求的一些元数据，如用户代理、授权信息等。在发送请求时，需要将适当的请求头信息包含在其中，以便与服务器进行通信。
    # uid[i]：微博用户的唯一标识符。每个微博用户都有一个独特的用户ID，用于标识用户的身份。
    # l_fid[i]：微博的唯一标识符。每条微博都有一个独特的微博ID，用于标识微博的内容。
    # container_id[i]：微博容器的唯一标识符。微博容器是一个包含微博及其相关内容的容器，如用户主页、话题页面等。通过容器ID，可以定位到特定的微博容器，从而获取相关的评论信息。
    # min_since_id：最小的评论ID。通过设置最小的评论ID，可以筛选出大于该ID的评论，以获取最新的评论内容。
    @classmethod
    def crawl_data(self, user_id, l_id, contain_id, time_counter):
        session = requests.Session()
        session.headers = self.__default_headers

        min_since_id = ''
        text_data = []
        time_s = ''

        text_data, time_s = self.get_data(session, min_since_id, user_id, l_id, contain_id, time_counter)
        print('选取微博条数：' + str(len(text_data)))
        self.save_file(self.get_user_name(session, user_id, contain_id) + '_' + time_s, text_data[::-1])

    # 5. 批量使用函数：使用多线程进行爬取
    @classmethod
    def crawl_data_multi_thread(self, user_ids, l_ids, container_ids, time_counter):
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self.crawl_data, user_ids[i], l_ids[i], container_ids[i], time_counter) for i in
                       range(len(user_ids))]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print('Error data:', e)


# 使用示例
# if __name__ == '__main__':
#     crawler = WeiboCommentCrawler()
#     user_ids = [
#         '1648007681',
#         '7768333203',
#         '7263656476',
#         '5747294735'
#     ]
#
#     # 这里的发现了微博id间拼接规律
#     l_ids = ['107603{}'.format(uid) for uid in user_ids]
#     container_ids = ['107603{}'.format(uid) for uid in user_ids]
#
#     crawler.crawl_data_multi_thread(user_ids, l_ids, container_ids, 4)
