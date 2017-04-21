#!/usr/bin/env python
# -*- coding: utf-8 -*-

import web
import time
import gc
from bson.objectid import ObjectId
from config.url import urls
from config import setting
from config.mongosession import MongoStore
import helper
from helper import Logger, time_str

web_db = setting.db_web  # 默认db使用web本地
file_db = web_db #setting.db_file1

app = web.application(urls, globals())
application = app.wsgifunc()

web.config.session_parameters['cookie_name'] = 'web_session'
web.config.session_parameters['secret_key'] = 'f6102bff8452386b8ca1'
web.config.session_parameters['timeout'] = 86400
web.config.session_parameters['ignore_expiry'] = True

if setting.debug_mode==False:
	### for production
	session = web.session.Session(app, MongoStore(web_db, 'sessions'), 
		initializer={'login': 0, 'privilege': 0, 'uname':'', 'uid':''})
else:
	### for staging,
	if web.config.get('_session') is None:
		session = web.session.Session(app, MongoStore(web_db, 'sessions'), 
			initializer={'login': 0, 'privilege': 0, 'uname':'', 'uid':''})
		web.config._session = session
	else:
		session = web.config._session

gc.set_threshold(300,5,5)

##############################################

PRIV_VISITOR = 0b0000  # 0
PRIV_ADMIN   = 0b1000  # 8
PRIV_USER    = 0b0100  # 4
PRIV_KAM     = 0b0010  # 2
PRIV_API     = 0b0001  # 1

user_level = {
	PRIV_VISITOR: '访客',
	PRIV_USER: '人工座席',
	PRIV_ADMIN: '管理员',
	PRIV_KAM: 'DEMO用户', # demo 借用
	PRIV_API: 'API接口',
}

is_mobi=''  # '' - 普通请求，'M' - html5请求

def my_crypt(codestr):
	import hashlib
	return hashlib.sha1("sAlT139-"+codestr).hexdigest()

def my_rand():
	import random
	return ''.join([random.choice('ABCDEFGHJKLMNPQRSTUVWXY23456789') for ch in range(8)])

def my_simple_hid(codestr):
	codebook='EPLKJHQWEIRUSDOPCNZX';
	newcode=''
	for i in range(0, len(codestr)):
		newcode+=codebook[ord(codestr[i])%20]
	return newcode

def new_api_code():
	api_id = my_rand()
	api_key = my_crypt(api_id)
	return {'API_ID' : api_id, 'API_KEY' : api_key}

def logged(privilege = -1):
    if session.login==1:
      if privilege == -1:  # 只检查login, 不检查权限
        return True
      else:
        if int(session.privilege) & privilege: # 检查特定权限
          return True
        else:
          return False
    else:
        return False

def create_render(privilege, plain=False):
    global is_mobi
    # check mobile
    #if helper.detect_mobile():
    #  is_mobi='M'
    #else:
    #  is_mobi=''
    
    if plain: layout=None
    else: layout='layout'
    
    if logged():
        if privilege == PRIV_USER or privilege == PRIV_KAM:
            render = web.template.render('templates/user%s' % is_mobi, base=layout)
        elif privilege == PRIV_ADMIN:
            render = web.template.render('templates/admin%s' % is_mobi, base=layout)
        elif privilege == PRIV_API:
            render = web.template.render('templates/api%s' % is_mobi, base=layout)
        else:
            render = web.template.render('templates/visitor%s' % is_mobi, base=layout)
    else:
        render = web.template.render('templates/visitor%s' % is_mobi, base=layout)

    # to find memory leak
    #_unreachable = gc.collect()
    #print 'Unreachable object: %d' % _unreachable
    #print 'Garbage object num: %s' % str(gc.garbage)

    return render

class Aticle:
    def GET(self):
      render = create_render(PRIV_VISITOR)
      user_data=web.input(id='')
      if user_data.id=='1':
        return render.article_agreement()
      elif user_data.id=='2':
        return render.article_faq()
      else:
        return render.info('不支持的文档查询！', '/')

class Agreement:
    def GET(self):
      render = create_render(PRIV_VISITOR)
      # 删除旧的注册记录
      web_db.alert_queue.remove({'$and': [{'type' : 'signup'},{'sent' : -99}]})
      return render.agreement()

    def POST(self):
      render = create_render(PRIV_VISITOR)
      user_data=web.input(agree='')
      
      if user_data['agree']=='':
        return render.info('请阅读并同意《芙蓉捌网络科技云服务条款》后，方可注册！', '/agreement', '阅读服务条款')  
      else:
        raise web.seeother('/sign_up') 

class SignUp:
    def GET(self):
      render = create_render(PRIV_VISITOR)
      
      if web.ctx.has_key('environ'):
        if web.ctx.environ.has_key('HTTP_REFERER'):
          if '/agreement' not in web.ctx.environ['HTTP_REFERER']:
            return render.info('请阅读并同意《芙蓉捌网络科技云服务条款》后，方可注册！', '/agreement', '阅读服务条款')
        else:
          return render.info('请阅读并同意《芙蓉捌网络科技云服务条款》后，方可注册！', '/agreement', '阅读服务条款')

      db_sys = web_db.user.find_one({'uname':'settings'})
      if db_sys==None: # 新系统？！！！
        return render.info('系统维护中，暂时不允许注册新用户。请稍候再试。', '/', '返回')
      elif db_sys['signup']==0:
        return render.info('系统维护中，暂时不允许注册新用户。请稍候再试。', '/', '返回')
        
      import random
      import Image
      
      magic="%06d" % random.randrange(0,999999)
      hash1=my_crypt(magic+str(time.time()))

      try:
        im = Image.open(setting.tmp_path+'/_blank.jpg')
        im2 = Image.open(setting.tmp_path+'/_digits.jpg')
        for i in range(0,6):
          box1=(0+int(magic[i])*15, 0, 15+int(magic[i])*15, 25)
          box2=(0+i*15, 0, 15+i*15, 25)
          im.paste(im2.crop(box1), box2)
        im.save(setting.tmp_path+'/ts_'+hash1+'.jpg')
      except IOError, e:
        Logger.uLog(Logger.SIGNUP_IOERR, str(e)) 
        return render.info('系统有点忙，请重试！', '/')  
      
      web_db.alert_queue.insert({'type' : 'signup', 
                                 'email': '',
                                 'hash' : hash1, 
                                 'magic': magic,
                                 'time' : time.time(),
                                 'sent' : -99, # 不允许发送
                                })
      return render.sign_up(hash1)

    def POST(self):
      render = create_render(PRIV_VISITOR)
      user_data=web.input(email='', hash1='', magic='')
          
      if helper.validateEmail(user_data['email'])==0:
        return render.info('请输入正确的email地址！')  

      db_reg = web_db.alert_queue.find_one({'hash': user_data['hash1']})
      if db_reg==None:
        Logger.uLog(Logger.SIGNUP_WRONG, user_data['e']) 
        return render.info('未找到您的注册信息，注册失败！') 

      if db_reg['magic']!=user_data['magic']:
        return render.info('您输入的验证码不对，请重新注册！') 
          
      db_user=web_db.user.find_one({'uname':user_data['email'].lower()},{'_id':1})
      if db_user!=None:
        return render.info('此邮件地址已注册，不能重复注册！')  
      
      # 删除此email的旧注册记录
      web_db.alert_queue.remove({'$and': [{'type' :'signup'}, {'email':user_data['email'].lower()} ]}),
      # 更新注册记录                                       
      web_db.alert_queue.update({'hash' : db_reg['hash']},
                                {'$set': {'email': user_data['email'].lower(), 'sent' : 0 }})
      return render.info('系统已经发送确认邮件给您，请在收到邮件后根据提示完成注册。谢谢！', '/')

class SignIn:
    def GET(self):
      render = create_render(PRIV_VISITOR)
      user_data=web.input(h='')
        
      if user_data['h']=='':
        return render.info('参数错误！请点击确认邮件的中连接地址。', '/') 
          
      db_reg = web_db.alert_queue.find_one({'hash': user_data['h']})
      if db_reg==None:
        Logger.uLog(Logger.SIGNIN_WRONG, user_data['h']) 
        return render.info('未找到您的注册信息，注册失败！', '/') 
      else:
        if db_reg['sent']!=1: # 用未发确认邮件的hash来注册，有问题！
          Logger.uLog(Logger.SIGNIN_WRONG, user_data['h']) 
          return render.info('未找到您的注册信息，注册失败！！', '/')  
        
        db_user=web_db.user.find_one({'uname':db_reg['email']},{'_id':1})
        if db_user!=None:
          return render.info('此邮件地址已注册，不能重复注册！', '/')
          
        return render.sign_in(db_reg['email'], user_data['h'])

    def POST(self):
      render = create_render(PRIV_VISITOR)
      user_data=web.input(h='', new_pwd='', new_pwd2='')

      if user_data['h']=='':
        return render.info('参数错误！请点击确认邮件的中连接地址。', '/') 
          
      db_reg = web_db.alert_queue.find_one({'hash': user_data['h']})
      if db_reg==None:
        Logger.uLog(Logger.SIGNIN_WRONG, user_data['h']) 
        return render.info('未找到您的注册信息，注册失败！', '/') 
      else:
        if db_reg['sent']!=1: # 用未发确认邮件的hash来注册，有问题！
          Logger.uLog(Logger.SIGNIN_WRONG, user_data['h']) 
          return render.info('未找到您的注册信息，注册失败！！', '/')  
        
        db_user=web_db.user.find_one({'uname':db_reg['email']},{'_id':1})
        if db_user!=None:
          return render.info('此邮件地址已注册，不能重复注册！', '/')

        new_pwd = user_data.new_pwd.strip()
        new_pwd2 = user_data.new_pwd2.strip()
        
        if new_pwd=='':
          return render.info('密码不能为空！请重新设置。', '/sign_in?h=%s' % user_data.h, '重新设置')
        
        if new_pwd!=new_pwd2:
          return render.info('两次输入的新密码不一致！请重新设置。', '/sign_in?h=%s' % user_data.h, '重新设置')

        # 添加用户记录
        web_db.user.insert({'login'           : 1,
                            'uname'           : db_reg['email'],
                            'full_name'       : '',
                            'privilege'       : PRIV_API,
                            'passwd'          : my_crypt(new_pwd),
                            'time'            : time.time(),  # 注册时间
                           })
        # 清理注册信息
        web_db.alert_queue.update({'hash' : db_reg['hash']}, {'$set': {'sent' : -99}})
        return render.info(u'已完成注册！现在可以用您登记的邮件地址登录了。', '/', '登录') 
        
class Login:
    def GET(self):
        if logged():
            render = create_render(session.privilege)
            return render.portal(session.uname, user_level[session.privilege])
        else:
            render = create_render(session.privilege)

            db_sys = web_db.user.find_one({'uname':'settings'})
            if db_sys==None:
              signup=0
            else:
              signup=db_sys['signup']
            Logger.uLog(Logger.VISIT, '')
            return render.login(signup)

    def POST(self):
        name0, passwd = web.input().name, web.input().passwd
        
        name = name0.lower()
                
        db_user=web_db.user.find_one({'uname':name},{'login':1,'passwd':1,'privilege':1})
        if db_user!=None and db_user['login']!=0:
          if db_user['passwd']==my_crypt(passwd):
                session.login = 1
                session.uname=name
                session.uid = db_user['_id']
                session.privilege = db_user['privilege']
                raise web.seeother('/')
        
        session.login = 0
        session.privilege = 0
        session.uname=''
        render = create_render(session.privilege)
        Logger.uLog(Logger.LOGIN_FAIL, name)
        return render.login_error()

class Reset:
    def GET(self):
        session.login = 0
        session.kill()
        render = create_render(session.privilege)
        return render.logout()

class SettingsUser:
    def _get_settings(self):
      db_user=web_db.user.find_one({'_id':session.uid},{'uname':1,'full_name':1})
      return db_user
        
    def GET(self):
      if logged(PRIV_USER|PRIV_API):
        render = create_render(session.privilege)
        return render.settings_user(session.uname, user_level[session.privilege], self._get_settings())
      else:
        raise web.seeother('/')

    def POST(self):
      if logged(PRIV_USER|PRIV_API):
        render = create_render(session.privilege)
        full_name = web.input().full_name
        old_pwd = web.input().old_pwd.strip()
        new_pwd = web.input().new_pwd.strip()
        new_pwd2 = web.input().new_pwd2.strip()
        
        if old_pwd!='':
          if new_pwd=='':
            return render.info('新密码不能为空！请重新设置。')          
          if new_pwd!=new_pwd2:
            return render.info('两次输入的新密码不一致！请重新设置。')
          db_user=web_db.user.find_one({'_id':session.uid},{'passwd':1})
          if my_crypt(old_pwd)==db_user['passwd']:
            web_db.user.update({'_id':session.uid}, 
              {'$set':{'passwd'   : my_crypt(new_pwd),
                       'full_name': full_name}})
          else:
            return render.info('登录密码验证失败！请重新设置。')
        else:
          web_db.user.update({'_id':session.uid}, {'$set':{'full_name':full_name}})
        
        Logger.uLog(Logger.USER_UPDATE, session.uid)
        return render.info('成功保存！')
      else:
        raise web.seeother('/')

class Query:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			db_todos=web_db.todo.find(
				{'$and' : [
					{'uid': session.uid},
					{'lock' : {'$ne': 1}},
					{'man':1}
				]},
				{'event':1, 'status':1, 'train_info':1}
			)
			todos=[]
			if db_todos.count()>0:
				for todo in db_todos:
					todos.append((todo['_id'], todo['event'], todo['status'], todo['train_info']))
			return render.query(session.uname, user_level[session.privilege], todos)
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_USER):
			import stations

			render = create_render(session.privilege)
			user_data=web.input(start_station='', stop_station='', start_date='')

			if '' in (user_data['start_station'], user_data['stop_station'], user_data['start_date']):
				return render.info('请输入查询条件！')

			begin_code=stations.find_code(user_data['start_station'].encode('utf-8'))
			end_code=stations.find_code(user_data['stop_station'].encode('utf-8'))

			if begin_code=='' or end_code=='':
				begin_like=stations.find_like(user_data['start_station'].encode('utf-8')).keys()
				end_like=stations.find_like(user_data['stop_station'].encode('utf-8')).keys()
				return render.info('起始站名有误，请检查！', 
						more=['相似的出发站：%s ' % '、'.join(begin_like),
						      '相似的目的站：%s' %  '、'.join(end_like)] )

			tick=int(time.time())
			todo_id=web_db.todo.insert({
				'uid'            : session.uid,
				'event'          : 'ORDER_UI',
				'status'         : 'QUERY',
				'start_station'  : begin_code,
				'stop_station'   : end_code,
				'start_date'     : user_data['start_date'],
				'lock'           : 0,
				'man'            : 0,
				'next_status'    : '',
				'comment'        : '',
				'history'        : [],
				'b_time'         : tick,
				'e_time'         : tick
			})
			
			if todo_id!=None:
				return render.query_result(session.uname, user_level[session.privilege], str(todo_id))
			else:
				Logger.uLog(Logger.TODO_INS_FAIL, session.uid)
				return render.info('查询失败，请稍后重试。')
		else:
			raise web.seeother('/')

class Checkout:
	def GET(self):
		import json

		result={}
		if logged(PRIV_USER):
			user_data=web.input(todo='')

			if user_data.todo!='': #除API以为的订单
				db_todo=web_db.todo.find_one({'$and' : [{'_id': ObjectId(user_data.todo)}, {'event':{'$ne':'ORDER_API'}}]})
				if db_todo!=None:
					result['id']=str(db_todo['_id'])
					result['event']=db_todo['event']
					result['status']=db_todo['status']
					result['elapse']=db_todo['e_time']-db_todo['b_time']
					result['lock']=db_todo['lock']
					result['man']=db_todo['man']
					result['comment']=db_todo['comment']
					if db_todo.has_key('result'):
						result['result']=db_todo['result']
					else:
						result['result']=[]
					# 如果事件已处理完，checkout将删除此事件
					#if db_todo['status'] in ('SUCCESS', 'FAIL'):
					#	web_db.todo.remove({'_id': db_todo['_id']}) 

		web.header("Content-Type", "application/json")
		return json.dumps(result)

class Sjrand:
	def GET(self):
		if logged(PRIV_USER):
			user_data=web.input(todo='')

			if user_data.todo=='':
				raise web.seeother('/static/sjrand.png')

			db_todo=web_db.todo.find_one({'$and': [{'_id': ObjectId(user_data.todo)},
							       {'status' : 'SJRAND'}]})
			if db_todo!=None and db_todo.has_key('sjrand'):
				try:
					h=open('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand']), 'rb')
					data = h.read()
					h.close()
				except IOError, e:
					print "IOError: %s" % e
					raise web.seeother('/static/sjrand.png')

				web.header("Content-Description", "File Transfer")
				web.header("Content-Type", "application/octet-stream")
				web.header('Content-Disposition', 'attachment; filename="sjrand.png"')
				web.header("Content-Transfer-Encoding", "binary")
				web.header("Content-Length", "%d" % len(data))
				return data
			else:
				raise web.seeother('/static/sjrand.png')
		else:
			raise web.seeother('/static/sjrand.png')

class Sjrand_p:
	def GET(self):
		if logged(PRIV_USER):
			user_data=web.input(todo='')

			if user_data.todo=='':
				raise web.seeother('/static/sjrand.png')

			db_todo=web_db.todo.find_one({'$and': [{'_id': ObjectId(user_data.todo)},
							       {'status' : 'SJRAND_P'}]})
			if db_todo!=None and db_todo.has_key('sjrand_p'):
				try:
					h=open('%s/%s.png' % (setting.sjrand_path, db_todo['sjrand_p']), 'rb')
					data = h.read()
					h.close()
				except IOError, e:
					print "IOError: %s" % e
					raise web.seeother('/static/sjrand.png')

				web.header("Content-Description", "File Transfer")
				web.header("Content-Type", "application/octet-stream")
				web.header('Content-Disposition', 'attachment; filename="sjrand.png"')
				web.header("Content-Transfer-Encoding", "binary")
				web.header("Content-Length", "%d" % len(data))
				return data
			else:
				raise web.seeother('/static/sjrand.png')
		else:
			raise web.seeother('/static/sjrand.png')

class Order:
	#
	# 输入验证码、车票信息 --> 提交 --> 等待返回结果
	#
	def GET(self):
		if logged(PRIV_USER):
			import urllib, base64

			render = create_render(session.privilege)
			user_data=web.input(todo='', s='')
			
			if session.uname not in setting.auth_user:
				return render.info('无操作权限！')
			
			if '' in (user_data.s, user_data.todo):
				return render.info('参数错误！')

			s2 = user_data.s.replace('%2B','+').replace('%2b','+').replace('%2F','/').replace('%2f','/').replace('%3D','=').replace('%3d','=')
			s3=base64.b64decode(s2).split('#')
			
			#添加todo事件
			tick=int(time.time())
			web_db.todo.update({'$and':[{'_id':ObjectId(user_data.todo)},{'uid':session.uid}]},
				{'$set':{
					'status'         : 'ORDER',
					'lock'           : 0,
					'man'            : 0,
					'retry'          : 0,
					'secretStr'      : urllib.quote_plus(user_data.s),
					'train_info'     : '%s %s %s %s %s %s %s' % (s3[0], s3[4], s3[2], s3[9], s3[10], s3[6], s3[7]),
					'e_time'         : tick
					}
			})
			return render.router(session.uname, user_level[session.privilege], user_data.todo)
		else:
			raise web.seeother('/')

class Router:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='')
			
			if user_data.todo=='':
				return render.info('参数错误！')

			return render.router(session.uname, user_level[session.privilege], user_data.todo)
		else:
			raise web.seeother('/')

class Cancel:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='')
			
			if user_data.todo=='':
				return render.info('参数错误！')

			web_db.todo.update({'$and':[{'_id':ObjectId(user_data.todo)},{'uid':session.uid}]},
				{'$set':{'status':'CANCEL', 'comment':'手工取消', 'lock':0, 'man':0}})

			return web.seeother('/query')
		else:
			raise web.seeother('/')

class Order2:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='')
			
			if user_data.todo=='':
				return render.info('参数错误！')

			db_todo=web_db.todo.find_one({'_id': ObjectId(user_data.todo)},
				{'_id':1, 'rand_code':1, 'user_12306':1, 'pass_12306':1})
			if db_todo!=None:
				return render.order(session.uname, user_level[session.privilege], user_data.todo,
					db_todo['user_12306'] if db_todo.has_key('user_12306') else '',
					db_todo['pass_12306'] if db_todo.has_key('pass_12306') else '',
					db_todo['rand_code'] if db_todo.has_key('rand_code') else '')
			else:
				return render.info('出错，请重新提交。')
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='', rand_code='', name12306='', pwd12306='')
			if '' in (user_data.rand_code, user_data.name12306, user_data.pwd12306, user_data.todo):
				return render.info('请输入用户名、密码和随机码！')
			
			todo_update={'status'     : 'LOGIN', 
				     'comment'    : '',
				     'man'        : 0,
				     'lock'       : 0,
				     'rand_code'  : user_data.rand_code, #sj_rand,
				     'user_12306' : user_data.name12306,
				     'pass_12306' : user_data.pwd12306,
				     'e_time'     : int(time.time())
				    }
			r = web_db.todo.update({'_id':ObjectId(user_data.todo)}, {'$set': todo_update})
			#print r
			return render.router(session.uname, user_level[session.privilege], user_data.todo)
		else:
			raise web.seeother('/')

class Verify:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='')
			
			if user_data.todo=='':
				return render.info('参数错误！')

			db_todo=web_db.todo.find_one({'_id': ObjectId(user_data.todo)},{'initDc':1, 'rand_code_p':1})
			if db_todo!=None:
				# 取得车次信息
				return render.verify(session.uname, user_level[session.privilege], 
					user_data.todo, 
					db_todo['initDc']['query_ticket_request'],
					db_todo['initDc']['left_details'],
					db_todo['rand_code_p'] if db_todo.has_key('rand_code_p') else '')
			else:
				return render.info('出错，请重新提交。')
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='', rand_code='', seat_type='', id_name='', id_type='', id_no='')
			if user_data.rand_code=='':
				return render.info('请输入随机码！')

			if '' in (user_data.seat_type, user_data.id_name, user_data.id_type, user_data.id_no, user_data.todo):
				return render.info('请输入购票信息！')

			passengers = [
				{
						'name'       : user_data.id_name,
						'certType'   : user_data.id_type,
						'certNo'     : user_data.id_no,
						'ticketType' : '1', # 成人票
				}
			]
			
			todo_update={'status'      : 'BOOK', 
				     'comment'     : '',
				     'man'         : 0,
				     'lock'        : 0,
				     'rand_code_p' : user_data.rand_code, #sj_rand,
				     'passengers'  : passengers,
				     'seat_type'   : user_data.seat_type,
				     'e_time'      : int(time.time())
				    }
			r = web_db.todo.update({'_id':ObjectId(user_data.todo)}, {'$set': todo_update})
			#print r
			return render.router(session.uname, user_level[session.privilege], user_data.todo)
		else:
			raise web.seeother('/')

class Pay:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='')
			if user_data.todo=='':
				return render.info('参数错误！')

			db_todo=web_db.todo.find_one({'_id': ObjectId(user_data.todo)},{'ticket':1, 'user_12306':1})
			if db_todo!=None:
				# 取得车次信息
				return render.pay(session.uname, user_level[session.privilege], 
					user_data.todo, 
					db_todo['ticket']['orderId'],
					db_todo['user_12306'])
			else:
				return render.info('出错，请重新提交。')
		else:
			raise web.seeother('/')

class Man:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			return render.man(session.uname, user_level[session.privilege])
		else:
			raise web.seeother('/')

class Man2:
	def GET(self):
		if logged(PRIV_USER|PRIV_KAM):
			render = create_render(session.privilege)
			return render.man2(session.uname, user_level[session.privilege])
		else:
			raise web.seeother('/')

class Man3:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			return render.man3(session.uname, user_level[session.privilege])
		else:
			raise web.seeother('/')

class CheckoutSjrand:
	def GET(self):
		import json
		result={'data':[]}
		if logged(PRIV_USER):
			db_todo=web_db.todo.find(
				{'$and': [
					{'status' : {'$nin': ['FINISH']}},  # ['FINISH','SJRAND','SJRAND_P']
					{'event'  : {'$ne':'ORDER_API'}},
					{'lock'   : 0}
				]}, 
				{'event':1, 'status':1, 'b_time':1, 'e_time':1, 'lock':1, 
				 'man':1, 'user_12306':1, 'comment':1, 'pay_limit_time':1, 
				 'payStatus':1, 'orderNo':1, 'trainStartTime':1, 'orderType':1, 'return':1, 'ticketPay':1}
			) .sort([('b_time',1)])  # 先下单的先打码
			if db_todo.count()>0:
				for todo in db_todo:
					if todo['event'] == 'ORDER_UI':  # 人工处理界面，不处理手工下单的订单
						continue
					
					start_tick = int(time.mktime(time.strptime(todo['trainStartTime'],"%Y-%m-%d %H:%M")))
					
					result['data'].append({
						'id'        : str(todo['_id']), 
						'event'     : todo['event'],
						'status'    : todo['status'],
						'elapse'    : int(time.time())-todo['e_time'], #todo['e_time']-todo['b_time'],
						'lock'      : todo['lock'],
						'man'       : todo['man'],
						'user'      : todo['user_12306'] if todo.has_key('user_12306') else '',
						'comment'   : todo['comment'],
						'limit'     : todo['pay_limit_time'] if todo.has_key('pay_limit_time') else '',
						'payStatus' : todo['payStatus'] if todo.has_key('payStatus') else '',
						'orderNo'   : todo['orderNo'],
						'urgent'    : 1 if (start_tick-int(time.time()))/3600<24 else 0,
						'orderType' : todo['orderType'],
						'return'    : todo['return'],
						'ticketPay' : todo['ticketPay'],
					})
			result['num']=len(result['data'])
		#print result
		web.header("Content-Type", "application/json")
		return json.dumps(result)


class CheckoutSjrand2: # 提交验证码后返回新的图片
	def GET(self):
		import json

		web.header("Content-Type", "application/json")

		result={'data':[]}
		
		if logged(PRIV_USER|PRIV_KAM):
			user_data=web.input(todo='', rand_code='99,87', p='0')
			if user_data.todo!='': # 有验证码提交
				db_todo=web_db.todo.find_and_modify(
					query=	{'$and' : [
							{ '_id': ObjectId(user_data.todo) },
							{ 'lock' : 0}
						]},
					update=	{'$set': {'lock':1}},
					fields=	{'status':1}
				)
				if db_todo==None:
					return json.dumps({'ret':-1})

				now_tick = int(time.time())
				if db_todo['status']=='SJRAND':
					todo_update={'status'     : 'LOGIN', 
						     'comment'    : '',
						     'man'        : 0,
						     'lock'       : 0,
						     'rand_code'  : user_data.rand_code, #sj_rand,
						     'cs_rand'    : session.uname,
						     'cs_time'    : now_tick
						    }
				elif db_todo['status']=='SJRAND_P':
					todo_update={'status'      : 'BOOK', 
						     'comment'     : '',
						     'man'         : 0,
						     'lock'        : 0,
						     'rand_code_p' : user_data.rand_code, #sj_rand,
						     'cs_rand_p'   : session.uname,
						     'cs_time'     : now_tick
						    }
				else:
					todo_update={ 
						     'lock'        : 0,
						     'cs_time'     : now_tick
						    }			
					#return json.dumps({'ret':-1})

				r = web_db.todo.update({'_id':ObjectId(user_data.todo)}, {'$set': todo_update})
				#print r
				#return json.dumps({'ret':0})
			

			# 准备新的随机码图片, 只返回一个 -----------------------------------

			if user_data.p=='1':
				code_type = 'SJRAND_P'
			else:
				code_type = 'SJRAND'
			db_todo=web_db.todo.find_and_modify(
				query  = {'$and': [
						{'status' : code_type}, 
						{'event'  : {'$nin': ['ORDER_API', 'ORDER_UI']}},
						{'lock'   : 0},
						{'cs_time': {'$lt': int(time.time())} }
					]
				}, 
				sort   = [('b_time',1)],  # 先下单的先打码
				update = {'$set': {'cs_time':int(time.time())+10}}, # 排名拖后，避免不同客服同时刷到。
				fields = {'event':1, 'status':1, 'b_time':1, 'e_time':1, 'lock':1, 'man':1}
				#, 'user_12306':1, 'comment':1, 'ticket_no_complete':1, 'payStatus':1}
			) 
			if db_todo!=None:
				result['data'].append({
					'id'      : str(db_todo['_id']), 
					'event'   : db_todo['event'],
					'status'  : db_todo['status'],
					#'elapse'  : db_todo['e_time']-db_todo['b_time'],
					'lock'    : db_todo['lock'],
					'man'     : db_todo['man'],
					#'user'    : db_todo['user_12306'] if db_todo.has_key('user_12306') else '',
					#'comment' : db_todo['comment'],
					#'limit'   : db_todo['ticket_no_complete']['orderDBList'][0]['tickets'][0]['pay_limit_time'] \
					#	if db_todo.has_key('ticket_no_complete') else '',
					#'payStatus' : db_todo['payStatus'] if db_todo.has_key('payStatus') else '',
				})
			result['num']=len(result['data'])

		#print result
		web.header("Content-Type", "application/json")
		return json.dumps(result)


class CheckoutSjrand3:
	def GET(self):
		import json
		result={'data':[]}
		if logged(PRIV_USER):
			db_todo=web_db.todo.find(
				{'$and': [
					{'status' : {'$in': ['PAY', 'SCAN', 'SCAN2']}},  # 只处理支付有关
					{'event'  : {'$ne':'ORDER_API'}},
					{'lock'   : 0}
				]}, 
				{'event':1, 'status':1, 'b_time':1, 'e_time':1, 'lock':1, 
				 'man':1, 'user_12306':1, 'comment':1, 'pay_limit_time':1, 
				 'payStatus':1, 'orderNo':1, 'trainStartTime':1, 'orderType':1, 'return':1, 'ticketPay':1}
			) .sort([('b_time',1)])  # 先下单的先打码
			if db_todo.count()>0:
				for todo in db_todo:
					if todo['event'] == 'ORDER_UI':  # 人工处理界面，不处理手工下单的订单
						continue
					
					start_tick = int(time.mktime(time.strptime(todo['trainStartTime'],"%Y-%m-%d %H:%M")))
					
					result['data'].append({
						'id'        : str(todo['_id']), 
						'event'     : todo['event'],
						'status'    : todo['status'],
						'elapse'    : int(time.time())-todo['e_time'], #todo['e_time']-todo['b_time'],
						'lock'      : todo['lock'],
						'man'       : todo['man'],
						'user'      : todo['user_12306'] if todo.has_key('user_12306') else '',
						#'comment'   : todo['comment'],
						'limit'     : todo['pay_limit_time'] if todo.has_key('pay_limit_time') else '',
						'payStatus' : todo['payStatus'] if todo.has_key('payStatus') else '',
						'orderNo'   : todo['orderNo'],
						'urgent'    : 1 if (start_tick-int(time.time()))/3600<24 else 0,
						'orderType' : todo['orderType'],
						'return'    : todo['return'],
						'ticketPay' : todo['ticketPay'],
					})
			result['num']=len(result['data'])
		#print result
		web.header("Content-Type", "application/json")
		return json.dumps(result)


class VerifySjrand:
	def GET(self):
		import json

		web.header("Content-Type", "application/json")
		
		if logged(PRIV_USER):
			user_data=web.input(todo='', rand_code='99,87')
			if '' == user_data.todo:
				return json.dumps({'ret':-1})

			db_todo=web_db.todo.find_and_modify(
				query=	{'$and' : [
						{ '_id': ObjectId(user_data.todo) },
						{ 'lock' : 0}
					]},
				update=	{'$set': {'lock':1}},
				fields=	{'status':1}
			)
			if db_todo==None:
				return json.dumps({'ret':-1})

			now_tick = int(time.time())
			if db_todo['status']=='SJRAND':
				todo_update={'status'     : 'LOGIN', 
					     'comment'    : '',
					     'man'        : 0,
					     'lock'       : 0,
					     'rand_code'  : user_data.rand_code, #sj_rand,
					     'cs_rand'    : session.uname,
					     'cs_time'    : now_tick
					    }
			elif db_todo['status']=='SJRAND_P':
				todo_update={'status'      : 'BOOK', 
					     'comment'     : '',
					     'man'         : 0,
					     'lock'        : 0,
					     'rand_code_p' : user_data.rand_code, #sj_rand,
					     'cs_rand_p'   : session.uname,
					     'cs_time'     : now_tick
					    }
			else:
				todo_update={ 
					     'lock'        : 0,
					     'cs_time'     : now_tick
					    }			
				#return json.dumps({'ret':-1})

			r = web_db.todo.update({'_id':ObjectId(user_data.todo)}, {'$set': todo_update})
			#print r
			return json.dumps({'ret':0})
		else:
			return json.dumps({'ret':-1})

class Pay2:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='')
			if user_data.todo=='':
				return render.info('参数错误！')
			
			db_status = web_db.todo.find_one({'_id':ObjectId(user_data.todo)},{'status':1, 'gateway_result':1})
			if db_status==None:
				return render.info('参数错误！')
			
			if db_status.has_key('gateway_result'): # 已生成一次支付宝交易，不再自动生成，避免重复付款
				todo_update={'status'     : 'FAIL', 
					     'comment'    : '0|PAY|已生成一次支付宝交易,需手工检查.',
					     'man'        : 0,
					     'lock'       : 0,
					     'e_time'     : int(time.time())
				}
				r = web_db.todo.update({'_id':ObjectId(user_data.todo)}, {'$set': todo_update})
				return render.info('已生成一次支付宝交易,需手工检查.')
			
			if db_status['status']=='PAY':
				todo_update={'status'     : 'PAY2', 
					     'comment'    : '',
					     'man'        : 0,
					     'lock'       : 0,
					     'e_time'     : int(time.time())
				}
				r = web_db.todo.update({'_id':ObjectId(user_data.todo)}, {'$set': todo_update})
				#print r
				return render.router(session.uname, user_level[session.privilege], user_data.todo)
			else:
				return render.info('状态不对，可能有人正在付款！')
		else:
			raise web.seeother('/')

class AliForm:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='')			
			if user_data.todo=='':
				return render.info('参数错误！')

			db_todo=web_db.todo.find_one({'_id': ObjectId(user_data.todo)},{'alipay_form':1})
			if db_todo!=None:
				# 状态转到 SCAN2, 等待确认结果
				todo_update={'status'     : 'SCAN2',
					     'comment'    : '',
					     'man'        : 1,
					     'lock'       : 0,
					     'e_time'     : int(time.time())
					    }
				web_db.todo.update({'_id': ObjectId(user_data.todo)}, {'$set': todo_update})
				# 取得车次信息
				return render.ali_form(session.uname, user_level[session.privilege], 
					user_data.todo, db_todo['alipay_form'])
			else:
				return render.info('出错，请重新提交。')
		else:
			raise web.seeother('/')


class PayResult:
	def GET(self):
		import json

		web.header("Content-Type", "application/json")
		
		if logged(PRIV_USER):
			user_data=web.input(todo='', success='')
			if '' in (user_data.success, user_data.todo):
				return json.dumps({'ret':-1})
			
			if user_data.success=='1':
				todo_update={'status'     : 'SCAN3', # 检查支付结果
					     'comment'    : '',
					     'man'        : 0,
					     'lock'       : 0,
					     'e_time'     : int(time.time())
					    }
			else:
				todo_update={'status'      : 'PAY', # 重新支付
					     'comment'     : '',
					     'man'         : 1,
					     'lock'        : 0,
					     'e_time'      : int(time.time())
					    }

			r = web_db.todo.update({'_id':ObjectId(user_data.todo)}, {'$set': todo_update})
			#print r
			return json.dumps({'ret':0})
		else:
			return json.dumps({'ret':-1})


class ViewEvent:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='')
			
			if user_data.todo=='':
				return render.info('参数错误！')

			auth_level = -1
			if session.uname in setting.auth_user:
				auth_level = 999
			elif session.uname in setting.cs_admin:
				auth_level = 1
			
			db_todo=web_db.todo.find_one({'_id': ObjectId(user_data.todo)})
			if db_todo!=None:
				pass_12306 = ''
				if auth_level>0 and db_todo['event'] in ('ORDER_SINGLE','ORDER_JOINT') and db_todo.has_key('user_12306'):
					db_u=web_db.user_12306.find_one({'uname': db_todo['user_12306']})
					if db_u!=None:
						pass_12306 = db_u['passwd']
				return render.view_event(session.uname, user_level[session.privilege], 
					user_data.todo, db_todo, int(time.time()-db_todo['e_time']), 
					auth_level,pass_12306) # 授权客服才能修改
			else:
				return render.info('出错，请重新提交。')
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(todo='', status='', crmtext0='', crmtext='')

			if '' in (user_data.status, user_data.todo):
				return render.info('错误的参数！')
			
			# 保存客服备注
			if user_data.status=='__CRM__':
				if user_data.crmtext0[0:3]=='n/a':
					crmt = u'%s %s\r\n%s' % (time_str(), session.uname, user_data.crmtext)
				else:
					crmt = u'%s%s %s\r\n%s' % (user_data.crmtext0, time_str(), session.uname, user_data.crmtext)
				web_db.todo.update({'_id':ObjectId(user_data.todo)}, {'$set' : {'crm_text' : crmt}})
				return render.info('保存完成', goto="/view_event?todo=%s" % user_data.todo)

			# 授权客服才能修改
			auth = False
			if user_data.status in ['RETURN_OK', 'FREE_USER', 'SCAN3', 'NO_TICKET', 'QUERY', 'FINISH'] and session.uname in setting.cs_admin:
				auth = True 
			elif session.uname in setting.auth_user:
				auth = True

			if not auth:
				return render.info('无操作权限！')

			todo_update={
				'lock'        : 0,
				'e_time'      : int(time.time())
			}				
				
			if user_data.status != '__NOP__':
				todo_update['status']=user_data.status

			if user_data.status=='PAY':
				todo_update['man']=1
			else:
				todo_update['man']=0
			
			if user_data.status=='RETURN':
				todo_update['return']=1
			elif user_data.status == '__CANCEL_RETURN__': # 手工拒绝退票
				todo_update['status']='REPORT'
				todo_update['return']=-1
				todo_update['comment']='1|__CANCEL_RETURN__|已取纸质车票或临近开车.'

			r = web_db.todo.update({'_id':ObjectId(user_data.todo)}, {'$set': todo_update})
			#print r
			return render.info('提交完成',goto="javascript:window.opener=null;window.close();",text2='关闭窗口')
		else:
			raise web.seeother('/')

class Crm:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			return render.crm(session.uname, user_level[session.privilege])
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(cat='', content='')

			if user_data.cat=='' or user_data.content=='':
				return render.info('错误的参数！')
			
			if user_data.cat=='_id':
				condi = {user_data.cat:ObjectId(user_data.content.strip())}
			else:
				condi = {user_data.cat:user_data.content.strip()}
			db_todo = web_db.todo.find(condi, {'orderNo':1,'tripNum':1,'seq':1}).sort([('_id',1)])
			if db_todo.count()>0:
				return render.report_order(session.uname, user_level[session.privilege], db_todo)
			else:
				return render.info('未查到订单信息。')
		else:
			raise web.seeother('/')


class Report:
	def GET(self):
		if logged(PRIV_USER):
			render = create_render(session.privilege)
			user_data=web.input(start_date='', cat='')
			
			if user_data['start_date']=='':
				return render.report(session.uname, user_level[session.privilege])

			import stations

			start_tick = time.mktime(time.strptime('%s 00:00:00' % user_data['start_date'],'%Y-%m-%d %H:%M:%S'))
			stop_tick = time.mktime(time.strptime('%s 23:59:59' % user_data['start_date'],'%Y-%m-%d %H:%M:%S'))
			and_request = [
					{'event' : {'$ne' : 'ORDER_UI'}},
					{'status': 'FINISH'},
					{'e_time': {'$gte' : start_tick}},
					{'e_time': {'$lte' : stop_tick}},
			]
			
			if user_data.cat=='1': # 成功付款
				and_request.append({'pay_off':1})
				and_request.append({'return':0})
			elif user_data.cat=='2': # 成功退款
				and_request.append({'pay_off':1})
				and_request.append({'return':2})
			elif user_data.cat=='3': # 尚未付款（含出错）
				and_request.append({'pay_off': {'$ne':1}})

			db_todo=web_db.todo.find({'$and': and_request}, {
				'alipay_form':1, 'ticket_no':1, 'passengers':1, 'return':1, 'comment':1,
				'dptStation':1, 'arrStation':1, 'trainNo':1, 'start_date':1, 'pay_off':1, 'orderNo':1
			})
			report=[]
			total_pay = 0
			total_return = 0
			amt_pay = 0.0
			amt_return = 0.0

			if db_todo.count()>0:
				for item in db_todo:
					if item.has_key('pay_off') and item['pay_off']==1:
						report.append((
							item['_id'],
							item['ticket_no'],
							item['dptStation'],
							item['arrStation'],
							item['start_date'],
							item['trainNo'],
							item['alipay_form']['ord_amt'],
							'已退票' if item['return']==2 else '',
							item['orderNo'] if item.has_key('orderNo') else 'n/a'
						))
						if item['return']==2:
							amt_return += float(item['alipay_form']['ord_amt'])
							total_return += 1
						else:
							amt_pay += float(item['alipay_form']['ord_amt'])
							total_pay += 1
					else:
						msg=item['comment'].split('|')
						report.append((
							item['_id'],
							item['ticket_no'] if item.has_key('ticket_no') else 'n/a',
							item['dptStation'] if item.has_key('dptStation') else 'n/a',
							item['arrStation'] if item.has_key('arrStation') else 'n/a',
							item['start_date'] if item.has_key('start_date') else 'n/a',
							item['trainNo'] if item.has_key('trainNo') else 'n/a',
							'n/a',
							msg[2] if len(msg)==3 else item['comment'],
							item['orderNo'] if item.has_key('orderNo') else 'n/a'
						))
			return render.report_result(session.uname, user_level[session.privilege], report,
				(total_pay, amt_pay, total_return, amt_return), user_data.start_date)
		else:
			raise web.seeother('/')

########## API 功能 ####################################################
class APIInfo:
	def GET(self):
		if logged(PRIV_API):
			render = create_render(session.privilege)
			db_user=web_db.user.find_one({'_id':session.uid},{'API_ID':1, 'API_KEY':1})
			if db_user!=None and db_user.has_key('API_ID') and db_user.has_key('API_KEY'):
				return render.api_info(session.uname, user_level[session.privilege], db_user['API_ID'], db_user['API_KEY'])
			else:
				return render.info('未找到用户信息。')
		else:
			raise web.seeother('/')


#
# API 建立新的task，参数：
# {
#	'api_key'   : 'XXXX',
#	'login_info' : { 'user':'jack_139', 'passwd':'????' }  --- base64
#	'secret'    : hashlib.md5('%s%s%s' % (API_KEY, api_id, date)).hexdigest().upper()
#	'device_id' : ''
# }
# 
# 返回：
# {
#	'ret'  : 0,  # 0 正常，<0 出错
#	'task' : '' # todo_id
# }
#
# 出错代码：
# -1 系统不受理
# -2 json格式错误
# -3 secret不匹配
# -4 上次请求未结束
# 
class APITask:
	def POST(self):
		import json, hashlib, base64
		
		while 1:
			try:
				data=json.loads(web.data())
				print data
			except ValueError:
				# json格式有问题
				print web.data()
				ret = { 'ret': -2}
				break

			try:
				db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
				if db_user==None: 
					# 未找到uid
					ret = { 'ret': -1}
					break

				HMAC = hashlib.md5(
					'%s%s%s' % (db_user['API_KEY'], 
							data['api_key'], 
							data['login_info'])
				).hexdigest().upper()
			except KeyError:
				# 参数有问题
				ret = { 'ret': -2}
				break

			if data['secret']!=HMAC:
				# 加密串不对
				ret = { 'ret': -3}
				break

			# 准备参数
			login_info = json.loads(base64.b64decode(data['login_info']))

			tick=int(time.time())
			todo_id=web_db.todo.insert({
				'uid'            : data['device_id'] if data.has_key('device_id') else 'api', # 用于标识不用的手机个体
				'event'          : 'ORDER_API',
				'status'         : 'FINISH',
				'user_12306'     : login_info['user'],
				'pass_12306'     : login_info['passwd'],
				'lock'           : 0,
				'man'            : 0,
				'next_status'    : '',
				'comment'        : '',
				'history'        : [],
				'b_time'         : tick,
				'e_time'         : tick
			})
			
			# 记录 device_id
			if data.has_key('device_id'):
				web_db.device.update({'device_id':data['device_id']}, {'$set':{'time':tick}}, upsert=True)

			if todo_id!=None:
				ret = { 'ret': 0, 'task' : str(todo_id)}
			else:
				# '查询失败，请稍后重试。'
				ret = { 'ret': -1}

			break

		web.header("Content-Type", "application/json")
		return json.dumps(ret)

#
# API 查询车次，参数：
# {
#	'api_key'   : 'XXXX',
#	'task'      : '',
#	'departure' : 'VBB',
#	'arrival'   : 'HBB'
#	'date'      : '2015-01-09',
#	'secret'    : hashlib.md5('%s%s%s%s%s%s' % (API_KEY, api_id, task, departure, arrival, date)).hexdigest().upper()
# }
# 
# 返回：
# {
#	'ret'  : 0,  # 0 正常，<0 出错
# }
#
# 出错代码：
# -1 系统不受理
# -2 json格式错误
# -3 secret不匹配
# -4 上次请求未结束
# 
class APIQuery:
	def POST(self):
		import json, hashlib
		
		while 1:
			try:
				data=json.loads(web.data())
				print data
			except ValueError:
				# json格式有问题
				print web.data()
				ret = { 'ret': -2}
				break

			try:
				db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
				if db_user==None: 
					# 未找到uid
					ret = { 'ret': -1}
					break

				HMAC = hashlib.md5(
					'%s%s%s%s%s%s' % (db_user['API_KEY'], 
							data['api_key'], 
							data['task'],
							data['departure'], 
							data['arrival'], 
							data['date'])
				).hexdigest().upper()
			except KeyError:
				# 参数有问题
				ret = { 'ret': -2}
				break

			if data['secret']!=HMAC:
				# 加密串不对
				ret = { 'ret': -3}
				break

			db_todo=web_db.todo.find_one({'_id':ObjectId(data['task'])},{'event':1, 'status':1, 'result':1})
			if db_todo==None:
				# 未找到task
				ret = { 'ret': -5}
				break

			if db_todo['status']!='FINISH':
				# 未结束
				print db_todo['status']
				ret = { 'ret': -4}
				break

			tick=int(time.time())
			web_db.todo.update({'_id':ObjectId(data['task'])},
				{'$set':{
					'status'         : 'QUERY',
					'start_station'  : data['departure'],
					'stop_station'   : data['arrival'],
					'start_date'     : data['date'],
					'lock'           : 0,
					'man'            : 0,
					'retry'          : 0,
					'next_status'    : '',
					'comment'        : '',
					'e_time'         : tick
					}
			})

			ret = { 'ret': 0 }
			break

		web.header("Content-Type", "application/json")
		return json.dumps(ret)

#
# API 下单，参数：
# {
#	'api_key'  : 'XXXX',
#	'task'     : '54b2378685cb310c270f67d5',
#	'passengers' : [
#		{
#			'name'        : '关涛',
#			'certType'    : '1',
#			'certNo'      : '12010419760404761X',
#			'ticketType'  : '1',
#		}
#	]		 --- base64
# 	'seat_type'  : '1', 
#	's'          : 查询信息的火车票串
#	'secret'     : hashlib.md5('%s%s%s%s%s' % (API_KEY, api_id, task, s, passengers)).hexdigest().upper()
# }
# 
# 返回：
# {
#	'ret'  : 0,  # 0 正常，<0 出错
# }
#
# 出错代码：
# -1 系统不受理
# -2 json格式错误
# -3 secret不匹配
# -4 请求未结束
# -5 未找到task
# 
class APIOrder:
	def POST(self):
		import json, hashlib, base64, urllib
		
		while 1:
			try:
				data=json.loads(web.data())
				#print data
			except ValueError:
				# json格式有问题
				print web.data()
				ret = { 'ret': -2}
				break
			
			try:
				db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
				if db_user==None: 
					# 未找到uid
					ret = { 'ret': -1}
					break

				HMAC = hashlib.md5(
					'%s%s%s%s%s' % (db_user['API_KEY'], 
							data['api_key'], 
							data['task'], 
							data['s'], 
							data['passengers'])
				).hexdigest().upper()
			except KeyError:
				# 参数有问题
				print data
				ret = { 'ret': -2}
				break

			if data['secret']!=HMAC:
				# 加密串不对
				ret = { 'ret': -3}
				break
			
			db_todo=web_db.todo.find_one({'_id':ObjectId(data['task'])},{'event':1, 'status':1, 'result':1})
			if db_todo==None:
				# 未找到task
				ret = { 'ret': -5}
				break

			if db_todo['status']!='FINISH':
				# 未结束
				print db_todo['status']
				ret = { 'ret': -4}
				break

			# 准备参数
			passengers = json.loads(base64.b64decode(data['passengers']))

			s2 = data['s'].replace('%2B','+').replace('%2b','+').replace('%2F','/').replace('%2f','/').replace('%3D','=').replace('%3d','=')
			s3=base64.b64decode(s2).split('#')

			tick=int(time.time())
			web_db.todo.update({'_id':ObjectId(data['task'])},
				{'$set':{
					'status'         : 'ORDER',
					'passengers'     : passengers,
					'seat_type'      : data['seat_type'],
					'secretStr'      : data['s'], #urllib.quote_plus(data['s']),
					'train_info'     : '%s %s %s %s %s %s %s' % (s3[0], s3[4], s3[2], s3[9], s3[10], s3[6], s3[7]),
					'lock'           : 0,
					'man'            : 0,
					'retry'          : 0,
					'next_status'    : '',
					'comment'        : '',
					'e_time'         : tick
					}
			})

			ret = { 'ret' : 0, }
			break

		web.header("Content-Type", "application/json")
		return json.dumps(ret)


#
# API 查询常用联系人，参数：
# {
#	'api_key'   : 'XXXX',
#	'task'     : '54b2378685cb310c270f67d5',
#	'secret'    : hashlib.md5('%s%s%s' % (API_KEY, api_id, task)).hexdigest().upper()
# }
# 
# 返回：
# {
#	'ret'  : 0,  # 0 正常，<0 出错
# }
#
# 出错代码：
# -1 系统不受理
# -2 json格式错误
# -3 secret不匹配
# -4 上次请求未结束
# 
class APIPassengers:
	def POST(self):
		import json, hashlib, base64

		while 1:
			try:
				data=json.loads(web.data())
				print data
			except ValueError:
				# json格式有问题
				print web.data()
				ret = { 'ret': -2}
				break

			try:
				db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
				if db_user==None: 
					# 未找到uid
					ret = { 'ret': -1}
					break

				HMAC = hashlib.md5(
					'%s%s%s' % (db_user['API_KEY'], 
							data['api_key'], 
							data['task'])
				).hexdigest().upper()
			except KeyError:
				# 参数有问题
				ret = { 'ret': -2}
				break

			if data['secret']!=HMAC:
				# 加密串不对
				ret = { 'ret': -3}
				break

			db_todo=web_db.todo.find_one({'_id':ObjectId(data['task'])},{'event':1, 'status':1, 'result':1})
			if db_todo==None:
				# 未找到task
				ret = { 'ret': -5}
				break

			if db_todo['status']!='FINISH':
				# 未结束
				print db_todo['status']
				ret = { 'ret': -4}
				break


			tick=int(time.time())
			web_db.todo.update({'_id':ObjectId(data['task'])},
				{'$set':{
					'status'         : 'PASSENGER',
					'lock'           : 0,
					'man'            : 0,
					'retry'          : 0,
					'next_status'    : '',
					'comment'        : '',
					'e_time'         : tick
					}
			})

			ret = { 'ret': 0 }
			break

		web.header("Content-Type", "application/json")
		return json.dumps(ret)

#
# API 取消未完成订单，参数：
# {
#	'api_key'   : 'XXXX',
#	'task'     : '54b2378685cb310c270f67d5',
#	'secret'    : hashlib.md5('%s%s%s%s%s' % (API_KEY, api_id, task)).hexdigest().upper()
# }
# 
# 返回：
# {
#	'ret'  : 0,  # 0 正常，<0 出错
# }
#
# 出错代码：
# -1 系统不受理
# -2 json格式错误
# -3 secret不匹配
# -4 上次请求未结束
# 
class APICancelNoComplete:
	def POST(self):
		import json, hashlib, base64

		while 1:
			try:
				data=json.loads(web.data())
				print data
			except ValueError:
				# json格式有问题
				print web.data()
				ret = { 'ret': -2}
				break

			try:
				db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
				if db_user==None: 
					# 未找到uid
					ret = { 'ret': -1}
					break

				HMAC = hashlib.md5(
					'%s%s%s' % (db_user['API_KEY'], 
							data['api_key'], 
							data['task'])
				).hexdigest().upper()
			except KeyError:
				# 参数有问题
				ret = { 'ret': -2}
				break

			if data['secret']!=HMAC:
				# 加密串不对
				ret = { 'ret': -3}
				break

			db_todo=web_db.todo.find_one({'_id':ObjectId(data['task'])},{'event':1, 'status':1, 'result':1})
			if db_todo==None:
				# 未找到task
				ret = { 'ret': -5}
				break

			if db_todo['status']!='FINISH':
				# 未结束
				print db_todo['status']
				ret = { 'ret': -4}
				break

			tick=int(time.time())
			web_db.todo.update({'_id':ObjectId(data['task'])},
				{'$set':{
					'status'         : 'API_CANCEL',
					'lock'           : 0,
					'man'            : 0,
					'retry'          : 0,
					'next_status'    : '',
					'comment'        : '',
					'e_time'         : tick
					}
			})

			ret = { 'ret' : 0 }
			break

		web.header("Content-Type", "application/json")
		return json.dumps(ret)


#
# API 查询未完成订单，参数：
# {
#	'api_key'   : 'XXXX',
#	'task'     : '54b2378685cb310c270f67d5',
#	'secret'    : hashlib.md5('%s%s%s%s%s' % (API_KEY, api_id, task)).hexdigest().upper()
# }
# 
# 返回：
# {
#	'ret'  : 0,  # 0 正常，<0 出错
# }
#
# 出错代码：
# -1 系统不受理
# -2 json格式错误
# -3 secret不匹配
# -4 上次请求未结束
# 
class APINoComplete:
	def POST(self):
		import json, hashlib, base64

		while 1:
			try:
				data=json.loads(web.data())
				print data
			except ValueError:
				# json格式有问题
				print web.data()
				ret = { 'ret': -2}
				break

			try:
				db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
				if db_user==None: 
					# 未找到uid
					ret = { 'ret': -1}
					break

				HMAC = hashlib.md5(
					'%s%s%s' % (db_user['API_KEY'], 
							data['api_key'], 
							data['task'])
				).hexdigest().upper()
			except KeyError:
				# 参数有问题
				ret = { 'ret': -2}
				break

			if data['secret']!=HMAC:
				# 加密串不对
				ret = { 'ret': -3}
				break

			db_todo=web_db.todo.find_one({'_id':ObjectId(data['task'])},{'event':1, 'status':1, 'result':1})
			if db_todo==None:
				# 未找到task
				ret = { 'ret': -5}
				break

			if db_todo['status']!='FINISH':
				# 未结束
				print db_todo['status']
				ret = { 'ret': -4}
				break

			tick=int(time.time())
			web_db.todo.update({'_id':ObjectId(data['task'])},
				{'$set':{
					'status'         : 'NO_COMPLETE',
					'lock'           : 0,
					'man'            : 0,
					'retry'          : 0,
					'next_status'    : '',
					'comment'        : '',
					'e_time'         : tick
					}
			})

			ret = { 'ret' : 0 }
			break

		web.header("Content-Type", "application/json")
		return json.dumps(ret)


#
# API 查询已完成订单，参数：
# {
#	'api_key'   : 'XXXX',
#	'task'     : '54b2378685cb310c270f67d5',
#	'secret'    : hashlib.md5('%s%s%s%s%s' % (API_KEY, api_id, task)).hexdigest().upper()
# }
# 
# 返回：
# {
#	'ret'  : 0,  # 0 正常，<0 出错
# }
#
# 出错代码：
# -1 系统不受理
# -2 json格式错误
# -3 secret不匹配
# -4 上次请求未结束
# 
class APIComplete:
	def POST(self):
		import json, hashlib

		while 1:
			try:
				data=json.loads(web.data())
				print data
			except ValueError:
				# json格式有问题
				print web.data()
				ret = { 'ret': -2}
				break

			try:
				db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
				if db_user==None: 
					# 未找到uid
					ret = { 'ret': -1}
					break

				HMAC = hashlib.md5(
					'%s%s%s' % (db_user['API_KEY'], 
							data['api_key'], 
							data['task'])
				).hexdigest().upper()
			except KeyError:
				# 参数有问题
				ret = { 'ret': -2}
				break

			if data['secret']!=HMAC:
				# 加密串不对
				ret = { 'ret': -3}
				break

			db_todo=web_db.todo.find_one({'_id':ObjectId(data['task'])},{'event':1, 'status':1, 'result':1})
			if db_todo==None:
				# 未找到task
				ret = { 'ret': -5}
				break

			if db_todo['status']!='FINISH':
				# 未结束
				print db_todo['status']
				ret = { 'ret': -4}
				break

			tick=int(time.time())
			web_db.todo.update({'_id':ObjectId(data['task'])},
				{'$set':{
					'status'         : 'COMPLETE',
					'lock'           : 0,
					'man'            : 0,
					'retry'          : 0,
					'next_status'    : '',
					'comment'        : '',
					'e_time'         : tick
					}
			})

			ret = { 'ret': 0 }
			break

		web.header("Content-Type", "application/json")
		return json.dumps(ret)


#
# API 查询处理结果，参数：
# {
#	'api_key' : 'XXXX',
#	'task'    : '54b2378685cb310c270f67d5',
#       'data'    : 'result', # 需返回的字段
#	'secret'  : hashlib.md5('%s%s%s%s' % (API_KEY, api_id, task, data)).hexdigest().upper()
# }
# 
# 返回：
# {
#	'ret'     : 0,        # 0 正常，<0 出错
#	'status'  : 'FINISH', # 当前状态
#	'result'  : '',       # 请求查询的字段
#	'comment' : ''        # 错误提示，正常为空
# }
#
# 出错代码：
# -1 系统不受理
# -2 json格式错误
# -3 secret不匹配
# -5 未找到task
# 
class APIResult:
	def POST(self):
		import json, hashlib
		
		while 1:
			try:
				data=json.loads(web.data())
				print data
			except ValueError:
				# json格式有问题
				print web.data()
				ret = { 'ret': -2}
				break
			
			try:
				db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
				if db_user==None: 
					# 未找到uid
					ret = { 'ret': -1}
					break

				HMAC = hashlib.md5(
					'%s%s%s%s' % (db_user['API_KEY'], 
							data['api_key'], 
							data['task'], 
							data['data'])
				).hexdigest().upper()
			except KeyError:
				# 参数有问题
				ret = { 'ret': -2}
				break

			if data['secret']!=HMAC:
				# 加密串不对
				ret = { 'ret': -3}
				break

			db_todo=web_db.todo.find_one({'_id':ObjectId(data['task'])},
				{'event':1, 'status':1, data['data']:1, 'comment':1})
			if db_todo==None:
				# 未找到task
				ret = { 'ret': -5}
				break

			ret = { 
				'ret'     : 0, 
				'status'  : db_todo['status'],
				'result'  : db_todo[data['data']] if db_todo.has_key(data['data']) else '',
				'comment' : db_todo['comment']
			}
			break

		web.header("Content-Type", "application/json")
		return json.dumps(ret)

#
# API 支付宝支付网关，GET参数：
# {
#	'api_key' : 'XXXX',
#	'task'    : '54b2378685cb310c270f67d5',
#	'secret'  : hashlib.md5('%s%s%s' % (API_KEY, api_id, data)).hexdigest().upper()
# }
# 

class APIPay2:
	def GET(self):
		import hashlib
		
		render = web.template.render('templates/api', base='m_layout') # m_layout没有菜单
		data=web.input(api_key='', task='', secret='')

		try:
			db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
			if db_user==None: 
				# 未找到uid
				return render.m_info('api参数错误！')

			HMAC = hashlib.md5(
				'%s%s%s' % (db_user['API_KEY'], 
						data['api_key'], 
						data['task'])
			).hexdigest().upper()
		except KeyError:
			# 参数有问题
			return render.m_info('输入参数错误！')

		if data['secret']!=HMAC:
			# 加密串不对
			return render.m_info('参数核对错误！')

		todo_update={'status'     : 'PAY2', 
			     'comment'    : '',
			     'man'        : 0,
			     'lock'       : 0,
			     'e_time'     : int(time.time())
			    }
		r = web_db.todo.update({'_id':ObjectId(data['task'])}, {'$set': todo_update})
		#print r
		return render.m_router(data['task'], data['api_key'], data['secret'])

class APICheckout:
	def GET(self):
		import json, hashlib

		result={}

		user_data=web.input(api_key='', todo='', secret='')

		while 1:
			data = user_data
			try:
				db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
				if db_user==None: 
					# 未找到uid
					return render.m_info('api参数错误！')

				HMAC = hashlib.md5(
					'%s%s%s' % (db_user['API_KEY'], 
							data['api_key'], 
							data['todo'])
					).hexdigest().upper()
			except KeyError:
				# 参数有问题
				print '输入参数错误！'
				break
	
			if data['secret']!=HMAC:
				# 加密串不对
				print '参数核对错误！'
				break

			# 只查 API 的订单
			db_todo=web_db.todo.find_one({'$and' : [{'_id': ObjectId(user_data.todo)}, {'event':'ORDER_API'}]})
			if db_todo!=None:
				result['id']=str(db_todo['_id'])
				result['event']=db_todo['event']
				result['status']=db_todo['status']
				result['elapse']=db_todo['e_time']-db_todo['b_time']
				result['lock']=db_todo['lock']
				result['man']=db_todo['man']
				result['comment']=db_todo['comment']
				if db_todo.has_key('result'):
					result['result']=db_todo['result']
				else:
					result['result']=[]
				# 如果事件已处理完，checkout将删除此事件
				#if db_todo['status'] in ('SUCCESS', 'FAIL'):
				#	web_db.todo.remove({'_id': db_todo['_id']}) 
			break

		web.header("Content-Type", "application/json")
		return json.dumps(result)

class APIAliForm:
	def GET(self):
		import hashlib

		render = web.template.render('templates/api', base='m_layout') # m_layout没有菜单
		user_data=web.input(api_key='', todo='', secret='')

		data = user_data
		try:
			db_user=web_db.user.find_one({'API_ID':data['api_key']},{'API_KEY':1})
			if db_user==None: 
				# 未找到uid
				return render.m_info('api参数错误！')

			HMAC = hashlib.md5(
				'%s%s%s' % (db_user['API_KEY'], 
						data['api_key'], 
						data['todo'])
			).hexdigest().upper()
		except KeyError:
			# 参数有问题
			return render.m_info('输入参数错误！')

		if data['secret']!=HMAC:
			# 加密串不对
			return render.m_info('参数核对错误！')

		db_todo=web_db.todo.find_one({'_id': ObjectId(user_data.todo)},{'alipay_form':1})
		if db_todo!=None:
			# 状态转到 FINISH，处理完成
			todo_update={'status'     : 'FINISH',
				     'comment'    : '',
				     'man'        : 0,
				     'lock'       : 0,
				     'e_time'     : int(time.time())
				    }
			web_db.todo.update({'_id': ObjectId(user_data.todo)}, {'$set': todo_update})
			# 取得车次信息
			return render.m_ali_form(user_data.todo, db_todo['alipay_form'])
		else:
			return render.m_info('出错，请重新提交。')


########## Admin 功能 ####################################################

class AdminIdPool:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)

			ids=[]
			db_ids=web_db.id_pool.find({'id_type':'1'},{'_id':1})
			return render.info('共有 %d 个身份证信息记录。' % db_ids.count(), goto='/')
		else:
			raise web.seeother('/')

class AdminKam:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(cat='0')

			if user_data.cat=='0': # 所有记录
				condi={}
			elif user_data.cat=='1': # 空闲的
				condi={'status':'OK'}
			elif user_data.cat=='2': # 有问题的
				condi={'status':'FAIL'}
			elif user_data.cat=='3': # 在使用的
				condi={'$and' : [{'status': {'$ne':'OK'}},{'status': {'$ne':'FAIL'}},{'status': {'$ne':'READY'}}]}
			elif user_data.cat=='4': # 停用的
				condi={'status':'READY'}
			elif user_data.cat=='5': # 在线的
				condi={'online':1}
			elif user_data.cat=='6': # 离线的
				condi={'online':0}
			elif user_data.cat=='99': # 更新购票数据
				condi={}
				db_user=web_db.user_12306.find({},{'uname':1})
				for u in db_user:
					order_num = web_db.todo.find({'user_12306':u['uname']},{'_id':1}).count()
					web_db.user_12306.update({'_id':u['_id']},{'$set':{'order_num':order_num}})
			else:
				condi={'group':user_data.cat.strip()}

			kams=[]
			db_kam=web_db.user_12306.find(condi, {'uname':1, 'status':1, 'online':1, 'group':1, 'order_num':1}).sort([('order_num',-1)])
			if db_kam.count()>0:
				for u in db_kam:
					if type(u['status'])==type(ObjectId('551d346c6ba7857f2256661c')):
						db_t=web_db.todo.find_one({'_id':u['status']}, {'status':1})
						if db_t!=None:
							todo_status=db_t['status']
							if db_t['status']=='FINISH': # 清理 FINISH标志的占用
								web_db.user_12306.update({'_id':u['_id']},{'$set':{'status':'OK'}}) 
						else:
							todo_status=''
					else:
						todo_status=''
					kams.append((u['uname'],str(u['_id']),u['status'],todo_status,u['online'],u['group'],
						u['order_num'] if u.has_key('order_num') else 0))
			return render.kam(session.uname, user_level[session.privilege], kams, user_data.cat)
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(group='', action='QUERY', new_pass='1234')
  
			group = user_data.group.strip()

			if group=='': # 所有记录
				return render.info('请输入分组名！', goto="/admin/kam")

			if user_data.action=='QUERY':
				raise web.seeother('/admin/kam?cat=%s' % group)
			elif user_data.action=='ONLINE':
				web_db.user_12306.update({'group':group}, {'$set':{'online':1}}, multi=True)
				return render.info('此分组已上线', goto="/admin/kam")
			elif user_data.action=='OFFLINE':
				web_db.user_12306.update({'group':group}, {'$set':{'online':0}}, multi=True)
				return render.info('此分组已下线', goto="/admin/kam")
			elif user_data.action=='CHANGE': # 修改12306密码
				# 先做下线处理再改密码
				web_db.user_12306.update({'group':group}, {'$set':{'online':0}}, multi=True)
				db_user=web_db.user_12306.find({'group':group},{'uname':1, 'passwd':1})
				for u in db_user:
					tick=int(time.time())
					todo_id=web_db.todo.insert({
						'uid'            : session.uid,
						'event'          : 'ORDER_SINGLE',
						'status'         : 'CHANGE_PWD',
						'lock'           : 0,
						'man'            : 0,
						'next_status'    : '',
						'comment'        : '',
						'history'        : [],
						'b_time'         : tick,
						'e_time'         : tick,
						'user_12306'     : u['uname'],
						'pass_12306'     : u['passwd'],
						'new_pass'       : user_data['new_pass'],
						# 下面是假数据，只为CheckoutSjrand不出错
						'trainStartTime' : time_str()[:-3], 
						'orderNo'        : 'change_pwd',
						'orderType'      : 0,
						'return'         : 0,
						'ticketPay'      : 0,
					})

				return render.info('已提交。', goto="/admin/kam")
			else:
				return render.info('未知操作！', goto="/admin/kam")
		else:
			raise web.seeother('/')


class AdminKamSetting:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(kid='')

			if user_data.kid=='':
				return render.info('错误的参数！')  

			db_kam=web_db.user_12306.find_one({'_id':ObjectId(user_data.kid)})
			if db_kam!=None:
				return render.kam_setting(session.uname, user_level[session.privilege], 
					(db_kam['_id'],db_kam['uname'],db_kam['passwd'],db_kam['status'],
					 db_kam['auto_pay'],db_kam['online'],db_kam['group']))
			else:
				return render.info('错误的参数！')  
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(kid='', status='-', auto_pay='0', online='1')

			todo_update = {
				'passwd'   : user_data['passwd'], 
				'auto_pay' : int(user_data['auto_pay']), 
				'online'   : int(user_data['online']),
				'group'    : user_data['group'].strip()
			}
			if user_data['status']!='-':
				todo_update['status'] = user_data['status']
			web_db.user_12306.update({'_id':ObjectId(user_data['kid'])}, {'$set': todo_update})

			return render.info('成功保存！','/admin/kam')
		else:
			raise web.seeother('/')

class AdminKamDel:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(kid='')

			if user_data.kid=='':
				return render.info('错误的参数！')  

			db_kam=web_db.user_12306.find_one({'_id':ObjectId(user_data.kid)},{'status':1})
			if db_kam!=None:
				if db_kam['status']=='FAIL':
					web_db.user_12306.remove({'_id':ObjectId(user_data.kid)})
					return render.info('已删除！','/admin/kam')  
				else:
					return render.info('不能删除正在使用的12306用户！') 
			else:
				return render.info('错误的参数！')  
		else:
			raise web.seeother('/')

class AdminKamAdd:
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			return render.kam_new(session.uname, user_level[session.privilege])
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(uname='', passwd='', status='OK', auto_pay='1', online='1', group='')

			if user_data.uname=='':
				return render.info('登录名不能为空！')  

			db_kam=web_db.user_12306.find_one({'uname': user_data['uname'].strip()})
			if db_kam==None:
				web_db.user_12306.insert({
					'uname'    : user_data['uname'].strip(),
					'passwd'   : user_data['passwd'],
					'status'   : user_data['status'],
					'auto_pay' : int(user_data['auto_pay']),
					'online'   : int(user_data['online']),
					'group'    : user_data['group'].strip(),
				})
				return render.info('成功保存！', '/admin/kam')
			else:
				return render.info('用户名已存在！请重新添加。')
		else:
			raise web.seeother('/')

class AdminUser:
    def GET(self):
        if logged(PRIV_ADMIN):
            render = create_render(session.privilege)

            users=[]            
            db_user=web_db.user.find({'$or':[{'privilege':PRIV_USER},
                                             {'privilege':PRIV_API}]},{'uname':1,'privilege':1}).sort([('_id',1)])
            if db_user.count()>0:
              for u in db_user:
                users.append([u['uname'],u['_id'],user_level[u['privilege']]])
            return render.user(session.uname, user_level[session.privilege], users)
        else:
            raise web.seeother('/')

class AdminUserSetting:        
    def GET(self):
      if logged(PRIV_ADMIN):
        render = create_render(session.privilege)
        user_data=web.input(uid='')

        if user_data.uid=='':
          Logger.aLog(Logger.A_ERR_PARAM, session.uid)
          return render.info('错误的参数！')  
        
        db_user=web_db.user.find_one({'_id':ObjectId(user_data.uid)})
        if db_user!=None:
          return render.user_setting(session.uname, user_level[session.privilege], 
              db_user, time_str(db_user['time']), user_level[db_user['privilege']])
        else:
          Logger.aLog(Logger.A_ERR_PARAM, session.uid)
          return render.info('错误的参数！')  
      else:
        raise web.seeother('/')

    def POST(self):
      if logged(PRIV_ADMIN):
        render = create_render(session.privilege)
        user_data=web.input(uid='')
        
        web_db.user.update({'_id':ObjectId(user_data['uid'])}, 
            {'$set':{'login' : int(user_data['login'])}})
        
        Logger.aLog(Logger.A_USER_UPDATE, user_data['uid'])
        return render.info('成功保存！','/admin/user')
      else:
        raise web.seeother('/')

class AdminUserAdd:        
	def GET(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			return render.user_new(session.uname, user_level[session.privilege])
		else:
			raise web.seeother('/')

	def POST(self):
		if logged(PRIV_ADMIN):
			render = create_render(session.privilege)
			user_data=web.input(uname='', login='0', passwd='', priv='user')

			if user_data.uname=='':
				return render.info('用户名不能为空！')  

			db_user=web_db.user.find_one({'uname': user_data['uname']})
			if db_user==None:
				if user_data['priv']=='api':
					api_info=new_api_code()
					web_db.user.insert({
						'login'     : int(user_data['login']),
						'uname'     : user_data['uname'],
						'full_name' : '',
						'privilege' : PRIV_USER if user_data['priv']=='user' else PRIV_API,
						'passwd'    : my_crypt(user_data['passwd']),
						'time'      : time.time(),  # 注册时间
						'API_ID'    : api_info['API_ID'],
						'API_KEY'   : api_info['API_KEY']
					})
				else:
					web_db.user.insert({
						'login'     : int(user_data['login']),
						'uname'     : user_data['uname'],
						'full_name' : '',
						'privilege' : PRIV_USER if user_data['priv']=='user' else PRIV_API,
						'passwd'    : my_crypt(user_data['passwd']),
						'time'      : time.time()  # 注册时间
					})
				Logger.aLog(Logger.A_USER_ADD, user_data['uname'])
				return render.info('成功保存！','/admin/user')
			else:
				return render.info('用户名已存在！请修改后重新添加。')
		else:
			raise web.seeother('/')

class AdminSysSetting:        
    def GET(self):
      if logged(PRIV_ADMIN):
        render = create_render(session.privilege)
        
        db_sys=web_db.user.find_one({'uname':'settings'})
        if db_sys!=None:
          return render.sys_setting(session.uname, user_level[session.privilege], db_sys)
        else:
          web_db.user.insert({'uname':'settings','signup':0,'login':0,'sjrand_max':0,
          	'return_check':0,'auto_sjrand':0,'auto_sjrand_p':0,'pay_threshold':0})
          Logger.aLog(Logger.A_SYS_FAIL, session.uid)
          return render.info('如果是新系统，请重新进入此界面。','/')  
      else:
        raise web.seeother('/')

    def POST(self):
      if logged(PRIV_ADMIN):
        render = create_render(session.privilege)
        user_data=web.input(signup='0', sjrand_max='10', pay_threshold='0')
        
        if not user_data['sjrand_max'].isdigit():
        	return render.info('队列长度必须是数字！','/')
  
        web_db.user.update({'uname':'settings'},
        	{'$set':{'signup': int(user_data['signup']), 
        		'sjrand_max': int(user_data['sjrand_max']),
        		'return_check': int(user_data['return_check']),
        		'auto_sjrand': int(user_data['auto_sjrand']),
        		'auto_sjrand_p': int(user_data['auto_sjrand_p']),
        		'pay_threshold': int(user_data['pay_threshold']),
        	}})
        
        Logger.aLog(Logger.A_SYS_UPDATE, session.uid)
        return render.info('成功保存！','/admin/sys_setting')
      else:
        raise web.seeother('/')

class AdminSelfSetting:
    def _get_settings(self):
      db_user=web_db.user.find_one({'_id':session.uid})
      return db_user
        
    def GET(self):
      #print web.ctx
      if logged(PRIV_ADMIN):
        render = create_render(session.privilege)
        return render.self_setting(session.uname, user_level[session.privilege], self._get_settings())
      else:
        raise web.seeother('/')

    def POST(self):
      if logged(PRIV_ADMIN):
        render = create_render(session.privilege)
        old_pwd = web.input().old_pwd.strip()
        new_pwd = web.input().new_pwd.strip()
        new_pwd2 = web.input().new_pwd2.strip()
        
        if old_pwd!='':
          if new_pwd=='':
            return render.info('新密码不能为空！请重新设置。')
          if new_pwd!=new_pwd2:
            return render.info('两次输入的新密码不一致！请重新设置。')
          db_user=web_db.user.find_one({'_id':session.uid},{'passwd':1})
          if my_crypt(old_pwd)==db_user['passwd']:
            web_db.user.update({'_id':session.uid}, {'$set':{'passwd':my_crypt(new_pwd)}})
            Logger.aLog(Logger.A_SELF_UPDATE, session.uid)
            return render.info('成功保存！','/')
          else:
            Logger.aLog(Logger.A_SELF_FAIL, session.uid)
            return render.info('登录密码验证失败！请重新设置。')
        else:
          return render.info('未做任何修改。')
      else:
        raise web.seeother('/')

class AdminStatus: 
    def GET(self):
      import os
      
      if logged(PRIV_ADMIN):
        render = create_render(session.privilege)
                
        uptime=os.popen('uptime').readlines()
        takit=os.popen('pgrep -f "uwsgi_takit.sock"').readlines()
        #collector=os.popen('pgrep -f "collector.py"').readlines()
        error_log=os.popen('tail %s/error.log' % setting.logs_path).readlines()
        uwsgi_log=os.popen('tail %s/uwsgi_takit.log' % setting.logs_path).readlines()
        dispatcher_log=os.popen('tail %s/dispatcher.log' % setting.logs_path).readlines()
        processor_log=os.popen('tail %s/processor.log' % setting.logs_path).readlines()
        df_data=os.popen('df -h').readlines()

        return render.status(session.uname, user_level[session.privilege],
            {
              'uptime'       :  uptime,
              'takit'        :  takit,
              'error_log'    :  error_log,
              'uwsgi_log'    :  uwsgi_log,
              'dispatch_log' :  dispatcher_log,
              'process_log'  :  processor_log,
              'df_data'      :  df_data,
            })
      else:
        raise web.seeother('/')

class AdminData: 
    def GET(self):
      if logged(PRIV_ADMIN):
        render = create_render(session.privilege)
        
        db_active=web_db.user.find({'$and': [{'login'     : 1},
                                         {'privilege' : PRIV_USER},
                                        ]},
                                   {'_id':1}).count()
        db_nonactive=web_db.user.find({'$and': [{'login'     : 0},
                                         {'privilege' : PRIV_USER},
                                        ]},
                                   {'_id':1}).count()
        db_admin=web_db.user.find({'privilege' : PRIV_ADMIN}, {'_id':1}).count()

        db_sessions=web_db.sessions.find({}, {'_id':1}).count()
       	db_device=web_db.device.find({}, {'_id':1}).count()
       	db_todo=web_db.todo.find({}, {'_id':1}).count()
       	db_sleep=web_db.todo.find({'status':'SLEEP'}, {'_id':1}).count()
       	db_lock=web_db.todo.find({'lock':1}, {'_id':1}).count()
       	db_thread=web_db.thread.find({}).sort([('tname',1)])
       	idle_time = []
       	for t in db_thread:
       		idle_time.append(t)
       	
       	'''        
        db_ulog01=web_db.ulog.find({'msg':Logger.VISIT}, {'_id':1}).count()
        db_ulog02=web_db.ulog.find({'msg':Logger.LOGIN_FAIL}, {'_id':1}).count()
        db_ulog04=web_db.ulog.find({'msg':Logger.ERR_PARAM}, {'_id':1}).count()
        db_ulog05=web_db.ulog.find({'msg':Logger.NO_PRIV}, {'_id':1}).count()
        db_ulog11=web_db.ulog.find({'msg':Logger.USER_UPDATE}, {'_id':1}).count()

        db_alog01=web_db.alog.find({'msg':Logger.A_ERR_PARAM}, {'_id':1}).count()
        db_alog02=web_db.alog.find({'msg':Logger.A_USER_UPDATE}, {'_id':1}).count()
        db_alog03=web_db.alog.find({'msg':Logger.A_USER_ADD}, {'_id':1}).count()
        db_alog04=web_db.alog.find({'msg':Logger.A_SELF_UPDATE}, {'_id':1}).count()
        db_alog05=web_db.alog.find({'msg':Logger.A_SELF_FAIL}, {'_id':1}).count()
        db_alog06=web_db.alog.find({'msg':Logger.A_IO_ERROR}, {'_id':1}).count()
        '''

        return render.data(session.uname, user_level[session.privilege],
            {
              'active'       :  db_active,
              'nonactive'    :  db_nonactive,
              'admin'        :  db_admin,
              'sessions'     :  db_sessions,
              'device'       :  db_device,
              'todo'         :  db_todo,
              'sleep'        :  db_sleep,
              'lock'         :  db_lock,
              'idle_time'    :  idle_time,
              #'ulog01'       :  db_ulog01,
              #'ulog02'       :  db_ulog02,
              #'ulog04'       :  db_ulog04,
              #'ulog05'       :  db_ulog05,
              #'ulog11'       :  db_ulog11,
              #'alog01'       :  db_alog01,
              #'alog02'       :  db_alog02,
              #'alog03'       :  db_alog03,
              #'alog04'       :  db_alog04,
              #'alog05'       :  db_alog05,
              #'alog06'       :  db_alog06,
            })
      else:
        raise web.seeother('/')



########## Qunar 回调接口 ####################################################

class QunarReservation:  # 先占座后支付回调
	def POST(self):
		import json
		
		user_data = web.input(orderNo='',reqFrom='',reqTime='',trainNo='',to='',date='',retUrl='',passengers='',HMAC='')
		print web.input()
		
		ret = { "ret": True}
		
		while 1:
			if '' in (user_data['orderNo'],user_data['reqFrom'],user_data['reqTime'], \
				user_data['trainNo'],user_data['from'],user_data['to'],user_data['date'], \
				user_data['retUrl'],user_data['passengers'],user_data['HMAC']):
				ret = { 'ret': False, 'errMsg':'订单参数不正确', 'errCode':'112'}
				break
			if not user_data.has_key('from'):
				ret = { 'ret': False, 'errMsg':'订单参数不正确', 'errCode':'112'}
				break
			
			db_chk = web_db.qunar.find_one({'orderNo': user_data['orderNo']},{'_id':1})
			if db_chk!=None:
				ret = { 'ret': False, 'errMsg':'订单号已存在', 'errCode':'111'}
				break
			
			qunar_id=web_db.qunar.insert({'orderNo': user_data['orderNo'], 'data': user_data, 'return':0})
			if qunar_id==None:
				ret = { 'ret': False, 'errMsg':'处理失败', 'errCode':'111'}
				break
			
			import httphelper3, stations
			ret, passengers = httphelper3.QUNAR_process_result(user_data['passengers'])
			if ret!=httphelper3.E_OK:
				ret = { 'ret': False, 'errMsg':'乘客信息格式不正确', 'errCode':'112'}
				break
			
			new_todo={
				'status'         : 'QUERY',
				'lock'           : 0,
				'man'            : 0,
				'retry'          : 0,
				'comment'        : '',
				'history'        : [],
				'return'         : 0, # 用于标记退票：0: 无退票，1: 退票中, 2: 已退票, -1: 退票出错
				'tripNum'        : 1, # 默认为单程订单
				'next_status'    : '',
				'reservation'    : 1, # 占座不付款

				# 以下来自 qunar
				'orderNo'        : user_data['orderNo'],
				'orderType'      : 0, # 单程订单
				'orderDate'      : user_data['reqTime'],
				'passengers'     : passengers,
				'ticketPay'      : 0, # 占座票，用户未付款
				'reserve_url'     : user_data['retUrl']
			}
			# 处理乘客信息
			for people in new_todo['passengers']:
				# 转换ticket type为12306类型
				#people['ticketType'] = stations.TICKET_TYPE_QUNAR[people['ticketType']]
				# 儿童使用大人的名字购票
				if people['ticketType']==stations.TICKET_TYPE['儿童']:
					for ppp in passengers: 
						if ppp['certNo']==people['certNo'] and ppp['ticketType']!=stations.TICKET_TYPE['儿童']:
							people['origin_name']=people['name']
							people['name']=ppp['name']

			new_todo['event']          = 'ORDER_SINGLE'
			new_todo['arrStation']     = user_data['to']
			new_todo['dptStation']     = user_data['from']
			new_todo['extSeat']        = []
			new_todo['seat']           = {passengers[0]['seatCode']:-1}
			new_todo['trainStartTime'] = ''
			new_todo['trainEndTime']   = ''
			new_todo['trainNo']        = user_data['trainNo']
			new_todo['b_time'] = new_todo['e_time'] = int(time.time())

			# 数据调整，匹配processor
			begin_code=stations.find_code(user_data['from'].encode('utf-8'))
			end_code=stations.find_code(user_data['to'].encode('utf-8'))
			new_todo['start_station'] = begin_code
			new_todo['stop_station'] = end_code
			#start_time = order['trainStartTime'].split()
			new_todo['start_date'] = user_data['date'].replace('_','-') #start_time[0]
			new_todo['start_time'] = '' #start_time[1]

			# 转换seat type为12306类型
			new_todo['seat_type'] =  passengers[0]['seatCode'] #stations.SEAT_TYPE_QUNAR[order['seat'].keys()[0]] 
			new_todo['ext_seat_type'] = [] #[stations.SEAT_TYPE_QUNAR[s.keys()[0]] for s in order['extSeat']]
			#new_todo['ext_seat_type'].sort(reverse=True)

			todo_id=web_db.todo.insert(new_todo)
			if todo_id==None:
				#print 'order: fail to insert todo.'
				#print new_todo
				ret = { 'ret': False, 'errMsg':'处理失败', 'errCode':'111'}
				break
			#else:
			#	print '%s: %s %s %s' % (helper.time_str(), todo_id, new_todo['event'], new_todo['orderNo'])

			break
		
		web.header("Content-Type", "application/json")
		return json.dumps(ret, ensure_ascii=False) # utf-8

class QunarCancel:  # 取消占座回调
	def POST(self):
		import json
		
		user_data = web.input(orderNo='',reqFrom='',reqTime='',HMAC='')
		print web.input()
		
		ret = { "ret": True}

		while 1:
			db_todo = web_db.todo.find_one({'orderNo':user_data['orderNo']},{'status':1})
			if db_todo==None:
				ret = { "ret": False, 'errMsg':'未知的订单号', 'errCode':'112'}
				break
			if db_todo['status']!='RESERVE_WAIT':
				ret = { "ret": False, 'errMsg':'占座状态出错', 'errCode':'112'}
				print 'Error: %s not in RESERVE_WAIT status.' % user_data['orderNo']
				break

			r = web_db.todo.update({'_id':ObjectId(db_todo['_id'])}, {'$set': {'status':'CANCEL', 'man':0}})
			break

		web.header("Content-Type", "application/json")
		return json.dumps(ret, ensure_ascii=False) # utf-8

class QunarPayResult:  # 代付结果回调
	def POST(self):
		import json
		
		user_data = web.input(orderNo='',payStatus='',HMAC='')
		print '%s: payStatus=%s orderNo=%s ' % (time_str(),user_data['payStatus'],user_data['orderNo'])

		ret = { "ret": True}

		while 1: # 记录代付结果到db，20150404
			db_todo = web_db.todo.find_one({'orderNo':user_data['orderNo']},{'status':1})
			if db_todo==None:
				ret = { "ret": False, 'msg':'未知的订单号'} # 如果返回False，qunar会一直发结果3次
				break
			if db_todo['status']!='AUTO_PAY':
				#ret = { "ret": False, 'msg':'支付状态出错'}
				print '(payStatus) Error: %s not in AUTO_PAY status. now in %s' % (user_data['orderNo'],db_todo['status'])
				web_db.todo.update({'_id':ObjectId(db_todo['_id'])}, {'$set': {'payStatus':user_data['payStatus']}})
				break

			todo_update={ 'status':'PAY', 'man':1, 'pay_off':0, 'payStatus':user_data['payStatus'], 'e_time': int(time.time()) }
			if user_data['payStatus']=='1': #代付成功
				todo_update['pay_off'] = 1
				todo_update['pay_by_auto_pay']=1
				todo_update['status']='CHECK2'
				todo_update['man']=0

			r = web_db.todo.update({'_id':ObjectId(db_todo['_id'])}, {'$set': todo_update})
			#print r

			break

		web.header("Content-Type", "application/json")
		return json.dumps(ret, ensure_ascii=False) # utf-8


########## 内部模拟qunar测试 ####################################################
class TestQueryOrders:
	def GET(self):
		import json

		#print web.input()
		user_data = web.input()
		

		orders = { 
			"data": [
				{ 
					"orderDate": "2015-04-24 17:00:33", 
					"orderNo": "xyxhc140221160433005636", 
					"orderType": 0,  # 0 - 单程， 1 - 联程

					"arrStation": "哈尔滨", 
					"dptStation": "哈尔滨东", 
					"extSeat": [ { "0": 1 } ], 
					"seat": { "1": 1 }, 
					"ticketPay": 2, 
					"trainEndTime": "2015-05-22 16:41", 
					"trainNo": "6225", 
					"trainStartTime": "2015-05-22 16:20",

					"jointTrip": [ 
						{ 
							"arrStation": "哈尔滨", 
							"dptStation": "哈尔滨东", 
							"extSeat": [ { "0": 1 } ], 
							"seat": { "1": 1 }, 
							"seq": 1, 
							"trainEndTime": "2015-05-22 16:41", 
							"trainNo": "6225", 
							"trainStartTime": "2015-05-22 16:20" 
						}, 
						{ 
							"arrStation": "哈尔滨", 
							"dptStation": "哈尔滨东", 
							"extSeat": [], 
							"seat": { "1": 1 }, 
							"seq": 2, 
							"trainEndTime": "2015-05-23 16:41", 
							"trainNo": "6225", 
							"trainStartTime": "2015-05-23 16:20" # 16:20 
						} 
					], 

					"passengers": [ 
						{ 
							"certNo": "12010419760404761X", 
							"certType": "1", 
							"name": "关涛", 
							"ticketType": "1" 
						}, 
						{ 
							"certNo": "12010419760404761X", 
							"certType": "1", 
							"name": "关可贞", 
							"ticketType": "0" 
						}, 
					], 
				}, 
			], 
			"ret": True, 
			"total": 1
		} 

		if user_data['type']=='WAIT_TICKET':
			orders['data']=[] # 注释掉此行 --> 出票
			None 
		else:
			orders['data']=[] # 注释掉此行 --> 退票
			None 

		web.header("Content-Type", "application/json")
		return json.dumps(orders)

class TestProcess:
	def POST(self):
		import json
		
		print web.input()
		ret = { "ret": True }

		web.header("Content-Type", "application/json")
		return json.dumps(ret)

class TestProcess2: # ProcessPurchase 出票确认
	def POST(self):
		import json
		
		print web.input()
		#ret = { "ret": False, "errCode":"001", "errMsg":"test error" }
		ret = { "ret": True }
		
		web.header("Content-Type", "application/json")
		return json.dumps(ret)

#if __name__ == "__main__":
#    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)
#    app.run()



