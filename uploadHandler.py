#!/usr/bin/env python
# coding=utf-8

__author__ = 'Rnd495'

import os
import time

from oss import oss_api


uploadHandlerDict = {}


def register(name):
    global uploadHandlerDict

    def wrapper(target):
        if not issubclass(target, UploadHandler):
            raise TypeError('TypeError: target type should be UploadHandler\'s subclass, but "%s" found.' % target)
        if name in uploadHandlerDict:
            raise KeyError('KeyError: "%s" is already registered.' % target)
        uploadHandlerDict[name] = target
        return target

    return wrapper


def get_upload_handler(tag="file"):
    return uploadHandlerDict[tag]


class UploadHandler(object):
    def __init__(self):
        object.__init__(self)

    def save(self, buf, ext):
        raise NotImplementedError()


@register("file")
class UploadHandlerFile(UploadHandler):
    def __init__(self, root_path, upload_path):
        UploadHandler.__init__(self)
        self.root_path = root_path
        self.upload_path = upload_path

    def save(self, buf, ext):
        offset = 0
        file_path = os.path.join(self.root_path, self.upload_path)
        file_name = "%x_%x%s" % (int(time.time()), id(buf) + offset, ext)
        file_full_name = os.path.join(file_path, file_name)
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        while os.path.exists(file_full_name):
            offset += 1
            file_full_name = os.path.join(file_path, file_name)
        with open(file_full_name, 'wb') as file_handle:
            file_handle.write(buf)
        return "/"  + os.path.join(self.upload_path, file_name)


@register("ali_oss")
class UploadHandlerAliOSS(UploadHandler):
    def __init__(self, host, access_id, secret_access_key, bucket):
        UploadHandler.__init__(self)
        self.host = host
        self.access_id = access_id
        self.secret_access_key = secret_access_key
        self.bucket = bucket
        self.oss = oss_api.OssAPI(host + ".aliyuncs.com", access_id, secret_access_key, bucket)

    def save(self, buf, ext):
        ext = ext.lower()
        content_type = "application/octet-stream"
        if ext == ".jpg" or ext == ".jpeg":
            content_type = "image/jpeg"
        elif ext == ".gif":
            content_type = "image/gif"
        elif ext == ".png":
            content_type = "image/png"
        file_name = "%x_%x%s" % (int(time.time()), id(buf), ext)
        headers = {}
        res = self.oss.put_object_from_string(self.bucket, file_name, buf, content_type, headers)
        if (res.status / 100) != 2:
            raise IOError("IOError: put object failed with AliOSS.")
        return "http://%s.%s.aliyuncs.com/%s" % (self.bucket, self.host, file_name)