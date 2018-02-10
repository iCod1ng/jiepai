import requests
import json
import pymongo
import re
import os
from requests.exceptions import RequestException
from urllib.parse import urlencode
from hashlib import md5
from bs4 import BeautifulSoup
from multiprocessing import Pool
from config import *
client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]

def get_page_index(offset,keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword':keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': '3'
    }
    url = 'https://www.toutiao.com/search_content/?'+ urlencode(data)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求索引失败')
        return None

def get_page_detail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求详细页失败')
        return None

def parse_page_detail(html,url):
    soup = BeautifulSoup(html,'lxml')
    title = soup.select('title')[0].get_text()
    # image_pattern = re.compile('gallery: JSON.parse\("(.*?)"\),',re.S)
    # result = re.search(image_pattern,html)
    # s = result.replace('\\', "")
    # if result:
    #      print(title)
    #      print(s)
    #      # print(result.group(1))
    image_pattern = re.compile('gallery: JSON.parse\("(.*?)"\),\s+siblingList', re.S)
    urls = re.findall(image_pattern, html)
    # print(title)
    # print(urls)
    if urls:
        d = ",".join(urls)
        s = d.replace('\\', "")
        j = json.loads(s)
        if j and 'sub_images' in j.keys():
            sub_images = j.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:download_image(image)
            return {
                'title':title,
                'url':url,
                'images':images
            }



def parse_page_index(html):
    data = json.loads(html)
    if data and 'data' in data.keys():
        for item in data.get('data'):
            yield item.get('article_url')
def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功',result)
        return True
    return False
def download_image(url):
    print('正在下载',url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            save_image(response.content)
        return None
    except RequestException:
        print('请求图片失败')
        return None
def save_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(),md5(content).hexdigest(),'jpg')
    if not os.path.exists(file_path):
        with open(file_path,'wb') as f:
            f.write(content)
def main(offset):
    html=get_page_index(offset,KEYWORD)
    for url in parse_page_index(html):
        html = get_page_detail(url)
        if html:
            # parse_page_detail(html)
            result = parse_page_detail(html,url)
            if result:
                save_to_mongo(result)

if __name__ == '__main__':
    groups = [x*20 for x in range(GROUP_START,GROUP_END+1)]
    pool = Pool()
    pool.map(main,groups)



