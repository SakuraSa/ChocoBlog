#!/usr/bin/env python
#coding=utf-8

__author__ = 'Rnd495'

import os
import hashlib
import tornado.options

#option helper
tornado.options.define("ip", default="0.0.0.0", help="run on the given ip", type=str)
tornado.options.define("port", default=8000, help="run on the given port", type=int)

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

#nav tabs
blog_nav_tabs = [(u'聊天室', '/'), (u'文章', '/post/list'), (u'图片', '/image/list')]

#load from user file
setting_file_path = "setting.conf"
file_config = {}
if os.path.exists(setting_file_path):
    with open(setting_file_path) as file_handle:
        for line in file_handle:
            line = line.strip()
            if (not line) or line.startswith("#"):
                continue
            parts = line.split("=")
            if len(parts) < 1:
                print "Config Error: config syntax error"
                print "              %s" % line
                continue
            name = parts[0]
            value = line[line.index("=") + 1:].strip()
            cmd = "%s = %s" % (name, value)
            exec cmd
            print cmd

