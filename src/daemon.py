#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 后台daemon进程，启动后台处理进程，并检查进程监控状态
#

import sys
import time, shutil, os
import helper
from config import setting

web_db = setting.db_web
db = web_db

TAKIT_DIR=''
LOG_DIR=''

def start_processor(pname):
	cmd0="nohup python %s/%s.pyc &>> %s/%s.log &" % \
		(TAKIT_DIR, pname, LOG_DIR, pname)
	#print cmd0
	os.system(cmd0)

def get_processor_pid(pname):
	cmd0='pgrep -f "%s"' % pname
	#print cmd0
	pid=os.popen(cmd0).readlines()
	if len(pid)>0:
		return pid[0].strip()
	else:
		return None

def kill_processor(pname):
	cmd0='kill -9 `pgrep -f "%s"`' % pname
	#print cmd0
	os.system(cmd0)

if __name__=='__main__':
	if len(sys.argv)<3:
		print "usage: daemon.py <TAKIT_DIR> <LOG_DIR>"
		sys.exit(2)

	TAKIT_DIR=sys.argv[1]
	LOG_DIR=sys.argv[2]

	print "DAEMON: %s started" % helper.time_str()
	print "TAKIT_DIR=%s\nLOG_DIR=%s" % (TAKIT_DIR, LOG_DIR)

	#
	#启动后台进程
	#
	kill_processor('%s/processor' % TAKIT_DIR)
	kill_processor('%s/dispatcher' % TAKIT_DIR)
	start_processor('processor')
	#start_processor('dispatcher')

	try:	
		_count=_ins=0
		while 1:						
			# 检查processor进程
			pid=get_processor_pid('%s/processor' % TAKIT_DIR)
			if pid==None:
				# 进程已死, 重启进程
				kill_processor('%s/processor' % TAKIT_DIR)
				start_processor('processor')
				_ins+=1
				print "%s\tProcessor restart" % helper.time_str()
			
			# 检查dispatcher进程
			pid=get_processor_pid('%s/dispatcher' % TAKIT_DIR)
			if pid==None:
				# 进程已死, 重启进程
				kill_processor('%s/dispatcher' % TAKIT_DIR)
				start_processor('dispatcher')
				_ins+=1
				print "%s\tDispatcher restart" % helper.time_str()
			
			time.sleep(5)
			if _count>1000:
				if _ins>0:
					print "%s  HEARTBEAT: error %d" % (helper.time_str(), _ins)
				else:
					print "%s  HEARTBEAT: fine." % (helper.time_str())
				_count=_ins=0
			sys.stdout.flush()

	except KeyboardInterrupt:
		print
		print 'Ctrl-C!'

	print "DAEMON: %s exited" % helper.time_str()
