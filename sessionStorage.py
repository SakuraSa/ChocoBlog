#!/usr/bin/env python
#coding=utf-8

__author__ = 'Rnd495'

import time
import hashlib
import collections


class SessionStorage(object):
    def __init__(self, manager):
        object.__init__(self)
        self.mem = dict()
        self.user_id = None
        self.time = time.time()
        self.id = hashlib.sha256(str(self.time) + str(id(self))).hexdigest()
        self.manager = manager

    def __getitem__(self, item):
        return self.mem[item]

    def __setitem__(self, key, value):
        self.mem[key] = value

    def close(self):
        self.manager.remove(self)

    def is_logged_in(self):
        return not self.user_id is None


class SessionStoragePool(object):
    def __init__(self, timeout=3600 * 24 * 30, max_size=10000):
        self.timeout = timeout
        self.max_size = max_size
        self.queue = collections.deque()
        self.dic = dict()

    def create(self):
        session = SessionStorage(self)
        self.queue.append(session)
        self.dic[session.id] = session
        return session

    def check(self):
        now = time.time()
        while len(self.queue) > 0 and (len(self.queue) > self.max_size or
                self.queue[0].time + self.timeout > now or
                not self.queue[0].id in self.dic):
            del self.dic[self.queue.popleft().id]

    def get(self, session_id=None):
        if session_id and session_id in self.dic:
            return self.dic[session_id]
        return self.create()

    def remove(self, session):
        if session.id in self.dic:
            del self.dic[session.id]