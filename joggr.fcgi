#!/home/yuval/venv/flask/bin/python
from flup.server.fcgi import WSGIServer
from joggr import app

if __name__ == '__main__':
  #WSGIServer(app, bindAddress='unix:/tmp/joggr-fcgi.sock').run()
  WSGIServer(app, bindAddress='/tmp/joggr-fcgi.sock').run()
