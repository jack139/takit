#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#
import socket, urllib2, cookielib
import json, hashlib
from config import setting

if setting.enable_proxy:
	proxy_handler = urllib2.ProxyHandler({"https" : setting.https_proxy, "http" : setting.http_proxy})
else:
	proxy_handler = urllib2.ProxyHandler({})

# 处理cookie
cookie = cookielib.CookieJar()
cookie_handler = urllib2.HTTPCookieProcessor(cookie)

# 设置opener
opener = urllib2.build_opener(proxy_handler, cookie_handler)
urllib2.install_opener(opener)

user_agent = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36'
#user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:23.0) Gecko/20100101 Firefox/23.0'


E_OK		= 0
E_QUERY		= -1
E_JSON		= -2
E_DATA		= -3
E_IMAGE		= -6

#
# ----------------- HTTP GET/POST ---------------------------------------------
#

socket.setdefaulttimeout(60)

def http_request(url, host='', origin='', refer='', more=None, para=None): # 
	try:
		if para==None:
			request = urllib2.Request(url) # GET
		else:
			request = urllib2.Request(url, para) # POST
		request.add_header('Accept', '*/*')
		request.add_header('Accept-Language', 'zh-CN,zh;q=0.8')
		request.add_header('Accept-Encoding', 'gzip,deflate')
		#request.add_header('Cache-Control' , 'no-cache')
		request.add_header('User-Agent', user_agent)
		request.add_header('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8')
		if more!=None:
			request.add_header(more[0], more[1])
		if host!='':
			request.add_header('Host', host)
		if origin!='':
			request.add_header('Origin', origin)
		if refer!='':
			request.add_header('Referer', refer)
		
		return request

	except Exception,e: 
		print '%s: %s (%s)' % (type(e), e, url)
		return None

def http_do_request(request):
	try:
		f = urllib2.urlopen(request)

		data = f.read()
		f.close()

		#for item in cookie:
		#	print 'Cookie: %s = %s' % (item.name, item.value)

		return data

	except Exception,e: 
		print '%s: %s (%s)' % (type(e), e, request.get_full_url())
		return None

def http_get(url, host='', origin='', refer='', more=None): # 
	# GET
	request = http_request(url, host, origin, refer, more)
	if request==None:
		return None

	return http_do_request(request)


def http_post(url, para, host='', origin='', refer='', more=None, json=True): # para 是字典格式的参数(json=False)
	# POST
	if json:
		data = para
	else:
		data = '&'.join(['%s=%s' % (str(k),str(v)) if v!=None else str(k) for (k,v) in para.items()])
	request = http_request(url, host, origin, refer, more, data)
	if request==None:
		return None

	request.add_header('X-Requested-With', 'XMLHttpRequest')
	#request.add_header('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8')

	return http_do_request(request)


def get_cookie_value(c): # c 是 cookielib.Cookie 实例，返回 cookie字典
	cv = {
		'version'		:	c.version, 
		'name'			:	c.name, 
		'value'			:	c.value,
		'port'			:	c.port,
		'port_specified'	:	c.port_specified,
		'domain'		:	c.domain,
		'domain_specified'	:	c.domain_specified,
		'domain_initial_dot'	:	c.domain_initial_dot,
		'path'			:	c.path,
		'path_specified'	:	c.path_specified,
		'secure'		:	c.secure,
		'expires'		:	c.expires,
		'discard'		:	c.discard,
		'comment'		:	c.comment,
		'comment_url'		:	c.comment_url,
		'rfc2109'		:	c.rfc2109
	}
	return cv

def set_cookie_value(c): # c 是cookie字典, 返回 cookielib.Cookie 实例
	ck = cookielib.Cookie(
		version			=	c['version'],
		name			=	c['name'],
		value			=	c['value'],
		port			=	c['port'],
		port_specified		=	c['port_specified'],
		domain			=	c['domain'],
		domain_specified	=	c['domain_specified'],
		domain_initial_dot	=	c['domain_initial_dot'],
		path			=	c['path'],
		path_specified		=	c['path_specified'],
		secure			=	c['secure'],
		expires			=	c['expires'],
		discard			=	c['discard'],
		comment			=	c['comment'],
		comment_url		=	c['comment_url'],
		rest			=	{},
		rfc2109			=	c['rfc2109']
	)
	return ck

def new_cookie(name, value): # 添加新cookie
	ck = cookielib.Cookie(
		version			=	0,
		name			=	name,
		value			=	value,
		port			=	None,
		port_specified		=	False,
		domain			=	'kyfw.12306.cn',
		domain_specified	=	False,
		domain_initial_dot	=	False,
		path			=	'',
		path_specified		=	False,
		secure			=	False,
		expires			=	None,
		discard			=	True,
		comment			=	None,
		comment_url		=	None,
		rest			=	{},
		rfc2109			=	False
	)
	cookie.set_cookie(ck)

def get_cookie(): # c 是 cookielib.CookieJar 实例, 返回 cookie字典 的列表(存入db)
	cv = [get_cookie_value(i) for i in cookie]
	return cv

def set_cookie(cv): # c 是 cookielib.CookieJar 实例, cv 是 元素为cookie字典 的 列表(来自db)
	cookie.clear()
	for i in cv:
		cookie.set_cookie(set_cookie_value(i))

def clear_cookie(): # 
	cookie.clear()




## ============= Takit API test =================================================
API_UID = 'app'
API_ID = 'Q4XV3WAU'
API_KEY = 'aebf7bda2f16525ebba4f26004fbf8e6f379e772'
#
# 查询车次信息
def takit_query(dept, arri, date):
	import json
	# POST
	print 'takit_query'

	HMAC = hashlib.md5(
		'%s%s%s%s%s' % (API_KEY, API_ID, dept, arri, date)
		).hexdigest().upper()

	para = {
		'api'       : API_UID,
		'api_key'   : API_ID,
		'departure' : dept,
		'arrival'   : arri,
		'date'      : date,
		'secret'    : HMAC
	}
	print para

	url='https://192.168.2.98:82/api/query'
	data = http_post(url, json.dumps(para), json=True)

	if data==None:
		return (E_QUERY, 'query no return')

	return QUNAR_process_result(data)

# 下单
def takit_order(task, login_info, passengers, seat_type, s):
	import json, base64
	# POST
	print 'takit_query'
	
	login_info = base64.b64encode(json.dumps(login_info))
	passengers = base64.b64encode(json.dumps(passengers))
	
	HMAC = hashlib.md5(
		'%s%s%s%s%s%s' % (API_KEY, API_ID, task, s, login_info, passengers)
		).hexdigest().upper()

	para = {
		'api'        : API_UID,
		'api_key'    : API_ID,
		'task'       : task,
		's'          : s,
		'login_info' : login_info,
		'passengers' : passengers,
		'seat_type'  : seat_type,
		'secret'     : HMAC
	}
	print para

	url='https://192.168.2.98:82/api/order'
	data = http_post(url, json.dumps(para), json=True)

	if data==None:
		return (E_QUERY, 'query no return')

	return QUNAR_process_result(data)

# 查询结果
def takit_result(task, result='result'):
	import json
	# POST
	print 'takit_query'
	
	HMAC = hashlib.md5(
		'%s%s%s%s' % (API_KEY, API_ID, task, result)
		).hexdigest().upper()

	para = {
		'api'     : API_UID,
		'api_key' : API_ID,
		'task'    : task,
		'data'    : result,
		'secret'  : HMAC
	}
	print para

	url='https://192.168.2.98:82/api/result'
	data = http_post(url, json.dumps(para), json=True)

	if data==None:
		return (E_QUERY, 'query no return')

	return QUNAR_process_result(data)

#
# 查询常用联系人
def takit_passengers(login_info):
	import json, base64
	# POST
	print 'takit_query'

	login_info = base64.b64encode(json.dumps(login_info))
	
	HMAC = hashlib.md5(
		'%s%s%s' % (API_KEY, API_ID, login_info)
		).hexdigest().upper()

	para = {
		'api'        : API_UID,
		'api_key'    : API_ID,
		'login_info' : login_info,
		'secret'     : HMAC
	}
	print para

	url='https://192.168.2.98:82/api/passengers'
	data = http_post(url, json.dumps(para), json=True)

	if data==None:
		return (E_QUERY, 'query no return')

	return QUNAR_process_result(data)


## ============= Qunar callback test =================================================
AGENT_ID  = 'xcslw'
AGENT_KEY = '27316DD7742B441CB705D210FCA8FC0A'
QUNAR_URL = 'http://192.168.2.98:82'

def QUNAR_process_result(data):
	try:
		data2=json.loads(data)
		print data2
	except ValueError:
		print data
		return (E_JSON, 'json fail')

	return (E_OK, data2)

#
# 查询车次信息
def test_reservation(orderNo):
	import json
	# POST
	print 'test_reservation()'
	
	#orderNo="xyxhc140221160433005-58"
	reqFrom='qunar'
	reqTime='20150320202020'
	trainNo='6225'
	from0='哈尔滨东'
	to='哈尔滨'
	date='2015_03_30'
	retUrl='%s/test/reserve_callback' % QUNAR_URL
	passengers=json.dumps([ 
		{ 
			"certNo"     : "12010419760404761X", 
			"certType"   : "1", 
			"name"       : "关涛", 
			"ticketType" : "1",
			"seatCode"   : "1"
		}, 
		{ 
			"certNo"     : "12010419760404761X", 
			"certType"   : "1", 
			"name"       : "关可贞", 
			"ticketType" : "2",
			"seatCode"   : "1"
		}, 
	])
	HMAC='hmac'

	para = {
		'orderNo'    : orderNo,
		'reqFrom'    : reqFrom,
		'reqTime'    : reqTime,
		'trainNo'    : trainNo,
		'from'       : from0,
		'to'         : to,
		'date'       : date,
		'retUrl'     : retUrl,
		'passengers' : passengers,
		'HMAC'       : HMAC
	}
	print para

	url='%s/qunar/reservation' % QUNAR_URL
	data = http_post(url, para, json=False)

	if data==None:
		return (E_QUERY, 'query no return')

	return QUNAR_process_result(data)


#
# 代付结果
def test_auto_pay_finish(orderNo, ret=1):
	import json
	# POST
	print 'test_auto_pay_finish()'
	
	#orderNo="xyxhc140221160433005-58"
	payStatus=ret
	HMAC='hmac'

	para = {
		'orderNo'    : orderNo,
		'payStatus'  : payStatus,
		'HMAC'       : HMAC
	}
	print para

	url='%s/qunar/pay_result' % QUNAR_URL
	data = http_post(url, para, json=False)

	if data==None:
		return (E_QUERY, 'query no return')

	return QUNAR_process_result(data)

# 取消占座
def test_cancel(orderNo):
	import json
	# POST
	print 'test_cancel()'
	
	#orderNo="xyxhc140221160433005-58"
	reqFrom='qunar'
	reqTime='20150322'
	HMAC='hmac'

	para = {
		'orderNo'    : orderNo,
		'reqFrom'    : reqFrom,
		'reqTime'    : reqTime,
		'HMAC'       : HMAC
	}
	print para

	url='%s/qunar/cancel' % QUNAR_URL
	data = http_post(url, para, json=False)

	if data==None:
		return (E_QUERY, 'query no return')

	return QUNAR_process_result(data)
