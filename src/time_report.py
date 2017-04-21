#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import sys, time
from config import setting

db = setting.db_web

#


if __name__ == "__main__":
	if len(sys.argv)==1:
		print "usage: time_report.py <date>"
		sys.exit(2)

	report_date=sys.argv[1]

	status = [u'SLEEP', u'ORDER', u'VERIFY0', u'WAIT', u'AUTO_PAY', u'PAY2', u'SCAN3', u'CHECK2', u'FINISH']

	sys.stdout.write('orderNo,orderDate')
	for h in status:
		sys.stdout.write(',%s' % h)
	sys.stdout.write('\n')

	db_h = db.todo.find({'orderDate':{'$regex' : '%s.*' % report_date}},{'orderDate':1,'orderNo':1,'history':1})
	for h2 in db_h:
		sys.stdout.write('%s,%s' % (h2['orderNo'],h2['orderDate'].split()[1]))
		last_tick = int(time.mktime(time.strptime(h2['orderDate'], "%Y-%m-%d %H:%M:%S")))
		new_line={}
		for h in h2['history']: #  [u'Thread-11', u'2015-04-23 07:54:07', u'AUTO_PAY - break']
			ss = h[2].split()[0]
			if ss in status and (not new_line.has_key(ss)):
				new_line[ss]=int(time.mktime(time.strptime(h[1], "%Y-%m-%d %H:%M:%S")))
		for s in status:
			if not new_line.has_key(s):
				sys.stdout.write(',')
				continue
			now_tick = new_line[s]
			leak = now_tick - last_tick
			sys.stdout.write(',%d' % leak)
			last_tick = now_tick
		sys.stdout.write('\n')
