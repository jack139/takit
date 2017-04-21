#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 外包云打码，使用 urllib3
#
import httphelper3
import urllib, json, base64, random
from config import setting

## ---- 打码有关参数  ---------------------------------------------------

# 用户名
username    = 'dragon'
# 密码
password    = 'ilovekam'
# 软件ＩＤ
appid       = 1267
# 软件密钥
appkey      = 'bb660bbafcc242155f8068b0bd046976'
# 验证码类型
codetype    = 6701
# 超时时间，秒
timeout     = 30
# API url
apiurl = 'http://api.yundama.com/api.php'

#
# --------------- API to YDM --------------------------------------------------
#


# 返回结果中的data域
def process_result(data):
	try:
		data2=json.loads(data)
		print data2
	except ValueError:
		print data
		return (httphelper3.E_JSON, 'load json fail.')

	if data2['ret']==0:
		return (httphelper3.E_OK, data2)
	else:
		return (httphelper3.E_DATA, data2)

def login():
	# POST
	print 'sjrandhelper3.login()'
	body = {'method': 'login', 'username': username, 'password': password, 'appid': appid, 'appkey': appkey}
	data = httphelper3.http_do_post_encode_body('YDM', apiurl, body)
	if data==None:
		return (httphelper3.E_QUERY, 'query no return')
	else:
		return process_result(data)

def balance():
	# POST
	print 'sjrandhelper3.balance()'
	body = {'method': 'balance', 'username': username, 'password': password, 'appid': appid, 'appkey': appkey}
	data = httphelper3.http_do_post_encode_body('YDM', apiurl, body)
	if data==None:
		return (httphelper3.E_QUERY, 'query no return')
	else:
		return process_result(data)

def upload(image):
	# POST
	print 'sjrandhelper3.upload()'
	body = {'method': 'upload', 'username': username, 'password': password, 'appid': appid, 'appkey': appkey, 'codetype': str(codetype), 'timeout': str(timeout)}
	body['file'] = (image, open('%s/%s' % (setting.sjrand_path,image)).read(), 'application/octet-stream')
	data = httphelper3.http_do_post_encode_body('YDM', apiurl, body)
	if data==None:
		return (httphelper3.E_QUERY, 'query no return')
	else:
		return process_result(data)

def result(cid):
	# POST
	print 'sjrandhelper3.result(%d)' % cid
	body = {'method': 'result', 'username': username, 'password': password, 'appid': appid, 'appkey': appkey, 'cid': str(cid)}
	data = httphelper3.http_do_post_encode_body('YDM', apiurl, body)
	if data==None:
		return (httphelper3.E_QUERY, 'query no return')
	else:
		return process_result(data)


def report(cid, flag=0):
	# POST
	print 'sjrandhelper3.report(%d, %d)' % (cid, flag)
	body = {'method': 'report', 'username': username, 'password': password, 'appid': appid, 'appkey': appkey, 'cid': str(cid), 'flag': str(flag)}
	data = httphelper3.http_do_post_encode_body('YDM', apiurl, body)
	if data==None:
		return (httphelper3.E_QUERY, 'query no return')
	else:
		return process_result(data)

