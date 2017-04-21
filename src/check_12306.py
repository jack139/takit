#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 检查12306用户是否正常
# 
# 注意: 请在非工作时间运行此程序
#
import sys, time, gc, os
import json
import helper, stations
import httphelper3, httphelper, sjrandhelper
from config import setting

db = setting.db_web

#
# 目前需手工处理的status: SJRAND, SJRAND_P, PAY
#


def main_loop(u12306):
	# { 
	#	"_id" : ObjectId("54479246f43515cc1f491a54"), 
	#	"last_time" : 1420599592.583044, 
	#	"passwd" : "xxxxx", 
	#	"status" : "OK", 
	#	"uname" : "jack139@gmail.com" 
	# }

	# 处理事件
	print '----> %s: %s %s %s' % (helper.time_str(), str(u12306['_id']), u12306['uname'], u12306['status'])

	db_todo={
		'status'      : 'ORDER', 
		'retry'       : 0,
		'login_retry' : 0,
	}

	while 1:
		DELAY=0
		if db_todo.has_key('comment') and db_todo['comment']!='':
			print '%s: %s' % (db_todo['status'], db_todo['comment'])
			db_todo['comment']=''
		sys.stdout.flush()

		if db_todo['status']=='ORDER':
			# 准备https连接
			httphelper3.set_todo('test')

			# 准备cookie
			httphelper3.remove_session_cookie('test')
			httphelper3.new_cookie('test', 'current_captcha_type','C')

			# 取得动态加密串
			ret, dynamic_key=httphelper3.get_dynamic_key('test', db_todo['_id'], 0)
			if ret<0:
				db_todo['comment']='0|get_dynamic_key(0)|%s.' % dynamic_key
				db_todo['status']='ORDER'
				continue
			else:
				db_todo['dynamic_key']=dynamic_key

			# 取得验证码图片
			ret, sjrand=httphelper3.get_sjrand('test')
			if ret<0:
				db_todo['retry']=db_todo['retry']+1
				db_todo['comment']='0|get_sjrand|%s.' % sjrand
				if db_todo['retry']<5:
					db_todo['status']='ORDER'
			else:
				db_todo['status']='SJRAND2'
				db_todo['sjrand']=sjrand
				db_todo['retry']=0

		elif db_todo['status']=='SJRAND2':
			# 清空cookie，为打码
			httphelper.clear_cookie() 

			ret, data = sjrandhelper.text_sjrand('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand']))
			if ret<0:
				# 5此获取失败，则手工打码
				db_todo['comment']='0|text_sjrand|打码失败.'
				db_todo['status']='SJRAND2'
				continue

			db_todo['rand_code']=data

			# 准备https连接
			httphelper3.set_todo('test', db_todo['cookie'])

			ret, data2 = httphelper3.check_sjrand('test', data)
			if ret==httphelper3.E_OK and data2==True:
				db_todo['status']='LOGIN'
				DELAY=2
			else:
				# 检测随机码失败，重新打码
				db_todo['status']='ORDER'

		elif db_todo['status']=='LOGIN':
			# 准备https连接
			httphelper3.set_todo('test', db_todo['cookie'])

			# check随机码
			ret, data = httphelper3.check_sjrand('test', db_todo['rand_code'])
			if ret==httphelper3.E_OK and data==True:
				db_todo['status']='LOGIN2'
				DELAY=1
			else:
				# 检测随机码失败，重新打码
				db_todo['status']='ORDER'

		elif db_todo['status']=='LOGIN2':
			# 准备https连接
			httphelper3.set_todo('test', db_todo['cookie'])

			# 登录12306
			ret, data = httphelper3.login('test', u12306['uname'], 
						u12306['passwd'], db_todo['rand_code'], db_todo['dynamic_key'])

			if ret!=httphelper3.E_OK:
				db_todo['comment']='0|login|%s.' % data
				if '登陆失败' in data or '不存在' in data or '密码输入错误' in data:
					# 12306 用户有问题
					db.user_12306.update({'uname':u12306['uname']},{'$set':{'status':data}})
					break
				elif '网络繁忙' in data:
					db_todo['status']='ORDER'
					DELAY=3
				else:
					# 登录失败，重新验证码
					new_path = '_%s' % (db_todo['sjrand'])
					db_todo['sjrand']=new_path
					try:
						os.rename('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand']), 
							  '%s/%s.png' % (setting.sjrand_path, new_path))
					except OSError:
						pass
					db_todo['status']='ORDER'
					DELAY=3
			else:
				# 登录成功
				# 记录已识别的随机码
				new_path = '_%s_%s' % (db_todo['sjrand'], db_todo['rand_code'])
				db_todo['sjrand']=new_path
				try:
					os.rename('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand']), 
						  '%s/%s.png' % (setting.sjrand_path, new_path))
				except OSError:
					pass
	
				# 检查用户登录
				ret, data = httphelper3.check_user('test')
				if ret<0: # 包括 E_DATA 的可能
					db_todo['comment']='0|check_user|%s.' % data
					db_todo['status'] = 'ORDER'
				elif data==False: # 未登录
					db_todo['comment']='0|check_user|未登录.'
					db_todo['status'] = 'ORDER'
				else:
					db_todo['comment']='0|check_user|用户正常登录-OK.'
					if u12306['status']!='READY': # 非自动添加用户
						db.user_12306.update({'uname':u12306['uname']},{'$set':{'status':'OK'}})
					break
	
		db_todo['cookie'] = httphelper3.get_cookie('test') # 保存cookie
		time.sleep(DELAY)  # DELAY 秒后再继续执行

	httphelper3.close_pool('test') # 处理结束，删除https连接
	print '----> %s: %s\n' % (helper.time_str(), db_todo['comment'])


if __name__=='__main__':
	print "PROCESSOR: %s started" % helper.time_str()

	gc.set_threshold(300,5,5)

	try:
		db_user=db.user_12306.find()
		if db_user.count()<=0:
			print '数据库中无用户！'
		else:
			for u in db_user:
				main_loop(u)
	
				# 周期性打印日志
				time.sleep(0.2)
				sys.stdout.flush()

	except KeyboardInterrupt:
		print
		print 'Ctrl-C!'

	print "PROCESSOR: %s exited" % helper.time_str()
