#!/usr/bin/env python
# -*- coding: utf-8 -*-
import web
from pymongo import MongoClient

#####
debug_mode = True   # Flase - production, True - staging
#####
# 
enable_proxy = True
http_proxy = 'http://192.168.2.108:8888'
https_proxy = 'https://192.168.2.108:8888'
proxy_list = ['192.168.2.103']
enable_local_test = True
#####

web_serv_list={'web1' : ('192.168.2.98','192.168.2.98')}  # 

local_ip=web_serv_list['web1'][1]

cli = {'web'  : MongoClient(web_serv_list['web1'][0]),}
      
db_web = cli['web']['takit_db']
db_web.authenticate('ipcam','ipcam')

thread_num = 1
auth_user = ['test']
cs_admin = ['cs0']

tmp_path = '/usr/local/nginx/html/takit/static/tmp'
logs_path = '/usr/local/nginx/logs'
sjrand_path = '.'

http_port=80
https_port=443

mail_server='127.0.0.1'
sender='"Kam@Cloud"<kam@f8geek.com>'
worker=['2953116@qq.com']

web.config.debug = debug_mode

config = web.storage(
    email = 'jack139@gmail.com',
    site_name = 'ipcam',
    site_des = '',
    static = '/static'
)
