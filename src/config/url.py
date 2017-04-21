#!/usr/bin/env python
# -*- coding: utf-8 -*-

urls = (
    '/',                'Login',
    '/login',           'Login',
    '/logout',          'Reset',
    '/settings_user',   'SettingsUser',
    '/agreement',       'Agreement',
    '/sign_up',         'SignUp',
    '/sign_in',         'SignIn',
    '/article',         'Aticle',

    '/query',           'Query',
    '/checkout',        'Checkout',
    '/order',           'Order',
    '/order2',          'Order2', 
    '/verify',          'Verify',
    '/sjrand',          'Sjrand',
    '/sjrand_p',        'Sjrand_p',
    '/router',          'Router',
    '/cancel',          'Cancel',
    '/pay',             'Pay',
    '/man',             'Man',
    '/man2',            'Man2', # 20150407
    '/man3',            'Man3', # 20150412
    '/checkout_sjrand', 'CheckoutSjrand',
    '/checkout_sjrand2','CheckoutSjrand2', # 20150407
    '/checkout_sjrand3','CheckoutSjrand3', # 20150412
    '/verify_sjrand',   'VerifySjrand',
    '/pay2',            'Pay2',
    '/ali_form',        'AliForm',
    '/pay_result',      'PayResult',
    '/view_event',      'ViewEvent',
    '/crm',             'Crm',
    '/report',          'Report',

    '/api_info',        'APIInfo',

    '/api/task',        'APITask', # POST
    '/api/query',       'APIQuery', # POST
    '/api/order',       'APIOrder', # POST
    '/api/result',      'APIResult', # POST
    '/api/passengers',  'APIPassengers', # POST
    '/api/no_complete', 'APINoComplete', # POST
    '/api/complete',    'APIComplete', # POST
    '/api/cancel',      'APICancelNoComplete', # POST
    '/api/alipay',      'APIPay2', # GET
    '/api/checkout',    'APICheckout', # GET
    '/api/ali_form',    'APIAliForm', # GET

    '/admin/kam',          'AdminKam',
    '/admin/kam_setting',  'AdminKamSetting',
    '/admin/kam_add',      'AdminKamAdd',    
    '/admin/kam_del',      'AdminKamDel',
    '/admin/user',         'AdminUser',
    '/admin/user_setting', 'AdminUserSetting',
    '/admin/user_add',     'AdminUserAdd',
    '/admin/self_setting', 'AdminSelfSetting',
    '/admin/sys_setting',  'AdminSysSetting',
    '/admin/status',       'AdminStatus',
    '/admin/data',         'AdminData',
    '/admin/idpool',       'AdminIdPool',

    '/test/QueryOrders.do',            'TestQueryOrders', # GET 
    '/test/ProcessPurchase.do',        'TestProcess2', # POST
    '/test/ProcessRefund.do',          'TestProcess', # POST
    '/test/ProcessApplyAutoRefund.do', 'TestProcess', # POST
    '/test/ProcessGoPay.do',           'TestProcess', # POST
    '/test/reserve_callback',          'TestProcess', # POST

    '/qunar/reservation',   'QunarReservation', # POST
    '/qunar/cancel',        'QunarCancel', # POST
    '/qunar/pay_result',    'QunarPayResult', # POST
)

urls2 = (
    '/kyfw/passengers/query', 'CheckPassengers',
)
