from threading import Thread
from queue import Queue
from flask import Flask, request
import json
import pythoncom

from core import CFG
from core import STool
from core import ServerManager


class WebServerThread(Thread):
    def __init__(self, host, port, errs: Queue):
        super().__init__()
        self.name = 'WebServerThread'
        self._host = host
        self._port = port
        self._errs = errs

    def run(self):
        app = Flask(__name__)

        @app.route('/gs')
        def gs():
            # https://blog.csdn.net/zhouf00/article/details/93630823
            pythoncom.CoInitialize()
            id, cmd = None, None
            if request.method == 'POST':
                obj = request.get_json()
                cmd = obj['cmd']
                id = obj['id']
            else:
                # return 'hello world'
                cmd = request.args.get('cmd')
                id = request.args.get('id')
            return self.proc(cmd, id)

        try:
            app.run(host=self._host, port=self._port)
        except Exception as e:
            self._errs.put(str(e))

    def proc(self, cmd, id):
        # todo 检查参数有效性
        if cmd == 'create':
            ret, err = ServerManager.createServer(id)
            return self.resp(0) if ret else self.resp(-1, err)
        elif cmd == 'delete':
            ret, err = ServerManager.deleteServer(id=id)
            return self.resp(0) if ret else self.resp(-1, err)
        elif cmd in ('start', 'hotUpdate', 'exit'):
            dirname = STool.getServerDirName(id)
            s = ServerManager.getServer(dirname)
            ret, err = s.call(cmd)
            return self.resp(0) if ret else self.resp(-1, err)
        else:
            return self.resp(-1, '参数错误')

    def resp(self, code, msg=''):
        return json.dumps({
            'code': code,
            'msg': msg,
        })


class WebServer():
    def __init__(self) -> None:
        host = CFG.Get('WebServer', 'host', 'localhost')
        port = CFG.Get('WebServer', 'port', '5000')
        self._errs = Queue()
        self._service = WebServerThread(host, port, self._errs)

    def start(self):
        self._service.setDaemon(True)
        self._service.start()
        return self

    def stop(self):
        # 因为设置了守护，可以随着进程一起关闭
        pass

    @property
    def running(self) -> bool:
        return self._service.is_alive()

    @property
    def next_error(self):
        if not self._errs.empty():
            return self._errs.get()
        return None


# if __name__ == '__main__':
#     WebServer().start()
