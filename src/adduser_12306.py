#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import sys
import helper
from config import setting

db = setting.db_web

#
# 文件格式:
#
# user1	passwd1
# user2	passwd2
# $$$
#

if __name__ == "__main__":
	if len(sys.argv)==1:
		print "usage: adduser_12306.py <user_list.txt>"
		sys.exit(2)

	user_file=sys.argv[1]

	print "ADDUSER: %s started" % helper.time_str()
	print "data file: %s" % user_file

	try:  
		f=file(user_file)
		while 1:
			l=f.readline().split()
			if len(l)<2:
				break
			db_user=db.user_12306.find_one({'uname': l[0]})
			if db_user==None:
				db.user_12306.insert({
					'uname'  : l[0],
					'passwd' : l[1],
					'status' : 'FAIL',
				})
				print '    已添加 %s' % l[0]
			else:
				print '--> 已存在 %s' % l[0]
		f.close()
	except KeyboardInterrupt:
		print
		print 'Ctrl-C!'

	print "ADDUSER: %s exited" % helper.time_str()    
