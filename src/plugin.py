#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import tkinter
import re
import logging
from webserver import WebServer

from core import STool
from core import ServerManager
from common import counter
from common import GUITool


class IPlugin:
    pass


# 批量创建服务器插件
class PluginCreateMultiServers(tkinter.Frame, IPlugin):
    def __init__(self, gui):
        tkinter.Frame.__init__(self)
        self._gui = gui
        self.initUI()

    def initUI(self):
        nextcol = counter()
        tkinter.Label(self, text='批量创建:').grid(row=0, column=nextcol())
        self._edit = tkinter.Entry(self, width=16)
        self._edit.grid(row=0, column=nextcol())
        self._edit.bind("<Return>", lambda _: self.onCreateMultiServerClick())
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
class PluginExecuteCommand(tkinter.Frame, IPlugin):
    def __init__(self, gui):
        tkinter.Frame.__init__(self)
        self._gui = gui
        self.initUI()

    def initUI(self):
        nextcol = counter()
        tkinter.Label(self, text='输入命令:').grid(row=0, column=nextcol())
        self._edit = tkinter.Entry(self, width=16)
        self._edit.grid(row=0, column=nextcol())
        self._edit.bind("<Return>", lambda _: self.onExecuteClick())
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
class PluginServerSelector(tkinter.Frame, IPlugin):
    FILTER_ALL = lambda s: True
    FILTER_NONE = lambda s: False
    FILTER_RUNNING = lambda s: ServerManager.getServer(s).isRunning()
    FILTER_CLOSED = lambda s: not ServerManager.getServer(s).isRunning()

    def __init__(self, gui):
        tkinter.Frame.__init__(self, gui)
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
        self._edit.bind("<Return>", lambda _: self.onExecuteClick())
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
class PluginExtendOperations(tkinter.Frame, IPlugin):
    def __init__(self, gui):
        tkinter.Frame.__init__(self)
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


class PluginWebService(tkinter.Frame, IPlugin):
    def __init__(self, gui):
        tkinter.Frame.__init__(self)
        self._gui = gui
        self._lbl = tkinter.Label(self, text='WebService准备启动')
        self._lbl.grid(row=0, column=0)
        self._service = None
        self.after(2000, self.initWebServer)

    def initWebServer(self):
        self._service = WebServer().start()
        self.after(2000, self.checkWebServer)

    def checkWebServer(self):
        if not self._service.running:
            self._lbl['text'] = 'WebService停止运行:{}'.format(self._service.next_error)
            self._lbl['fg'] = 'red'
            return
        else:
            self._lbl['text'] = 'WebService运行中'
            cmd = self._service.next_cmd
            if cmd:
                cmd, id = cmd
                server = STool.getServerDirName(id)
                server = ServerManager.getServer(server)
                server.call(cmd)
            self.after(1000, self.checkWebServer)
