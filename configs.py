#!/usr/bin/env python
#coding=utf-8

__author__ = 'Rnd495'

import os
import hashlib
import tornado.options

#option helper
tornado.options.define("ip", default="0.0.0.0", help="run on the given ip", type=str)
tornado.options.define("port", default=80, help="run on the given port", type=int)

tornado.options.parse_command_line()

#tornado setting
service_ip = tornado.options.options.ip
service_port = tornado.options.options.port
cookie_secret = hashlib.sha256("rnd495".encode("base64")).hexdigest()
password_hash_salt = "rnd495"

#blog admin
admin_username = "admin"
admin_password = "admin"

#init blog
blog_first_post_name = u"欢迎使用ChocoBlog"
with open("markdown-help.md", "r") as file_handler:
    blog_first_post_content = file_handler.read().decode("utf-8")

#upload handler
upload_handler_name = "file"
upload_handler_param = {
    "root_path": os.path.split(__file__)[0],
    "upload_path": "static/upload"
}

#nav tabs
blog_nav_tabs = [(u'聊天室', '/'), (u'文章', '/post/list'), (u'图片', '/image/list')]

#load from user_setting
from user_setting import *

