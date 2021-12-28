#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import tkinter
from tkinter import ttk
from datetime import datetime
from abc import ABCMeta, abstractmethod

from core import STool
from core import ServerManager
from core import Plan
from core import PlanManager
from core import CFG
from core import PlanType
from common import counter
from common import GUITool
import plugin
import tkicon


class IServerListView:
    # 服务器列表视图
    __metaclass__ = ABCMeta

    @abstractmethod
    def init(self):
        raise NotImplementedError

    @abstractmethod
    def refresh(self, name=None):
        raise NotImplementedError

    @abstractmethod
    def getAll(self):
        raise NotImplementedError

    @abstractmethod
    def selectAll(self):
        raise NotImplementedError

    @abstractmethod
    def deselectAll(self):
        raise NotImplementedError

    @abstractmethod
    def getSelected(self):
        raise NotImplementedError

    @abstractmethod
    def setSelected(self, slt=[]):
        raise NotImplementedError


class ServerItem(tkinter.Frame):
    def __init__(self, master, name) -> None:
        super().__init__(master=master, name=name)
        self._name = name
        var = tkinter.BooleanVar(value=True)
        btn = tkinter.Checkbutton(self, text=name, variable=var, onvalue=True, offvalue=False)
        btn.var = var
        btn.grid(row=0, column=0, sticky='W')
        self._btn = btn

    def getName(self):
        return self._name

    def setSelected(self, st):
        self._btn.select() if st else self._btn.deselect()

    def isSelected(self):
        return self._btn.var.get()

    def refresh(self):
        pass

    def setText(self, text, color=None):
        self._btn['text'] = text
        if color:
            self._btn['fg'] = color


class ServerItemBasic(ServerItem):
    LESS_OPTIONS = CFG.GetBool('View', 'FixedMultiCol.LESS_OPTIONS', False)

    def __init__(self, master, name) -> None:
        super().__init__(master, name)
        self.setSelected(False)
        nextcol = counter(1)
        GUITool.createBtn('目录', lambda: self.onClick('showInExplorer'), parent=self, grid=(0, nextcol(), 2))
        GUITool.createBtn('配置', lambda: self.onClick('showConfigInEditor'), parent=self, grid=(0, nextcol(), 2))
        if not self.LESS_OPTIONS:
            GUITool.createBtn('开启', lambda: self.onClick('start'), parent=self, grid=(0, nextcol(), 2))
            GUITool.createBtn('热更', lambda: self.onClick('hotUpdate'), parent=self, grid=(0, nextcol(), 2))
            GUITool.createBtn('重启', lambda: self.onClick('restart'), parent=self, grid=(0, nextcol(), 2))
            GUITool.createBtn('关闭', self.onClickExit, parent=self, grid=(0, nextcol(), 2))
        GUITool.createBtn('控制台', lambda: self.onClick('showConsoleWindow'), parent=self, grid=(0, nextcol(), 2))

    def refresh(self):
        name = self.getName()
        if not STool.isServerDirExists(name):
            ServerManager.clear(name)
            self.destroy()
            return False
        server = ServerManager.getServer(name)
        text = server.getInfo(debug=CFG.DEBUG_MODE)
        fg = None
        if server.isRunning():
            fg = 'red' if server.getExceptionDump() else 'green'
        else:
            fg = 'black'
        self.setText(text, fg)
        return True

    def onClick(self, func):
        ret, err = ServerManager.getServer(self.getName()).call(func)
        if not ret:
            GUITool.MessageBox(err)

    def onClickExit(self):
        s = ServerManager.getServer(self.getName())
        ret, err = s.exit()
        if not ret and GUITool.MessageBox(f'{err}，是否强制关闭?', ask=True):
            s.exit(bForce=True)


# 单列高度无限扩展视图（原始版本）
class ServerListViewFixed(tkinter.Frame, IServerListView):
    def __init__(self, gui):
        tkinter.Frame.__init__(self, gui, bd=1, relief="sunken")
        self._gui = gui
        self.init()

    def init(self):
        for i, v in enumerate(STool.getServerDirs()):
            if GUITool.getChildByWidgetName(self, v):
                continue
            self.createServerItem(i, v)

        GUITool.GridConfig(self, padx=5, pady=5)
        self.refresh()

    def createServerItem(self, idx, name):
        ServerItemBasic(self, name).grid(row=idx, column=0, sticky='W')

    def refresh(self, name=None):
        if name:
            # 刷新单个
            item = GUITool.getChildByWidgetName(self, name)
            if item:
                item.refresh()
            return

        items = GUITool.getChildsByType(self, ServerItem)
        dirty = False
        while True:
            if len(items) < ServerManager.getCount():
                # 处理新增
                dirty = True
                break

            for w in items:
                if not w.refresh():
                    # 处理删除
                    dirty = True
                    break

            break

        if dirty:
            self.init()

    def getAll(self):
        ret = GUITool.getChildsByType(self, ServerItem)
        ret = list(map(lambda w: w.getName(), ret))
        return ret

    def selectAll(self):
        for w in GUITool.getChildsByType(self, ServerItem):
            w.setSelected(True)

    def deselectAll(self):
        for w in GUITool.getChildsByType(self, ServerItem):
            w.setSelected(False)

    def getSelected(self):
        ft = lambda w: isinstance(w, ServerItem) and w.isSelected()
        ret = GUITool.getChildsByFilter(self, ft)
        ret = list(map(lambda w: w.getName(), ret))
        return ret

    def setSelected(self, slt=[]):
        for w in GUITool.getChildsByType(self, ServerItem):
            w.setSelected(w.getName() in slt)


# 多列扩展视图（兼容单列）
class ServerListViewFixedMultiCol(ServerListViewFixed):
    # 默认使用单列
    COL_NUM = max(1, CFG.GetInt('View', 'FixedMultiCol.COL_NUM', 1))

    def createServerItem(self, idx, name):
        ServerItemBasic(self, name).grid(row=idx // self.COL_NUM, column=idx % self.COL_NUM)


class ServerItemPlan(ServerItem):
    def __init__(self, master, name) -> None:
        super().__init__(master, name)
        self.setSelected(False)
        GUITool.createBtn('清 除', lambda: self.clearPlan(), parent=self, grid=(0, 1))

    def refresh(self):
        name = self.getName()
        if not STool.isServerDirExists(name):
            PlanManager.getInstance().getPlan(name).clear()
            self.destroy()
            return
        server = ServerManager.getServer(self._name)
        plan = PlanManager.getInstance().getPlan(self._name)
        # 修改按钮文字，颜色
        text = '{}:{}'.format(server.getCfg().title, plan)
        fg = 'black' if plan.empty else 'blue'
        self.setText(text, fg)

    def clearPlan(self):
        PlanManager.getInstance().getPlan(self.getName()).clear()
        PlanManager.getInstance().save()
        self.refresh()


# 多列扩展视图【计划任务】（兼容单列）
class ServerListPlanViewFixedMultiCol(ServerListViewFixed):
    # 默认使用单列
    COL_NUM = max(1, CFG.GetInt('View', 'FixedMultiCol.COL_NUM', 1))

    def createServerItem(self, idx, name):
        ServerItemPlan(self, name).grid(row=idx // self.COL_NUM, column=idx % self.COL_NUM)


class PlanWindow(tkinter.Toplevel):
    def __init__(self, master) -> None:
        super().__init__()
        self.title("计划任务")
        self.resizable(False, False)
        tkicon.use(self.iconbitmap)

        if CFG.SERVER_STATE_UPDATE_INTERVAL > 0:
            self.after(CFG.SERVER_STATE_UPDATE_INTERVAL, self.onUpdate)

        self._frameServers = ServerListPlanViewFixedMultiCol(self)
        self._frameServers.pack(padx=5)

        # 使用选服插件方便多选
        plugin.PluginServerSelector(self).pack(padx=5, pady=5)

        frameOption = tkinter.Frame(self)
        frameOption.pack(padx=5, pady=5)
        nextcol = counter()
        tkinter.Label(frameOption, text='任务类型:').grid(row=0, column=nextcol())

        self._cmdsEnum = [v.value for v in PlanType]
        comboxCmds = ttk.Combobox(frameOption, textvariable=tkinter.StringVar(), width=8)
        comboxCmds["values"] = self._cmdsEnum
        comboxCmds.current(0)
        comboxCmds.grid(row=0, column=nextcol(), sticky='W')
        self._comboxCmds = comboxCmds

        tkinter.Label(frameOption, text='执行时间:').grid(row=0, column=nextcol())
        self._time = tkinter.Entry(frameOption, width=20)
        self._time.grid(row=0, column=nextcol())
        self._time.insert(0, datetime.now().replace(microsecond=0))
        self._time.bind("<Return>", lambda _: self.onSetClick())

        GUITool.createBtn('设 置', lambda: self.onSetClick(), parent=frameOption, grid=(0, nextcol()))

    def getServerListView(self):
        return self._frameServers

    def onSetClick(self):
        servers = self._frameServers.getSelected()
        planIndex = self._comboxCmds.current()
        if planIndex < 0:
            GUITool.MessageBox('请选择正确的任务类型')
            return
        planType = PlanType(self._cmdsEnum[planIndex])
        if len(servers) == 0:
            GUITool.MessageBox('没有选择服务器')
            return

        # 检查时间输入有效性
        time = None
        try:
            time = datetime.strptime(self._time.get(), Plan.TIME_FMT)
            if time < datetime.now():
                GUITool.MessageBox('该时间已过，请重新设置')
                return
        except ValueError:
            GUITool.MessageBox('时间格式错误')
            return

        # 为每个服务器设置任务
        for s in servers:
            plan = PlanManager.getInstance().getPlan(s)
            plan.set(planType, time)

        PlanManager.getInstance().save()

    def onUpdate(self):
        self._frameServers.refresh()
        self.after(CFG.SERVER_STATE_UPDATE_INTERVAL, self.onUpdate)
