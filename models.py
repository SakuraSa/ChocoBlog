#!/usr/bin/env python
#coding=utf-8

__author__ = 'Rnd495'

from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker

import datetime
import hashlib

import configs

engine = create_engine('sqlite:///db.db', echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)

IMAGE_EXT = {'.jpg', '.png'}


class User(Base):
    __tablename__ = 'T_USER'

    id = Column(Integer, primary_key=True)
    name = Column(String(length=64), nullable=False)
    pwd = Column(String(length=128), nullable=False)
    role_id = Column(Integer, ForeignKey('T_ROLE.id'))
    register_time = Column(DateTime)

    role = relationship("Role", uselist=False, backref=backref('T_USER'))

    def __init__(self, name, pwd, role_id=0, id=None):
        self.name = name
        self.pwd = User.password_hash(pwd)
        self.register_time = datetime.datetime.now()
        self.role_id = role_id
        if not id is None:
            self.id = id

    def __repr__(self):
        return "<%s[%s]: %s>" % (type(self).__name__, self.id, self.name)

    def get_is_same_password(self, password):
        return User.password_hash(password) == self.pwd

    def set_password(self, password):
        self.pwd = User.password_hash(password)

    def get_can_edit(self, current_user):
        return current_user and current_user.id == self.id

    @staticmethod
    def password_hash(text):
        return hashlib.sha256(text + configs.password_hash_salt).hexdigest()


class Role(Base):
    __tablename__ = 'T_ROLE'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    def __init__(self, name, id=None):
        self.name = name
        if not id is None:
            self.id = id

    def __repr__(self):
        return "<%s[%s]: %s>" % (type(self).__name__, self.id, self.name)


class Image(Base):
    __tablename__ = 'T_IMAGE'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    uploader_id = Column(Integer, ForeignKey('T_USER.id'))
    upload_time = Column(DateTime)
    upload_path = Column(String(128))
    thumbnail_path = Column(String(128))

    uploader = relationship("User", uselist=False, backref=backref('T_IMAGE'))

    def __init__(self, name, path, thumbnail_path, uploader_id, id=None):
        self.name = name
        self.upload_path = path
        self.thumbnail_path = thumbnail_path
        self.uploader_id = uploader_id
        self.upload_time = datetime.datetime.now()
        if not id is None:
            self.id = id

    def __repr__(self):
            return"<%s[%s]: %s>" % (type(self).__name__, self.id, self.upload_path)

    def get_url(self):
        return '/' + self.upload_path

    def get_thumbnail_url(self):
        return '/' + self.thumbnail_path


class Post(Base):
    __tablename__ = 'T_POST'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(Text)
    post_time = Column(DateTime)
    author_id = Column(Integer, ForeignKey('T_USER.id'))
    image_id = Column(Integer, ForeignKey('T_IMAGE.id'))

    author = relationship("User", uselist=False, backref=backref('T_POST'))
    image = relationship("Image", uselist=False, backref=backref('T_POST'))

    def __init__(self):
        self.post_time = datetime.datetime.now()
        self.image_id = 0

    def __repr__(self):
        return"<%s[%s]: %s>" % (type(self).__name__, self.id, self.title)

    def get_can_edit(self, current_user):
        return current_user and current_user.id == self.author_id

    def get_can_delete(self, current_user):
        if self.id == 0:
            return False
        return current_user and (self.get_can_edit(current_user) or current_user.id == self.author_id)


class Comment(Base):
    __tablename__ = 'T_Comment'

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('T_POST.id'))
    content = Column(Text)
    post_time = Column(DateTime)
    author_id = Column(Integer, ForeignKey('T_USER.id'))

    post = relationship("Post", uselist=False, backref=backref('T_Comment'))
    author = relationship("User", uselist=False, backref=backref('T_Comment'))

    def __init__(self, post_id, content, author_id):
        self.post_id = post_id
        self.content = content
        self.author_id = author_id
        self.post_time = datetime.datetime.now()

    def __repr__(self):
        return"<%s[%s]: %s>" % (type(self).__name__, self.id, self.post_id)


def init():
    """
    init database structure
    """
    Base.metadata.create_all(engine)

    session = Session()
    if session.query(Role).count() == 0:
        session.add(Role(name=u'管理员', id=0))
        session.add(Role(name=u'会员', id=1))
        session.add(Image(name=u'choco.jpg',
                          path='static/image/choco.jpg',
                          thumbnail_path='static/image/choco.jpg',
                          uploader_id=0, id=0))
        session.add(User(name=configs.admin_username, pwd=configs.admin_password, role_id=0, id=0))
        post = Post()
        post.id = 0
        post.title = configs.blog_first_post_name
        post.content = configs.blog_first_post_content
        post.post_time = datetime.datetime.now()
        post.image_id = 0
        post.author_id = 0
        session.add(post)
        session.commit()


if __name__ == '__main__':
    print 'initializing database structure ...'
    engine.echo = True
    init()
    print 'ok'
