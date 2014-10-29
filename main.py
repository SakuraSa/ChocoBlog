__author__ = 'Rnd495'

import os
import tornado.ioloop
import models
import pages
import configs

if __name__ == '__main__':
    if not os.path.exists('db.db'):
        print 'db.db not exists, initializing...'
        models.init()
        print 'ok'

    app = pages.create_app()
    app.listen(configs.service_port, configs.service_ip)
    print "starting service on %s:%s" % (configs.service_ip, configs.service_port)
    tornado.ioloop.IOLoop.instance().start()
