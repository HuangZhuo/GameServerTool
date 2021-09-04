#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import tkinter
from tkinter import ttk
import math
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
        frame = self
        var = tkinter.BooleanVar(value=True)
        btn = tkinter.Checkbutton(frame, text=name, variable=var, onvalue=True, offvalue=False)
        btn.var = var
        btn.widgetName = name
        btn.select() if ServerManager.getServer(name).isRunning() else btn.deselect()
        btn.grid(row=idx, column=0, sticky='W')
        nextcol = counter(1)
        GUITool.createBtn('目录', lambda: self.onClick(name, 'showInExplorer'), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('配置', lambda: self.onClick(name, 'showConfigInEditor'), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('开启', lambda: self.onClick(name, 'start'), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('热更', lambda: self.onClick(name, 'hotUpdate'), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('重启', lambda: self.onClick(name, 'restart'), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('关闭', lambda: self.onClick(name, 'exit'), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('控制台', lambda: self.onClick(name, 'showConsoleWindow'), parent=frame, grid=(idx, nextcol()))

    def refresh(self, name=None):
        items = None
        if name:
            items = [GUITool.getChildByWidgetName(self, name)]
        else:
            items = GUITool.getChildsByType(self, tkinter.Checkbutton)

        for w in items:
            servername = w.widgetName
            if not STool.isServerDirExists(servername):
                # todo:delete the serveritem
                pass
            server = ServerManager.getServer(servername)
            # 修改按钮文字，颜色
            w['text'] = server.getInfo(debug=CFG.DEBUG_MODE)
            w['fg'] = 'green' if server.isRunning() else 'black'

    def onClick(self, name, func):
        ret, err = ServerManager.getServer(name).call(func)
        if not ret:
            GUITool.MessageBox(err)

    def getAll(self):
        ret = GUITool.getChildsByType(self, tkinter.Checkbutton)
        ret = list(map(lambda w: w.widgetName, ret))
        return ret

    def selectAll(self):
        for w in GUITool.getChildsByType(self, tkinter.Checkbutton):
            w.select()

    def deselectAll(self):
        for w in GUITool.getChildsByType(self, tkinter.Checkbutton):
            w.deselect()

    def getSelected(self):
        ft = lambda w: isinstance(w, tkinter.Checkbutton) and w.var.get()
        ret = GUITool.getChildsByFilter(self, ft)
        ret = list(map(lambda w: w.widgetName, ret))
        return ret

    def setSelected(self, slt=[]):
        for w in GUITool.getChildsByType(self, tkinter.Checkbutton):
            servername = w.widgetName
            w.select() if servername in slt else w.deselect()


# 多列扩展视图（兼容单列）
class ServerListViewFixedMultiCol(ServerListViewFixed):
    # 默认使用单列
    COL_NUM = max(1, CFG.GetInt('View', 'FixedMultiCol.COL_NUM', 1))
    LESS_OPTIONS = CFG.GetBool('View', 'FixedMultiCol.LESS_OPTIONS', False)
    GRID_COUNT_PER_ITEM = 4 if LESS_OPTIONS else 8

    def createServerItem(self, idx, name):
        frame = self
        row = math.floor(idx / self.COL_NUM)
        nextcol = counter((idx % self.COL_NUM) * self.GRID_COUNT_PER_ITEM)

        var = tkinter.BooleanVar(value=True)
        btn = tkinter.Checkbutton(frame, text=name, variable=var, onvalue=True, offvalue=False)
        btn.var = var
        btn.widgetName = name
        btn.select() if ServerManager.getServer(name).isRunning() else btn.deselect()
        btn.grid(row=row, column=nextcol(), sticky='W')
        GUITool.createBtn('目录', lambda: self.onClick(name, 'showInExplorer'), parent=frame, grid=(row, nextcol()))
        GUITool.createBtn('配置', lambda: self.onClick(name, 'showConfigInEditor'), parent=frame, grid=(row, nextcol()))
        if not self.LESS_OPTIONS:
            GUITool.createBtn('开启', lambda: self.onClick(name, 'start'), parent=frame, grid=(row, nextcol()))
            GUITool.createBtn('热更', lambda: self.onClick(name, 'hotUpdate'), parent=frame, grid=(row, nextcol()))
            GUITool.createBtn('重启', lambda: self.onClick(name, 'restart'), parent=frame, grid=(row, nextcol()))
            GUITool.createBtn('关闭', lambda: self.onClick(name, 'exit'), parent=frame, grid=(row, nextcol()))
        GUITool.createBtn('控制台', lambda: self.onClick(name, 'showConsoleWindow'), parent=frame, grid=(row, nextcol()))


# 多列扩展视图【计划任务】（兼容单列）
class ServerListPlanViewFixedMultiCol(ServerListViewFixed):
    # 默认使用单列
    COL_NUM = max(1, CFG.GetInt('View', 'FixedMultiCol.COL_NUM', 1))

    def createServerItem(self, idx, name):
        frame = self
        row = math.floor(idx / self.COL_NUM)
        nextcol = counter((idx % self.COL_NUM) * 3)

        var = tkinter.BooleanVar(value=True)
        btn = tkinter.Checkbutton(frame, text=name, variable=var, onvalue=True, offvalue=False)
        btn.var = var
        btn.widgetName = name
        btn.deselect()
        btn.grid(row=row, column=nextcol(), sticky='W')
        GUITool.createBtn('清 除', lambda: self.clearPlan(name), parent=frame, grid=(row, nextcol()))

    def clearPlan(self, servername):
        PlanManager.getInstance().getPlan(servername).clear()
        PlanManager.getInstance().save()
        self.refresh(servername)

    def refresh(self, name=None):
        '''刷新计划任务'''
        items = None
        if name:
            items = [GUITool.getChildByWidgetName(self, name)]
        else:
            items = GUITool.getChildsByType(self, tkinter.Checkbutton)
        for w in items:
            servername = w.widgetName
            if not STool.isServerDirExists(servername):
                # todo:delete the serveritem
                pass
            server = ServerManager.getServer(servername)
            plan = PlanManager.getInstance().getPlan(servername)
            # 修改按钮文字，颜色
            w['text'] = '{}:{}'.format(server.getCfg().title, plan)
            w['fg'] = 'black' if plan.empty else 'blue'


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
        # self._edit.bind("<Return>", lambda _: self.onExecuteClick())

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
                GUITool.MessageBox('白驹过隙，请重新设置时间')
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