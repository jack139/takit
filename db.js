/* -------------- Collections list ---------------*/
alog
device
id_pool
qunar
sessions
todo
ulog
user
user_12306

/* -------------- Indexes ---------------*/

db.user_12306.ensureIndex({uname:1})
db.user_12306.ensureIndex({status:1})
db.user_12306.ensureIndex({status:1,online:1})
db.user_12306.ensureIndex({order_num:1})
db.user_12306.ensureIndex({group:1})

db.user.ensureIndex({privilege:1})
db.user.ensureIndex({uname:1})
db.user.ensureIndex({login:1,privilege:1})

db.qunar.ensureIndex({orderNo:1})

db.todo.ensureIndex({orderNo:1})
db.todo.ensureIndex({event:1})
db.todo.ensureIndex({lock:1})
db.todo.ensureIndex({b_time:1})
db.todo.ensureIndex({e_time:1})
db.todo.ensureIndex({status:1})
db.todo.ensureIndex({man:1})
db.todo.ensureIndex({return:1})
db.todo.ensureIndex({orderNo:1,status:1})
db.todo.ensureIndex({lock:1,man:1,e_time:1})
db.todo.ensureIndex({status:1,event:1,lock:1,cs_time:1,b_time:1})
db.todo.ensureIndex({user_12306:1})
db.todo.ensureIndex({orderDate:1})

db.thread.ensureIndex({tname:1})

db.sessions.ensureIndex({session_id:1})

