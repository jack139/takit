#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import web
import time, datetime, os
import urllib2
import re
from config import setting

db = setting.db_web

ISOTIMEFORMAT='%Y-%m-%d %X'

reg_b = re.compile(r"(android|bb\\d+|meego).+mobile|avantgo|bada\\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino", re.I|re.M)
reg_v = re.compile(r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\\-|your|zeto|zte\\-", re.I|re.M)

def time_str(t=None):
    return time.strftime(ISOTIMEFORMAT, time.localtime(t))

def check_schedule(schedule):
    current_datetime = datetime.datetime.now()
    hours = schedule[current_datetime.strftime('%a')]
    if int(current_datetime.strftime('%H')) in hours:
        return True
    else:
        return False

def detect_mobile():
  if web.ctx.has_key('environ'):
    user_agent = web.ctx.environ['HTTP_USER_AGENT']
    b = reg_b.search(user_agent)
    v = reg_v.search(user_agent[0:4])
    if b or v:
      return True
  return False

def validateEmail(email):
    if len(email) > 7:
      if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", email) != None:
        return 1
    return 0

class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_301(
            self, req, fp, code, msg, headers)
        result.status = code
        return result

    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)
        result.status = code
        return result

    
###### logger class #######################################################

class Logger:

  VISIT          = 1 # 'Login: visit'
  LOGIN_FAIL     = 2 # 'Login: fail'
  ERR_PARAM      = 4 # 'Error: parameter'
  NO_PRIV        = 5 # 'Error: NO PRIV'
  USER_UPDATE    = 11 # 'SettingsUser: update'
  SIGNIN_WRONG   = 16 # 知道hash，email不对，有问题！
  SIGNUP_IOERR   = 17 # 注册验证码出问题
  SIGNUP_WRONG   = 18 # 有问题！
  TODO_INS_FAIL  = 19

  A_ERR_PARAM    = 901 # 'Error: parameter'
  A_USER_UPDATE  = 902 # 'AdminUserSettings: post'
  A_USER_ADD     = 903 # 'AdminUserAdd: post'
  A_SELF_UPDATE  = 904 # 'AdminSelfSetting: update'
  A_SELF_FAIL    = 905 # 'AdminSelfSetting: update fail, wrong pwd!'
  A_IO_ERROR     = 906 # 'Detector IOError'
  A_SYS_UPDATE   = 907 # 修改系统设置 成功
  A_SYS_FAIL     = 908 # 修改系统设置 取得settings出问题

  @classmethod 
  def uLog(self, msg, ref, ref2=None):
      db.ulog.insert({'time'  : time.time(),
                      'msg'   : msg,
                      'ref'   : ref,
                      'ref2'  : ref2,
                      'from'  : web.ctx.ip,
                     })

  @classmethod
  def aLog(self, msg, ref):
      db.alog.insert({'time'  : time.time(),
                      'msg'   : msg,
                      'ref'   : ref,
                      'from'  : web.ctx.ip,
                     })

  @classmethod
  def aLog2(self, msg, ref):
      db.alog.insert({'time'  : time.time(),
                      'msg'   : msg,
                      'ref'   : ref,
                      'from'  : 'localhost',
                     })
