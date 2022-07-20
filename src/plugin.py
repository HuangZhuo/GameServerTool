#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import json
import logging
import re
import tkinter
from datetime import date
from urllib import request

import psutil

from common import GUITool, counter, get_free_space_gb
from core import CFG, DB, ServerManager, STool
from webserver import WebServer


class FrameEx(tkinter.Frame):
    def __init__(self, *args, **kw) -> None:
        super().__init__(*args, **kw)

    def pack(self, *args, **kw):
        # pack() function -> method
        super().pack(*args, **kw)
        return self


class IPlugin:
    def __init__(self, name=None) -> None:
        self._section = self.__class__.__name__
        self._name = name if name else self._section

    @property
    def section(self):  # INI配置文件区块
        return self._section

    @property
    def name(self):  # 插件名称
        return self._name

    @property
    def enabled(self):  # 插件是否开启
        return CFG.HasSection(self._section) and CFG.GetBool(self._section, 'enabled')

    def log_info(self, msg, *args):
        logging.info(f'[{self.name}]' + msg, *args)

    def log_warning(self, msg, *args):
        logging.warning(f'[{self.name}]' + msg, *args)

    def log_error(self, msg, *args):
        logging.error(f'[{self.name}]' + msg, *args)


# 批量创建服务器插件
class PluginCreateMultiServers(FrameEx, IPlugin):
    def __init__(self, gui):
        FrameEx.__init__(self)
        self._gui = gui
        self.initUI()

    def initUI(self):
        nextcol = counter()
        tkinter.Label(self, text='批量创建:').grid(row=0, column=nextcol())
        self._edit = tkinter.Entry(self, width=16)
        self._edit.grid(row=0, column=nextcol())
        self._edit.bind('<Return>', lambda _: self.onCreateMultiServerClick())
        GUITool.createBtn('执行', self.onCreateMultiServerClick, parent=self, grid=(0, nextcol()))
        tkinter.Label(self, text='*支持输入格式: 10|10-20|10,20', fg='gray').grid(row=0, column=nextcol())
        GUITool.GridConfig(self, padx=5)

    def onCreateMultiServerClick(self):
        input = self._edit.get().strip()
        print('onCreateMultiServerClick', input)
        if len(input) == 0:
            GUITool.MessageBox('批量创建输入为空')
            return

        listCreate = []
        err = '匹配序列为空'
        while True:
            # 10
            if input.isnumeric():
                listCreate.append(int(input))
                break

            # 10-20
            m = re.search(r'^([0-9]+)-([0-9]+)$', input)
            if m:
                print(m.groups())
                tmp = [int(n) for n in m.groups()]
                for i in range(tmp[0], tmp[1] + 1):
                    listCreate.append(i)
                break

            # 10,20
            tmp = input.strip(',').split(',')
            if len(tmp) > 1:
                try:
                    for n in tmp:
                        if not n.isnumeric():
                            err = '[{}]不是数字类型'.format(n)
                            raise ValueError
                    listCreate = list(set([int(n) for n in tmp]))
                    listCreate.sort()
                except:
                    break

            err = '不支持的输入格式'
            break

        if len(listCreate) == 0:
            err = '输入[{0}]错误：{1}'.format(input, err)
            logging.error(err)
            GUITool.MessageBox(err)
            return

        if not GUITool.MessageBox('是否创建以下服务器：{}'.format(listCreate), ask=True):
            return

        logging.info('开始批量创建服务器：{}'.format(listCreate))
        listSuc = []
        for id in listCreate:
            ret, err = ServerManager.createServer(id)
            if ret:
                listSuc.append(id)
            else:
                logging.error('创建服务器{}失败，终止批量创建'.format(id))
                GUITool.MessageBox(err)
                break

        if len(listSuc) > 0:
            logging.info('完成批量创建服务器：{}'.format(listSuc))
            self._gui.initServerList()


# 控制台执行命令插件
class PluginExecuteCommand(FrameEx, IPlugin):
    def __init__(self, gui):
        FrameEx.__init__(self)
        self._gui = gui
        self.initUI()

    def initUI(self):
        nextcol = counter()
        tkinter.Label(self, text='输入命令:').grid(row=0, column=nextcol())
        self._edit = tkinter.Entry(self, width=16)
        self._edit.grid(row=0, column=nextcol())
        self._edit.bind('<Return>', lambda _: self.onExecuteClick())
        GUITool.createBtn('执行', self.onExecuteClick, parent=self, grid=(0, nextcol()))
        tkinter.Label(self, text='*命令参考: GMCommand::DoSystemCommand', fg='gray').grid(row=0, column=nextcol())
        GUITool.GridConfig(self, padx=5)

    def onExecuteClick(self):
        input = self._edit.get().strip()
        print('onExecuteClick', input)
        if len(input) == 0:
            GUITool.MessageBox('命令输入为空')
            return
        servers = self._gui.getSelectedServers()
        servers = map(ServerManager.getServer, servers)
        servers = list(filter(lambda s: s.isRunning(), servers))
        if len(servers) == 0:
            GUITool.MessageBox('没有选择运行中的服务器')
            return
        for s in servers:
            if not s.isRunning():
                continue
            ret, err = s.execute(input)
            if not ret:
                GUITool.MessageBox(err)
                break


# 服务器选择器
class PluginServerSelector(FrameEx, IPlugin):
    FILTER_ALL = lambda s: True
    FILTER_NONE = lambda s: False
    FILTER_RUNNING = lambda s: ServerManager.getServer(s).isRunning()
    FILTER_CLOSED = lambda s: not ServerManager.getServer(s).isRunning()

    def __init__(self, gui):
        FrameEx.__init__(self, gui)
        # self._gui = gui
        self._serverListView = gui.getServerListView()
        self.initUI()

    def initUI(self):
        nextcol = counter()
        GUITool.createBtn('全选', lambda: self.doSelect(PluginServerSelector.FILTER_ALL), parent=self, grid=(0, nextcol()))
        GUITool.createBtn('全不选', lambda: self.doSelect(PluginServerSelector.FILTER_NONE), parent=self, grid=(0, nextcol()))
        GUITool.createBtn('运行中', lambda: self.doSelect(PluginServerSelector.FILTER_RUNNING), parent=self, grid=(0, nextcol()))
        GUITool.createBtn('已关闭', lambda: self.doSelect(PluginServerSelector.FILTER_CLOSED), parent=self, grid=(0, nextcol()))
        tkinter.Label(self, text='|').grid(row=0, column=nextcol())
        tkinter.Label(self, text='选择范围:').grid(row=0, column=nextcol())
        self._edit = tkinter.Entry(self, width=10)
        self._edit.grid(row=0, column=nextcol())
        self._edit.bind('<Return>', lambda _: self.onExecuteClick())
        GUITool.createBtn('执行', self.onExecuteClick, parent=self, grid=(0, nextcol()))
        GUITool.GridConfig(self, padx=5)

    def onExecuteClick(self):
        input = self._edit.get().strip()
        if len(input) == 0:
            GUITool.MessageBox('输入为空')
            return

        begin = end = None
        err = '匹配序列为空'
        while True:
            # 10
            if input.isnumeric():
                begin = end = int(input)
                self.doSelectRange(begin, end)
                return

            # 10-20
            m = re.search(r'^([0-9]+)-([0-9]+)$', input)
            if m:
                tmp = [int(n) for n in m.groups()]
                begin, end = tmp[0], tmp[1]
                self.doSelectRange(begin, end)
                return

            # 版本号
            m = re.search(r'^[Vv]([0-9.]+)$', input)
            if m:
                self.doSelectVersion(m.group(1))
                return

            err = '不支持的输入格式'
            break

        err = '输入[{0}]错误：{1}'.format(input, err)
        logging.error(err)
        GUITool.MessageBox(err)
        return

    def doSelect(self, ft):
        servers = self._serverListView.getAll()
        servers = list(filter(ft, servers))
        self._serverListView.setSelected(servers)

    def doSelectRange(self, begin, end):
        self.doSelect(lambda s: STool.getServerDirID(s) in range(begin, end + 1))

    def doSelectVersion(self, version):
        self.doSelect(lambda s: ServerManager.getServer(s).getVersion() == version)


# 扩展操作
class PluginExtendOperations(FrameEx, IPlugin):
    def __init__(self, gui):
        FrameEx.__init__(self)
        self._gui = gui
        self.initUI()

    def initUI(self):
        nextcol = counter()
        GUITool.createBtn('关闭->整包更新->开启', self.onUpdateClick, parent=self, grid=(0, nextcol()))
        GUITool.createBtn('数据更新->热更', self.onHotUpdateClick, parent=self, grid=(0, nextcol()))
        GUITool.GridConfig(self, padx=5)

    def onUpdateClick(self):
        for v in self._gui.getSelectedServers():
            server = ServerManager.getServer(v)
            if not server.isValid():
                continue
            if server.isRunning():
                ret, err = server.exit()
                if not ret:
                    GUITool.MessageBox(err)
                    break
            STool.updateServerDir(v)
            server.start()

    def onHotUpdateClick(self):
        for v in self._gui.getSelectedServers():
            server = ServerManager.getServer(v)
            if not server.isValid():
                continue
            STool.updateServerDir(v, filelist=('data', 'GameConfig.ini'))
            if server.isRunning():
                server.hotUpdate()


class PluginWebService(FrameEx, IPlugin):
    def __init__(self, gui):
        FrameEx.__init__(self)
        IPlugin.__init__(self, 'WebService')
        self._gui = gui
        self._lbl = tkinter.Label(self, text=f'[{self.name}]准备启动..')
        self._lbl.grid(row=0, column=0)

        self._host = CFG.Get('WebServer', 'host', 'localhost')
        self._port = CFG.Get('WebServer', 'port', '5000')
        self._service = None
        self.after(2000, self.initWebServer)
        self.log_info('初始化完成')

    def initWebServer(self):
        # self._gui.callPlugin('PluginDingTalkRobot', 'send', 'initWebServer')
        self._service = WebServer(self._host, self._port).start()
        self.after(2000, self.checkWebServer)

    def checkWebServer(self):
        if not self._service.running:
            self._lbl['text'] = f'[{self.name}]停止运行:{self._service.next_error}'
            self._lbl['fg'] = 'red'
            return
        else:
            self._lbl['text'] = f'[{self.name}]运行中@{self._host}:{self._port}'
            self._lbl['fg'] = 'green'
            self.after(1000, self.checkWebServer)


class PluginServerMgr(FrameEx, IPlugin):
    def __init__(self, gui):
        FrameEx.__init__(self)
        IPlugin.__init__(self, '自动开服')
        self._lbl = tkinter.Label(self, text='[{self._name}]检测中..', fg='gray')
        self._lbl.grid(row=0, column=0)
        if not self.enabled:
            self._lbl['text'] = f'[{self._name}]已关闭'
            return

        data = CFG.GetItems(self.section)
        # print(data)
        self._data = json.dumps(dict(data)).encode('utf-8')
        self._checkInterval = CFG.GetInt(self.section, 'check_interval', 5) * 1000
        self._gameId = CFG.GetInt(self.section, 'game_id', 0)
        self._phpSessionId = CFG.Get(self.section, 'PHPSESSID', '')
        if self._checkInterval > 0 and self._gameId and self._phpSessionId:
            self._lbl['text'] = f'[{self._name}]运行中'
            self._lbl['fg'] = 'green'
            self.after(self._checkInterval, self.check)
        else:
            self._lbl['text'] = f'[{self._name}]开启失败'
            self._lbl['fg'] = 'red'
        self.log_info('初始化完成')

    def check(self):
        url = f'http://127.0.0.1:81/Admin/Ctrl/server_add_check.html?gameid={self._gameId}'
        header = {'Cookie': f'game_id={self._gameId}; PHPSESSID={self._phpSessionId}; sdmenu_my_menu=111'}
        req = request.Request(url=url, headers=header, data=self._data)
        try:
            resp = request.urlopen(req)
            if resp.url.find('login.html') > 0:
                self._lbl['text'] = f'[{self._name}]PHPSESSID 已失效'
                self._lbl['fg'] = 'red'
                return
            resp_msg = resp.read().decode()
            # print(self.section, resp_msg)
        except Exception as e:
            print(repr(e))
        self.after(self._checkInterval, self.check)


class PluginServerMonitor(FrameEx, IPlugin):
    def __init__(self, gui):
        FrameEx.__init__(self)
        IPlugin.__init__(self, '服务器监控')
        self._gui = gui
        self._lbl = tkinter.Label(self, text=f'[{self._name}]', fg='gray')
        self._lbl.grid(row=0, column=0)
        if not self.enabled:
            self._lbl['text'] = f'[{self._name}]已关闭'
            return
        self._lbl['text'] = f'[{self._name}]运行中'
        self._lbl['fg'] = 'green'
        self.initUI()
        self._max_restart_times = CFG.GetInt(self.section, 'max_restart_times', 0)
        self._db = DB('monitor.json')
        self.after(CFG.SERVER_STATE_UPDATE_INTERVAL, self.check)
        self.log_info('初始化完成')

    def initUI(self):
        var = tkinter.BooleanVar(value=True)
        self._check = tkinter.Checkbutton(self,
                                          text='自动重启',
                                          fg='gray',
                                          variable=var,
                                          onvalue=True,
                                          offvalue=False,
                                          command=self.onCheckToggle)
        self._check.var = var
        self._check.grid(row=0, column=1)
        self.onCheckToggle()

    def onCheckToggle(self):
        st = self._check.var.get()
        self._check['text'] = '自动重启开' if st else '自动重启关'
        self._check['fg'] = 'green' if st else 'gray'

    def getClosedServers(self):
        ret = []
        for s in STool.getServerDirs():
            s = ServerManager.getServer(s)
            if not s.isRunning():
                ret.append(s)
        return ret

    def getNotRespondingServer(self):
        '''获取*一个*未响应服务器进程。依赖WerFault进行检测'''
        for pid in psutil.pids():
            if pid == 0 or not psutil.pid_exists(pid):
                continue
            try:
                p = psutil.Process(pid)
                if p.exe().find('WerFault') >= 0:
                    # print(p.exe(), p.cmdline())
                    pid = p.cmdline()[3]  # pid 参数位置， todo：判错
                    s = ServerManager.getServer(pid=int(pid))
                    if s:
                        p.kill()
                        return s
            except FileNotFoundError as e:
                pass
            except psutil.NoSuchProcess as e:
                pass
            except psutil.AccessDenied as e:
                pass
            except Exception as e:
                self.log_error(repr(e))
        return None

    def check(self):
        s = self.getNotRespondingServer()
        delay = 0  # 下次检测延迟
        while True:
            if not s: break
            self.log_info(f'服务器[{s.dirname}]未响应，自动重启[{self._check.var.get()}]')
            s.exit(bForce=True)
            self._gui.callPlugin('PluginDingTalkRobot', 'send', f'{s.name}未响应，强制关闭')

            if not self._check.var.get(): break
            today = str(date.today())
            if self._db.get('date') != today:
                self._db.clear()
                self._db.set('date', today)
                self._db.save()
                self.log_info(f'重启记录过期，日期已更新为 {today}')
            times = self._db.get(s.dirname, 0)
            # print(s.dirname, s.name, times)
            if times < self._max_restart_times:
                times += 1
                s.start()
                self.log_info(f'服务器[{s.dirname}]第{times}/{self._max_restart_times}次自动重启')
                self._gui.callPlugin('PluginDingTalkRobot', 'send', f'{s.name}第{times}/{self._max_restart_times}次自动重启')
                self._db.set(s.dirname, times)
                self._db.save()
                delay = 5000
            else:
                self.log_warning(f'重启次数已满：{times}/{self._max_restart_times}')
            break
        self.after(CFG.SERVER_STATE_UPDATE_INTERVAL + delay, self.check)


class PluginDingTalkRobot(FrameEx, IPlugin):
    def __init__(self, gui):
        FrameEx.__init__(self)
        IPlugin.__init__(self, '钉钉机器人')
        self._lbl = tkinter.Label(self, text=f'[{self._name}]初始化', fg='gray')
        self._lbl.grid(row=0, column=0)
        if not self.enabled:
            self._lbl['text'] = f'[{self._name}]已关闭'
            return
        self._lbl['text'] = f'[{self._name}]已开启'
        self._lbl['fg'] = 'green'
        self._tag = CFG.Get(self.section, 'tag', 'GST')
        self._token = CFG.Get(self.section, 'access_token')
        self._url = f'https://oapi.dingtalk.com/robot/send?access_token={self._token}'
        self.log_info('初始化完成')

    def send(self, msg):
        if not self.enabled:
            return
        try:
            header = {'Content-Type': 'application/json'}
            data = json.dumps({'text': {'content': f'[{self._tag}]{msg}'}, 'msgtype': 'text'})
            data = data.encode('utf-8')
            req = request.Request(url=self._url, headers=header, data=data)
            resp = request.urlopen(req)
            # print(resp.read().decode())
        except Exception as e:
            self.log_error(repr(e))


class PluginDiskFreeSpace(FrameEx, IPlugin):
    def __init__(self, gui):
        FrameEx.__init__(self)
        IPlugin.__init__(self, '磁盘剩余空间')
        self._lbl = tkinter.Label(self, text=self.name)
        self._lbl.pack()
        self.check()
        self.log_info('初始化完成')

    def check(self):
        gb = get_free_space_gb(CFG.SERVER_ROOT)
        self._lbl['text'] = f'{self._name} [{gb} GB]'
        self._lbl['fg'] = 'black' if gb > CFG.DISK_LEFT_SPACE_WARING_NUM_GB else 'red'
        self.after(CFG.SERVER_STATE_UPDATE_INTERVAL, self.check)
