#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import tkinter
import tkinter.messagebox as tkMessageBox
import tkinter.ttk as ttk
import re
import logging

from core import STool
from core import ServerManager
from common import counter
from common import GUITool
from common import INI


class IPlugin:
    def onUpdate(self):
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
        tkinter.Label(self, text='*支持输入格式: 10|10-20|10,20', fg='red').grid(row=0, column=nextcol())
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
            if ServerManager.createServer(id):
                listSuc.append(id)
            else:
                logging.error('创建服务器{}失败，终止批量创建'.format(id))
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
        tkinter.Label(self, text='*命令参考: GMCommand::DoSystemCommand', fg='red').grid(row=0, column=nextcol())
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
            if s.isRunning():
                s.execute(input)


# 服务器选择器
class PluginServerSelector(tkinter.Frame, IPlugin):
    FILTER_ALL = lambda s: True
    FILTER_NONE = lambda s: False
    FILTER_RUNNING = lambda s: ServerManager.getServer(s).isRunning()
    FILTER_CLOSED = lambda s: not ServerManager.getServer(s).isRunning()

    def __init__(self, gui):
        tkinter.Frame.__init__(self)
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
                break

            # 10-20
            m = re.search(r'^([0-9]+)-([0-9]+)$', input)
            if m:
                tmp = [int(n) for n in m.groups()]
                begin, end = tmp[0], tmp[1]
                break

            err = '不支持的输入格式'
            break

        if not begin or not end:
            err = '输入[{0}]错误：{1}'.format(input, err)
            logging.error(err)
            GUITool.MessageBox(err)
            return

        self.doSelectRange(begin, end)

    def doSelect(self, ft):
        servers = self._serverListView.getAll()
        servers = list(filter(ft, servers))
        self._serverListView.setSelected(servers)

    def doSelectRange(self, begin, end):
        self.doSelect(lambda s: STool.getServerDirID(s) in range(begin, end + 1))


class GM_INI(INI):
    def __init__(self):
        INI.__init__(self, 'gm.ini')

    def getTotalCmds(self) -> dict:
        return dict(self.GetItems('GM'))

    @property
    def ROLE_NAME(self):
        return self.Get('Data', 'ROLE_NAME')

    @ROLE_NAME.setter
    def ROLE_NAME(self, str):
        self.Set('Data', 'ROLE_NAME')


# 控制台执行命令插件
class PluginExecuteCommandEx(tkinter.Frame, IPlugin):
    def __init__(self, gui):
        tkinter.Frame.__init__(self)
        # self._gui = gui
        self._serverListView = gui.getServerListView()
        self._gmCfg = GM_INI()
        self._gmCmds = self._gmCfg.getTotalCmds()
        self.initUI()

    def initUI(self):
        nextcol = counter()
        tkinter.Label(self, text='角色名:').grid(row=0, column=nextcol(), sticky='E')
        self._editName = tkinter.Entry(self, width=24)
        self._editName.grid(row=0, column=nextcol(), sticky='W')
        self._editName.bind("<KeyRelease>", self.refresh)
        self._editName.insert(0, self._gmCfg.ROLE_NAME)

        nextcol = counter()
        tkinter.Label(self, text='参数:').grid(row=1, column=nextcol(), sticky='E')
        self._editArg0 = tkinter.Entry(self, width=24)
        self._editArg0.grid(row=1, column=nextcol(), sticky='W')
        self._editArg0.bind("<KeyRelease>", self.refresh)
        self._editArg0.insert(0, 100)

        nextcol = counter()
        tkinter.Label(self, text='命令选项:').grid(row=2, column=nextcol(), sticky='E')
        comboxCmds = ttk.Combobox(self, textvariable=tkinter.StringVar(), width=22)
        comboxCmds["values"] = tuple(self._gmCmds.keys())
        comboxCmds.current(0)
        comboxCmds.bind("<<ComboboxSelected>>", self.refresh)
        comboxCmds.grid(row=2, column=nextcol(), sticky='W')
        self._comboxCmds = comboxCmds
        GUITool.createBtn('执行', self.onExecuteClick, parent=self, grid=(2, nextcol()))

        nextcol = counter()
        tkinter.Label(self, text='命令预览:').grid(row=3, column=nextcol(), sticky='E')
        self._lblCmd = tkinter.Label(self, text='GM')
        self._lblCmd.grid(row=3, column=nextcol(), columnspan=2, sticky='W')

        GUITool.GridConfig(self, padx=5, pady=5)
        self.refresh()

    def getCmd(self):
        cmd = self._gmCmds.get(self._comboxCmds.get())
        name = self._editName.get().strip()
        arg0 = self._editArg0.get().strip()
        if len(name) > 0:
            cmd = cmd.replace('${rolename}', str(name))
        if len(arg0) > 0:
            cmd = cmd.replace('${arg0}', str(arg0))

        isComplete = cmd.find('${') < 0
        return cmd, isComplete

    def refresh(self, *args):
        cmd, complete = self.getCmd()
        self._lblCmd['text'] = cmd
        self._lblCmd['fg'] = 'green' if complete else 'red'

    def onExecuteClick(self):
        servers = self._serverListView.getAll()
        servers = map(ServerManager.getServer, servers)
        servers = list(filter(lambda s: s.isRunning(), servers))
        if len(servers) == 0:
            GUITool.MessageBox('服务器未开启')
            return
        for s in servers:
            if s.isRunning():
                cmd = self.getCmd()
                if cmd.find('${') >= 0:
                    GUITool.MessageBox('命令参数不完整')
                    return
                if s.execute(cmd):
                    s.hideConsoleWindow()
