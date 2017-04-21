#!/usr/bin/env python
# -*- coding: utf-8 -*-

import web, urllib
#import time
import gc
from config.url import urls2
#from helper import Logger, time_str

app = web.application(urls2, globals())
application = app.wsgifunc()

gc.set_threshold(300,5,5)

##############################################

ERR_MSG = {
	'100' : '正常返回',
	'101' : '网络购票时间为7:00~23:00，其余时间不提供查询',
	'102' : '系统错误，未知服务异常',
	'103' : '访问限制，IP被禁止',
	'104' : '实际出票座席数量与证件数不符',
	'105' : 'Datas不是有效的JSON数据',
}

ID_TYPE = {
	"1" : "二代身份证",
	"C" : "港澳通行证",
	"G" : "台湾通行证",
	"B" : "护照"
}

CITY={
	'11':"北京",'12':"天津",'13':"河北",'14':"山西",'15':"内蒙古",'21':"辽宁",'22':"吉林",'23':"黑龙江 ",
	'31':"上海",'32':"江苏",'33':"浙江",'34':"安徽",'35':"福建",'36':"江西",'37':"山东",'41':"河南",
	'42':"湖北",'43':"湖南",'44':"广东",'45':"广西",'46':"海南",'50':"重庆",'51':"四川",'52':"贵州",
	'53':"云南",'54':"西藏",'61':"陕西",'62':"甘肃",'63':"青海",'64':"宁夏",'65':"新疆",'71':"台湾",
	'81':"香港",'82':"澳门",'91':"国外"
}

CHECK_BIT = lambda string: ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2'] \
		[sum( map( lambda x: x[0]*x[1], \
		zip([7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2], map( int, string )))) % 11]

def check_id_valid(id_no):
	
	if len(id_no)!=18:
		return False
	
	if not CITY.has_key(id_no[:2]):
		return False
	
	if not (id_no[6:8] in ('18', '19', '20')):
		return False
	
	mon=int(id_no[10:12])
	day=int(id_no[12:14])
	if mon==0 or mon>12 or day==0 or day>31:
		return False
	
	if CHECK_BIT(id_no[:-1])!=id_no[-1].upper():
		return False
		
	return True

class CheckPassengers:
	def POST(self):
		import json
		
		result={}
		
		while 1:
			try:
				user_data=json.loads(urllib.unquote_plus(web.data().split('=')[1]))
			except ValueError:
				print web.data()
				result = { 'ret':False, 'errCode':'105', 'errMsg':ERR_MSG['105'] }
				break

			if not user_data.has_key('passengers'):
				result = { 'ret':False, 'errCode':'105', 'errMsg':ERR_MSG['105'] }
				break

			result['status'] = True
			result['passenger_total'] = len(user_data['passengers'])
			result['passengers'] = []
			for p in user_data['passengers']:
				p2 = {
					'passenger_name'         : p['passenger_name'].encode('utf-8'),
					'passenger_id_no'        : p['passenger_id_no'].encode('utf-8'),
					'passenger_id_type_code' : p['passenger_id_type_code'].encode('utf-8'),
					'passenger_id_type_name' : ID_TYPE[p['passenger_id_type_code']] if ID_TYPE.has_key(p['passenger_id_type_code']) else '未知',
					'passenger_type'         : '1',
					'passenger_type_name'    : '成人' # 无法判断是否儿童，按1.5米以下分别
				}
				if p['passenger_id_type_code']!='1': # 对非二代身份证，返回“待核验”
					p2['verification_status']='0'
					p2['verification_status_name']='待核验'
				else:
					if check_id_valid(p['passenger_id_no']): # 检查身份证号码是否有效
						p2['verification_status']='1'
						p2['verification_status_name']='已通过'
					else:
						p2['verification_status']='-1'
						p2['verification_status_name']='未通过'
				result['passengers'].append(p2)

			break

		web.header("Content-Type", "application/json")
		#print result
		return json.dumps(result, ensure_ascii=False)


#if __name__ == "__main__":
#    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)
#    app.run()



