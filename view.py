#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import tkinter
import tkinter.messagebox as tkMessageBox
import math
from abc import ABCMeta, abstractmethod

from core import STool
from core import ServerManager
from core import CFG
from common import counter
from common import GUITool


class IServerListView:
    # 服务器列表视图
    __metaclass__ = ABCMeta

    @abstractmethod
    def init():
        raise NotImplementedError

    @abstractmethod
    def refresh():
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


# 单列高度无限扩展视图（原始版本）
class ServerListViewFixed(tkinter.Frame, IServerListView):
    def __init__(self, gui):
        tkinter.Frame.__init__(self, bd=1, relief="sunken")
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
        GUITool.createBtn('目录', lambda: ServerManager.getServer(name).showInExplorer(), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('配置', lambda: self.onServerConfigClick(name), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('开启', lambda: ServerManager.getServer(name).start(), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('热更', lambda: ServerManager.getServer(name).hotUpdate(), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('重启', lambda: ServerManager.getServer(name).restart(), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('关闭', lambda: ServerManager.getServer(name).exit(), parent=frame, grid=(idx, nextcol()))
        GUITool.createBtn('控制台', lambda: ServerManager.getServer(name).showConsoleWindow(), parent=frame, grid=(idx, nextcol()))

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

    def onServerConfigClick(self, name):
        server = ServerManager.getServer(name)
        if not server.isValid():
            GUITool.MessageBox('服务器不可用')
            return
        server.getCfg().showInEditor()

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


# 多列扩展视图（兼容单列）
class ServerListViewFixedMultiCol(ServerListViewFixed):
    def createServerItem(self, idx, name):
        # 默认使用单列
        COL_NUM = CFG.GetInt('View', 'FixedMultiCol.COL_NUM', 1)
        LESS_OPTIONS = CFG.GetBool('View', 'FixedMultiCol.LESS_OPTIONS', False)
        GRID_COUNT_PER_ITEM = 4 if LESS_OPTIONS else 8

        frame = self
        row = math.floor(idx / COL_NUM)
        nextcol = counter((idx % COL_NUM) * GRID_COUNT_PER_ITEM)

        var = tkinter.BooleanVar(value=True)
        btn = tkinter.Checkbutton(frame, text=name, variable=var, onvalue=True, offvalue=False)
        btn.var = var
        btn.widgetName = name
        btn.select() if ServerManager.getServer(name).isRunning() else btn.deselect()
        btn.grid(row=row, column=nextcol(), sticky='W')
        GUITool.createBtn('目录', lambda: ServerManager.getServer(name).showInExplorer(), parent=frame, grid=(row, nextcol()))
        GUITool.createBtn('配置', lambda: self.onServerConfigClick(name), parent=frame, grid=(row, nextcol()))
        if not LESS_OPTIONS:
            GUITool.createBtn('开启', lambda: ServerManager.getServer(name).start(), parent=frame, grid=(row, nextcol()))
            GUITool.createBtn('热更', lambda: ServerManager.getServer(name).hotUpdate(), parent=frame, grid=(row, nextcol()))
            GUITool.createBtn('重启', lambda: ServerManager.getServer(name).restart(), parent=frame, grid=(row, nextcol()))
            GUITool.createBtn('关闭', lambda: ServerManager.getServer(name).exit(), parent=frame, grid=(row, nextcol()))
        GUITool.createBtn('控制台', lambda: ServerManager.getServer(name).showConsoleWindow(), parent=frame, grid=(row, nextcol()))
