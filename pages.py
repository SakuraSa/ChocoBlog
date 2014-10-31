#!/usr/bin/env python
# coding=utf-8

__author__ = 'Rnd495'

import os
import datetime
import time
import math
import json

import tornado.ioloop
import tornado.web

import helper
import configs
import chatRoom
import models
import sessionStorage
import verification


Image = verification.Image
page_dict = dict()
module_dict = dict()
session = models.Session()
storage = sessionStorage.SessionStoragePool()
chat_room = chatRoom.ChatRoom(cache_size=10)
verification_code_manager = verification.Verification()


def mapping(mapping_path):
    def wrapper(target):
        if issubclass(target, tornado.web.RequestHandler):
            if mapping_path in page_dict:
                raise KeyError("KeyError: page '%s' is already registered." % mapping_path)
            return page_dict.setdefault(mapping_path, target)
        elif issubclass(target, tornado.web.UIModule):
            if mapping_path in module_dict:
                raise KeyError("KeyError: module '%s' is already registered." % mapping_path)
            return module_dict.setdefault(mapping_path, target)
        else:
            raise TypeError("TypeError: unexcepted type '%s' registered." % repr(target))

    return wrapper


@mapping(r'title')
class UITitle(tornado.web.UIModule):
    def render(self, title, subtitle=''):
        return self.render_string('ui/title.html', title=title, subtitle=subtitle)


@mapping(r'navigation')
class UINavigation(tornado.web.UIModule):
    def render(self, select, current_user):
        tabs = [(name, url, 'active' if name == select else None) for name, url in configs.blog_nav_tabs]
        return self.render_string('ui/navigation.html', tabs=tabs, current_user=current_user)


@mapping(r'blog_preview')
class UIBlogPreview(tornado.web.UIModule):
    def render(self, post, current_user):
        return self.render_string('ui/blog_preview.html', post=post, current_user=current_user)


@mapping(r'markdown')
class UIMarkdown(tornado.web.UIModule):
    def render(self, content):
        return self.render_string('ui/markdown.html', content=helper.safe_markdown(content))

    def css_files(self):
        return "/static/css/high-light/default.css"


@mapping(r'page_div')
class UIPageDivBase(tornado.web.UIModule):
    def render(self, sqliter, page_index, page_size, nav_size, current_user, template):
        item_count = sqliter.count()
        page_count = int(math.ceil(item_count / float(page_size)))
        item_index_from = page_index * page_size
        item_index_to = item_index_from + page_size
        item_list = sqliter[item_index_from:item_index_to]
        return self.render_string(template,
                                  page_count=page_count,
                                  page_index=page_index,
                                  page_size=page_size,
                                  nav_size=nav_size,
                                  item_list=item_list,
                                  current_user=current_user)


@mapping(r'chat_room')
class UIChatRoom(tornado.web.UIModule):
    def render(self, current_user):
        return self.render_string('ui/chat_room.html', current_user=current_user)

    def javascript_files(self):
        return "/static/js/chat-room.js"

    def css_files(self):
        return "/static/css/high-light/default.css"


class MessageInterrupt(Exception):
    TITLE_DICT = {'info': u'信息', 'success': u'成功', 'warning': u'注意', 'danger': u'警告'}
    TITLE_DEFAULT = u'未知'

    def __init__(self, next_url, msg, info_type='info', title=None, count_down=10):
        self.next = next_url
        self.msg = msg
        self.type = info_type
        if title is None:
            self.title = MessageInterrupt.TITLE_DICT.get(self.type, MessageInterrupt.TITLE_DEFAULT)
        else:
            self.title = title
        self.count_down = count_down


def catch_message(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except MessageInterrupt, msg:
            self.render('message.html', msg=msg)
    return wrapper


def json_response(func):
    def wrapper(self, *args, **kwargs):
        try:
            obj = func(self, *args, **kwargs)
            self.write(json.dumps({
                "success": True,
                "message": "ok",
                "data": obj
            }))
        except tornado.web.HTTPError, ex:
            self.write(json.dumps({
                "success": False,
                "message": "%s:%s" % (type(ex).__name__, ex.log_message or ex.message),
                "data": {}
            }))
        except MessageInterrupt, ex:
            self.write(json.dumps({
                "success": False,
                "message": "%s:%s" % (type(ex).__name__, ex.msg),
                "data": {}
            }))
    return wrapper


class PageBase(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.session = session
        self.storage = None
        self._current_user = self.get_current_user()

    def get_current_user(self):
        self.storage = storage.get(self.get_secure_cookie("session_id", None))
        if self.storage.id != self.get_secure_cookie("session_id", ''):
            self.set_secure_cookie("session_id", self.storage.id)
        return self.session.query(models.User).filter(models.User.id == self.storage.user_id).first()

    def get_login_url(self):
        return '/login'


def get_str(request_handler, name, default=None):
    value = request_handler.get_argument(name, default)
    referer = request_handler.request.headers.get('Referer', '/')
    if value is None:
        raise MessageInterrupt(referer, u"未找到参数 '%s'" % name, 'warning', u'不正确的参数')
    return value


def get_int(request_handler, name, default=None):
    value = request_handler.get_argument(name, default)
    referer = request_handler.request.headers.get('Referer', '/')
    if value is None:
        raise MessageInterrupt(referer, u"未找到参数 '%s'" % name, 'warning', u'不正确的参数')
    try:
        return int(value)
    except ValueError:
        raise MessageInterrupt(referer, u"无法将 '%s' 转化为 int" % value, 'warning', u'不正确的参数')


def get_float(request_handler, name, default=None):
    value = request_handler.get_argument(name, default)
    referer = request_handler.request.headers.get('Referer', '/')
    if value is None:
        raise MessageInterrupt(referer, u"未找到参数 '%s'" % name, 'warning', u'不正确的参数')
    try:
        return float(value)
    except ValueError:
        raise MessageInterrupt(referer, u"无法将 '%s' 转化为 float" % value, 'warning', u'不正确的参数')


def get_model_by_id(request_handler, model, name='id'):
    model_id = get_int(request_handler, name)
    referer = request_handler.request.headers.get('Referer', '/')
    obj = request_handler.session.query(model).filter(model.id == model_id).first()
    if obj is None:
        raise MessageInterrupt(referer,
                               u"无法找到id为 '%s' 的 %s" % (model_id, model.__name__),
                               'warning',
                               u'不正确的参数')
    return obj


def render_list_page_template(request_handler, template, sqliter, **kwargs):
    page_index = get_int(request_handler, 'page_index', '0')
    page_size = get_int(request_handler, 'page_size', '8')
    nav_size = get_int(request_handler, 'nav_size', '10')
    request_handler.render(template,
                           sqliter=sqliter,
                           page_index=page_index,
                           page_size=page_size,
                           nav_size=nav_size,
                           **kwargs)


@mapping(r'/')
class PageHome(PageBase):
    @catch_message
    def get(self):
        limit = get_int(self, 'limit', default=8)
        self.render('home.html', posts=self.session.query(models.Post).order_by(models.Post.post_time)[:limit])


@mapping(r'/logout')
class PageLogout(PageBase):
    @catch_message
    def get(self):
        self.current_user = None
        self.storage.user_id = None
        self.set_secure_cookie('session_id', '')

        back_url = self.get_argument('next', r'/')
        raise MessageInterrupt(back_url, u'您已经注销', 'info', u'注销', count_down=3)


@mapping(r'/login')
class PageLogin(PageBase):
    def get(self):
        username = self.get_argument("username", None)
        if username is None:
            username = self.get_cookie("username", None)
        if username is None:
            username = ""
        ver_code = verification_code_manager.new()
        self.render('login.html', next=self.get_argument('next', '/'), username=username, ver_code=ver_code)

    @catch_message
    def post(self):
        username = self.get_body_argument('username', '')
        self.set_cookie('username', username, expires_days=30)
        ver_code_uuid = self.get_body_argument('uuid')
        ver_code = self.get_body_argument('ver_code')
        if not verification_code_manager.check(ver_code_uuid, ver_code):
            raise MessageInterrupt('/login', u'验证码不正确', 'warning', u'登陆失败')
        password = models.User.password_hash(self.get_body_argument('password', ''))
        user = self.session.query(models.User).filter(models.User.name == username, models.User.pwd == password).first()
        if not user:
            raise MessageInterrupt('/login', u'用户名或密码错误', 'warning', u'登陆失败')
        self.storage.user_id = user.id if user else None
        self.current_user = user
        expires_days = 30 if self.get_argument("remember_me", None) else 1
        self.set_secure_cookie('session_id', self.storage.id, expires_days=expires_days)

        back_url = self.get_argument('next', r'/')
        raise MessageInterrupt(back_url, u'您已经成功登陆', 'success', u'登陆成功', count_down=3)


@mapping(r'/register')
class PageRegister(PageBase):
    def get(self):
        ver_code = verification_code_manager.new()
        self.render('register.html', next=self.get_argument('next', '/'), ver_code=ver_code)

    @catch_message
    def post(self):
        username = get_str(self, 'username')
        password = get_str(self, 'password')
        password_cfm = get_str(self, 'password_cfm')
        ver_code_uuid = self.get_body_argument('uuid')
        ver_code = self.get_body_argument('ver_code')
        if not verification_code_manager.check(ver_code_uuid, ver_code):
            raise MessageInterrupt('/register', u'验证码不正确', 'warning', u'注册失败')
        if len(password) < 6:
            raise MessageInterrupt('/register', u'密码小于6位', 'warning', u'注册失败')
        if password != password_cfm:
            raise MessageInterrupt('/register', u'两次输入的密码不相符', 'warning', u'注册失败')
        if self.session.query(models.User).filter(models.User.name == username).first():
            raise MessageInterrupt('/register', u'用户名已经存在', 'warning', u'注册失败')

        user = models.User(name=username, pwd=password, role_id=2)
        self.session.add(user)
        self.session.commit()

        self.storage.user_id = user.id
        self.current_user = user
        self.set_secure_cookie('session_id', self.storage.id)

        raise MessageInterrupt(self.get_argument('next', '/'), u'您已经成功注册', 'success', u'注册成功', count_down=3)


@mapping(r'/post/list')
class PagePostList(PageBase):
    @catch_message
    def get(self):
        sqliter = self.session.query(models.Post).order_by(models.Post.post_time.desc())
        render_list_page_template(self, template='post/list.html', sqliter=sqliter)


@mapping(r'/post/view')
class PagePostView(PageBase):
    @catch_message
    def get(self):
        post = get_model_by_id(self, models.Post)
        sqliter = self.session.query(models.Comment)\
            .filter(models.Comment.post_id == post.id)\
            .order_by(models.Comment.post_time.desc())
        render_list_page_template(self, template='post/view.html', sqliter=sqliter, post=post)


@mapping(r'/post/create')
class PagePostCreate(PageBase):
    @tornado.web.authenticated
    def get(self):
        if not self.current_user or not self.current_user.role_id in (0, 1):
            raise MessageInterrupt('/', u'您没有权限发布文章', 'danger', u'拒绝访问')
        self.render('post/create.html')

    @tornado.web.authenticated
    def post(self):
        if not self.current_user or not self.current_user.role_id in (0, 1):
            raise MessageInterrupt('/', u'您没有权限布文章', 'danger', u'拒绝访问')
        title = self.get_argument('title')
        content = self.get_argument('content')
        post = models.Post()
        post.title = title
        post.content = content
        post.author_id = self.current_user.id
        last_upload = PageImageCreate.upload(self)
        post.image_id = last_upload[0].id if last_upload else 0
        self.session.add(post)
        self.session.commit()

        #send message
        chat_room.send_message(
            u"%s 刚刚发布了 [%s](/post/view?id=%s)" % (self.current_user.name, post.title, post.id),
            u"系统")

        self.redirect('/post/view?id=%s' % post.id)


@mapping(r'/post/edit')
class PagePostEdit(PageBase):
    @tornado.web.authenticated
    @catch_message
    def get(self):
        post = get_model_by_id(self, models.Post)
        if not post.get_can_edit(self.current_user):
            raise MessageInterrupt('/', u'您没有权限编辑此文章', 'danger', u'拒绝访问')
        self.render('post/edit.html', post=post)

    @tornado.web.authenticated
    @catch_message
    def post(self):
        post = get_model_by_id(self, models.Post)
        if not post.get_can_edit(self.current_user):
            raise MessageInterrupt('/', u'您没有权限编辑此文章', 'danger', u'拒绝访问')
        post.author_id = self.current_user.id
        post.title = self.get_argument('title')
        post.content = self.get_argument('content')
        post.post_time = datetime.datetime.now()
        self.session.commit()
        self.redirect('/post/view?id=%s' % post.id)


@mapping(r'/post/delete')
class PagePostDelete(PageBase):
    @tornado.web.authenticated
    @catch_message
    def get(self):
        post = get_model_by_id(self, models.Post)
        if not post.get_can_delete(self.current_user):
            raise MessageInterrupt('/', u'您没有权限做此操作', 'danger', u'拒绝访问')
        self.session.query(models.Comment).filter(models.Comment.post_id == post.id).delete()
        self.session.delete(post)
        self.redirect(self.get_argument('next', '/post/list'))


@mapping(r'/comment/create')
class PageCommentCreate(PageBase):
    @tornado.web.authenticated
    @catch_message
    def post(self):
        post = get_model_by_id(self, models.Post, name='post_id')
        content = get_str(self, 'content')
        if not 0 < len(content) < 140:
            referer = self.request.headers.get('Referer', '/')
            raise MessageInterrupt(referer, u'您的评论信息过长或过短', 'warning', u'文本错误')
        self.session.add(models.Comment(post.id, content, self.current_user.id))
        self.session.commit()
        next_url = self.get_argument('next', '/post/view?id=%s' % post.id)
        self.redirect(next_url)


@mapping(r'/image/list')
class PageImageList(PageBase):
    @catch_message
    def get(self):
        sqliter = self.session.query(models.Image).order_by(models.Image.upload_time.desc())
        render_list_page_template(self, template='image/list.html', sqliter=sqliter)


@mapping(r'/image/create')
class PageImageCreate(PageBase):
    @tornado.web.authenticated
    def get(self):
        if not self.current_user or not self.current_user.role_id in (0, 1):
            raise MessageInterrupt('/', u'您没有权限上传图片', 'danger', u'拒绝访问')
        self.render('image/create.html', last_upload=[])

    @tornado.web.authenticated
    def post(self):
        if not self.current_user or not self.current_user.role_id in (0, 1):
            raise MessageInterrupt('/', u'您没有权限上传图片', 'danger', u'拒绝访问')
        last_upload = PageImageCreate.upload(self)
        self.render('image/create.html', last_upload=last_upload)

    @staticmethod
    @catch_message
    def upload(self):
        image_mate = self.request.files.get('upload')
        image_list = []
        if image_mate:
            referer = self.request.headers.get('Referer', '/')
            try:
                for meta in image_mate:
                    upload_name = os.path.split(meta['filename'])[-1]
                    ext = os.path.splitext(upload_name)[-1]
                    if not ext.lower() in models.IMAGE_EXT:
                        raise MessageInterrupt(referer, u'图片格式必须为 %s' % u' 或 '.join(models.IMAGE_EXT),
                                               'warning', u'格式错误')
                    if len(meta['body']) > 1024 * 1024 * 2:
                        raise MessageInterrupt(referer, u'图片尺寸必须小于2Mb', 'warning', u'尺寸错误')
                    file_name = str(int(time.time())) + hex(id(self)) + ext
                    upload_path = 'static/upload/'
                    if not os.path.exists(upload_path):
                        os.makedirs(upload_path)
                    file_path = os.path.join(upload_path, file_name)
                    image = models.Image(name=meta['filename'],
                                         path=file_path, thumbnail_path=None, uploader_id=self.current_user.id)
                    with open(file_path, 'wb') as file_handle:
                        file_handle.write(meta['body'])
                    image_obj = Image.open(file_path)
                    size = image_obj.size
                    do_resize = False
                    max_size = (300, 200)
                    if size[0] > max_size[0]:
                        size = (max_size[0], int(float(max_size[0]) / size[0] * size[1]))
                        do_resize = True
                    if size[1] > max_size[1]:
                        size = (int(float(max_size[1]) / size[1] * size[0]), max_size[1])
                        do_resize = True
                    if do_resize:
                        image_obj.thumbnail(size, Image.ANTIALIAS)
                        file_name = "thumbnail" + str(int(time.time())) + hex(id(self)) + ext
                        upload_path = 'static/upload/thumbnail/'
                        if not os.path.exists(upload_path):
                            os.makedirs(upload_path)
                        file_path = os.path.join(upload_path, file_name)
                        image_obj.save(file_path)
                        image.thumbnail_path = file_path
                    else:
                        image.thumbnail_path = file_path
                    self.session.add(image)
                    image_list.append(image)
                self.session.commit()
            except Exception, err:
                self.session.rollback()
                raise err
        return image_list


@mapping(r'/user/view')
class PageUserView(PageBase):
    @catch_message
    def get(self):
        user = get_model_by_id(self, models.User)
        if user.role_id == 0:
            roles = self.session.query(models.Role).filter(models.Role.id == 0).order_by(models.Role.id)
        else:
            roles = self.session.query(models.Role).filter(models.Role.id != 0).order_by(models.Role.id)
        self.render('user/view.html', user=user, roles=roles)


@mapping(r'/user/update_role')
class PageUserUpdateRole(PageBase):
    @tornado.web.authenticated
    @catch_message
    def post(self):
        user = get_model_by_id(self, models.User)
        role_id = int(self.get_body_argument('role_id'))
        next_url = self.get_argument('next', '/user/view?id=%s' % user.id)
        if self.current_user.role_id != 0:
            raise MessageInterrupt(next_url, u'只有管理员测能修改角色', 'danger', u'拒绝访问')
        if user.role_id == 0:
            raise MessageInterrupt(next_url, u'不能修改管理员的角色', 'danger', u'拒绝访问')
        if role_id == 0:
            raise MessageInterrupt(next_url, u'不能将其他角色修改成管理员', 'danger', u'拒绝访问')
        user.role_id = role_id
        self.session.commit()
        raise MessageInterrupt(next_url, u'"%s"的角色修改成功' % user.name, 'success', u'修改成功', count_down=3)


@mapping(r'/user/change_password')
class PageUserChangePassword(PageBase):
    @tornado.web.authenticated
    @catch_message
    def post(self):
        old_password = get_str(self, 'old_password')
        new_password = get_str(self, 'password')
        user = get_model_by_id(self, models.User, name='user_id')
        if not user.get_is_same_password(old_password):
            referer = self.request.headers.get('Referer', '/')
            raise MessageInterrupt(referer, u'您输入的原有密码有误', 'warning', u'密码错误')
        user.set_password(new_password)
        self.session.commit()
        next_url = self.get_argument('next', '/user/view?id=%s' % user.id)
        raise MessageInterrupt(next_url, u'您的密码修改成功', 'success', u'修改成功', count_down=3)


@mapping(r'/user/check_username')
class PageUserCheckUsername(PageBase):
    @json_response
    def get(self):
        username = get_str(self, 'username')
        return self.session.query(models.User).filter(models.User.name == username).count() > 0


@mapping(r'/chat/update')
class PageChatUpdate(PageBase):
    @tornado.web.asynchronous
    def get(self):
        method = self.get_argument("method", "listen")
        if method == "join":
            chat_room.join(self)
        elif method == "listen":
            index = self.get_argument("method", "index", "-1")
            try:
                index = int(index)
            except ValueError:
                index = chat_room.last_index
            chat_room.listen(self, index)
        else:
            raise tornado.web.HTTPError(404, log_message="unknown method '%s'" % method)


@mapping(r'/chat/say')
class PageChatSay(PageBase):
    def get(self):
        return self.post()

    @json_response
    def post(self):
        message = get_str(self, "message")
        if self.current_user is None:
            raise tornado.web.HTTPError(401, log_message="you should login before say something")
        name = '<a href="/user/view?id=%d">%s</a>' % (
            self.current_user.id,
            tornado.web.escape.xhtml_escape(self.current_user.name)
        )
        if chat_room.api(self, message):
            user = self.current_user
            chat_room.send_message(
                u'应答[%s](/user/view?id=%d)的指令 `%s`' % (user.name, user.id, message),
                u"系统",
                "info"
            )
        else:
            chat_room.send_message(message, name)
        return None


def create_app(gzip=True):
    return tornado.web.Application(
        handlers=[
            (path, page)
            for path, page in page_dict.iteritems()
        ],
        ui_modules=module_dict,
        gzip=gzip,
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        cookie_secret=configs.cookie_secret
    )


if __name__ == '__main__':
    import os

    if not os.path.exists('db.db'):
        print 'db.db not exists, initializing...'
        models.init()
        print 'ok'

    app = create_app()
    app.listen(configs.service_ip, configs.service_port)
    tornado.ioloop.IOLoop.instance().start()