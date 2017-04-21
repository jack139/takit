#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import stations


if __name__=='__main__':
	f = open("stations.java", "w")
	f.write('{\n')
	tmp1=stations.station_names.split('@')
	for i in tmp1:
		s='"%s",\n' % i
		f.write(s)
	f.write('}\n')
	f.close()


