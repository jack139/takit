#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import smtplib, os, time, sys, gc
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders
from email.Header import Header

import helper
from config import setting

db = setting.db_web

HTML = u'<div><p>现在有 %%s 个事件等待人工处理</p><p>时间：%%s</p></div>' \
       u'<div><p style="color:#E6E6E6;font-size:4px">%s</p></div>' % os.uname()[1]

def send_mail(send_from, send_to, subject, text):
	assert type(send_to)==list

	msg = MIMEMultipart()
	msg['From'] = send_from
	msg['To'] = COMMASPACE.join(send_to)
	msg['Date'] = formatdate(localtime=True)
	msg['Subject'] = Header(subject, 'gb2312')

	msg.attach(MIMEText(text, 'html', 'gb2312'))

	smtp = smtplib.SMTP()
	try:
		smtp.connect(setting.mail_server)    
		smtp.sendmail(send_from, send_to, msg.as_string())
	except Exception,e: 
		print "%s: %s" % (type(e), str(e))
	smtp.close()


if __name__ == "__main__":

	gc.set_threshold(300,5,5)

	print "MAILER: %s started" % helper.time_str()
	
	last_count=0

	try:  
		while 1:
			# 搜索人工事件
			db_alert=db.todo.find({'$and': [{'$and': [{'event': {'$ne':'ORDER_UI'}}, {'event': {'$ne':'ORDER_API'}}]}, {'man':1}]})
			if db_alert.count()>last_count:
				text = HTML % (db_alert.count(), helper.time_str())
				send_mail(setting.sender, setting.worker, u'人工事件提醒'.encode('gb2312'), 
					text.encode('gb2312'))
				print "%s MAILER: sent a mail" % (helper.time_str())

			last_count=db_alert.count()

			sys.stdout.flush()    
			time.sleep(5)

	except KeyboardInterrupt:
		print
		print 'Ctrl-C!'

	print "MAILER: %s exited" % helper.time_str()    
