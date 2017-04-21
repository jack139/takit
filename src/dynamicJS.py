#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import math, urllib

def bin216(s1):
	s=str(s1)
	o = ''
	for i in xrange(len(s)):
		b = ord(s[i])
		n = '%02x' % b
		o += n
	return o
	

delta = 0x9E3779B8;

def longArrayToString(data, includeLength):
	length = len(data)
	n = (length - 1) << 2

	if includeLength:
		m = data[length - 1];
		if (m < n - 3) or (m > n):
			return None;
		n = m;

	for i in xrange(length):
		# 无符号右移 js: -1 >>> 1， python: (-1 & 0xffffffff) >> 1
		data[i] = chr(data[i] & 0xff) \
			+ chr((data[i] & 0xffffffff) >> 8 & 0xff)  \
			+ chr((data[i] & 0xffffffff) >> 16 & 0xff) \
			+ chr((data[i] & 0xffffffff) >> 24 & 0xff)

	if includeLength:
		return ''.join(x for x in data)[0:n]
	else:
		return ''.join(x for x in data)

def stringToLongArray(string1, includeLength):
	length = len(string1)
	result = []
	for i in xrange(0,length,4): 
		result.append(ord(string1[i])    \
			| ord(string1[i + 1]) << 8  \
			| ord(string1[i + 2]) << 16 \
			| ord(string1[i + 3]) << 24)

	if includeLength:
		result.append(length)

	return result

def encrypt(string1, key):
	if string1 == '':
		return ''

	v = stringToLongArray(string1, True);
	k = stringToLongArray(key, False);

	if len(k) < 4:
		k += [0]*(4-len(k)) # 填充 0
	
	n = len(v) - 1;
	z = v[n]
	y = v[0]
	q = int(math.floor(6 + 52 / (n + 1)))
	sum1 = 0;
	
	while 0 < q:
		q -= 1
		sum1 = sum1 + delta & 0xffffffff
		e = (sum1 & 0xffffffff) >> 2 & 3
		
		for p in xrange(n):
			y = v[p + 1]
			mx = 	  ((z & 0xffffffff) >> 5 ^ y << 2) \
				+ ((y & 0xffffffff) >> 3 ^ z << 4) ^ (sum1 ^ y) \
				+ (k[p & 3 ^ e] ^ z)
			z = v[p] = v[p] + mx & 0xffffffff;
		p += 1
		y = v[0]
		mx = 	  ((z & 0xffffffff) >> 5 ^ y << 2) \
			+ ((y & 0xffffffff) >> 3 ^ z << 4) ^ (sum1 ^ y) \
			+ (k[p & 3 ^ e] ^ z)
		z = v[n] = v[n] + mx & 0xffffffff

	return longArrayToString(v, False)

keyStr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";
	
def encode32(input0):
	input1 = urllib.quote_plus(input0)
	input1 += '\0'*((3-len(input1)%3)%3)
	output = ''
	i = 0
	while 1:
		chr1 = ord(input1[i])
		chr2 = ord(input1[i+1])
		chr3 = ord(input1[i+2])
		i += 3
		enc1 = chr1 >> 2;
		enc2 = ((chr1 & 3) << 4) | (chr2 >> 4)
		enc3 = ((chr2 & 15) << 2) | (chr3 >> 6)
		enc4 = chr3 & 63
		if chr2==0:
			enc3 = enc4 = 64
		elif chr3==0:
			enc4 = 64
		output = output + keyStr[enc1] + keyStr[enc2] + keyStr[enc3] + keyStr[enc4]
	
		if i >= len(input1):
			break

	return output

def encrypt1(string1, key):
	return encode32(bin216(encrypt(string1, key)))
