from threading import Thread
from queue import Queue
from flask import Flask, request
import json

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

        @app.route('/', methods=['GET', 'POST'])
        def index():
            return 'GameServerTool is running..'

        @app.route('/gs', methods=['GET', 'POST'])
        def gs():
            data = self.req(request)
            id = data.get('id')
            cmd = data.get('cmd')
            return self.proc(id, cmd, data)

        @app.route('/gs_running', methods=['GET', 'POST'])
        def gs_running():
            dirs = STool.getServerDirs()
            ret = list()
            for dir in dirs:
                s = ServerManager.getServer(dir)
                if s.isValid() and s.isRunning():
                    ret.append(STool.getServerDirID(dir))
            ret.sort()
            return self.resp(0, '', data=ret)

        try:
            app.run(host=self._host, port=self._port)
        except Exception as e:
            self._errs.put(str(e))

    def proc(self, id, cmd, data):
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
            s = ServerManager.getServer(id=id)
            ret, err = s.call(cmd)
            return self.resp(0) if ret else self.resp(-1, err)
        elif cmd == 'gm':
            if not 'order' in data:
                return self.resp(-1, 'order参数错误')
            s = ServerManager.getServer(id=id)
            ret, resp = s.execute(data.get('order'))
            return self.resp(0 if ret else -1, resp)
        else:
            return self.resp(-1, '参数错误')

    def req(self, request):
        if request.method == 'POST':
            if request.json:
                # for postman
                return request.json
            else:
                # for php http_post
                return request.form
        elif request.method == 'GET':
            return request.args

    def resp(self, code, msg='', data=None):
        return json.dumps({
            'code': code,
            'msg': msg,
            'data': data,
        })


class WebServer():
    def __init__(self, host, port) -> None:
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
