#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 后台服务进程，后台运行
#
# 1. 检查qunar，分发todo事件
# 2. 检查订单处理结果，回报qunar
#
#
import sys, time, gc, os
import json
from bson.objectid import ObjectId
import helper, httphelper3, httphelper, stations
from config import setting

web_db = setting.db_web

DEALY=8

def free_12306():
	db_kam=web_db.user_12306.find({}, {'uname':1, 'status':1})
	if db_kam.count()>0:
		for u in db_kam:
			if type(u['status'])==type(ObjectId('551d346c6ba7857f2256661c')):
				db_t=web_db.todo.find_one({'_id':u['status']}, {'status':1})
				if db_t!=None:
					todo_status=db_t['status']
					if db_t['status']=='FINISH':
						web_db.user_12306.update({'_id':u['_id']},{'$set':{'status':'OK'}}) 
				else:
					todo_status=''


def main_loop_wait():
	# 取出票订单信息, 并分发事件
	ret, result = httphelper3.QUNAR_query_orders('QUNAR')
	if ret<0:
		print 'ERROR:', result
		return
		
	if result['ret']==False:
		print result['errMsg']
		return

	
	for order in result['data']:
		db_chk = web_db.qunar.find_one({'orderNo': order['orderNo']},{'_id':1})
		if db_chk!=None:
			db_chk = web_db.todo.find_one({'orderNo': order['orderNo']},{'reservation':1,'status':1})
			if db_chk!=None:
				if db_chk['reservation']==1 and db_chk['status']!='FINISH':
					web_db.todo.update({'orderNo': order['orderNo']},{'$set':{'qunar_paid':1}})
					print '%s: order <%s> is RESERVED. status = %s' % \
						(helper.time_str(), order['orderNo'], db_chk['status'])
				else:
					print '%s: order <%s> in queue. status = %s' % \
						(helper.time_str(), order['orderNo'], db_chk['status'])
				continue

		qunar_id=web_db.qunar.insert({'orderNo': order['orderNo'], 'data': order, 'return':0})
		if qunar_id==None:
			print 'order: fail to insert into qunar.'
			print new_tod
		
		new_todo={
			'status'         : 'SLEEP', #'QUERY',
			'lock'           : 0,
			'man'            : 0,
			'retry'          : 0,
			'comment'        : '',
			'history'        : [],
			'return'         : 0, # 用于标记退票：0: 无退票，1: 退票中, 2: 已退票, -1: 退票出错
			'tripNum'        : 1, # 默认为单程订单
			'next_status'    : 'QUERY', # SLEEP支持next_status, 20150406
			'reservation'    : 0,
			'pay_off'        : 0,
			'cs_time'        : 0, # 用于客服打码
				
			# 以下来自 qunar
			'orderNo'        : order['orderNo'],
			'orderType'      : order['orderType'],
			'orderDate'      : order['orderDate'],
			'orderTick'      : int(time.mktime(time.strptime(order['orderDate'],"%Y-%m-%d %H:%M:%S"))),
			'passengers'     : order['passengers'],
			'ticketPay'      : order['ticketPay'],
			'secondRefund'   : order['secondRefund'] if order.has_key('secondRefund') else 0,
		}
		# 处理乘客信息
		for people in new_todo['passengers']:
			# 转换ticket type为12306类型
			people['ticketType'] = stations.TICKET_TYPE_QUNAR[people['ticketType']]
			# 儿童使用大人的名字购票
			if people['ticketType']==stations.TICKET_TYPE['儿童']:
				for ppp in order['passengers']: 
					if ppp['certNo']==people['certNo'] and ppp['ticketType']!=stations.TICKET_TYPE['儿童']:
						people['origin_name']=people['name']
						people['name']=ppp['name']

		if order['orderType']==0: # 单程票				
			new_todo['event']          = 'ORDER_SINGLE'
			new_todo['arrStation']     = order['arrStation']
			new_todo['dptStation']     = order['dptStation']
			new_todo['extSeat']        = order['extSeat']
			new_todo['seat']           = order['seat']
			new_todo['trainStartTime'] = order['trainStartTime']
			new_todo['trainEndTime']   = order['trainEndTime']
			new_todo['trainNo']        = order['trainNo']
			new_todo['b_time'] = int(time.time())
			if new_todo['b_time']-new_todo['orderTick']>600: # 根据订单下单时间优先进入队列
				new_todo['e_time'] = new_todo['b_time']
			else:
				new_todo['e_time'] = new_todo['b_time'] + 15

			# 数据调整，匹配processor
			begin_code=stations.find_code(order['dptStation'].encode('utf-8'))
			end_code=stations.find_code(order['arrStation'].encode('utf-8'))
			new_todo['start_station'] = begin_code
			new_todo['stop_station'] = end_code
			start_time = order['trainStartTime'].split()
			new_todo['start_date'] = start_time[0]
			new_todo['start_time'] = start_time[1]

			if len(order['seat'])==0:
				print '订单无座席数据'
				print order
				new_todo['status']='FAIL'
				new_todo['comment']='5|dispatcher|订单无座席数据.'
			else:
				if not stations.SEAT_TYPE_QUNAR.has_key(order['seat'].keys()[0]):
					new_todo['status']='FAIL'
					new_todo['comment']='0|dispatcher|座席类型不能识别.'
				else:
					# 转换seat type为12306类型
					new_todo['seat_type'] = stations.SEAT_TYPE_QUNAR[order['seat'].keys()[0]] 
					new_todo['ext_seat_type'] = [stations.SEAT_TYPE_QUNAR[s.keys()[0]] for s in order['extSeat']]
					new_todo['ext_seat_type'].sort(reverse=True)

			todo_id=web_db.todo.insert(new_todo)
			if todo_id==None:
				print 'order: fail to insert todo.'
				print new_todo
			else:
				print '%s: %s %s %s' % (helper.time_str(), todo_id, new_todo['event'], new_todo['orderNo'])

		elif order['orderType']==1: # 联程订单，分开处理
			new_todo['tripNum'] = len(order['jointTrip']) # 几段行程
			for trip in order['jointTrip']:
				new_todo2=new_todo.copy()
				new_todo2['event']          = 'ORDER_JOINT'
				new_todo2['arrStation']     = trip['arrStation']
				new_todo2['dptStation']     = trip['dptStation']
				new_todo2['extSeat']        = trip['extSeat']
				new_todo2['seat']           = trip['seat']
				new_todo2['trainStartTime'] = trip['trainStartTime']
				new_todo2['trainEndTime']   = trip['trainEndTime']
				new_todo2['trainNo']        = trip['trainNo']
				new_todo2['seq']            = int(trip['seq'])
				new_todo2['check_pass']     = 'WAIT'	# 用于同步联程订单, 所以子订单都到CHECK通过
									# WAIT 等待CHECK
									# FAIL CHECK失败
									# PASS CHECK通过
				new_todo2['pay_pass']       = 'WAIT'	# 用于同步联程订单, 所以子订单都到READY_TO_PAY通过
									# WAIT 等待CHECK
									# FAIL CHECK失败
									# PASS CHECK通过
				new_todo2['b_time'] = int(time.time())
				if new_todo2['b_time']-new_todo2['orderTick']>600: # 根据订单下单时间优先进入队列
					new_todo2['e_time'] = new_todo2['b_time']
				else:
					new_todo2['e_time'] = new_todo2['b_time'] + 15

				# 数据调整，匹配processor
				begin_code=stations.find_code(trip['dptStation'].encode('utf-8'))
				end_code=stations.find_code(trip['arrStation'].encode('utf-8'))
				new_todo2['start_station'] = begin_code
				new_todo2['stop_station'] = end_code
				start_time = trip['trainStartTime'].split()
				new_todo2['start_date'] = start_time[0]
				new_todo2['start_time'] = start_time[1]
				# 转换seat type为12306类型
				if not stations.SEAT_TYPE_QUNAR.has_key(trip['seat'].keys()[0]):
					new_todo2['status']='FAIL'
					new_todo2['comment']='0|dispatcher|座席类型不能识别.'
				else:
					new_todo2['seat_type'] = stations.SEAT_TYPE_QUNAR[trip['seat'].keys()[0]] 
					new_todo2['ext_seat_type'] = [stations.SEAT_TYPE_QUNAR[s.keys()[0]] for s in trip['extSeat']]
					new_todo2['ext_seat_type'].sort(reverse=True)

				todo_id=web_db.todo.insert(new_todo2)
				if todo_id==None:
					print 'order: fail to insert todo.'
					print new_todo2
				else:
					print '%s: %s %s %s' % (helper.time_str(), todo_id, new_todo2['event'], new_todo2['orderNo'])

		else:
			print '%s: unknown orderType: %d' % (helper.time_str(), order['orderType'])

	print '-------------------------------------------------------'

def main_loop_refund():
	# 取退票订单信息, 并分发事件
	ret, result = httphelper3.QUNAR_query_orders('QUNAR', True)
	if ret<0:
		print 'ERROR: ', result
		return
		
	if result['ret']==False:
		print result['errMsg']
		return
	
	for order in result['data']:
		db_chk = web_db.qunar.find_one({'orderNo': order['orderNo']},{'_id':1, 'return':1})
		if db_chk==None: # 没有出票记录，无法退票
			print '%s: order <%s> no order history.' % (helper.time_str(), order['orderNo'])
			ret, data = httphelper3.QUNAR_process_refund('QUNAR', order['orderNo'].encode('utf-8'), False, 5, '没有出票记录')
			if ret<0:
				print data
			elif data['ret']==False:
				print data['errMsg']
			continue
		
		# 检查退票状态
		if db_chk['return']==1:
			print '%s: order <%s> is already in RETURN process.' % (helper.time_str(), order['orderNo'])
			continue
		elif db_chk['return']==2:
			print '%s: order <%s> has finished RETURN process.' % (helper.time_str(), order['orderNo'])
			continue

		web_db.qunar.update({'orderNo': order['orderNo']},{'$set': {'return':1, 'return_data':order}}) # 标记退票
		web_db.todo.update({'orderNo': order['orderNo']},
			{'$set': {'return':1, 'check_pass':'WAIT'}},multi=True) # 标记退票
		#
		# 标记退票后两种可能：
		#  1. 订单尚未付款，等待付款后到FINISH，才处理退票. ！如果客户在出票前退款，auto_pay会20分钟超时
		#  2. 订单已付款，在FINISH状态下，按已付款订单退票处理
		#  
		print '%s: RETURN %s' % (helper.time_str(), order['orderNo'])
	
	print '-------------------------------------------------------'

if __name__=='__main__':
  
	print "DISPATCHER: %s started" % helper.time_str()

	gc.set_threshold(300,5,5)

	try:
		while 1:
			hh = time.localtime().tm_hour
			
			if hh>=7 and hh<23:
				print 'WAIT_TICKET: %s' % helper.time_str()
				main_loop_wait()

				sys.stdout.flush()
				time.sleep(DEALY)
			
				print 'REFUND_TICKET: %s' % helper.time_str()
				main_loop_refund()

			sys.stdout.flush()
			free_12306()
			time.sleep(DEALY)

	except KeyboardInterrupt:
		print
		print 'Ctrl-C!'

	print "DISPATCHER: %s exited" % helper.time_str()