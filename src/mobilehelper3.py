#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 12306 无线端接口
#
import time
import socket, urllib, urllib3
import json, base64, random, hashlib
import dynamicJS, stations
from config import setting


# 返回结果
E_OK		= 0
E_QUERY		= -1
E_JSON		= -2
E_DATA		= -3
E_STATUS	= -4
E_STATION	= -5
E_IMAGE		= -6
E_FLAG		= -7
E_DC1		= -8
E_DC2		= -9
E_DC3		= -10
E_DC4		= -11
E_DC5		= -12
E_CHECK_ORDER	= -13
E_LOGIN		= -14
E_REAL_ADD	= -15
E_RETURN_TICKET = -16
E_PAY		= -17
E_JS		= -18


#
# ----------------- define about connection ---------------------------------------------
#

CONN_TIMEOUT = 180

socket.setdefaulttimeout(CONN_TIMEOUT)

urllib3.disable_warnings()

# cookie pool
cookie_pool = {}

# connection pool
conn_pool = {}

user_agent = 'Mozilla/5.0 (Linux; U; Android 4.1.2; zh-cn; MI 1S Build/JZO54K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30/Worklight/6.0.0'


#
# ----------------- HTTP GET/POST & Cookie ---------------------------------------------
#

def random_proxy():
	return 'http://%s:8888' % setting.proxy_list[random.randint(0,len(setting.proxy_list)-1)]

def new_cookie(pool_id, name, value): # 添加新cookie
	global cookie_pool
	if cookie_pool.has_key(pool_id):
		cookie_pool[pool_id][name] = value
	else:
		cookie_pool[pool_id] = { name : value }

def get_cookie(pool_id): 
	if cookie_pool.has_key(pool_id):
		return cookie_pool[pool_id]
	else:
		return {}

def set_cookie(pool_id, c):
	global cookie_pool
	if c==None:
		cookie_pool[pool_id]={}
	else:
		cookie_pool[pool_id]=c

def clear_cookie(pool_id):
	set_cookie(pool_id, None)

def remove_session_cookie(pool_id):
	global cookie_pool
	if cookie_pool.has_key(pool_id):
		cookie_pool[pool_id].pop('BIGipServernginxformobile', None)
		cookie_pool[pool_id].pop('JSESSIONID', None)
		cookie_pool[pool_id].pop('AlteonP', None)

def new_pool(pool_id):
	global conn_pool
	#if setting.enable_proxy:
		#pool = urllib3.ProxyManager(setting.http_proxy, num_pools=50, timeout=CONN_TIMEOUT, retries=False)
	#else:
	#	pool = urllib3.PoolManager(num_pools=50, timeout=CONN_TIMEOUT, retries=False)
	pool = urllib3.ProxyManager(random_proxy(), num_pools=50, timeout=CONN_TIMEOUT, retries=False)
	conn_pool[pool_id]=pool
	return pool

def get_pool(pool_id):
	if conn_pool.has_key(pool_id):
		return conn_pool[pool_id]
	else:
		print 'get_pool(): %s not found!' % pool_id 
		return None

def set_todo(pool_id, new_cookie=None):
	# 添加链接，如果不存在
	if not conn_pool.has_key(pool_id):
		new_pool(pool_id)
	# 设置 cookie
	set_cookie(pool_id, new_cookie)
	print 'set_todo(): %s - %s' % (pool_id, conn_pool[pool_id].proxy.host)
	return get_pool(pool_id)

def close_pool(pool_id):
	global conn_pool
	# 清除连接
	if conn_pool.has_key(pool_id):
		conn_pool.pop(pool_id, None)
	# 清除cookie
	clear_cookie(pool_id)

def http_header(pool_id, host=None, origin=None, refer=None, more=None, isPOST=True):
	header={}
	header['Connection'] = 'keep-alive'
	header['Accept'] = '*/*'
	header['Accept-Language'] = 'zh-CN, en-US'
	header['Accept-Charset'] = 'utf-8, iso-8859-1, utf-16, *;q=0.7'
	header['Accept-Encoding'] = 'gzip,deflate'
	header['User-Agent'] = user_agent
	if isPOST:
		header['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
	if more!=None:
		for h in more:
			header[h[0]] = h[1]
	if host!=None:
		header['Host'] = host
	if origin!=None:
		header['Origin'] = origin
	if refer!=None:
		header['Referer'] = refer
	if len(cookie_pool[pool_id])>0:
		header['Cookie'] = '; '.join('%s=%s' % (k,v) for (k,v) in cookie_pool[pool_id].items())
	#print header
	return header

def http_do_request(pool_id, method, url, header, body=None):
	#print body
	try:
		pool = get_pool(pool_id)
		#print pool, method, url, header
		r = pool.urlopen(method, url, headers=header, body=body)

		# 处理 set-cookie
		if 'set-cookie' in r.headers.keys():
			global cookie_pool
			#print r.headers
			l = r.headers['set-cookie'].split(',')
			for i in l:
				t = i.split(';')[0].split('=')
				if len(t)==2: 
					# cookie变量里有逗号！！！ 要避免！
					#WL_PERSISTENT_COOKIE=8994f904-d72f-4e78-80f0-6c0ebd60f30d; Expires=Sat, 23-Apr-16 07:55:41 GMT; Path=/mobileticket
					cookie_pool[pool_id][t[0].strip()] = t[1].strip()

		if r.status<500: #r.status==200 or r.status==405:
			return r.data
		else:
			print 'HTTP ERROR: ', r.status, url
			return None

	except Exception,e: 
		print '%s: %s (%s)' % (type(e), e, url)
		return None

def http_get(pool_id, url, host=None, origin=None, refer=None, more=None): # 
	# GET
	print url
	header = http_header(pool_id, host, origin, refer, more, isPOST=False)
	return http_do_request(pool_id, 'GET', url, header)

def http_post(pool_id, url, para, host=None, origin=None, refer=None, more=None, json=True): # para 是字典格式的参数(json=False)
	# POST
	if json:
		data = para
	else:
		data = '&'.join(['%s=%s' % (str(k),str(v)) if v!=None else str(k) for (k,v) in para.items()])
	print url
	print para
	header = http_header(pool_id, host, origin, refer, more)
	#header['X-Requested-With'] = 'XMLHttpRequest'
	return http_do_request(pool_id, 'POST', url, header, data)

def http_do_post_encode_body(pool_id, url, body=None): # 用于打码
	#print body
	try:
		pool = get_pool(pool_id)
		#print url
		#print body
		r = pool.request_encode_body('POST', url, fields=body)

		if r.status<500: #r.status==200 or r.status==405:
			return r.data
		else:
			print 'HTTP ERROR: ', r.status, url
			return None

	except Exception,e: 
		print '%s: %s (%s)' % (type(e), e, url)
		return None


#
# --------------- Mobile API to 12306 --------------------------------------------------
#

# 返回结果中的data域
def process_result2(data): # 数据格式 '/*-secure-\n {...} */'
	try:
		data2=json.loads(data.split('\n')[1].split('*')[0])
		print data2
		return (E_OK, data2)
	except ValueError:
		print data
		return (E_JSON, 'load json fail.')

# 登录前准备，出错返回 None，正常返回 True 或 False
def reach(pool_id):
	# POST
	print 'reach()'

	url='https://mobile.12306.cn/otsmobile/apps/services/reach'
	data = http_get(pool_id, url, host='mobile.12306.cn', more=[('X-Requested-With', 'com.MobileTicket')])
	if data==None:
		return (E_QUERY, 'query no return')

	if data=='OK':
		print data
		return (E_OK, data)
	else:
		return (E_DATA, data)

# 登录init1，出错返回 None，正常返回 True 或 False
def init1(pool_id):
	# POST
	print 'init1()'

	url='https://mobile.12306.cn/otsmobile/apps/services/api/MobileTicket/android/init'
	para = 'skin=default&skinLoaderChecksum=&isAjaxRequest=true&x=%.16f' % random.random()
	header = [
		('X-Requested-With', 'XMLHttpRequest'),
		('x-wl-app-version', '2.0'),
		('x-wl-platform-version', '6.0.0'),
	]
	data = http_post(pool_id, url, para, host='mobile.12306.cn', origin='file://', more=header)
	if data==None:
		return (E_QUERY, 'query no return')

	return process_result2(data)

# 登录init2，出错返回 None，正常返回 True 或 False
def init2(pool_id, Authorization, WLInstanceId):
	# POST
	print 'init1()'

	url='https://mobile.12306.cn/otsmobile/apps/services/api/MobileTicket/android/init'
	para = 'skin=default&skinLoaderChecksum=&isAjaxRequest=true&x=%.16f' % random.random()
	header = [
		('X-Requested-With', 'XMLHttpRequest'),
		('x-wl-app-version', '2.0'),
		('x-wl-platform-version', '6.0.0'),
		('Authorization', Authorization),
		('WL-Instance-Id', WLInstanceId)
	]
	data = http_post(pool_id, url, para, host='mobile.12306.cn', origin='file://', more=header)
	if data==None:
		return (E_QUERY, 'query no return')

	return (E_OK, data)
	
