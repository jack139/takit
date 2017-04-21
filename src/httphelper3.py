#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

user_agent = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36'

# qunar专用，不使用代理
conn_pool['QUNAR'] = urllib3.PoolManager(num_pools=100, timeout=CONN_TIMEOUT, retries=False)
cookie_pool['QUNAR'] = {}

# 打码专用
#if setting.enable_proxy:
#	# 测试用，使用fiddler
#	conn_pool['YDM'] = urllib3.ProxyManager(setting.http_proxy, num_pools=10, timeout=CONN_TIMEOUT, retries=False)
#else:
# 生成用，不使用代理
conn_pool['YDM'] = urllib3.PoolManager(num_pools=100, timeout=CONN_TIMEOUT, retries=False)
cookie_pool['YDM'] = {}

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
		cookie_pool[pool_id].pop('BIGipServerotn', None)
		cookie_pool[pool_id].pop('JSESSIONID', None)

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
	header['Accept-Language'] = 'zh-CN,zh;q=0.8'
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
			l = r.headers['set-cookie'].split(',')
			for i in l:
				t = i.split(';')[0].split('=')
				if len(t)==2: 
					# cookie变量里有逗号！！！ 要避免！
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
	header['X-Requested-With'] = 'XMLHttpRequest'
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
# --------------- API to 12306 --------------------------------------------------
#

# 返回sjrand图片随机文件名
def rand_filename():
	return ''.join([random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for ch in range(8)])

# 返回结果中的data域
def process_result(data):
	try:
		data2=json.loads(data)
		print data2
	except ValueError:
		print data
		return (E_JSON, 'load json fail.')

	if data2['status']==True:
		if data2.has_key('data'):
			return (E_OK, data2['data'])
		else:
			return (E_DATA, ' '.join(i for i in data2['messages'] if i).encode('utf-8'))
	else:
		return (E_STATUS, ' '.join(i for i in data2['messages'] if i).encode('utf-8'))


# utf-8字符串转为utf-8，例如 '\xe5\x93\x88\xe5\xb0\x94\xe6\xbb\xa8\xe4\xb8\x9c' -> '%u54C8%u5C14%u6EE8%u4E1C'
def str_to_unicode_code(s):
	b=s.decode('utf-8')
	return repr(b).replace('u','').replace("'",'').upper().replace('\\','%u')
	
# 转义字符串转为utf-8，例如 '\\u6d4b\\u8bd5' -> u'\u6d4b\u8bd5'
def str_to_unicode(s):
	try:
		s2 = json.loads('{"foo":"%s"}' % s.encode('utf-8'))
		return s2['foo']
	except ValueError:
		print "str_to_unicode(): load json fail."
		return None


# 返回变量赋值中的值，类似"var abc={'a':1}"
find_start={}
def get_content(pool_id, whole_str, var_name, end_char=';', split_char='=', add_head='', add_tail='', need_replace=False, no_eval=False):
	global find_start
	
	b = whole_str.find(var_name)
	if b==-1:
		print 'get_content() fail: var_name = %s' % var_name
		return None
	c=whole_str[b:].find(end_char)
	if c==-1:
		print 'get_content() fail: var_name = %s, end_char = %s' % (var_name, end_char)
		return None
	d=whole_str[b:b+c].split(split_char)
	find_start[pool_id] = b+c
	if len(d)!=2:
		print whole_str[b:b+c]
		print 'get_content() fail: var_name = %s, split_char = %s' % (var_name, split_char)
		return None

	e=add_head+d[1]+add_tail
	if no_eval: # 对字符串，可不是用eval
		return e[1:-1]
	try:
		if need_replace:
			return eval(e.replace('null','None').replace('true','True').replace('false','False'))
		else:
			return eval(e)
	except SyntaxError:
		print 'get_content() SyntaxError: var_name = %s, d = %s' % (var_name, str(d))
		return None


# 查询车票信息，出错返回 None，正常返回查询结果，无结果返回[]
def check_ticket(pool_id, begin_station, end_station, check_date, start_time='00:00', end_time='23:59'):
	# GET
	print 'check_ticket(%s, %s, %s)' % (check_date, begin_station, end_station)
	
	today_date = time.strftime('%Y-%m-%d', time.localtime())
	if check_date < today_date: # 不能查询今天前的车次
		return (E_DATA, '不在预售日期范围内')
	
	begin_code=begin_station #stations.find_code(begin_station)
	end_code=end_station #stations.find_code(end_station)
	
	if begin_code=='' or end_code=='':
		return (E_STATION, 'check_ticket(): begin_code and end_code is NULL')
	
	# add cookies
	new_cookie(pool_id, '_jc_save_showZtkyts', 'true')
	new_cookie(pool_id, '_jc_save_detail', 'true')
	new_cookie(pool_id, '_jc_save_fromStation', '%s%%2C%s' % (str_to_unicode_code(stations.find_station(begin_code)), begin_code))
	new_cookie(pool_id, '_jc_save_toStation', '%s%%2C%s' % (str_to_unicode_code(stations.find_station(end_code)), end_code))
	new_cookie(pool_id, '_jc_save_fromDate', check_date)
	new_cookie(pool_id, '_jc_save_toDate', check_date)
	new_cookie(pool_id, '_jc_save_wfdc_flag', 'dc')
	
	# QUERY - log
	url='https://kyfw.12306.cn/otn/leftTicket/log?leftTicketDTO.train_date=%s&leftTicketDTO.from_station=%s&leftTicketDTO.to_station=%s&purpose_codes=ADULT' % \
		(check_date, begin_code, end_code)
	http_get(pool_id, url, host='kyfw.12306.cn', refer='https://kyfw.12306.cn/otn/leftTicket/init', more=[('X-Requested-With', 'XMLHttpRequest')])

	#print "7. query - do query"
	url='https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date=%s&leftTicketDTO.from_station=%s&leftTicketDTO.to_station=%s&purpose_codes=ADULT' % \
		(check_date, begin_code, end_code)
	data = http_get(pool_id, url, host='kyfw.12306.cn', refer='https://kyfw.12306.cn/otn/leftTicket/init', more=[('X-Requested-With', 'XMLHttpRequest')])
	if data==None:
		return (E_QUERY, 'query no return')

	try:
		data2=json.loads(data)
	except ValueError:
		print data
		return (E_JSON, 'json fail')

	if data2['status']==True:
		if data2.has_key("data"):
			tickets=[]
			for train in data2["data"]:
				if train["queryLeftNewDTO"]["start_time"]<start_time or \
				   train["queryLeftNewDTO"]["start_time"]>end_time:
					continue
				tickets.append((train["queryLeftNewDTO"],train["secretStr"]))  # 包括无票车次
			return (E_OK, tickets)
		else:
			return (E_DATA, ' '.join(i for i in data2['messages'] if i).encode('utf-8'))
	else:
		return (E_STATUS, ' '.join(i for i in data2['messages'] if i).encode('utf-8'))


# 取得登录验证码图片，返回图片路径
def get_sjrand(pool_id):
	# GET 图片
	print 'get_sjrand()'

	url='https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=login&rand=sjrand&%.17f' % random.random()
	data = http_get(pool_id, url, host='kyfw.12306.cn', refer='https://kyfw.12306.cn/otn/leftTicket/init')
	if data==None:
		return (E_QUERY, 'query no return')
	
	try:
		# json 说明未取得图片
		data2=json.loads(data)
		print data2
		return (E_IMAGE, ' '.join(i for i in data2['messages'] if i).encode('utf-8'))
	except ValueError:
		# 是图片
		tmp_path=rand_filename()
		print tmp_path
		h=open('%s/%s.png' % (setting.sjrand_path, tmp_path), 'wb')
		h.write(data)
		h.close()
		return (E_OK, tmp_path)

# 取得下单验证码图片，返回图片路径
def get_sjrand_p(pool_id):
	# GET 图片
	print 'get_sjrand_p()'
	
	url='https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew?module=passenger&rand=randp&%.17f' % random.random()
	data = http_get(pool_id, url, host='kyfw.12306.cn', refer='https://kyfw.12306.cn/otn/confirmPassenger/initDc')
	if data==None:
		return (E_QUERY, 'query no return')

	try:
		# json 说明未取得图片
		data2=json.loads(data)
		print data2
		return (E_IMAGE, ' '.join(i for i in data2['messages'] if i).encode('utf-8'))
	except ValueError:
		# 是否是jpeg图片, 20150404
		if data[0:2]!='\xff\xd8':
			# 不是jpeg
			return (E_DATA, 'not JPEG!')

		tmp_path=rand_filename()
		print tmp_path
		h=open('%s/%s.png' % (setting.sjrand_path, tmp_path), 'wb')
		h.write(data)
		h.close()	
		return (E_OK, tmp_path)

# 检查登录验证码，出错返回 None，正常返回 True 或 False
def check_sjrand(pool_id, rand_code):
	# POST
	print 'check_sjrand()'
	
	url='https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn'
	para = 'randCode=%s&rand=sjrand&randCode_validate=' % str(rand_code)

	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/leftTicket/init')
	if data==None:
		return (E_QUERY, 'query no return')

	ret, data2 = process_result(data)
	if ret==E_OK:
		if data2.has_key('result'):
			if data2['result']=='1':
				return (E_OK, True)
			else:
				return (E_OK, False)
		else:
			return (E_FLAG, data2)
	else:
		return (ret, data2)


# 检查下单验证码，出错返回 None，正常返回 True 或 False
def check_sjrand_p(pool_id, rand_code, submit_token):
	# POST
	print 'check_sjrand_p()'
	
	url='https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn'
	para = 'randCode=%s&rand=randp&_json_att=&REPEAT_SUBMIT_TOKEN=%s' % (str(rand_code), str(submit_token))

	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/confirmPassenger/initDc')
	if data==None:
		return (E_QUERY, 'query no return')

	ret, data2 = process_result(data)
	if ret==E_OK:
		if data2.has_key('result'):
			if data2['result']=='1':
				return (E_OK, True)
			else:
				return (E_OK, False)
		else:
			return (E_FLAG, data2)
	else:
		return (ret, data2)


# 取得动态加密参数
# 0 - login
# 1 - leftTicket
#

page_url = [
	{
		'url'   : 'https://kyfw.12306.cn/otn/login/init',
		'host'  : 'kyfw.12306.cn',
		'refer' : 'https://kyfw.12306.cn/otn/'
	},
	{
		'url'   : 'https://kyfw.12306.cn/otn/leftTicket/init',
		'host'  : 'kyfw.12306.cn',
		'refer' : 'https://kyfw.12306.cn/otn/index/init'
	},
]

def get_dynamic_key_from_js(pool_id, js_url, submit_token=None): 
	# GET 取得动态js
	print 'get_dynamic_key_from_js(%s)' % js_url
	
	data = http_get(pool_id, 'https://kyfw.12306.cn'+js_url, host='kyfw.12306.cn', refer='https://kyfw.12306.cn/otn/login/init')
	if data==None:
		return (E_QUERY, 'query no return from js')

	ready_start = data.find('ready(function()')
	if ready_start==-1:
		return (E_DATA, 'ready function not found')

	js_url0 = get_content(pool_id, data[ready_start:], 'url :\'/otn/dynamicJs/', split_char=':', end_char=',', no_eval=True)
	if js_url0!=None:
		print js_url0
		if submit_token==None:
			http_post(pool_id, 'https://kyfw.12306.cn'+js_url0, None, 
				host='kyfw.12306.cn', refer='https://kyfw.12306.cn/otn/login/init',
				more=[('Content-Length', '0')])
		else:
			http_post(pool_id, 'https://kyfw.12306.cn'+js_url0, '_json_att=&REPEAT_SUBMIT_TOKEN=%s' % submit_token, 
				host='kyfw.12306.cn', refer='https://kyfw.12306.cn/otn/confirmPassenger/initDc')

	key = get_content(pool_id, data, 'function gc(){', end_char=';', no_eval=True)
	#print key
	if key==None:
		return (E_DATA, 'key not found')
	else:
		return ( E_OK, ( key, urllib.quote_plus(dynamicJS.encrypt1('1111', key)) ) )

def get_dynamic_key(pool_id, page): 
	# GET
	print 'get_dynamic_key(%d)' % page

	# 取得动态js的url
	data = http_get(pool_id, page_url[page]['url'], host=page_url[page]['host'], refer=page_url[page]['refer'])
	if data==None:
		return (E_QUERY, 'query no return')

	js_url = get_content(pool_id, data, 'src="/otn/dynamicJs', end_char=' type', no_eval=True)
	#print js_url
	if js_url==None:
		return (E_DATA, 'dynamic JS not found')
	else:
		return get_dynamic_key_from_js(pool_id, js_url)


def logout(pool_id): 
	# GET 
	print 'logout()'

	data = http_get(pool_id, 'https://kyfw.12306.cn/otn/login/loginOut', refer='https://kyfw.12306.cn/otn/index/initMy12306')
	return ( E_OK, None ) 

# 12306用户登录，出错返回 None，正常返回 True 或 False
def login(pool_id, uname0, passwd, rand_code, dynamic_key):
	#POST
	uname = uname0.encode('utf-8') # 防止用户名输入中文
	print 'login(%s)' % uname

	url='https://kyfw.12306.cn/otn/login/loginAysnSuggest'

	para = 	'loginUserDTO.user_name=%s&' \
		'userDTO.password=%s&' \
		'randCode=%s&' \
		'randCode_validate=&' \
		'%s=%s&' \
		'myversion=undefined' % (str(uname), str(passwd), str(rand_code), str(dynamic_key[0]), str(dynamic_key[1]))

	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/login/init')
	if data==None:
		return (E_QUERY, 'query no return')

	try:
		data2=json.loads(data)
		print data2
	except ValueError:
		print data
		return (E_JSON, 'json fail')

	if data2['status']==True:
		if data2.has_key('data'):
			if data2['data'].has_key('loginCheck') and data2['data']['loginCheck']=='Y':
				return (E_OK, True)
			else:
				ret = E_LOGIN
		else:
			ret = E_DATA
	else:
		ret = E_STATUS
	return (ret, ' '.join(i for i in data2['messages'] if i).encode('utf-8'))

# 查询常用乘客信息，出错返回 None，正常返回查询结果，无结果返回None
def get_passenger(pool_id):
	# GET
	print 'get_passenger()'
	
	url='https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs'
	data = http_get(pool_id, url)
	if data==None:
		return (E_QUERY, 'query no return')

	return process_result(data)


# 检查用户，出错返回 None，正常返回 True 或 False
def check_user(pool_id):
	# POST
	print 'check_user()'

	url='https://kyfw.12306.cn/otn/login/checkUser'
	para = '_json_att='
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/leftTicket/init')
	if data==None:
		return (E_QUERY, 'query no return')

	ret, data2 = process_result(data)
	if ret==E_OK:
		if data2.has_key('flag'):
			return (E_OK, data2['flag'])
		else:
			return (E_FLAG, 'no flag return')
	elif ret==E_DATA and '其他地点登录' in data2:
		return (E_OK, False)
	else:
		return (ret, data2)


# 提交订单请求，出错返回 None，正常返回 True 或 False
def submit_order_request(pool_id, s, dynamic_key): # secretStr
	# POST
	print 'submit_order_request()'

	print s
	s2=s.replace('%2B','+').replace('%2b','+').replace('%2F','/').replace('%2f','/').replace('%3D','=').replace('%3d','=')
	s3=base64.b64decode(s2).split('#')

	url='https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest'
	para = 	'%s=%s&' \
		'myversion=undefined&' \
		'secretStr=%s&' \
		'train_date=%s&' \
		'back_train_date=%s&' \
		'tour_flag=dc&' \
		'purpose_codes=ADULT&' \
		'query_from_station_name=%s&' \
		'query_to_station_name=%s&' \
		'undefined' % (str(dynamic_key[0]), str(dynamic_key[1]), str(s), str(s3[0]), str(s3[0]), str(s3[9]), str(s[10]))
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/leftTicket/init')
	if data==None:
		return (E_QUERY, 'query no return')

	try:
		data2=json.loads(data)
		print data2
	except ValueError:
		print data
		return (E_JSON, 'json fail')

	if data2['status']==True:
		return (E_OK, True)
	else:
		return (E_STATUS, ' '.join(i for i in data2['messages'] if i).encode('utf-8'))


# 取得车票信息, 出错返回None
def get_initDc(pool_id):
	# POST initDc
	#
	# globalRepeatSubmitToken
	# leftDetails -- 票价信息
	# queryLeftTicketRequestDTO
	# key_check_isChange
	# train_location
	#
	print 'get_initDc()'
	
	url='https://kyfw.12306.cn/otn/confirmPassenger/initDc'
	para ='_json_att='
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/leftTicket/init')
	if data==None:
		return (E_QUERY, 'query no return')
	
	globalRepeatSubmitToken = get_content(pool_id, data, 'globalRepeatSubmitToken')
	if globalRepeatSubmitToken==None:
		return (E_DC1, 'get_initDc(): get globalRepeatSubmitToken fail')

	js_url = get_content(pool_id, data[find_start[pool_id]:], 'src="/otn/dynamicJs', end_char=' type', no_eval=True)
	if js_url==None:
		return (E_JS, 'get_initDc(): get js_url fail')
	
	leftDetails0 = get_content(pool_id, data[find_start[pool_id]:], 'leftDetails', ']', ':', add_tail=']')
	if leftDetails0==None:
		return (E_DC2, 'get_initDc(): get leftDetails fail')
	leftDetails = []
	for i in leftDetails0:
		i2=str_to_unicode(i).encode('utf-8').replace('(','#').replace(')','#').split('#')
		leftDetails.append((stations.SEAT_TYPE[i2[0]],i2[0],i2[1],i2[2]))

	key_check_isChange = get_content(pool_id, data[find_start[pool_id]:], 'key_check_isChange', ',', ':')
	if key_check_isChange==None:
		return (E_DC3, 'get_initDc(): get key_check_isChange fail')

	queryLeftTicketRequestDTO = get_content(pool_id, data[find_start[pool_id]:], 'queryLeftTicketRequestDTO', '}', ':{', '{', '}', True)
	if queryLeftTicketRequestDTO==None:
		return (E_DC4, 'get_initDc(): get queryLeftTicketRequestDTO fail')
	queryLeftTicketRequestDTO['from_station_name']=str_to_unicode(queryLeftTicketRequestDTO['from_station_name']).encode('utf-8')
	queryLeftTicketRequestDTO['to_station_name']=str_to_unicode(queryLeftTicketRequestDTO['to_station_name']).encode('utf-8')

	train_location = get_content(pool_id, data[find_start[pool_id]:], 'train_location', '}', ':')
	if train_location==None:
		return (E_DC5, 'get_initDc(): get train_location fail')
	
	return (E_OK, {
			'repeat_submit_token'  : globalRepeatSubmitToken,
			'left_details'         : leftDetails,
			'key_check_isChange'   : key_check_isChange,
			'query_ticket_request' : queryLeftTicketRequestDTO,
			'train_location'       : train_location,
			'js_url'               : js_url
	})

# 返回 True / False, 出错返回None
def check_order_info(pool_id, submit_token, rand_code_p, passengers, seat_type, dynamic_key):
	#POST
	print 'check_order_info()'
	
	passengerTicketStr=''
	oldPassengerStr=''
	for p in passengers:
		ap='%s,0,%s,%s,%s,%s,,N_' % (seat_type, p['ticketType'], p['name'], p['certType'], p['certNo'])
		passengerTicketStr += ap.encode('utf-8')
		ao='%s,%s,%s,%s_' % (p['name'], p['certType'], p['certNo'], p['ticketType'])
		oldPassengerStr += ao.encode('utf-8')
	
	#print repr(passengerTicketStr)
		
	url='https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo'
	para = 	'cancel_flag=2&' \
		'bed_level_order_num=000000000000000000000000000000&' \
		'passengerTicketStr=%s&' \
		'oldPassengerStr=%s&' \
		'tour_flag=dc&' \
		'randCode=%s&' \
		'%s=%s&' \
		'_json_att=&' \
		'REPEAT_SUBMIT_TOKEN=%s' % \
		(
			urllib.quote_plus(passengerTicketStr), 
			urllib.quote_plus(oldPassengerStr),
			str(rand_code_p),
			str(dynamic_key[0]), str(dynamic_key[1]),
			str(submit_token)
		)
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/confirmPassenger/initDc')
	if data==None:
		return (E_QUERY, 'query no return')

	ret, data2 = process_result(data)
	if ret==E_OK:
		if data2.has_key('submitStatus'):
			if data2['submitStatus']==True:
				return (E_OK, True)
			else:
				if data2.has_key('errMsg'):
					last_messages = data2['errMsg'].encode('utf-8')
				else:
					last_messages = 'check order fail'
				return (E_CHECK_ORDER, last_messages)
		else:
			return (E_FLAG, 'no submitStatus')
	else:
		return (ret, data2)


# 处理日期格式，并url编码
def format_date(t):
	b = time.strptime(t+' 00:00:00','%Y%m%d %H:%M:%S')
	c = time.strftime('%a %b %d %Y %H:%M:%S',b)
	d = '%s GMT+0800 (中国标准时间)' % c
	return urllib.quote_plus(d).replace('%28','(').replace('%29',')')

# 返回 data
def get_queue_count(pool_id, submit_token, train_info, seat_type):
	#POST
	print 'get_queue_count()'

	url='https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount'
	para = 	'train_date=%s&' \
		'train_no=%s&' \
		'stationTrainCode=%s&' \
		'seatType=%s&' \
		'fromStationTelecode=%s&' \
		'toStationTelecode=%s&' \
		'leftTicket=%s&' \
		'purpose_codes=%s&' \
		'_json_att=&' \
		'REPEAT_SUBMIT_TOKEN=%s' % \
		(
			str(format_date(train_info['train_date'])),
			str(train_info['train_no']),
			str(train_info['station_train_code']),
			str(seat_type),
			str(train_info['from_station']),
			str(train_info['to_station']),
			str(train_info['ypInfoDetail']),
			str(train_info['purpose_codes']),
			str(submit_token)
		)
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/confirmPassenger/initDc')
	if data==None:
		return (E_QUERY, 'query no return')

	return process_result(data)


def confirm_single_for_queue(pool_id, submit_token, rand_code_p, passengers, seat_type, train_info):
	#POST
	print 'confirm_single_for_queue()'

	passengerTicketStr=''
	oldPassengerStr=''
	for p in passengers:
		ap='%s,0,%s,%s,%s,%s,,N_' % (seat_type, p['ticketType'], p['name'], p['certType'], p['certNo'])
		passengerTicketStr += ap.encode('utf-8')
		ao='%s,%s,%s,%s_' % (p['name'], p['certType'], p['certNo'], p['ticketType'])
		oldPassengerStr += ao.encode('utf-8')

	url='https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue'
	para = 	'passengerTicketStr=%s&' \
		'oldPassengerStr=%s&' \
		'randCode=%s&' \
		'purpose_codes=%s&' \
		'key_check_isChange=%s&' \
		'leftTicketStr=%s&' \
		'train_location=%s&' \
		'dwAll=N&' \
		'_json_att=&' \
		'REPEAT_SUBMIT_TOKEN=%s' % \
		(
			urllib.quote_plus(passengerTicketStr),
			urllib.quote_plus(oldPassengerStr),
			str(rand_code_p),
			str(train_info['purpose_codes']),
			str(train_info['key_check_isChange']),
			str(train_info['ypInfoDetail']),
			str(train_info['train_location']),
			str(submit_token)
		)
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/confirmPassenger/initDc')
	if data==None:
		return (E_QUERY, 'query no return')

	ret, data2 = process_result(data)
	if ret==E_OK:
		if data2.has_key('submitStatus'):
			if data2['submitStatus']==True:
				return (E_OK, True)
			else:
				if data2.has_key('errMsg'): # 20150428
					return (E_DATA, data2['errMsg'].encode('utf-8'))
				else:
					return (E_DATA, 'confirm_single_for_queue fail')
		else:
			return (E_FLAG, 'no submitStatus')
	else:
		return (ret, data2)


# 检查排队结果，返回data， 出错返回None
def query_order_wait_time(pool_id, submit_token):
	# GET
	print 'query_order_wait_time()'

	url='https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?random=%d&tourFlag=dc&_json_att=&REPEAT_SUBMIT_TOKEN=%s' % \
		(int(time.time()*1000), submit_token)
	data = http_get(pool_id, url, host='kyfw.12306.cn', refer='https://kyfw.12306.cn/otn/confirmPassenger/initDc')
	if data==None:
		return (E_QUERY, 'query no return')

	return process_result(data)


# 确认结果，返回True / False
def result_order_for_DcQueue(pool_id, submit_token, order_no):
	# POST
	print 'result_order_for_DcQueue()'

	url='https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue'
	para = 'orderSequence_no=%s&_json_att=&REPEAT_SUBMIT_TOKEN=%s' % (str(order_no), str(submit_token))
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/confirmPassenger/initDc')
	if data==None:
		return (E_QUERY, 'query no return')

	ret, data2=process_result(data)
	if ret==E_OK:
		if data2.has_key('submitStatus'):
			return (E_OK, data2['submitStatus'])
		else:
			return (E_FLAG, 'no submitStatus')
	else:
		return (ret, data2)

# 实时添加乘客信息，返回data
def real_add(pool_id, submit_token, passenger):
	# POST
	print 'real_add()'

	#print repr(passenger['name'])
	url='https://kyfw.12306.cn/otn/passengers/realAdd'
	para = 	'passenger_name=%s&' \
		'passenger_id_type_code=%s&' \
		'passenger_id_no=%s&' \
		'passenger_type=%s&' \
		'country_code=CN&' \
		'_json_att=&' \
		'REPEAT_SUBMIT_TOKEN=%s' % \
		(
			urllib.quote_plus(passenger['name'].encode('utf-8')),
			str(passenger['certType']),
			str(passenger['certNo']),
			str(passenger['ticketType']),
			str(submit_token)
		)
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/confirmPassenger/initDc')
	if data==None:
		return (E_QUERY, 'query no return')

	ret, data2=process_result(data)
	if ret==E_OK:
		if data2.has_key('flag'):
			if data2['flag']==True:
				if data2.has_key('totalTimes'):
					if data2['totalTimes']=='99':
						return (E_OK, True)
					elif data2['totalTimes']=='98':
						return (E_REAL_ADD, '乘客信息待核验')
					else:
						return (E_REAL_ADD, '乘客信息出错（%s）' % data2['totalTimes'].encode('utf-8'))
				else:
					return (E_REAL_ADD, '乘客信息出错，没有totalTimes')
			else:
				return (E_REAL_ADD, data2['message'].encode('utf-8'))
		else:
			return (E_FLAG, 'no flag')
	else:
		return (ret, data2)

# 查询未完成的订单，返回data
def query_order_no_complete(pool_id):
	# POST
	print 'query_order_no_complete()'

	url='https://kyfw.12306.cn/otn/queryOrder/queryMyOrderNoComplete'
	para = '_json_att='
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/queryOrder/initNoComplete')
	if data==None:
		return (E_QUERY, 'query no return')

	return process_result(data)

# 查询已完成的订单，返回data
def query_my_order(pool_id, where='G'):
	# POST
	print 'query_my_order()'

	start_date = time.strftime('%Y-%m-%d', time.localtime(time.time()-3600*24*90))
	end_date = time.strftime('%Y-%m-%d', time.localtime())

	url='https://kyfw.12306.cn/otn/queryOrder/queryMyOrder'
	para = 	'queryType=1&' \
		'queryStartDate=%s&' \
		'queryEndDate=%s&' \
		'come_from_flag=my_order&' \
		'pageSize=8&' \
		'pageIndex=0&' \
		'query_where=%s&' \
		'sequeue_train_name=' % (start_date, end_date, where)

	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/queryOrder/init')
	if data==None:
		return (E_QUERY, 'query no return')

	return process_result(data)

# 所有已完成订单
def query_my_order_all(pool_id):
	print 'query_my_order_all()'

	ret, data = query_my_order(pool_id, 'G')
	if ret==E_OK:
		if data['order_total_number']=='':
			data['order_total_number']=0
		ret, data2 = query_my_order(pool_id, 'H')
		if ret==E_OK:
			if data2['order_total_number']=='':
				data2['order_total_number']=0
			data['order_total_number'] += data2['order_total_number']
			data['OrderDTODataList'] += data2['OrderDTODataList']
	return (ret, data)


# 取消未完成的订单，返回data
def cancel_no_complete_order(pool_id, ticket_no):
	# POST
	print 'cancel_no_complete_order()'

	url='https://kyfw.12306.cn/otn/queryOrder/cancelNoCompleteMyOrder'
	para = 'sequence_no=%s&cancel_flag=cancel_order&_json_att=' % str(ticket_no)
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/queryOrder/initNoComplete')
	if data==None:
		return (E_QUERY, 'query no return')

	return process_result(data)


# 取得query_order里的token, 出错返回None
def get_token_from_query_order(pool_id):
	# POST
	
	#
	# globalRepeatSubmitToken
	#
	print 'get_token_from_query_order()'
	
	url='https://kyfw.12306.cn/otn/queryOrder/init'
	para = '_json_att='
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/index/initMy12306')
	if data==None:
		return (E_QUERY, 'query no return')
	
	globalRepeatSubmitToken = get_content(pool_id, data, 'globalRepeatSubmitToken', no_eval=True)
	if globalRepeatSubmitToken==None:
		return (E_DC1, 'get_token_from_query_order(): get globalRepeatSubmitToken fail')
	else:
		return (E_OK, globalRepeatSubmitToken)


# 退票(订单中多张票，要一张一张退)，返回data
def return_ticket_affirm(pool_id, submit_token, order_db, ticket_info): # ticket_info 格式与 ticket_no_complete 相同
	# POST
	print 'return_ticket_affirm()'

	url='https://kyfw.12306.cn/otn/queryOrder/returnTicketAffirm'
	para = 	'sequence_no=%s&' \
		'batch_no=%s&' \
		'coach_no=%s&' \
		'seat_no=%s&' \
		'start_train_date_page=%s&' \
		'train_code=%s&' \
		'coach_name=%s&' \
		'seat_name=%s&' \
		'seat_type_name=%s&' \
		'train_date=%s&' \
		'from_station_name=%s&' \
		'to_station_name=%s&' \
		'start_time=%s&' \
		'passenger_name=%s&' \
		'_json_att=' % \
		(
			str(ticket_info['sequence_no']),
			str(ticket_info['batch_no']), 
			str(ticket_info['coach_no']), 
			str(ticket_info['seat_no']), 
			str(order_db['start_train_date_page']), 
			str(order_db['train_code_page']), 
			str(ticket_info['coach_name'].encode('utf-8')), 
			str(ticket_info['seat_name'].encode('utf-8')), 
			str(ticket_info['seat_type_name'].encode('utf-8')), 
			str(ticket_info['train_date']), 
			str(ticket_info['stationTrainDTO']['from_station_name'].encode('utf-8')), 
			str(ticket_info['stationTrainDTO']['to_station_name'].encode('utf-8')), 
			str(ticket_info['stationTrainDTO']['start_time']), 
			str(ticket_info['passengerDTO']['passenger_name'].encode('utf-8'))
		)
	if submit_token not in ('null', 'nul'):
		para+= '&REPEAT_SUBMIT_TOKEN=%s' % str(submit_token)

	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/queryOrder/init')
	if data==None:
		return (E_QUERY, 'query no return')

	return process_result(data)


# 确认退票, 出错返回None
def return_ticket(pool_id, submit_token):
	# POST
	
	print 'return_ticket()'
	
	url='https://kyfw.12306.cn/otn/queryOrder/returnTicket'
	para = '_json_att='
	if submit_token not in ('null', 'nul'):
		para+= '&REPEAT_SUBMIT_TOKEN=%s' % str(submit_token)

	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/queryOrder/init')
	if data==None:
		return (E_QUERY, 'query no return')
	
	if '退票成功' in data:
		return (E_OK, '')
	else:
		print data
		return (E_RETURN_TICKET, '未知错误，退票失败')


# 支付未完成订单，返回data
def pay_no_complete_order(pool_id, ticket_no):
	# POST
	print 'pay_no_complete_order()'

	url='https://kyfw.12306.cn/otn/queryOrder/continuePayNoCompleteMyOrder'
	para = 'sequence_no=%s&pay_flag=pay&_json_att=' % str(ticket_no)
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/queryOrder/initNoComplete')
	if data==None:
		return (E_QUERY, 'query no return')

	ret,data2 = process_result(data)
	if ret==E_OK:
		if data2.has_key('existError'):
			if data2['existError']=='N':
				return (E_OK, '')
			elif data2.has_key('errorMsg'):
				return (E_FLAG, data2['errorMsg'].encode('utf-8'))
			else:
				return (E_FLAG, data2)
		else:
			return (E_PAY, data2)
	else:
		return (ret, data2)


# 检查支付情况，返回data
def pay_check(pool_id):
	# POST
	print 'pay_check()'

	url='https://kyfw.12306.cn/otn/payOrder/paycheck'
	para = '_json_att='
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/payOrder/init')
	if data==None:
		return (E_QUERY, 'query no return')

	ret,data2 = process_result(data)
	if ret==E_OK:
		if data2.has_key('flag'):
			if data2['flag']==True:
				if data2.has_key('payForm'):
					return (E_OK, data2['payForm'])
				else:
					return (E_DATA, data2)
		if data2.has_key('message'):
			return (E_PAY, data2['message'].encode('utf-8'))
		else:
			return (E_PAY, data2)
	else:
		return (ret, data2)


# 支付: 进入支付页面，返回data
def pay_gateway(pool_id, pay_form):
	# POST
	print 'pay_gateway()'

	url='https://epay.12306.cn/pay/payGateway'
	para = 	'_json_att=&' \
		'interfaceName=%s&' \
		'interfaceVersion=%s&' \
		'tranData=%s&' \
		'merSignMsg=%s&' \
		'appId=%s&' \
		'transType=%s' % \
		(
			str(pay_form['interfaceName']),
			str(pay_form['interfaceVersion']),
			urllib.quote_plus(pay_form['tranData']),
			urllib.quote_plus(pay_form['merSignMsg']),
			str(pay_form['appId']),
			str(pay_form['transType'])
		)
	data = http_post(pool_id, url, para, 'epay.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/payOrder/init')
	if data==None:
		return (E_QUERY, 'query no return')

	global find_start
	offset = data.find('name="tranData"')
	channelId = merCustomIp = orderTimeoutDate = None
	while 1:
		find_start[pool_id] = 0
		value = get_content(pool_id, data[offset:], 'type="hidden" value=', 
				split_char='="hidden" value=', end_char=' n', no_eval=True)
		if value==None:
			break
		offset+=find_start[pool_id]
		find_start[pool_id] = 0
		name = get_content(pool_id, data[offset:], 'ame', end_char='/>')
		if name==None:
			break
		offset+=find_start[pool_id]
		if name=='channelId':
			channelId = value
		elif name=='merCustomIp':
			merCustomIp = value
		elif name =='orderTimeoutDate':
			orderTimeoutDate = value
	if channelId==None or merCustomIp==None or orderTimeoutDate==None:
		return (E_DC1, 'pay_gateway(): get varibles fail')
	else:
		return (E_OK, { 
			'channelId'        : channelId, 
			'merCustomIp'      : merCustomIp, 
			'orderTimeoutDate' : orderTimeoutDate 
		})


# 支付: 取得支付宝参数，返回data
def pay_web_business(pool_id, pay_form, gateway_result):
	# POST
	print 'pay_web_business()'

	url='https://epay.12306.cn/pay/webBusiness'
	para = 	'tranData=%s&' \
		'transType=%s&' \
		'channelId=%s&' \
		'appId=%s&' \
		'merSignMsg=%s&' \
		'merCustomIp=%s&' \
		'orderTimeoutDate=%s&' \
		'bankId=33000010' % \
		(
			urllib.quote_plus(pay_form['tranData']),
			str(pay_form['transType']),
			str(gateway_result['channelId']),
			str(pay_form['appId']),
			urllib.quote_plus(pay_form['merSignMsg']),
			str(gateway_result['merCustomIp']),
			str(gateway_result['orderTimeoutDate'])
		)
	data = http_post(pool_id, url, para, 'epay.12306.cn', 'https://epay.12306.cn', 'https://epay.12306.cn/pay/payGateway')
	if data==None:
		return (E_QUERY, 'query no return')

	global find_start
	offset = data.find('name="myform"')
	alipay_form = {}
	while 1:
		find_start[pool_id] = 0
		name = get_content(pool_id, data[offset:], 'type="hidden"  name=', 
				split_char='="hidden"  name=', end_char=' v', no_eval=True)
		if name==None:
			break
		offset+=find_start[pool_id]
		find_start[pool_id] = 0
		value = get_content(pool_id, data[offset:], 'alue', split_char='ue=', end_char='>')
		if value==None:
			break
		offset+=find_start[pool_id]
		alipay_form[name]=value

	if len(alipay_form)<17:
		print alipay_form
		return (E_DC1, 'pay_web_business(): get varibles fail')
	else:
		return (E_OK, alipay_form)


# 常用联系人
def passengers_query(pool_id, page, page_size):
	# POST
	print 'passengers_query(%d, %d)' % (page, page_size)

	url='https://kyfw.12306.cn/otn/passengers/query'
	para = 'pageIndex=%d&pageSize=%d' % (page, page_size)
	data = http_post(pool_id, url, para, 'kyfw.12306.cn', 'https://kyfw.12306.cn', 'https://kyfw.12306.cn/otn/passengers/init')
	if data==None:
		return (E_QUERY, 'query no return')

	return process_result(data)

# 所有常用联系人
def passengers_query_all(pool_id):
	print 'passengers_query_all()'

	ret, data = passengers_query(pool_id, 1, 10)
	if ret==E_OK:
		if data['pageTotal']>1:
			for i in range(2, data['pageTotal']+1):
				ret, data2 = passengers_query(pool_id, i, 10)
				if ret==E_OK:
					data['datas'] += data2['datas']
	return (ret, data)

# 修改登录密码
def edit_login_pwd(pool_id, pwd, new_pwd):
	# POST
	print 'edit_login_pwd(%s, %s)' % (pwd, new_pwd)

	url='https://kyfw.12306.cn/otn/userSecurity/editLoginPwd'
	para = 'password=%s&password_new=%s&confirmPassWord=%s' % (pwd, new_pwd, new_pwd)
	data = http_post(pool_id, url, para, host='kyfw.12306.cn', refer='https://kyfw.12306.cn/otn/userSecurity/loginPwd')
	if data==None:
		return (E_QUERY, 'query no return')

	return process_result(data)


## ============= Qunar API =================================================
#
#  注意：公用12306的连接池，所以会带有12306的cookie，如果必要，调用qunar时需要删除cookie
#

AGENT_ID  = ''
AGENT_KEY = ''
if setting.enable_local_test:
	QUNAR_URL = 'http://192.168.2.98:82/test' # 内部测试
else:
	QUNAR_URL = 'http://api.pub.train.qunar.com/api/pub/'  # 正式环境


def QUNAR_process_result(data):
	try:
		data2=json.loads(data)
		print data2
	except ValueError:
		print data
		return (E_JSON, 'json fail')

	return (E_OK, data2)


# 取得订单, 正常返回订单内容，错误返回None
def QUNAR_query_orders(pool_id, refund=False):
	# GET
	print 'QUNAR_query_orders()'
	
	if refund:
		query_type='APPLY_REFUND'
	else:
		query_type='WAIT_TICKET'
		
	HMAC = hashlib.md5('%s%s%s' % (AGENT_KEY, AGENT_ID, query_type)).hexdigest().upper()

	url='%s/QueryOrders.do?merchantCode=%s&type=%s&HMAC=%s' % (QUNAR_URL, AGENT_ID, query_type, HMAC)
	#print url

	data = http_get('QUNAR', url)
	if data==None:
		return (E_QUERY, 'query no return')

	return QUNAR_process_result(data)


# 提交订票结果, 正常返回结果，错误返回None
def QUNAR_process_purchase(pool_id, orderNo, result=None, reason='', passengerReason=None, comment='', un=''):
	# POST
	print 'QUNAR_process_purchase()'
	
	if result==None:
		opt='NO_TICKET'
		result1=''
	else:
		opt='CONFIRM'
		result1=json.dumps(result, ensure_ascii=False).encode('utf-8')
	
	if passengerReason==None:
		passengerReason1=''
	else:
		passengerReason1=json.dumps(passengerReason, ensure_ascii=False).encode('utf-8')

	if len(comment)>80:
		comment0=comment.decode('utf-8')[:33].encode('utf-8')
	else:
		comment0=comment

	HMAC = hashlib.md5(
		'%s%s%s%s%s%s%s%s%s' % (AGENT_KEY, AGENT_ID, orderNo, opt, result1, un, str(reason), passengerReason1, comment0)
		).hexdigest().upper()

	para = 'merchantCode=%s&orderNo=%s&opt=%s&result=%s&un=%s&reason=%s&passengerReason=%s&comment=%s&HMAC=%s' % \
		(AGENT_ID,orderNo,opt,result1,un,str(reason),passengerReason1,comment0,HMAC)
	#print para

	url='%s/ProcessPurchase.do' % QUNAR_URL
	
	while 1:
		data = http_post('QUNAR', url, para, json=True)
		if data!=None:
			break
		else:
			time.sleep(1)

	return QUNAR_process_result(data)


# 提交退票结果, 正常返回结果，错误返回None
def QUNAR_process_refund(pool_id, orderNo, agree=True, reason='', comment=''):
	# POST
	print 'QUNAR_process_refund()'
	
	if agree:
		opt='AGREE'
	else:
		opt='REFUSE'

	if len(comment)>80:
		comment0=comment.decode('utf-8')[:33].encode('utf-8')
	else:
		comment0=comment

	HMAC = hashlib.md5(
		'%s%s%s%s%s%s' % (AGENT_KEY, AGENT_ID, orderNo, opt, comment0, str(reason))
		).hexdigest().upper()

	para = 'merchantCode=%s&orderNo=%s&opt=%s&comment=%s&reason=%s&HMAC=%s' % \
		(AGENT_ID,orderNo,opt,comment0,str(reason),HMAC)
	#print para

	url='%s/ProcessRefund.do' % QUNAR_URL
	
	while 1:
		data = http_post('QUNAR', url, para, json=True)
		if data!=None:
			break
		else:
			time.sleep(1)

	return QUNAR_process_result(data)

# 提交原路退款请求, 正常返回结果，错误返回None
def QUNAR_process_apply_auto_refund(pool_id, orderNo, cash, reason, comment=''):
	# POST
	print 'QUNAR_process_apply_auto_refund()'

	if len(comment)>80:
		comment0=comment.decode('utf-8')[:33].encode('utf-8')
	else:
		comment0=comment

	HMAC = hashlib.md5(
		'%s%s%s%s%s%s' % (AGENT_KEY, AGENT_ID, orderNo, str(cash), str(reason), comment0)
		).hexdigest().upper()

	para = 'merchantCode=%s&orderNo=%s&refundCash=%s&reason=%s&comment=%s&HMAC=%s' % \
		(AGENT_ID,orderNo,str(cash),str(reason),comment0,HMAC)
	#print para

	url='%s/ProcessApplyAutoRefund.do' % QUNAR_URL
	while 1:
		data = http_post('QUNAR', url, para, json=True)
		if data!=None:
			break
		else:
			time.sleep(1)

	return QUNAR_process_result(data)


# 代付请求, 正常返回结果，错误返回None
def QUNAR_process_auto_pay(pool_id, orderNo, price, un, comment=''):
	# POST
	print 'QUNAR_process_auto_pay()'

	if len(comment)>99:
		comment0=comment.decode('utf-8')[:33].encode('utf-8')
	else:
		comment0=comment

	HMAC = hashlib.md5(
		'%s%s%s%s%s%s' % (AGENT_KEY, AGENT_ID, orderNo, str(price), un, comment0)
		).hexdigest().upper()

	para = 'merchantCode=%s&orderNo=%s&price=%s&un=%s&comment=%s&HMAC=%s' % \
		(AGENT_ID,orderNo,str(price),un,comment0,HMAC)
	#print para
	
	url='%s/ProcessGoPay.do' % QUNAR_URL
	while 1:
		data = http_post('QUNAR', url, para, json=True)
		if data!=None:
			break
		else:
			time.sleep(1)

	return QUNAR_process_result(data)


# 占座回调请求, 正常返回结果，错误返回None
def QUNAR_reservation_callback(pool_id, url, orderNo, result, status, code='', msg='', comment=''):
	# POST
	print 'QUNAR_reservation_callback()'

	if len(comment)>80:
		comment0=comment.decode('utf-8')[:33].encode('utf-8')
	else:
		comment0=comment

	HMAC = hashlib.md5(
		'%s%s%s%s%s%s%s%s' % (AGENT_KEY, AGENT_ID, orderNo, result, status, code, msg, comment0)
		).hexdigest().upper()

	para = 'merchantCode=%s&orderNo=%s&result=%s&status=%s&code=%s&msg=%s&comment=%s&HMAC=%s' % \
		(AGENT_ID,orderNo,result,status,code,msg,comment0,HMAC)
	#print para
	
	#url='%s/???.do' % QUNAR_URL
	while 1:
		data = http_post('QUNAR', url, para, json=True)
		if data!=None:
			break
		else:
			time.sleep(1)

	return QUNAR_process_result(data)
