from multiprocessing import Process, Queue
from flask import Flask, request
import json
import pythoncom

from core import STool
from core import ServerManager


class WebServerProcess(Process):
    def __init__(self, errs: Queue, cmds: Queue):
        super().__init__()
        self.name = 'WebServerProcess'
        self._errs = errs
        self._cmds = cmds

    def run(self):
        app = Flask(__name__)

        @app.route('/gs')
        def home():
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
            app.run(host='0.0.0.0', port=5000)
        except Exception as e:
            self._errs.put(str(e))

    def proc(self, cmd, id):
        # todo 检查参数有效性
        if cmd == 'create':
            s, err = ServerManager.createServer(id)
            return self.resp(0) if s else self.resp(-1, err)
        elif cmd in ('start', 'hotUpdate'):
            dirname = STool.getServerDirName(id)
            s = ServerManager.getServer(dirname)
            ret, err = s.call(cmd)
            return self.resp(0) if ret else self.resp(-1, err)
        elif cmd == 'exit':
            self._cmds.put((cmd, id))
            return self.resp(0, '关闭服务器暂时异步执行')
        else:
            return self.resp(-1, '参数错误')

    def resp(self, code, msg=''):
        return json.dumps({
            'code': code,
            'msg': msg,
        })


class WebServer():
    def __init__(self) -> None:
        # 使用queue获取子进程数据
        self._errs = Queue()
        self._cmds = Queue()
        self._service = WebServerProcess(self._errs, self._cmds)

    def start(self):
        self._service.daemon = True
        self._service.start()
        return self

    def stop(self):
        # 因为设置了守护，可以随着父进程一起关闭
        pass

    @property
    def running(self) -> bool:
        return self._service.is_alive()

    @property
    def next_error(self):
        if not self._errs.empty():
            return self._errs.get()
        return None

    @property
    def next_cmd(self):
        if not self._cmds.empty():
            return self._cmds.get()
        return None


# if __name__ == '__main__':
#     WebServer().start()
