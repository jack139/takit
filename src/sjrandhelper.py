#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#
import socket, urllib
import json, base64, random
import httphelper
from config import setting

#
# --------------- API to suanya --------------------------------------------------
#

def read_img(f_img):
	try:
		h=open(f_img, 'rb')
	except IOError, e:
		print 'read_img() IOError: %s' % str(e)
		return None
	data = h.read()
	h.close()
	return urllib.quote_plus(base64.b64encode(data))

# 检查登录验证码
def text_sjrand(img, host=None):
	# POST
	print 'text_sjrand()'

	while host==None:
		host = 's%d' % random.randint(0,39)
		if host in ('s6', 's39'):
			host = None
		else:
			break

	img_data=read_img(img)

	if img_data==None:
		return (httphelper.E_IMAGE, 'read_img() fail')

	url='http://%s.suanya.cn/shell/img' % host
	para = 'callBy=login&d=%s&v=2.1.7&c=2' % img_data
	data = httphelper.http_post(url, para, '%s.suanya.cn' % host, more=('sykey','12306.cn_n'))
	if data==None:
		return (httphelper.E_QUERY, 'query no return')

	print data
	if len(data)==4:
		return (httphelper.E_OK, data)
	else:
		return (httphelper.E_DATA, data)

# launch
def launch():
	# POST
	print 'launch()'

	url='http://suanya.cn/zx/json/launch'
	a = {
		"ruleVersion":"2",
		"clientVersion":"2.2.4",
		"emei":"863360028272973",
		"data":{
			"userName":"jack_139",
			"clientVersion":"2.2.4",
			"sysVersion":"4.4.4",
			"emei":"863360028272973",
			"markets":"com.xiaomi.market|com.android.vending",
			"model":"MI 3W",
			"ruleVersion":"",
			"sid":8,
			"configVersion":379,
			"clientId":35240156
		},
		"clientId":35240156,
		"configVersion":379
	}

	para = json.dumps(a)

	data = httphelper.http_post(url, para, 'suanya.cn')
	if data==None:
		return (httphelper.E_QUERY, 'query no return')

	print data
	return (httphelper.E_OK, data)
