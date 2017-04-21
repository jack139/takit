#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 后台服务进程，后台运行 - 多线程版本
#
# 1. 检查todo，是否有event
# 2. 按event和status处理
#
# ！！！需改进：
#		对中断的处理：kill信号
#
import sys, time, gc #, os
import threading
import json, random
import helper, stations
import httphelper3, httphelper, sjrandhelper3, sjrandhelper
from config import setting

db = setting.db_web

SJRAND_MAX = 1 # 默认打码最大队列
AUTO_SJRAND = 0 # 默认禁止外包打码
AUTO_SJRAND_P = 0 # 默认禁止外包打码
PAY_THRESHOLD = 0 # 默认全部先代付

#
# 目前需手工处理的status: SJRAND, SJRAND_P, PAY
#

def waring(s): # 输出到stderr
	sys.stderr.write(s)

# ------- 计算图片坐标

img_xy = {
	1:{'x':(6,72),   'y':(12,78)},
	2:{'x':(78,144), 'y':(12,78)},
	3:{'x':(150,216),'y':(12,78)},
	4:{'x':(222,288),'y':(12,78)},
	5:{'x':(6,72),   'y':(84,150)},
	6:{'x':(78,144), 'y':(84,150)},
	7:{'x':(150,216),'y':(84,150)},
	8:{'x':(222,288),'y':(84,150)},
}

def sjrand_xy(rand_pos): # 返回坐标串
	import random
	r = ()
	for n in rand_pos:
		if n>8 or n<1:
			continue
		x = random.randint(img_xy[n]['x'][0]+5, img_xy[n]['x'][1]-5)
		y = random.randint(img_xy[n]['y'][0]+5, img_xy[n]['y'][1]-5)
		r += (x,y)
	return ','.join(str(i) for i in r)

def main_loop(tname):
	global SJRAND_MAX, AUTO_SJRAND, AUTO_SJRAND_P, PAY_THRESHOLD

	# 取事件队列，取得入口status
	db_todo0=db.todo.find_and_modify(
		query = {'$and': [
					{'lock' : 0},
					{'man'  : 0},
					#{'event' : {'$ne' : 'ORDER_API'}}, # 不处理API事件
					{'e_time' : {'$lt': int(time.time())}}, # 不执行未来的事件
					{'$or'  : [
							{'status':{'$ne':'FINISH'}},
							{'return': 1}
						]
					}
				]
			},
		update= {'$set': {'lock':1}},
		sort  = [('e_time',1)],
		fields= {'status':1}
	)

	if db_todo0==None: # 队列中没有要处理的event
		#sys.stdout.write('.')
		hh = time.localtime().tm_hour
		idle_time = random.randint(1,5) # 随机休息1-5秒
		
		if hh==5: # 5点统计清零
			db.thread.update({'tname':tname},{'$set':{
				'0':0,   '1':0,  '2':0,  '3':0,  '4':0,  '5':0,  '6':0,  '7':0,
				'8':0,   '9':0, '10':0, '11':0, '12':0, '13':0, '14':0, '15':0,
				'16':0, '17':0, '18':0, '19':0, '20':0, '21':0, '22':0, '23':0,				
			}}, upsert=True)
		else:
			db.thread.update({'tname':tname},{'$inc':{str(hh):idle_time}},upsert=True)

		time.sleep(idle_time) 
		return

	#print "%s: %s - enter loop ...." % (tname helper.time_str())

	while 1: # 连续处理status

		# 取得todo的实际数据
		db_todo=db.todo.find_one({'_id':db_todo0['_id']})
		
		process_time = helper.time_str()
	
		# 处理事件
		print '%s: %s - %s %s %s' % (tname, process_time, str(db_todo['_id']), db_todo['event'], db_todo['status'])
	
		todo_update={ # 不再处理, 默认出错返回
			'status'  : 'FAIL',
			'man'     : 0,
			#'lock'    : 0,
		}
		DELAY=0
	
		# 添加 history
		#if db_todo.has_key('history'):
		#	todo_update['history']=db_todo['history']
		#else:
		#	todo_update['history']=[]
		#todo_update['history'].append((tname, process_time, db_todo['status']))


		while 1: # 方便跳出

			# API 订单暂时不处理
			#if db_todo['event']=='ORDER_API' and db_todo['status']!='QUERY': 
			#	todo_update['comment']='1|QUERY|12306调整，暂时不能提供服务。'
			#	todo_update['status']='FINISH'
			#	break
	
			# 开始处理status
			if db_todo['status']=='SLEEP': # 20150404
				# 检查打码队列
				sjrand_queue = db.todo.find({'status':{'$in':['SJRAND','SJRAND_P','SJRAND3_RESULT']}}).count()
				if sjrand_queue >= SJRAND_MAX:
					# 队列太大，按紧急程度安排等候
					todo_update['status']='SLEEP'
					if db_todo.has_key('orderTick'): # 兼容旧数据 20150426
						if db_todo['e_time']-db_todo['orderTick']>600:
							# 处理时间超过5分钟的，优先进入队列处理
							DELAY = 3
						else:
							# 其他等待15秒
							DELAY = 15
					else:
						DELAY = 15
				else:
					# 跳转到next_status 20150406
					todo_update['status']=db_todo['next_status'].encode('utf-8')
					todo_update['next_status']=''

			elif db_todo['status']=='NO_TICKET':
				# 手工无票处理
				todo_update['comment']='1|NO_TICKET|无票'
				break
				
			elif db_todo['status']=='QUERY':
				# 全部无票 （测试用）
				#todo_update['comment']='1|QUERY|无票'
				#break
	
				# 准备https连接
				if db_todo['event']=='ORDER_API': # API订单会共用一个连接
					if db_todo.has_key('cookie'):
						httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
					else:
						httphelper3.set_todo(str(db_todo['_id']))
				else:
					httphelper3.set_todo(str(db_todo['_id']))
	
				# 获取bigip和session的cookie
				httphelper3.check_user(str(db_todo['_id'])) 
	
				# 查询车次
				ret, data = httphelper3.check_ticket(
					str(db_todo['_id']),
					db_todo['start_station'],
					db_todo['stop_station'],
					db_todo['start_date']
				)
				if ret<0:
					if '查询失败' in data:
						todo_update['comment']='0|check_ticket|%s.' % data
						todo_update['status']='QUERY'
					elif '不在预售日期范围内' in data:
						todo_update['comment']='1|check_ticket|%s.' % data
					else:
						todo_update['comment']='0|check_ticket|%s.' % data
					break;
				
				todo_update['login_retry']=0 # 登录失败计数
	
				if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT'):
					# 检查车次是否有票
					todo_update['comment']='4|QUERY|未查到车次'
					for item in data:
						if item[0]['station_train_code'] in db_todo['trainNo'].split('/'):
							if item[1]=="": # 无票
								todo_update['comment']='1|QUERY|无票'
								break
							if db_todo['reservation']==0 and \
								item[0]['start_time'].split(':')[0]!=db_todo['start_time'].split(':')[0]: 
								# 开车时间是否正确, 只检查整点时间，不检查分钟
								todo_update['comment']='4|QUERY|开车时间错误'
								break
							# 有票
							todo_update['status']='ORDER'
							todo_update['query']=item
							todo_update['secretStr']=item[1]
							todo_update['comment']=''
							todo_update['user_12306']=''
							break
					#todo_update['result']=data
				else:
					todo_update['status']='FINISH'
					todo_update['result']=data
	
	
			elif db_todo['status']=='ORDER':
				if db_todo['event']=='ORDER_API': # API订单会共用一个连接
					# 准备https连接
					if db_todo.has_key('cookie'):
						httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
					else:
						httphelper3.set_todo(str(db_todo['_id']))
	
					# 准备cookie
					httphelper3.new_cookie(str(db_todo['_id']), 'current_captcha_type','Z')
	
					# 检查用户登录
					ret, data = httphelper3.check_user(str(db_todo['_id']))
					if ret<0: # 包括 E_DATA 的可能
						todo_update['comment']='0|check_user|%s.' % data
						break
					if data==True: # 已登录，直接去预订
						todo_update['login_retry']=0 # 登录失败计数
						todo_update['status'] = 'VERIFY0' 
						break
				else:
					# 准备https连接
					httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
		
					# 准备cookie
					httphelper3.remove_session_cookie(str(db_todo['_id']))
					httphelper3.new_cookie(str(db_todo['_id']), 'current_captcha_type','Z')
	
				# 取得动态加密串
				ret, dynamic_key=httphelper3.get_dynamic_key(str(db_todo['_id']), 0)
				if ret<0:
					todo_update['comment']='0|get_dynamic_key(0)|%s.' % dynamic_key
					break
				else:
					todo_update['dynamic_key']=dynamic_key
	
				# 取得验证码图片
				ret, sjrand=httphelper3.get_sjrand(str(db_todo['_id']))
				if ret<0:
					todo_update['retry']=db_todo['retry']+1
					todo_update['comment']='0|get_sjrand|%s.' % sjrand
					if todo_update['retry']<5:
						todo_update['status']='ORDER'
				else:
					print 'AUTO SJRAND: %s' % ('Enabled' if AUTO_SJRAND==1 else 'Disabled')
					if AUTO_SJRAND==1:
						todo_update['status']='SJRAND3' # 外包云打码
						todo_update['next_status_sjrand']='LOGIN' # 打码成功的跳转
						todo_update['sjrand_count']=0
					else:
						todo_update['status']='SJRAND' # 人工打码
						todo_update['man']=1
					todo_update['sjrand']=sjrand
					todo_update['retry']=0

			elif db_todo['status']=='SJRAND2':
				# 清空cookie，为打码
				httphelper.clear_cookie() 
	
				ret, data = sjrandhelper.text_sjrand('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand']))
				if ret<0:
					if ret==httphelper.E_DATA:
						# 打码识别失败，结果不是4位，重新打码
						todo_update['status']='ORDER'
					else:
						if db_todo['event']=='ORDER_API': # API 订单，直接退出
							todo_update['comment']='0|text_sjrand|后台服务繁忙，请稍后再试.'
							todo_update['status']='FINISH'
							break
						else:
							# 失败(网络问题？)，则手工打码
							todo_update['status']='SJRAND'
							todo_update['man']=1
							todo_update['retry']=0
							break
	
				todo_update['rand_code']=data
	
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				ret, data2 = httphelper3.check_sjrand(str(db_todo['_id']), data)
				if ret==httphelper3.E_OK and data2==True:
					if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT', 'ORDER_API'):
						todo_update['status']='LOGIN'
						#DELAY=0.5 #2
					else:
						# ORDER_UI
						if db_todo.has_key('user_12306') and db_todo['user_12306']!='':
							# 重复登录的时候，不需要再手工输入用户名/密码
							todo_update['status']='LOGIN'
							#DELAY=0.5 #2
						else:
							# 输入用户密码
							todo_update['status']='SJRAND'
							todo_update['man']=1
				else:
					# 检测随机码失败，重新打码
					todo_update['status']='ORDER'

			elif db_todo['status']=='SJRAND3': # 云打码	
				if db_todo['next_status_sjrand']=='LOGIN':
					image_name = db_todo['sjrand']
				else:
					image_name = db_todo['sjrand_p']
				ret, data = sjrandhelper3.upload('%s.png' % image_name)
				if ret<0:
					if db_todo['event']=='ORDER_API': # API 订单，直接退出
						todo_update['comment']='0|text_sjrand|后台服务繁忙，请稍后再试.'
						todo_update['status']='FINISH'
						todo_update['next_status_sjrand']=''
						break
					else:
						# 失败(网络问题？)，则手工打码
						if db_todo['next_status_sjrand']=='LOGIN':
							todo_update['status']='SJRAND'
						else:
							todo_update['status']='SJRAND_P'
						todo_update['next_status_sjrand']=''
						todo_update['man']=1
						todo_update['retry']=0
						break
				else:
					todo_update['cid']=data['cid']
					todo_update['status']='SJRAND3_RESULT'
					DELAY=5

			elif db_todo['status']=='SJRAND3_RESULT': # 云打码查询结果
				ret, data = sjrandhelper3.result(db_todo['cid'])
				if ret<0:
					if ret==httphelper3.E_DATA and data['ret']==-3002 and db_todo['sjrand_count']<6: # 识别进行中
						todo_update['status']='SJRAND3_RESULT'
						todo_update['sjrand_count']=db_todo['sjrand_count']+1
						DELAY=5
						break
					if db_todo['event']=='ORDER_API': # API 订单，直接退出
						todo_update['comment']='0|text_sjrand|后台服务繁忙，请稍后再试.'
						todo_update['status']='FINISH'
					else:
						# 失败(网络问题？)，则手工打码
						if db_todo['next_status_sjrand']=='LOGIN':
							todo_update['status']='SJRAND'
						else:
							todo_update['status']='SJRAND_P'
						todo_update['man']=1
						todo_update['retry']=0
					todo_update['next_status_sjrand']=''
					break
				else:
					# 看不清，转人工打码
					if '看不清' in data['text'].encode('utf-8'):
						if db_todo['event']=='ORDER_API': # API 订单，直接退出
							todo_update['comment']='0|text_sjrand|后台服务繁忙，请稍后再试.'
							todo_update['status']='FINISH'
						else:
							# 失败，则手工打码
							if db_todo['next_status_sjrand']=='LOGIN':
								todo_update['status']='SJRAND'
							else:
								todo_update['status']='SJRAND_P'
							todo_update['man']=1
							todo_update['retry']=0
						todo_update['next_status_sjrand']=''
						break		
					
					# 计算虚拟坐标
					sj_xy=[]
					for c in data['text']:
						if not c.isdigit():
							sj_xy.append(1)
						else:
							sj_xy.append(int(c))
					sj_rand = sjrand_xy(sj_xy)
					if db_todo['next_status_sjrand']=='LOGIN':
						todo_update['rand_code']=sj_rand
					else:
						todo_update['rand_code_p']=sj_rand
					#todo_update['status']='LOGIN'

					if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT', 'ORDER_API'):
						todo_update['status']=db_todo['next_status_sjrand']
						#DELAY=0.5 #2
					else:   # ORDER_UI
						if db_todo['next_status_sjrand']=='LOGIN':
							if db_todo.has_key('user_12306') and db_todo['user_12306']!='':
								# 重复登录的时候，不需要再手工输入用户名/密码
								todo_update['status']='LOGIN'
								#DELAY=0.5 #2
							else:
								# 输入用户密码
								todo_update['status']='SJRAND'
								todo_update['man']=1
						else:
							todo_update['status']='SJRAND_P'
							todo_update['man']=1
					todo_update['next_status_sjrand']=''
						
			elif db_todo['status']=='LOGIN':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
					
				# check随机码
				ret, data = httphelper3.check_sjrand(str(db_todo['_id']), db_todo['rand_code'])
				if ret==httphelper3.E_OK and data==True:
					if db_todo.has_key('cid'):
						sjrandhelper3.report(db_todo['cid'], 1) # 回报打码正确
					todo_update['status']='LOGIN2'
				else:
					# 检测随机码失败，重新打码
					if db_todo.has_key('cid'):
						sjrandhelper3.report(db_todo['cid'], 0) # 回报打码错误
					todo_update['status']='ORDER'
	
			elif db_todo['status']=='LOGIN2':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT') and \
					(not (db_todo.has_key('user_12306') and db_todo['user_12306']!='')):
					# 查找可用的12306用户, 对新处理接口订单（非退票订单）
					db_u12306=db.user_12306.find_and_modify(
						query={'$and':[{'status': 'OK'},{'online':1}]},
						update={'$set': {'last_time':time.time(), 'status':db_todo['_id']}},
						sort=[('last_time',1)]
					)
					if db_u12306==None: # 没有可用的12306用户
						todo_update['status']='LOGIN'
						todo_update['comment']='0|LOGIN|没有可用的12306用户，等待释放...'
						break
					todo_update['user_12306']=db_u12306['uname']
					todo_update['pass_12306']=db_u12306['passwd']
				else:
					# 使用用户输入的12306账户
					db_u12306={
						'uname'  : db_todo['user_12306'],
						'passwd' : db_todo['pass_12306'],
					}
					 # 退票登录等重复登录，已知用户名
					if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT') and db_todo['next_status']!='CHANGE_PWD':
						# 占用12306用户
						db_u12306=db.user_12306.find_and_modify(
							query={'$and':[
									{'uname': db_todo['user_12306']},
									{'$or':[{'status': 'OK'}, {'status': db_todo['_id']}]}
								]},
							update={'$set': {'last_time':time.time(), 'status':db_todo['_id']}}
						)
						if db_u12306==None: # 12306用户，暂时不可用, 停留等待
							todo_update['status']='LOGIN'
							todo_update['comment']='0|LOGIN|12306用户被占用，等待释放...'
							break
						# 更新12306登录密码， 20150413
						todo_update['pass_12306']=db_u12306['passwd']

				# 登录12306
				ret, data = httphelper3.login(
					str(db_todo['_id']), 
					db_u12306['uname'], 
					db_u12306['passwd'], 
					db_todo['rand_code'], 
					db_todo['dynamic_key']
				)
	
				if ret!=httphelper3.E_OK:
					todo_update['comment']='0|login|%s.' % data
					if '不存在' in data or '密码输入错误' in data:
						if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT'): #and db_todo['next_status']!='CHANGE_PWD':
							# 12306 用户有问题
							db.user_12306.update({'uname':db_u12306['uname']},{'$set':{'status':data}})
							if db_todo['next_status']=='': # 换个用户试试（只对非跳转的登录）, 20150420
								todo_update['user_12306']=''
								todo_update['status']='ORDER'
					elif '网络繁忙' in data and db_todo['next_status']=='':
						if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT'):
							# 换个用户试试（只对非跳转的登录）
							db.user_12306.update({'uname':db_u12306['uname']},{'$set':{'status':'OK'}})
							todo_update['user_12306']=''
						todo_update['status']='ORDER'
						DELAY=3
					else:
						# 登录失败，重新验证码
						#new_path = '_%s' % (db_todo['sjrand'])
						todo_update['login_retry']=db_todo['login_retry']+1
						if (todo_update['login_retry']<5) and ('系统维护' not in data):
							todo_update['status']='ORDER'
						#todo_update['sjrand']=new_path
						#try:
						#	os.rename('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand']), 
						#		  '%s/%s.png' % (setting.sjrand_path, new_path))
						#except OSError:
						#	pass
					break
	
				# 登录成功
				# 记录已识别的随机码
				#new_path = '_%s_%s' % (db_todo['sjrand'], db_todo['rand_code'])
				#todo_update['sjrand']=new_path
				#try:
				#	os.rename('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand']), 
				#		  '%s/%s.png' % (setting.sjrand_path, new_path))
				#except OSError:
				#	pass
	
				#处理12306用户
				if db_todo['event'] in ('ORDER_UI', 'ORDER_API'):
					# 新用户则加入数据库
					db_tmp=db.user_12306.find_one({'uname': db_u12306['uname']},{'_id':1})
					if db_tmp==None: # 如果数据库中无此用户，添加到数据库中
						db.user_12306.insert({
							'uname'   : db_u12306['uname'],
							'passwd'  : db_u12306['passwd'],
							'status'  : 'READY',
							'auto_pay': 0,
							'online'  : 0,
							'comment' : 'auto_add' # 标记‘自动添加’
						})
	
				# 如果是next_status，跳转去指定status
				if db_todo['next_status']!='':
					todo_update['status']=db_todo['next_status'].encode('utf-8')
					todo_update['next_status']=''
					break
	
				todo_update['status']='VERIFY0'
				todo_update['retry']=0
	
			elif db_todo['status']=='VERIFY0':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break
				if data==False: # 未登录
					todo_update['status'] = 'ORDER'
					break
	
				# 提交order
				ret, data = httphelper3.submit_order_request(str(db_todo['_id']), db_todo['secretStr'], db_todo['dynamic_key'])
				if ret<0:
					todo_update['comment']='0|submit_order_request|%s.' % data
					if '车票信息已过期' in data:
						if db_todo['event'] in ('ORDER_UI', 'ORDER_API'):
							todo_update['status']='FAIL'
						else:
							todo_update['status']='QUERY'
					elif '不可购票' in data: 
						if db_todo['event'] in ('ORDER_UI', 'ORDER_API'):
							# 12306用户有问题，换个用户试试 2015.03.31
							db.user_12306.update({'uname':db_todo['user_12306']},{'$set':{'status':data}})
							todo_update['user_12306']=''
							todo_update['status']='ORDER'
					break
	
				# 取得initDc页面
				ret, data = httphelper3.get_initDc(str(db_todo['_id']))
				if ret<0:
					todo_update['comment']='0|get_initDc|%s.' % data
					break
				todo_update['initDc']=data
	
				# 从js取得动态加密串
				ret, dynamic_key = httphelper3.get_dynamic_key_from_js(str(db_todo['_id']), data['js_url'], data['repeat_submit_token'])
				if ret<0:
					todo_update['comment']='0|get_dynamic_key_from_js|%s.' % dynamic_key
					break
				todo_update['dynamic_key']=dynamic_key
	
				todo_update['status']='VERIFY'
				todo_update['retry']=0
	
			elif db_todo['status']=='VERIFY':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				# 对接口订单，检查seat_type是否有效
				if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT'):
					# 检查座席
					left_seat = [tkt[0] for tkt in db_todo['initDc']['left_details']]
					if db_todo['seat_type'] not in left_seat:
						# 首先座席不可用，在备选座席里选
						seat_ok = False
						for seat in db_todo['ext_seat_type']:
							if seat in left_seat:
								seat_ok = True
								todo_update['seat_type'] = seat
								break
						if seat_ok==False: # 没有合适的座席类型
							todo_update['comment'] = '1|VERIFY|没有合适的座席类型'
							break
					if db_todo['reservation']==0: # 检查票价, 对订座订单不检查
						price_ok=False
						for s in db_todo['initDc']['left_details']:
							if db_todo['seat_type']==s[0]:
								if s[2]!='--': # 有些没有价格信息，赌一把 20150501
									s_price=float(s[2].encode('utf-8').split('元')[0])
									if s_price in db_todo['seat'].values():
										price_ok=True
									elif s_price in [i.values()[0] for i in db_todo['extSeat']]:
										price_ok=True
								else:
									price_ok=True
								break
						if price_ok==False: # 票价不对
							todo_update['comment'] = '3|VERIFY|票价不对'
							break
				elif db_todo['event']=='ORDER_API':
					# 对API 订单，只检查座席合法性
					# 检查座席
					left_seat = [tkt[0] for tkt in db_todo['initDc']['left_details']]
					if db_todo['seat_type'] not in left_seat:
						# 如果是动车高铁出现无座（硬座），改为二等座，无座按二等座票价
						if db_todo['seat_type']==stations.SEAT_TYPE['无座'] and db_todo['initDc']['query_ticket_request']['station_train_code'][0] in ('D', 'G', 'C'):
							todo_update['seat_type'] = stations.SEAT_TYPE['二等座']
						elif db_todo['seat_type']==stations.SEAT_TYPE['软卧'] and db_todo['initDc']['query_ticket_request']['station_train_code'][0] in ('D', 'G', 'C'): 
							todo_update['seat_type'] = stations.SEAT_TYPE['动卧']
						elif db_todo['seat_type']==stations.SEAT_TYPE['高级软卧'] and db_todo['initDc']['query_ticket_request']['station_train_code'][0] in ('D', 'G', 'C'): 
							todo_update['seat_type'] = stations.SEAT_TYPE['高级动卧']
						else:
							print "座席选择有问题，可能有新座席类别！"

				# 取得验证码图片
				ret, sjrand=httphelper3.get_sjrand_p(str(db_todo['_id']))
				if ret<0:
					if 'not JPEG' in sjrand: # 不是jpeg, 20150404
						todo_update['status']='ORDER'
					if '网络繁忙' in sjrand:
						todo_update['status']='ORDER'
					else:
						todo_update['retry']=db_todo['retry']+1
						todo_update['comment']='0|get_sjrand_p|%s.' % sjrand
						if todo_update['retry']<5:
							todo_update['status']='VERIFY'
				else:
					print 'AUTO SJRAND_P: %s' % ('Enabled' if AUTO_SJRAND_P==1 else 'Disabled')
					if AUTO_SJRAND_P==1:
						todo_update['status']='SJRAND3' # 外包云打码
						todo_update['next_status_sjrand']='BOOK' # 打码成功的跳转
						todo_update['sjrand_count']=0
					else:
						todo_update['status']='SJRAND_P' # 人工打码
						todo_update['man']=1
					todo_update['sjrand_p']=sjrand
					todo_update['retry']=0

			elif db_todo['status']=='SJRAND_P2':
				# 清空cookie，为打码
				httphelper.clear_cookie() 
	
				ret, data = sjrandhelper.text_sjrand('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand_p']))
				if ret<0:
					if ret==httphelper.E_DATA:
						# 打码识别失败，结果不是4位，重新打码
						todo_update['status']='VERIFY'
					else:
						if db_todo['event']=='ORDER_API': # API 订单，直接退出
							todo_update['comment']='0|text_sjrand|后台服务繁忙(2)，请稍后再试.'
							todo_update['status']='FINISH'
							break
						else:
							# 其他失败（网络问题？），则手工打码
							todo_update['status']='SJRAND_P'
							todo_update['man']=1
							todo_update['retry']=0
							break
	
				todo_update['rand_code_p']=data
			
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				ret, data2 = httphelper3.check_sjrand_p(str(db_todo['_id']), data,db_todo['initDc']['repeat_submit_token'])
				if ret==httphelper3.E_OK and data2==True:
					if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT', 'ORDER_API'):
						todo_update['status']='BOOK'
					else:
						# 输入用户密码
						todo_update['status']='SJRAND_P'
						todo_update['man']=1
				else:
					# 检测随机码失败，重新打码
					todo_update['status']='VERIFY'

			elif db_todo['status']=='BOOK':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])

				# 检查随机码
				ret, data2 = httphelper3.check_sjrand_p(str(db_todo['_id']), db_todo['rand_code_p'], 
					db_todo['initDc']['repeat_submit_token'])
				if ret==httphelper3.E_OK and data2==True:
					if db_todo.has_key('cid'):
						sjrandhelper3.report(db_todo['cid'], 1) # 回报打码正确
					todo_update['status']='BOOK1'
				else:
					# 检测随机码失败，重新打码
					if db_todo.has_key('cid'):
						sjrandhelper3.report(db_todo['cid'], 0) # 回报打码错误
					todo_update['status']='VERIFY'
	
			elif db_todo['status']=='BOOK1':
				# 乘客信息格式，在takit里输入
				#passengers = [
				#	{
				#			'name'        : '关涛',
				#			'certType'     : '1',
				#			'certNo'       : '12010419760404761X',
				#			'ticketType' : '1',
				#	}
				#]
	
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])

				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break
				if data==False: # 未登录
					todo_update['status'] = 'ORDER' 
					#todo_update['next_status'] = 'BOOK1'
					break

				# 添加乘客信息
				people_ok=True
				fail_passenger=[]
				for people in db_todo['passengers']:
					ret, data = httphelper3.real_add(str(db_todo['_id']), db_todo['initDc']['repeat_submit_token'], people)
					if ret==httphelper3.E_OK or (ret==httphelper3.E_REAL_ADD and ('已存在' in data)):
						db.id_pool.update({'id_no':people['certNo']},
							{'$set':{'id_name':people['name'], 'id_type':people['certType']}},
							upsert=True)
						time.sleep(1.5)
						continue
					elif ret==httphelper3.E_REAL_ADD and ('待核验' in data):
						fail_passenger.append({
							'certNo'     : people['certNo'],
							'certType'   : people['certType'],
							'name'       : people['name'].encode('utf-8'),
							'ticketType' : people['ticketType'],
							'reason'     : '1'  # 待核验
						})
					else:
						fail_passenger.append({
							'certNo'     : people['certNo'],
							'certType'   : people['certType'],
							'name'       : people['name'].encode('utf-8'),
							'ticketType' : people['ticketType'],
							'reason'     : '2'  # 其他原因：未通过
						})
					people_ok=False
					break
	
				todo_update['fail_passenger']=fail_passenger
	
				if people_ok==False:
					todo_update['comment']='6|real_add|%s.' % data
					break
	
				#DELAY=3
				todo_update['status']='BOOK2'
	
			elif db_todo['status']=='BOOK2':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				# 检查订单信息和验证码
				ret, data = httphelper3.check_order_info(
					str(db_todo['_id']), 
					db_todo['initDc']['repeat_submit_token'],
					db_todo['rand_code_p'],
					db_todo['passengers'],
					db_todo['seat_type'],
					db_todo['dynamic_key']
				)
	
				if ret<0:
					if '取消次数过多' in data:
						todo_update['comment']='0|check_order_info|%s.' % data
						if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT'):
							# 12306 用户有问题
							db.user_12306.update({'uname':db_todo['user_12306']},{'$set':{'status':data}})
							todo_update['user_12306']=''
							todo_update['status']='ORDER'
					elif '不合法' in data: # 乘客姓名不合法
						todo_update['comment']='5|check_order_info|%s.' % data
					elif '非法' in data: # 非法的座席。。。。等
						todo_update['comment']='5|check_order_info|%s.' % data
					elif '网络繁忙' in data: 
						todo_update['comment']='0|check_order_info|%s.' % data
						todo_update['status']='ORDER'
						DELAY=3
					#else:
						# 登录失败，重新验证码
						#new_path = '_%s' % (db_todo['sjrand_p'])
						#todo_update['retry']=db_todo['retry']+1
						#if todo_update['retry']<5:
						#	todo_update['status']='VERIFY'
						#todo_update['sjrand_p']=new_path
						#todo_update['comment']='0|check_order_info|%s.' % data
						#try:
						#	os.rename('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand_p']), 
						#		  '%s/%s.png' % (setting.sjrand_path, new_path))
						#except OSError:
						#	pass
					break
	
				# 登录成功
				# 记录已识别的随机码
				#new_path = '_%s_%s' % (db_todo['sjrand_p'], db_todo['rand_code_p'])
				#todo_update['sjrand_p']=new_path
				#try:
				#	os.rename('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand_p']), 
				#		  '%s/%s.png' % (setting.sjrand_path, new_path))
				#except OSError:
				#	pass
	
				# 取得queue排队计数
				train_info={
					'train_date'          : db_todo['initDc']['query_ticket_request']['train_date'],
					'train_no'            : db_todo['initDc']['query_ticket_request']['train_no'],
					'station_train_code'  : db_todo['initDc']['query_ticket_request']['station_train_code'],
					'from_station'        : db_todo['initDc']['query_ticket_request']['from_station'],
					'to_station'          : db_todo['initDc']['query_ticket_request']['to_station'],
					'ypInfoDetail'        : db_todo['initDc']['query_ticket_request']['ypInfoDetail'],
					'purpose_codes'       : db_todo['initDc']['query_ticket_request']['purpose_codes'],
				}
				ret, data = httphelper3.get_queue_count(
					str(db_todo['_id']), 
					db_todo['initDc']['repeat_submit_token'],
					train_info,
					db_todo['seat_type']
				)
				if ret<0:
					todo_update['comment']='0|get_queue_count|%s.' % data
					break
	
				todo_update['queue_count']=data
				if data['op_2']==True:
					todo_update['comment']='1|get_queue_count|排队人数超过余票数量，请选择其他车次.'
					break
	
				# 确认排队
				train_info={
					'purpose_codes'      : db_todo['initDc']['query_ticket_request']['purpose_codes'],
					'ypInfoDetail'       : db_todo['initDc']['query_ticket_request']['ypInfoDetail'],
					'key_check_isChange' : db_todo['initDc']['key_check_isChange'],
					'train_location'     : db_todo['initDc']['train_location'],
				}
				ret, data = httphelper3.confirm_single_for_queue(
					str(db_todo['_id']), 
					db_todo['initDc']['repeat_submit_token'],
					db_todo['rand_code_p'],
					db_todo['passengers'],
					db_todo['seat_type'],
					train_info
				)
				if ret<0:
					todo_update['comment']='0|confirm_single_for_queue|%s.' % data
					if '余票不足' in data: # 余票不足，自动返回无票，20150428
						todo_update['comment']='1|BOOK2|余票不足'
					elif '超过余票数' in data: # 排队人数现已超过余票数，请您选择其他席别或车次。
						todo_update['comment']='1|BOOK2|排队人数超过余票数'
					break
				elif not (ret==httphelper3.E_OK and data==True):
					todo_update['comment']='0|confirm_single_for_queue|确认订单失败'
					break
	
				todo_update['status']='WAIT'
				todo_update['retry']=0
				todo_update['wait_retry']=0
				todo_update['waitCount']=0
				#todo_update['passengers']=passengers
	
			elif db_todo['status']=='WAIT':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				# 检查排队结果
				ret, data = httphelper3.query_order_wait_time(str(db_todo['_id']), db_todo['initDc']['repeat_submit_token'])
				if ret<0:
					todo_update['comment']='0|query_order_wait_time|%s.' % data
					if '用户未登录' in data:
						todo_update['status']='VERIFY'
					else:
						todo_update['retry']=db_todo['retry']+1
						if todo_update['retry']<5: # 重试5次
							todo_update['status']='WAIT'
					break

				# 12306可能返回很大的队列
				if data['waitTime']>1800 or data['waitCount']>500:
					todo_update['comment']='1|WAIT_TOO_BIG|无票'
					break

				if data['waitTime']>0:
					if not db_todo.has_key('waitCount'):
						todo_update['wait_retry']=0
					elif db_todo['waitCount']==data['waitCount']:
						todo_update['wait_retry']=db_todo['wait_retry']+1
					else:
						todo_update['wait_retry']=0
					if todo_update['wait_retry']<10: # 重试10次, 如果waitCount无变化，就返回无票
						todo_update['waitCount']=data['waitCount']
						todo_update['status']='WAIT'
						todo_update['comment']='0|query_order_wait_time|前面还有%d等待，大约需等待%d秒' % \
							(data['waitCount'], data['waitTime'])
						DELAY = 2
					else:
						todo_update['comment']='1|WAIT_REPEAT_MANY|无票'
					break
	
				if data['orderId']==None:
					if data.has_key('msg'):
						msg=data['msg'].encode('utf-8')
						print msg
						if '已购买' in msg: # 已购买当日当次车票
							todo_update['comment']='2|query_order_wait_time|已购买当日当次车票.'
						elif '已订' in msg: # 余一捷(二代身份证-330182197507171350)已订2015年04月07日G41次的车票!!.
							todo_update['comment']='2|query_order_wait_time|已订当日当次车票.'
						elif '购票行程冲突' in msg: # 尊敬的旅客，您的证件-文玉(510802195612301648)已订2015年04月06日K392次车票，
								#与本次购票行程冲突，请将已购车票办理改签，或办理退票后重新购票；如您确认此身份信息被他人冒用，
								#请点击“网上举报”并确认后，可以继续购票。谢谢您的合作。
							todo_update['comment']='2|query_order_wait_time|购票行程冲突.'
						elif '您的身份信息未经核验' in msg: # 乘客信息未核验
							todo_update['comment']='6|query_order_wait_time|乘客信息未核验.'
						elif '取消次数过多' in msg: # 由于您取消次数过多，需换个用户
							todo_update['comment']='0|query_order_wait_time|%s.' % msg
							if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT'):
								# 12306 用户有问题
								db.user_12306.update({'uname':db_todo['user_12306']},{'$set':{'status':msg}})
								todo_update['user_12306']=''
								todo_update['status']='ORDER'
								DELAY=3
						else:
							todo_update['comment']='1|query_order_wait_time|%s.' % msg
					else:
						todo_update['comment']='1|query_order_wait_time|未知原因'
					break
	
				todo_update['ticket']=data
				
				# 确认结果
				httphelper3.result_order_for_DcQueue(
					str(db_todo['_id']), 
					db_todo['initDc']['repeat_submit_token'],
					todo_update['ticket']['orderId']
				)
				
				todo_update['retry']=0 
				todo_update['status']='WAIT2' 
				DELAY=3 # 不要太快取订单信息，要给12306点时间
	
			elif db_todo['status']=='WAIT2':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break
				if data==False: # 未登录
					todo_update['status'] = 'ORDER' 
					todo_update['next_status'] = 'WAIT2'
					break
	
				# 检查订单信息
				ret, data = httphelper3.query_order_no_complete(str(db_todo['_id']))
				if ret==httphelper3.E_DATA:
					todo_update['retry']=db_todo['retry']+1
					if todo_update['retry']<5:
						DELAY=2 # 等待一下，如果太快，query_order_no_complete()可能会返回空
						todo_update['status'] = 'WAIT2' 
					else:
						todo_update['comment']='0|query_order_no_complete|获取未支付订单信息失败.'
					break
				if ret<0:
					todo_update['comment']='0|query_order_no_complete|%s.' % data
					break

				# 检查返回车票数是否与订票人数一致，不一致说明12306还没处理完
				if data['orderDBList'][0]['ticket_totalnum']!=len(db_todo['passengers']):
					DELAY=3
					todo_update['status'] = 'WAIT2'
					break

				todo_update['ticket_no']=db_todo['ticket']['orderId']
				todo_update['ticket_no_complete']=data
				# 记录付款截止时间和时刻
				todo_update['pay_limit_time']=data['orderDBList'][0]['tickets'][0]['pay_limit_time']
				todo_update['pay_limit_stick'] = int(time.mktime(time.strptime(todo_update['pay_limit_time'],"%Y-%m-%d %H:%M:%S")))

				# 对于人工订单，下单完成，等待支付
				if db_todo['event'] == 'ORDER_UI':
					todo_update['status']='PAY' 
					todo_update['man']=1
					break
				elif db_todo['event'] == 'ORDER_API':
					todo_update['status']='FINISH'
					break 

				# 生成订单返回结果，对ORDER_SINGLE, ORDER_JOINT
				result={
					'count'   : len(data['orderDBList'][0]['tickets']),
					'tickets' : []
				}

				seat_type_wrong_to_NO_TICKET = False # 坐席问题引起无票处理 20150408

				for ticket in data['orderDBList'][0]['tickets']:
					seat_name0 = ticket['seat_name'].encode('utf-8')
					if seat_name0 == '无座':
						seat_name2 = seat_name0
					else:  # "01号中铺"
						seat_name1 = seat_name0.split('号')
						if len(seat_name1)<2: 
							# 12306 返回的格式有问题
							todo_update['comment']='0|query_order_no_complete|格式有问题 %s' % seat_name0
							result=None
							break
						seat_name2 = ticket['seat_type_name'].encode('utf-8')+seat_name1[1] # 硬卧 + 中铺
					if stations.SEAT_TYPE_TO_QUNAR.has_key(seat_name2):
						seat_type=stations.SEAT_TYPE_TO_QUNAR[seat_name2]
					else:
						seat_type=None
						for st in stations.SEAT_TYPE_TO_QUNAR.keys(): # 处理类似 ‘软卧代二等座’ 的类型
							if st in seat_name2:
								seat_type=stations.SEAT_TYPE_TO_QUNAR[st]
								break
						if seat_type==None:
							# 未知的座席类型
							todo_update['comment']='0|query_order_no_complete|未知座席类型_%s' % seat_name2
							result=None
							break

					#检查坐席是否在seat和extSeat里，不在不能出票###  20150407
					user_ask_seat = db_todo['seat'].keys() + [i.keys()[0] for i in db_todo['extSeat']]
					if seat_type not in user_ask_seat:
						# 坐席不符，先取消未支付
						ret, data = httphelper3.cancel_no_complete_order(str(db_todo['_id']), todo_update['ticket_no'])
						if ret<0: # 包括 E_DATA 的可能
							todo_update['comment']='0|cancel_no_complete_order|%s.' % data
							break
						if data.has_key('existError') and data['existError']!='N':
							todo_update['comment']='0|cancel_no_complete_order|取消未支付订单出错'
							break
						
						# 自动报无票
						todo_update['comment']='1|WAIT2|无票'
						seat_type_wrong_to_NO_TICKET = True #  20150408
						break

					passengerName=ticket['passengerDTO']['passenger_name'].encode('utf-8')
					if ticket['ticket_type_code']==stations.TICKET_TYPE['儿童']: 
						# 恢复订单时儿童姓名
						for ppp in db_todo['passengers']:
							if ppp['certNo']==ticket['passengerDTO']['passenger_id_no'] \
							   and ppp['ticketType']==ticket['ticket_type_code']:
							   	if ppp.has_key('origin_name'):
									passengerName=ppp['origin_name']
								break
	
					result['tickets'].append({
						'ticketNo'      : ticket['sequence_no'],
						'seatType'      : seat_type,
						'seatNo'        : '%s车%s' % (ticket['coach_name'].encode('utf-8'), seat_name0),
						'price'         : '%.2f' % (ticket['ticket_price']/100.0),
						'passengerName' : passengerName,
						'seq'           : db_todo['seq'] if db_todo.has_key('seq') else 0,
						'ticketType'    : stations.TICKET_TYPE_TO_QUNAR[ticket['ticket_type_code']],
					})

				if seat_type_wrong_to_NO_TICKET: # 坐席问题引起无票处理 20150408
					break
					
				if result!=None:
					todo_update['order_result']= result
					# 对占座订单，不需要支付
					if db_todo['event']=='ORDER_SINGLE' and db_todo['reservation']==1:
						ret,data = httphelper3.QUNAR_reservation_callback(
							str(db_todo['_id']),
							url = db_todo['reserve_url'],
							orderNo = db_todo['orderNo'].encode('utf-8'),
							result = result,
							status = 'success'
						)
						if ret<0:
							# qunar未返回正常结果，可能是网络错误或qunar服务器错误
							todo_update['qunar_err']=data
							todo_update['comment']='0|QUNAR_reservation_callback|Qunar提交占座结果失败！'
							print '***** QUNAR error: %s' % data
							break

						if data['ret']==False and data['errCode']!='008': # 008 - 订单状态已改变，认为已成功
												  # 例如前一次调用失败，再次调用可能返回008
							# qunar 返回出错，需人工介入，需要取消此订单（未付款）
							todo_update['qunar_err']=data['errMsg']
							#print '***** QUNAR error: %s' % data['errMsg'].encode('utf-8')
							todo_update['comment']='0|QUNAR_reservation_callback|QunarError:%s' % data['errMsg'].encode('utf-8')
							todo_update['man']=1
						else:
							# 确认成功，等待支付
							todo_update['status']='RESERVE_WAIT'
							#todo_update['man']=2
					else:
						# 对qunar订单，先支付再检查合法性 20150410 #废弃：检查合法性后再进行支付
						todo_update['status'] = 'READY_TO_PAY' #'CHECK'

			elif db_todo['status']=='RESERVE_WAIT': # 占座后等待支付
				if db_todo.has_key('qunar_paid') and db_todo['qunar_paid']==1:
					todo_update['status']='CHECK' # 检查合法性后再进行支付
				else:
					DELAY = 10 # 等待qunar付款
					todo_update['status']='RESERVE_WAIT'

			elif db_todo['status']=='READY_TO_PAY': # 准备付款 ，20150410
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
				
				todo_update['pay_round']=0 # 标记是否进行过生成付款交易

				if db_todo['orderType']==1: # 联程订单, 等所有订单都READY_TO_PAY，再PAY
					cancel_this = False
					if db_todo['seq']==db_todo['tripNum']: 
						# 联程的最后一个订单, 汇集所有联程订单的结果
						db_joint=db.todo.find(
							{'$and' : [{'orderNo': db_todo['orderNo']},
								{'$or': [{'status' : 'READY_TO_PAY'},{'status' : 'REPORT'},]}]}, 
							{'status':1, 'seq':1, 'order_result':1, 'comment':1}
						)
						if db_joint.count()!=db_todo['tripNum']:
							# 还有订单未处理完
							todo_update['status']='READY_TO_PAY'
							DELAY=3 # 等待3秒
							break
						else:	
							for order in db_joint: # 检查所有的订单信息
								if order['status']=='REPORT' and order['comment']!='':
									# 用出错子订单的出错结果，作为联程订单的出错结果
									todo_update['comment']=order['comment'].encode('utf-8')
									result=None
									break
							if result==None: # ---> 取消本子订单，同时通知取消其他联程订单
								cancel_this=True
								db.todo.update({'orderNo': db_todo['orderNo']},
									{'$set': {'pay_pass':'FAIL', 'man':0}},multi=True)
								#break
							else: # 同时放行其他的联程订单
								db.todo.update({'orderNo': db_todo['orderNo']},
									{'$set': {'pay_pass':'PASS', 'man':0}},multi=True)

					else:
						if db_todo['pay_pass']=='WAIT':
							# pay_pass由最后一个订单的线程统一处理，其他seq的订单不动作
							todo_update['status']='READY_TO_PAY'
							todo_update['man']=2 # 离开线程，等待被唤醒
							break
						elif db_todo['pay_pass']=='PASS': # 可以进入支付通过，释放资源结束, 20150410
							#todo_update['status']='PAY' 
							#todo_update['man']=1
							todo_update['comment']=db_todo['comment'].encode('utf-8')
							#break
						else: # pay_pass == FAIL
							# ---> 取消本子订单
							cancel_this=True
							todo_update['comment']='0|CHECK_JOINT|其他联程订单失败'
							#break
	
					if cancel_this: # 取消未支付的订单 
						ret, data = httphelper3.cancel_no_complete_order(str(db_todo['_id']), db_todo['ticket_no'])
						if ret<0: # 包括 E_DATA 的可能
							todo_update['comment']='0|cancel_no_complete_order|%s.' % data
							#break
						if data.has_key('existError') and data['existError']!='N':
							print 'cancel_no_complete_order: 取消未支付订单出错'
							#todo_update['comment']='0|cancel_no_complete_order|取消未支付订单出错'
							#break
						break #结束当前状态的后续处理
					else:
						todo_update['status']='PAY' 
						todo_update['man']=1

				else: # 单程订单，尝试是否可以代付
					#db_u = db.user_12306.find_one({'uname':db_todo['user_12306']}, {'auto_pay':1})
					#if db_u!=None and db_u['auto_pay']==1: # 可以代付
					
					wait_to_pay = db_todo['ticket_no_complete']['orderDBList'][0]['ticket_total_price_page']
					
					# 根据pay_threshold是否选择代付, 20150423
					if float(wait_to_pay) > PAY_THRESHOLD:
						# 金额大于PAY_THRESHOLD，先代付
						ret, data = httphelper3.QUNAR_process_auto_pay(
							str(db_todo['_id']),
							orderNo = db_todo['orderNo'].encode('utf-8'),
							price = wait_to_pay,
							un = db_todo['user_12306']
						)
						if ret<0:
							# qunar未返回正常结果，可能是网络错误或qunar服务器错误
							todo_update['qunar_err']=data
							todo_update['comment']='0|QUNAR_process_auto_pay|Qunar提交代付失败！'
							#print '***** QUNAR error: %s' % data
							break
	
						if data['ret']==False and data['errCode']!='008':
							# qunar 返回出错，需人工介入
							todo_update['qunar_err']=data['errMsg']
							#print '***** QUNAR error: %s' % data['errMsg'].encode('utf-8')
							todo_update['comment']='0|QUNAR_process_auto_pay|QunarError:%s' % data['errMsg'].encode('utf-8')
							todo_update['man']=1
						else:
							# 提交代付成功
							todo_update['status']='AUTO_PAY'
							#todo_update['man']=2 # man=2 异步处理
							DELAY=60*25 # 25分钟超时
							todo_update['comment']=db_todo['comment'].encode('utf-8')
							todo_update['alipay_form']={'ord_amt' : db_todo['ticket_no_complete']['orderDBList'][0]['ticket_total_price_page']}
						break
					else: # 刷卡支付
						todo_update['status']='PAY'
						todo_update['man']=1

			elif db_todo['status']=='CHECK': # qunar订单检查订单正确性
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])

				result={
					'count'   : 0,
					'tickets' : []
				}
				if db_todo['orderType']==1: # 联程订单
					cancel_this = False
					if db_todo['seq']==db_todo['tripNum']: 
						# 联程的最后一个订单, 汇集所有联程订单的结果
						db_joint=db.todo.find(
							{'$and' : [{'orderNo': db_todo['orderNo']},
								{'$or': [{'status' : 'CHECK'},{'status' : 'REPORT'},]}]}, 
							{'status':1, 'seq':1, 'order_result':1, 'comment':1}
						)
						if db_joint.count()!=db_todo['tripNum']:
							# 还有订单未处理完
							todo_update['status']='CHECK'
							DELAY=3 # 等待3秒
							break
						else:	
							for order in db_joint: # 合并所有的订单信息
								if order['status']=='REPORT' and order['comment']!='':
									# 用出错子订单的出错结果，作为联程订单的出错结果
									todo_update['comment']=order['comment'].encode('utf-8')
									result=None
									break
								result['count']+=order['order_result']['count']
								result['tickets']+=order['order_result']['tickets']
							if result==None:
								# ---> 取消本子订单
								cancel_this=True
								#break
					else:
						if db_todo['check_pass']=='WAIT':
							# check_pass由最后一个订单的线程统一处理，其他seq的订单不动作
							todo_update['status']='CHECK'
							todo_update['man']=2 # 离开线程，等待被唤醒
							break
						elif db_todo['check_pass']=='PASS': # 验证通过，释放资源结束, 20150410
							todo_update['status']='FREE_USER' 
							#todo_update['man']=1
							todo_update['comment']=db_todo['comment'].encode('utf-8')
							break
						else: # check_pass == FAIL
							# ---> 取消本子订单
							cancel_this=True
							todo_update['comment']='0|CHECK_JOINT|其他联程订单失败'
							#break
	
					if cancel_this: # 取消已支付的订单 , 20150410
						todo_update['status']='RETURN_FOR_FAIL'
						#ret, data = httphelper3.cancel_no_complete_order(str(db_todo['_id']), db_todo['ticket_no'])
						#if ret<0: # 包括 E_DATA 的可能
						#	todo_update['comment']='0|cancel_no_complete_order|%s.' % data
						#	break
						#if data.has_key('existError') and data['existError']!='N':
						#	print 'cancel_no_complete_order: 取消未支付订单出错'
						#	#todo_update['comment']='0|cancel_no_complete_order|取消未支付订单出错'
						break #结束当前状态的后续处理
	
				else: # 单程订单
					result = db_todo['order_result']

				todo_update['check_result']=result # 对联程，check_result是多个订单合并后的结果
				todo_update['status']='CHECK2'
				
			elif db_todo['status']=='AUTO_PAY': # 代付超时才会到这, 直接去scan3检查， 20150422
				todo_update['pay_off'] = 0
				todo_update['payStatus'] = -1 # 代付结果超时，记录-1，20150404
				todo_update['status']='SCAN3'
				todo_update['man']=0

			elif db_todo['status']=='CHECK2': # qunar订单检查订单正确性
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])

				if db_todo.has_key('check_result'):
					result = db_todo['check_result']
				else:
					result = db_todo['order_result'] # just for test only

				ret, data = httphelper3.QUNAR_process_purchase(
					str(db_todo['_id']),
					orderNo = db_todo['orderNo'].encode('utf-8'),
					result = result,
					comment = db_todo['comment'].encode('utf-8'),
					un = db_todo['user_12306'].encode('utf-8')
				)
				if ret<0:
					# qunar未返回正常结果，可能是网络错误或qunar服务器错误
					todo_update['qunar_err']=data
					todo_update['comment']='0|QUNAR_process_purchase|(已退票)Qunar提交出票结果失败'
					print '***** QUNAR error: %s' % data
					todo_update['status']='RETURN_FOR_FAIL' # 先退已支付的票
					break
	
				if data['ret']==False and data['errCode']!='008':
					# qunar 返回出错，需人工介入，需要取消此订单（已付款）
					todo_update['qunar_err']=data['errMsg']
					#print '***** QUNAR error: %s' % data['errMsg'].encode('utf-8')
					todo_update['comment']='0|QUNAR_process_purchase|(已退票)QunarError:%s' % data['errMsg'].encode('utf-8')
					#todo_update['man']=1
					todo_update['status']='RETURN_FOR_FAIL' # 先退已支付的票
					if db_todo['orderType']==1:
						db.todo.update({'orderNo': db_todo['orderNo']},
							{'$set': {'check_pass':'FAIL', 'man':0}},multi=True)
				else:
					# 确认成功，已支付，释放资源
					if db_todo['orderType']==0: # and db_todo['pay_off']==1: # 单程票
						#todo_update['pay_by_auto_pay']=1
						todo_update['status']='FREE_USER' 
					else: # 联程
						todo_update['status']='FREE_USER'
						#todo_update['man']=1
						todo_update['comment']=db_todo['comment'].encode('utf-8')
						#if db_todo['orderType']==1: # 联程订单
						db.todo.update({'orderNo': db_todo['orderNo']},
							{'$set': {'check_pass':'PASS', 'man':0}},multi=True)

			elif db_todo['status']=='RETURN_FOR_FAIL':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])

				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break

				if data==False: # 未登录
					todo_update['status'] = 'ORDER' 
					todo_update['next_status'] = 'RETURN_FOR_FAIL'
					break
				
				if not db_todo.has_key('ticket_no_complete'):
					todo_update['comment']='0|RETURN_FOR_FAIL|缺少订票数据ticket_no_complete.'
					break

				# 已登录，退票
				ret, data = httphelper3.get_token_from_query_order(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|get_token_from_query_order|%s.' % data
					break
	
				repeat_submit_token = data
				print 'submit_token = %s' % repeat_submit_token
	
				order_db={
					'start_train_date_page' : db_todo['ticket_no_complete']['orderDBList'][0]['start_train_date_page'],
					'train_code_page'       : db_todo['ticket_no_complete']['orderDBList'][0]['train_code_page']
				}
				return_ok = True
				return_tickets=[]
				for ticket in db_todo['ticket_no_complete']['orderDBList'][0]['tickets']:
					ret, data = httphelper3.return_ticket_affirm(str(db_todo['_id']), repeat_submit_token, order_db, ticket)
					if ret<0: # 包括 E_DATA 的可能
						todo_update['comment']='0|return_ticket_affirm|%s.' % data
						return_ok = False
						break
					if data.has_key('submitStatus') and data['submitStatus']==False:
						return_ok = False
						msg = data['errMsg'].encode('utf-8')
						todo_update['comment']='0|return_ticket_affirm|%s.' % msg
						break
	
					return_tickets.append(data)
	
					ret, data = httphelper3.return_ticket(str(db_todo['_id']), repeat_submit_token)
					if ret<0: # 包括 E_DATA 的可能
						todo_update['comment']='0|return_ticket|%s.' % data
						return_ok = False
						break
	
				if return_ok:
					todo_update['return_tickets']=return_tickets
					todo_update['comment']=db_todo['comment'].encode('utf-8')
					# 跳到FAIL，人工检查				
					#todo_update['status']='FREE_USER' # 退票完成，释放资源

			elif db_todo['status']=='RETURN':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])

				##### 检查订票信息，是否需要人工处理，赚钱可能！20150406
				return_check = db.user.find_one({'uname':'settings'}, {'return_check':1})
				if return_check['return_check']==1 and (not db_todo.has_key('return_checked')): # 只检查一次
					start_tick = int(time.mktime(time.strptime(db_todo['trainStartTime'],"%Y-%m-%d %H:%M")))
					now_tick = int(time.time())
				
					if (start_tick-now_tick)/3600/24<15 and int(db_todo['ticketPay'])>90:
						if db_todo['ticket_no_complete']['orderDBList'][0]['tickets'][0]['seat_type_name'].encode('utf-8') not in ('硬座','无座','站票'):
							if (start_tick-now_tick)/3600<24:
								todo_update['comment']='0|RETURN|<<紧急退票订单>>$$$$$$$$$需人工检查退票信息.'
							else:
								todo_update['comment']='0|RETURN|$$$$$$$$$需人工检查退票信息.'
							todo_update['return_checked']=1
							break
				##################################################

				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break

				if data==False: # 未登录
					todo_update['status'] = 'ORDER' 
					todo_update['next_status'] = 'RETURN'
					break
				
				if not db_todo.has_key('ticket_no_complete'):
					todo_update['comment']='0|RETURN|缺少订票数据ticket_no_complete.'
					break

				# 已登录，退票
				ret, data = httphelper3.get_token_from_query_order(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|get_token_from_query_order|%s.' % data
					break
	
				repeat_submit_token = data
				print 'submit_token = %s' % repeat_submit_token
	
				order_db={
					'start_train_date_page' : db_todo['ticket_no_complete']['orderDBList'][0]['start_train_date_page'],
					'train_code_page'       : db_todo['ticket_no_complete']['orderDBList'][0]['train_code_page']
				}
				return_ok = True
				returned = 0
				return_tickets=[]
				for ticket in db_todo['ticket_no_complete']['orderDBList'][0]['tickets']:
					ret, data = httphelper3.return_ticket_affirm(str(db_todo['_id']), repeat_submit_token, order_db, ticket)
					if ret<0: # 包括 E_DATA 的可能
						todo_update['comment']='0|return_ticket_affirm|%s.' % data
						return_ok = False
						break
					if data.has_key('submitStatus') and data['submitStatus']==False:
						return_ok = False
						msg = data['errMsg'].encode('utf-8')
						print msg
						if '已过规定退票时间' in msg: #  已过规定退票时间,不允许退票！
							todo_update['comment']='2|return_ticket_affirm|已过规定退票时间.'
						elif '不允许退票' in msg: # 该票不允许退票，请到我的订单中查询车票状态！
							todo_update['comment']='1|return_ticket_affirm|已取纸质车票或临近开车.'
						else: # 其他错误，手工处理
							todo_update['comment']='0|return_ticket_affirm|%s.' % msg
						break
	
					return_tickets.append(data)
	
					ret, data = httphelper3.return_ticket(str(db_todo['_id']), repeat_submit_token)
					if ret<0: # 包括 E_DATA 的可能
						todo_update['comment']='0|return_ticket|%s.' % data
						return_ok = False
						break
					
					returned = returned + 1
	
				if return_ok:
					todo_update['return_tickets']=return_tickets
					todo_update['return']=2 # 退票成功
					#todo_update['status']='REPORT'  # 20150406
					todo_update['comment']='' # 确保为空，REPORT以此判断是否是FAIL报告
				else:
					if returned>0:
						todo_update['comment']='0|RETURN|部分退票,需检查:%s' % todo_update['comment']
					elif '系统繁忙' in todo_update['comment']: # 系统繁忙，请稍后重试 20150416
						DELAY=30 # 等待30秒再试
						todo_update['status']='RETURN'
						break
					todo_update['return']=-1 # 退票失败
				
				todo_update['status']='REPORT' # 自动处理已知退票错误，20150406

			elif db_todo['status']=='RETURN_OK': # 手工退票成功
				todo_update['return']=2 # 退票成功
				todo_update['status']='REPORT'
				todo_update['comment']='' # 确保为空，REPORT以此判断是否是FAIL报告

			elif db_todo['status']=='REPORT':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])

				# REPORT处理两类报告
				#  1. 退票报告（正常、出错）
				#  2. 出票报告（出错）
				# 要区分单程订单和联程订单，联程订单只有最后一个子订单发报告
	
				fail_report = (db_todo['comment']!='') # True FAIL报告，False 正常退票报告
	
				if db_todo['orderType']==1: # 联程订单
					if db_todo['seq']!=db_todo['tripNum']: # 非最后一个订单
						if db_todo['check_pass']=='WAIT':
							todo_update['status']='REPORT'
							todo_update['man']=2
							todo_update['comment']=db_todo['comment'].encode('utf-8')
							break
						else: # 'check_pass'=='FAIL' or 'PASS'
							todo_update['status']='FREE_USER'
							todo_update['comment']=db_todo['comment'].encode('utf-8')
							break
	
				# 单程订单 或 联程订单的最后一个子订单
				if db_todo['return'] != 0: # 退票报告
					err_msg = db_todo['comment'].encode('utf-8').split('|')
					if fail_report:
						if err_msg[0]=='0' or err_msg[0]=='':
							# 未知原因，需人工处理
							todo_update['comment']=db_todo['comment'].encode('utf-8')
							todo_update['man']=1
							break
	
						return_ok=False
					else:
						return_ok=True
	
					# 返回结果给qunar
					if return_ok:
						reason = 0
						comment = '已退票'
					else:
						# 自动处理已知退票错误, 20150406
						reason = int(err_msg[0])
						comment = err_msg[2] if len(err_msg)==3 else db_todo['comment'].encode('utf-8')
	
					# 发回复给qunar
					ret, data = httphelper3.QUNAR_process_refund(
						str(db_todo['_id']),
						orderNo = db_todo['orderNo'].encode('utf-8'),
						agree = return_ok,
						reason = reason,
						comment = comment
					)
					if ret<0:
						# qunar未返回正常结果，可能是网络错误或qunar服务器错误
						todo_update['qunar_err']=data
						todo_update['comment']='0|QUNAR_process_refund|Qunar提交退票结果失败！'
						print '***** QUNAR error: %s' % data
						break
	
					if data['ret']==False and data['errCode']!='008':
						# qunar 返回出错，需人工介入
						todo_update['qunar_err']=data['errMsg']
						todo_update['comment']='0|QUNAR_process_refund|QunarError:%s' % data['errMsg'].encode('utf-8')
						#print '***** QUNAR error: %s' % data['errMsg'].encode('utf-8')
						# ----> 如果是联程订单，此时check_pass=WAIT，其他子订单还要继续等待 
						todo_update['man']=1
					else:
						# 退票确认
						todo_update['status']='FREE_USER'
						todo_update['comment']=db_todo['comment'].encode('utf-8')
						db.qunar.update({'orderNo': db_todo['orderNo']},{'$set': {'return':db_todo['return']}})
						if db_todo['orderType']==1: # 联程订单
							db.todo.update({'orderNo': db_todo['orderNo']},
								{'$set': {'check_pass':'PASS', 'man':0, 'return':db_todo['return']}},multi=True)
				else: # 出票出错报告
					err_msg = db_todo['comment'].encode('utf-8').split('|')
					if err_msg[0]=='0' or err_msg[0]=='':
						# 未知原因，需人工处理
						# ----> 如果是联程订单，此时check_pass=WAIT，其他子订单还要继续等待 
						todo_update['comment']=db_todo['comment'].encode('utf-8')
						todo_update['man']=1
					else:
						# 出错结果发回qunar
						ret, data = httphelper3.QUNAR_process_purchase(
							str(db_todo['_id']),
							orderNo = db_todo['orderNo'].encode('utf-8'),
							reason = int(err_msg[0]),
							passengerReason=db_todo['fail_passenger'] if err_msg[0]=='6' else None,
							comment = err_msg[2],
							un = db_todo['user_12306'].encode('utf-8') if db_todo.has_key('user_12306') else ''
						)
						if ret<0:
							# qunar未返回正常结果，可能是网络错误或qunar服务器错误
							todo_update['qunar_err']=data
							todo_update['comment']='0|QUNAR_process_purchase|Qunar提交订票结果失败！'
							print '***** QUNAR error: %s' % data
							break
	
						if data['ret']==False and data['errCode']!='008':
							# qunar 返回出错，需人工介入
							todo_update['qunar_err']=data['errMsg']
							#print '***** QUNAR error: %s' % data['errMsg'].encode('utf-8')
							todo_update['comment']='0|QUNAR_process_purchase|QunarError:%s' % data['errMsg'].encode('utf-8')
							# ----> 如果是联程订单，此时check_pass=WAIT，其他子订单还要继续等待 
							todo_update['man']=1
						else:
							# 出错确认成功
							todo_update['status']='FREE_USER'
							todo_update['comment']=db_todo['comment'].encode('utf-8')
							# 把其他联程单释放掉
							if db_todo['orderType']==1: # 联程订单
								db.todo.update({'orderNo': db_todo['orderNo']},
									{'$set': {'pay_pass':'FAIL', 'check_pass':'FAIL', 'man':0}}, multi=True)
	
			elif db_todo['status']=='FINISH':
				# 一定是要退票
				if db_todo['return']==1:
					# 退票也先进入SLEEP，20150406
					todo_update['next_status']='RETURN'
					todo_update['status']='SLEEP'
				else: # 应该不会到这里
					print "收到非退票的FINISH，事件分发出错！！！"
					todo_update['status']='FINISH'
					todo_update['comment']=db_todo['comment'].encode('utf-8')
					break

			elif db_todo['status'] in ('PAY', 'SJRAND', 'SJRAND_P', 'SCAN'): 
				# 预防 man 被 CHECK或READ_TO_PAY中联程处理时重置，导致手工处理变自动处理
				todo_update['man']=1
				todo_update['status'] = db_todo['status']

			elif db_todo['status']=='PAY2':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break
	
				if data==False: # 未登录
					todo_update['status'] = 'ORDER' 
					todo_update['next_status'] = 'PAY2'
					break

				# 检查订单信息，一般不需要，重新登录时候需要这一步
				ret, data = httphelper3.query_order_no_complete(str(db_todo['_id']))
				if ret==httphelper3.E_DATA:
					if (not db_todo.has_key('pay2_retry')) or (db_todo.has_key('pay2_retry') and db_todo['pay2_retry']<2):
						DELAY=3 # 等待一下，如果太快，query_order_no_complete()可能会返回空 20150416
						if db_todo.has_key('pay2_retry'):
							todo_update['pay2_retry'] = db_todo['pay2_retry'] + 1
						else:
							todo_update['pay2_retry'] = 1
						todo_update['status'] = 'PAY2' 
						break
						
					# 3次都没返回，20150416
					if not db_todo.has_key('pay_round'):
						todo_update['comment']='0|PAY2|缺少pay_round标记.'
						break
					elif db_todo['pay_round']==0:
						todo_update['comment']='0|PAY2|可能存在未支付情况，需检查.'
						break

					# 认为已支付完成	
					if db_todo['event'] in ('ORDER_SINGLE', 'ORDER_JOINT'):
						if int(time.time()) < db_todo['pay_limit_stick']-60:
							# 如果没超过付款时间，则已付过款，应该是AUTO_PAY未返回支付结果
							if db_todo['event'] == 'ORDER_SINGLE':
								todo_update['pay_by_auto_pay']=2 # 2表示检查后纪录
							todo_update['pay_off'] = 1
							todo_update['status'] = 'CHECK' # 20150412
						else:
							todo_update['comment']='0|PAY2|已超过付款截止时间，可能票已丢，需检查.'
							break
					else:
						DELAY=3 # 等待一下，如果太快，query_order_no_complete()可能会返回空
						todo_update['status'] = 'PAY2' 
						break
				if ret<0:
					todo_update['comment']='0|query_order_no_complete|%s.' % data
					break

				# 已登录，取得支付参数
				ret, data = httphelper3.pay_no_complete_order(str(db_todo['_id']), db_todo['ticket_no'])
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|pay_no_complete_order|%s.' % data
					break
	
				ret, data = httphelper3.pay_check(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|pay_check|%s.' % data
					break
				todo_update['pay_form'] = data
	
				back_cookie = httphelper3.get_cookie(str(db_todo['_id']))
				httphelper3.clear_cookie(str(db_todo['_id'])) # 使用新的session
				
				ret, data = httphelper3.pay_gateway(str(db_todo['_id']), todo_update['pay_form'])
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|pay_gateway|%s.' % data
					break
				todo_update['gateway_result']=data
	
				ret, data = httphelper3.pay_web_business(str(db_todo['_id']), todo_update['pay_form'], todo_update['gateway_result'])
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|pay_web_business|%s.' % data
					break
				todo_update['alipay_form']=data
	
				httphelper3.set_cookie(str(db_todo['_id']), back_cookie)
				
				# 等待扫描二维码付款
				todo_update['pay_round']=1 # pay_round 一轮，20150416
				todo_update['status']='SCAN'
				todo_update['man']=1
	
			elif db_todo['status']=='SCAN3':  # 检查支付结果：如果已支付，应该不存在未支付订单
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break
				if data==False: # 未登录
					todo_update['status'] = 'ORDER' 
					todo_update['next_status'] = 'SCAN3'
					break
	
				# 检查未支付订单信息
				ret, data = httphelper3.query_order_no_complete(str(db_todo['_id']))
				if ret==httphelper3.E_DATA: # 无未支付订单，正常
					if (not db_todo.has_key('scan3_retry')) or (db_todo.has_key('scan3_retry') and db_todo['scan3_retry']<2):
						DELAY=3 # 等待一下，如果太快，query_order_no_complete()可能会返回空 20150416
						if db_todo.has_key('scan3_retry'):
							todo_update['scan3_retry'] = db_todo['scan3_retry'] + 1
						else:
							todo_update['scan3_retry'] = 1
						todo_update['status'] = 'SCAN3' 
						break
					# 假设扫描2次，确实没有了
					todo_update['pay_off'] = 1
					if db_todo['event'] in ('ORDER_SINGLE','ORDER_JOINT'):
						if int(time.time()) < db_todo['pay_limit_stick']-60:
							# 如果没超过付款时间，则已付过款
							todo_update['status'] = 'CHECK'
						else:
							todo_update['comment']='0|SCAN3|已超过付款截止时间，可能票已丢，需检查.'
							break
					else:
						todo_update['status'] = 'FREE_USER'
					break
				if ret<0: # 其他出错
					todo_update['comment']='0|query_order_no_complete|%s.' % data
					break
	
				# 还有未支付订单，重新准备支付
				todo_update['ticket_no']=db_todo['ticket']['orderId']
				todo_update['ticket_no_complete']=data
				todo_update['status'] = 'PAY' 
				todo_update['man'] = 1
	
			elif db_todo['status']=='NO_COMPLETE':  # 查询未支付订单 # ORDER_API
				# 准备https连接
				if db_todo.has_key('cookie'):
					httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
				else:
					httphelper3.set_todo(str(db_todo['_id']))
	
				if db_todo['comment']!='':
					# 已出错，登录的时候
					todo_update['comment']=db_todo['comment'].encode('utf-8')
					break
	
				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break
				if data==False: # 未登录
					todo_update['login_retry']=0 # 登录失败计数
					todo_update['status'] = 'ORDER' 
					todo_update['next_status'] = 'NO_COMPLETE'
					break
	
				# 检查未支付订单信息
				ret, data = httphelper3.query_order_no_complete(str(db_todo['_id']))
				if ret==httphelper3.E_DATA: # 无未支付订单，正常
					todo_update['comment']='0|query_order_no_complete|none.'
					todo_update['status'] = 'FINISH'
					break
				if ret<0: # 其他出错
					todo_update['comment']='0|query_order_no_complete|%s.' % data
					break
	
				# 还有未支付订单，重新准备支付
				if data.has_key('orderDBList'):
					todo_update['ticket_no']=data['orderDBList'][0]['sequence_no']
					todo_update['ticket_no_complete']=data
				else:
					todo_update['comment']='0|query_order_no_complete|none.'
				todo_update['status'] = 'FINISH' 
	
			elif db_todo['status']=='API_CANCEL':  # 取消未支付订单 # ORDER_API
				# 准备https连接
				if db_todo.has_key('cookie'):
					httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
				else:
					httphelper3.set_todo(str(db_todo['_id']))
	
				if db_todo['comment']!='':
					# 已出错，登录的时候
					todo_update['comment']=db_todo['comment'].encode('utf-8')
					break
	
	
				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break
				if data==False: # 未登录
					todo_update['login_retry']=0 # 登录失败计数
					todo_update['status'] = 'ORDER' 
					todo_update['next_status'] = 'NO_COMPLETE'
					break
	
				# 检查订单信息
				ret, data = httphelper3.query_order_no_complete(str(db_todo['_id']))
				if ret==httphelper3.E_DATA: # 无未支付订单，正常
					todo_update['comment']='0|query_order_no_complete|none.'
					todo_update['status'] = 'FINISH'
					break
				if ret<0:
					todo_update['comment']='0|query_order_no_complete|%s.' % data
					break
	
				todo_update['ticket_no']=data['orderDBList'][0]['sequence_no']
	
				ret, data = httphelper3.cancel_no_complete_order(str(db_todo['_id']), todo_update['ticket_no'])
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|cancel_no_complete_order|%s.' % data
					break
				if data.has_key('existError') and data['existError']!='N':
					todo_update['comment']='0|cancel_no_complete_order|取消未支付订单出错'
					break
	
				todo_update['status'] = 'FINISH' 
	
			elif db_todo['status']=='COMPLETE':  # ORDER_API 查询已完成订单信息
				# 准备https连接, 新连接
				if db_todo.has_key('cookie'):
					httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
				else:
					httphelper3.set_todo(str(db_todo['_id']))
	
				if db_todo['comment']!='':
					# 已出错，登录的时候
					todo_update['comment']=db_todo['comment'].encode('utf-8')
					break
				
				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break
				if data==False: # 未登录
					todo_update['login_retry']=0 # 登录失败计数
					todo_update['status'] = 'ORDER' 
					todo_update['next_status'] = 'COMPLETE'
					break
	
				# 查询常用联系人
				ret, data = httphelper3.query_my_order(str(db_todo['_id']))
				if ret<0:
					todo_update['comment']='0|query_my_order|%s.' % data
					break
	
				todo_update['my_orders']=data
				todo_update['status']='FINISH'
	
	
			elif db_todo['status']=='PASSENGER':  # ORDER_API
				# 准备https连接, 新连接
				if db_todo.has_key('cookie'):
					httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
				else:
					httphelper3.set_todo(str(db_todo['_id']))
	
				if db_todo['comment']!='':
					# 已出错，登录的时候
					todo_update['comment']=db_todo['comment'].encode('utf-8')
					break
				
				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break
				if data==False: # 未登录
					todo_update['login_retry']=0 # 登录失败计数
					todo_update['status'] = 'ORDER' 
					todo_update['next_status'] = 'PASSENGER'
					break
	
				# 查询常用联系人
				ret, data = httphelper3.passengers_query_all(str(db_todo['_id']))
				if ret<0:
					todo_update['comment']='0|passengers_query_all|%s.' % data
					break
	
				todo_update['passengers_query']=data
				todo_update['status']='FINISH'
	
	
			elif db_todo['status']=='FAIL':
				if db_todo['event'] in ('ORDER_UI', 'ORDER_API'):
					# UI事件处理，到此结束
					None
				else:
					todo_update['next_status']='REPORT'
	
				todo_update['status']='FREE_USER'
				todo_update['comment']=db_todo['comment'].encode('utf-8')
	
			elif db_todo['status']=='FREE_USER':
				if db_todo['event'] in ('ORDER_SINGLE','ORDER_JOINT') and db_todo.has_key('user_12306'):
					# 释放12306用户
					db.user_12306.update({'uname': db_todo['user_12306']},{'$set': {'status': 'OK'}})
	
				# 如果是next_status，跳转去指定status
				if db_todo['next_status']!='':
					todo_update['status']=db_todo['next_status'].encode('utf-8')
					todo_update['next_status']=''
				else:
					todo_update['status']='FINISH'
	
				todo_update['comment']=db_todo['comment'].encode('utf-8')
	
			elif db_todo['status']=='CANCEL':
				# 准备https连接
				httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
	
				if db_todo.has_key('ticket_no'): #取消未付款的订单
					# 检查用户登录
					ret, data = httphelper3.check_user(str(db_todo['_id']))
					if ret<0: # 包括 E_DATA 的可能
						todo_update['comment']='0|check_user|%s.' % data
						break
					if data==False: # 未登录
						todo_update['status'] = 'ORDER' 
						todo_update['next_status'] = 'CANCEL'
						break
	
					# 检查订单信息
					ret, data = httphelper3.query_order_no_complete(str(db_todo['_id']))
					if ret<0:
						todo_update['comment']='0|query_order_no_complete|%s.' % data
						break
	
					ret, data = httphelper3.cancel_no_complete_order(str(db_todo['_id']), db_todo['ticket_no'])
					if ret<0: # 包括 E_DATA 的可能
						todo_update['comment']='0|cancel_no_complete_order|%s.' % data
						break
					if data.has_key('existError') and data['existError']!='N':
						todo_update['comment']='0|cancel_no_complete_order|取消未支付订单出错'
	
				todo_update['status']='FREE_USER'

			elif db_todo['status']=='CHANGE_PWD': # 修改12306登录密码
				# 准备https连接, 新连接
				if db_todo.has_key('cookie'):
					httphelper3.set_todo(str(db_todo['_id']), db_todo['cookie'])
				else:
					httphelper3.set_todo(str(db_todo['_id']))
	
				if db_todo['comment']!='':
					# 已出错，登录的时候
					todo_update['comment']=db_todo['comment'].encode('utf-8')
					break
				
				# 检查用户登录
				ret, data = httphelper3.check_user(str(db_todo['_id']))
				if ret<0: # 包括 E_DATA 的可能
					todo_update['comment']='0|check_user|%s.' % data
					break
				if data==False: # 未登录
					todo_update['login_retry']=0 # 登录失败计数
					todo_update['status'] = 'ORDER' 
					todo_update['next_status'] = 'CHANGE_PWD'
					break
	
				# 查询常用联系人
				ret, data = httphelper3.edit_login_pwd(str(db_todo['_id']), db_todo['pass_12306'], db_todo['new_pass'])
				if ret<0:
					todo_update['comment']='0|edit_login_pwd|%s.' % data
					break
	
				todo_update['edit_login_pwd']=data
				
				if data.has_key('flag') and data['flag']==True:
					db.user_12306.update({'uname':db_todo['user_12306']}, {'$set':{'passwd':db_todo['new_pass']}})
					todo_update['pass_12306']=db_todo['new_pass']
					todo_update['status']='FREE_USER'
				elif data.has_key('message'):
					todo_update['comment']='0|edit_login_pwd|%s.' % data['message'].encode('utf-8')
				else:
					todo_update['comment']='0|edit_login_pwd|修改登录密码出错.'

			# 退出内层while 1
			break

		# 更新comment信息
		if todo_update.has_key('comment') and todo_update['comment']!='':
			print '%s: %s' % (todo_update['status'], todo_update['comment'])
		else:
			todo_update['comment']=''

		# 添加 history
		if db_todo.has_key('history'):
			todo_update['history']=db_todo['history']
		else:
			todo_update['history']=[]
		todo_update['history'].append((tname, process_time, db_todo['status'], todo_update['comment']))

		# 更新todo状态
		todo_update['cookie'] = httphelper3.get_cookie(str(db_todo['_id'])) # 保存cookie
		todo_update['e_time'] = int(time.time()) + DELAY  # DELAY 秒后再继续执行
		
		if todo_update['status'] in ('FINISH', 'RESERVE_WAIT', 'AUTO_PAY', 'SLEEP', 'SJRAND3_RESULT') or todo_update['man']!=0: 
			#退出while前释放锁
			todo_update['lock'] = 0
			
			# 记录处理事件， 20150404
			todo_update['history'].append((tname, process_time, '%s - break' % todo_update['status']))
			 
			if todo_update['status']=='FINISH':
				# 处理结束，删除https连接,
				httphelper3.close_pool(str(db_todo['_id'])) 

				#设置打码最大队列，每次有FINISH时候设置， 20150418
				db_u = db.user.find_one({'uname':'settings'},
					{'sjrand_max':1, 'auto_sjrand':1, 'auto_sjrand_p':1, 'pay_threshold':1})
				if db_u!=None:
					if db_u.has_key('sjrand_max'):
						SJRAND_MAX = db_u['sjrand_max'] 
					if db_u.has_key('auto_sjrand'):
						AUTO_SJRAND = db_u['auto_sjrand']
					if db_u.has_key('auto_sjrand_p'):
						AUTO_SJRAND_P = db_u['auto_sjrand_p']
					if db_u.has_key('pay_threshold'):
						PAY_THRESHOLD = db_u['pay_threshold']
					print 'SLEEP QUEUE length = %d' % SJRAND_MAX
					print 'PAY THRESHOLD = %d' % PAY_THRESHOLD
					print 'AUTO SJRAND: %s, AUTO SJRAND_P: %s' % \
						(('Enabled' if AUTO_SJRAND==1 else 'Disabled'),
						 ('Enabled' if AUTO_SJRAND_P==1 else 'Disabled')) 
		else:
			time.sleep(DELAY)
			print "DELAY %d seconds" % DELAY

		# 更新todo的db数据
		db.todo.update({'_id':db_todo['_id']}, {'$set': todo_update})

		#原则上只有man=1 和 FINISH退出while 1
		if todo_update['status'] in ('FINISH', 'RESERVE_WAIT', 'AUTO_PAY', 'SLEEP', 'SJRAND3_RESULT') or todo_update['man']!=0:
			break

	#print "%s: %s - leave loop $$$$" % (tname, helper.time_str())


class MainLoop(threading.Thread):
	def __init__(self, tid):
		threading.Thread.__init__(self)
		self._tid = tid
		self._tname = None

	def run(self):
		global count, mutex
		self._tname = threading.currentThread().getName()
		
		print 'Thread - %s started.' % self._tname 

		while 1:
			main_loop(self._tname)

			# 周期性打印日志
			#time.sleep(0.2)
			sys.stdout.flush()


if __name__=='__main__':
	print "PROCESSOR: %s started" % helper.time_str()

	gc.set_threshold(300,5,5)

	#线程池
	threads = []
	
	#清理上次遗留的 lock, 分布式部署时，启动时要小心，一定要再没有lock的情况下同时启动分布时进程！！！ 20150403
	db.todo.update({'lock':1}, {'$set': {'lock':0}}, multi=True)
	
	#设置打码最大队列， 20150404
	db_u = db.user.find_one({'uname':'settings'},{'sjrand_max':1,'auto_sjrand':1,'auto_sjrand_p':1,'pay_threshold':1})
	if db_u!=None:
		if db_u.has_key('sjrand_max'):
			SJRAND_MAX = db_u['sjrand_max'] 
		if db_u.has_key('auto_sjrand'):
			AUTO_SJRAND = db_u['auto_sjrand']
		if db_u.has_key('auto_sjrand_p'):
			AUTO_SJRAND_P = db_u['auto_sjrand_p']
		if db_u.has_key('pay_threshold'):
			PAY_THRESHOLD = db_u['pay_threshold']

	print 'SLEEP QUEUE length = %d' % SJRAND_MAX
	print 'PAY THRESHOLD = %d' % PAY_THRESHOLD
	print 'AUTO SJRAND: %s, AUTO SJRAND_P: %s' % \
		(('Enabled' if AUTO_SJRAND==1 else 'Disabled'),
		 ('Enabled' if AUTO_SJRAND_P==1 else 'Disabled'))

		
	# 登录云打码，登录一次就可以
	sjrandhelper3.login()
	
	# 创建线程对象
	for x in xrange(0, setting.thread_num):
		threads.append(MainLoop(x))
	
	# 启动线程
	for t in threads:
		t.start()

	# 等待子线程结束
	for t in threads:
		t.join()  

	print "PROCESSOR: %s exited" % helper.time_str()
