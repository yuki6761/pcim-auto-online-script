import random
import time
import base64

import requests
import schedule
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from schedule import every, repeat, run_pending

SECRET_KEY = 'xxxxxxxxxxxxxxxx'
SECRET_IV = 'xxxxxxxxxxxxxxxx'

base_url = input('输入后端地址(https://im.xx.com/api/)：') or 'https://im.xx.com/api/'
org = input('输入机构：') or '广东xx计算机科技有限公司'
account = input('输入账号：') or '13444444444'
password = input('输入密码：') or '123456'
token = ''
# 心跳请求次数
heartbeat_request_success_count = 0
heartbeat_request_error_count = 0
# 心跳请求计划任务实例
heartbeat_request_job = None


# AES加密
def encrypt(text):
    cipher = AES.new(SECRET_KEY.encode('utf-8'), AES.MODE_CBC, SECRET_IV.encode('utf-8'))
    # 将文本填充为16的倍数
    padded_text = pad(text.encode('utf-8'), AES.block_size)
    # 加密
    encrypted_text = cipher.encrypt(padded_text)
    # 将加密后的文本进行base64编码
    encoded_text = base64.b64encode(encrypted_text).decode('utf-8')
    return encoded_text


def clear():
    global token
    global heartbeat_request_success_count
    global heartbeat_request_error_count
    global heartbeat_request_job

    token = ''
    heartbeat_request_success_count = 0
    heartbeat_request_error_count = 0
    if heartbeat_request_job is not None:
        schedule.cancel_job(heartbeat_request_job)
        heartbeat_request_job = None


# 心跳请求
def heartbeat_request():
    global heartbeat_request_success_count
    global heartbeat_request_error_count
    try:
        response = requests.post(url=base_url + 'im/mq/heartv2', data={
            'type': 'PC',
            'token': token
        })
        if response.status_code == 200:
            data_json = response.json()
            if data_json.get('status').get('code') == 0:
                heartbeat_request_success_count += 1
            elif data_json.get('status').get('code') == 401:
                clear()
                re_login = input('\rtoken已失效，是否重新登录？(Y/N)：') or 'Y'
                if re_login in 'yY':
                    login(True)
                else:
                    print('放弃重新登录')
        else:
            heartbeat_request_error_count += 1
    except requests.RequestException:
        heartbeat_request_error_count += 1

    print('\r心跳包请求成功', heartbeat_request_success_count, '次，失败', heartbeat_request_error_count, '次', end='', flush=True)


# 延迟计时器
def time_counter(text):
    sleep_seconds = random.randint(60, 1200)
    for i in range(sleep_seconds):
        print('\r将在', sleep_seconds - i, '秒后' + text, end='', flush=True)
        time.sleep(1)
    print('\r')


# 登录
@repeat(every().day.at('08:30'))
def login(is_immediately=False):
    global token
    global heartbeat_request_job

    if not is_immediately:
        time_counter('登录')

    try:
        response = requests.post(url=base_url + 'loginEncrypt', data={
            'platform': '3',
            'org': org,
            'account': encrypt(account),
            'password': encrypt(password)
        })
        if response.status_code == 200:
            data_json = response.json()
            if data_json.get('status').get('code') == 0:
                token = data_json.get('data').get('token')
                heartbeat_request_job = schedule.every(5).seconds.do(heartbeat_request)
                print('\n登录成功，用户名：', data_json.get('data').get('name'), '，token：', token, '\n')
            else:
                print('登录失败，3秒后重试')
                time.sleep(3)
                login()
        else:
            print('登录失败，3秒后重试')
            time.sleep(3)
            login()
    except requests.RequestException:
        print('登录失败，3秒后重试')
        time.sleep(3)
        login()


# 注销
@repeat(every().day.at('17:30'))
def logout(is_immediately=False):
    if len(token) == 0:
        return

    if not is_immediately:
        time_counter('登出')

    try:
        response = requests.post(url=base_url + 'logout', data={
            'platform': '3',
            'token': token
        })
        if response.status_code == 200:
            data_json = response.json()
            if data_json.get('status').get('code') == 0:
                clear()
                print('登出成功，落班愉快～～～\n')
            else:
                print('登出失败，3秒后重试')
                time.sleep(3)
                logout()
        else:
            print('登出失败，3秒后重试')
            time.sleep(3)
            logout()
    except requests.RequestException:
        print('登出失败，3秒后重试')
        time.sleep(3)
        logout()


if "08:30:00" < time.strftime("%H:%M:%S", time.localtime()) < "17:30:00":
    login(True)

while True:
    run_pending()
    time.sleep(1)
