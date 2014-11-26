#!/usr/bin/env python
# coding=utf-8

__author__ = 'Rnd495'

import time
import json
import thread
import datetime
import collections
import helper


class ChatRoom(object):
    def __init__(self, cache_size=100):
        object.__init__(self)
        self.pair_cache = collections.deque()
        self.cache_size = max(cache_size, 3)
        self.client_list = list()

        message = u"""
![Choco](/static/image/choco.jpg)
欢迎使用ChocoBlog
==================
聊天可以使用```Markdown```语法
帮助请见 [Markdown帮助](/post/view?id=0)"""
        message = helper.safe_markdown(message)
        self.last_index = 0
        self.cache_message(u"系统", message)

    def cache_message(self, user, message):
        self.last_index += 1
        pair = {
            "name": user,
            "message": message,
            "time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "index": self.last_index
        }
        self.pair_cache.append(pair)
        while len(self.pair_cache) > self.cache_size:
            self.pair_cache.popleft()
        return pair

    def send_message(self, message, name, info_type=None):
        message = helper.safe_markdown(message)
        if info_type is not None:
            message = self.system_info(message, info_type)
        self.cache_message(name, message)
        for c in self.client_list:
            self.response(**c)
        self.client_list = list()

    def send_delay_message(self, message, name, delay=1):
        def wrapper():
            time.sleep(delay)
            self.send_message(message, name)
        thread.start_new_thread(wrapper, tuple())

    def listen(self, client, index):
        if not self.response(client, index):
            self.client_list.append({
                "client": client,
                "index": index
            })

    def response(self, client, index):
        if index < self.last_index:
            client.write(self.json_response(pair for pair in self.pair_cache if pair["index"] > index))
            client.finish()
            return True
        return False

    def join(self, client):
        self.listen(client, index=-1)

    def api(self, sender, message):
        current_user = sender.current_user
        if not current_user:
            return False
        if message == "/online":
            lines = [u"在线用户:"]
            counter = 0
            id_set = set()
            for pair in self.client_list:
                client = pair["client"]
                user = client.current_user
                if user and user.id not in id_set:
                    counter += 1
                    lines.append(u"%4d. [%s](/user/view?id=%d) %s" % (counter, user.name, user.id, user.role.name))
                    id_set.add(user.id)
            self.send_delay_message(u"\n\r".join(lines), u"系统")
        elif message == "/clear":
            self.pair_cache.clear()
        else:
            return False
        return True

    @staticmethod
    def json_response(pairs):
        return json.dumps({
            "message": pairs if isinstance(pairs, list) else list(pairs),
        })

    @staticmethod
    def system_info(message, info_type):
        return message.replace(u"<p", u'<p class="text-%s"' % info_type)