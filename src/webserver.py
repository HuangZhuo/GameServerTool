from threading import Thread
from queue import Queue
from flask import Flask, request
import json

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

        @app.route('/gs', methods=['GET', 'POST'])
        def gs():
            id, cmd = None, None
            if request.method == 'POST':
                cmd = request.form.get('cmd')
                id = request.form.get('id')
            else:
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
            data = None if not ret else {
                # 这里的key是参照[cc-game-mili.servers]数据库命名
                'serverId': ret.getCfg().serverID,
                'name': ret.getCfg().title,
                'masterport': ret.getCfg().masterPort,
                'octgameName': ret.getCfg().Get('db', 'db'),
                'octlogName': ret.getCfg().Get('octlog', 'db'),
                # 'socket': '{}:{}'.format(
                #     ret.getCfg().Get('net', 'public_ip'),
                #     ret.getCfg().Get('net', 'port'),
                # ),
                'port': ret.getCfg().Get('net', 'port'),
            }
            return self.resp(0, '', data) if ret else self.resp(-1, err)
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

    def resp(self, code, msg='', data=None):
        return json.dumps({
            'code': code,
            'msg': msg,
            'data': data,
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
        raise NotImplementedError

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
