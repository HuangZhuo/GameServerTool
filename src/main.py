#!/usr/bin/python3
# -*- encoding: utf-8 -*-
"""
    传奇游戏服多服运维工具
"""

import tkinter
import tkinter.messagebox as tkMessageBox
import os
import time
import logging, traceback

from common import counter
from common import GUITool
from common import Profiler
from core import Action
from core import STool
from core import ServerManager
from core import CFG
import view
import plugin

VERSION_INFO = '3.2'


class GUI:
    def __init__(self, title):
        self._title = title
        self._tk = tkinter.Tk()
        self._tk.title('{} {}'.format(self._title, VERSION_INFO))
        self._tk.resizable(False, False)
        logging.info('Server Tools Opend!')
        self.initMenu()
        self.initUI()
        self._tk.protocol("WM_DELETE_WINDOW", self.onXClick)
        if CFG.SERVER_STATE_UPDATE_INTERVAL > 0:
            self._tk.after(CFG.SERVER_STATE_UPDATE_INTERVAL, self.onUpdate)
        self._tk.mainloop()

    def initUI(self):
        gui = self._tk

        tkinter.Label(gui, text='服务器列表 [%s]' % (CFG.SERVER_ROOT)).pack(fill=tkinter.X)
        self._frameServers = view.ServerListViewFixedMultiCol(self)
        self._frameServers.pack(padx=5)

        plugin.PluginServerSelector(self).pack(padx=5, pady=5)

        tkinter.Frame(height=2, bd=1, relief="sunken").pack(fill=tkinter.X, padx=5)

        frame3 = tkinter.Frame()
        frame3.pack(padx=5, pady=5)
        nextcol = counter()
        GUITool.createBtn('模板目录', STool.showServerTemplateInExplorer, parent=frame3, grid=(0, nextcol()))
        GUITool.createBtn('创建', self.onCreateServerClick, parent=frame3, grid=(0, nextcol()))
        GUITool.createBtn('整包更新', self.onUpdateServerClick, parent=frame3, grid=(0, nextcol()))
        GUITool.createBtn('数据更新', self.onUpdateServerDataClick, parent=frame3, grid=(0, nextcol()))
        GUITool.createBtn('开启', self.onStartServerClick, parent=frame3, grid=(0, nextcol()))
        GUITool.createBtn('热更', self.onHotUpdateServerClick, parent=frame3, grid=(0, nextcol()))
        GUITool.createBtn('重启', self.onRestartServerClick, parent=frame3, grid=(0, nextcol()))
        GUITool.createBtn('关闭', self.onStopServerClick, parent=frame3, grid=(0, nextcol()))
        GUITool.createBtn('隐藏控制台', self.onHideServerConsoleClick, parent=frame3, grid=(0, nextcol()))
        if CFG.DEBUG_MODE:
            GUITool.createBtn('终止', self.onTerminateServerClick, parent=frame3, grid=(0, nextcol()))['bg'] = 'red'
            GUITool.createBtn("测试", self.onTestClick, parent=frame3, grid=(0, nextcol()))['bg'] = 'yellow'
        GUITool.GridConfig(frame3, padx=5)

        # 显示扩展功能
        if CFG.GetBool('Plugin', 'EnableExtendOperations', True):
            plugin.PluginExtendOperations(self).pack(padx=5, pady=5)
        # 批量创建服务器插件
        if CFG.GetBool('Plugin', 'EnableCreateMultiServers', True):
            plugin.PluginCreateMultiServers(self).pack(padx=5, pady=5)
        # 执行命令插件
        if CFG.GetBool('Plugin', 'EnableExecuteCommand', False):
            plugin.PluginExecuteCommand(self).pack(padx=5, pady=5)

    def onUpdate(self):
        self.refreshServerList()
        self._tk.after(CFG.SERVER_STATE_UPDATE_INTERVAL, self.onUpdate)

    def onXClick(self):
        self._tk.destroy()
        logging.info('Server Tools Closed!')

    def initServerList(self):
        self._frameServers.init()

    def initMenu(self):
        mebubar = tkinter.Menu(self._tk)
        mebubar.add_command(label="日志", command=lambda: STool.showFileInTextEditor('cmd.log'))
        mebubar.add_command(label="配置", command=lambda: STool.showFileInTextEditor('cmd.ini'))
        mebubar.add_command(label="刷新", command=self.reload)
        mebubar.add_command(label="重启", command=self.restart)
        self._tk.config(menu=mebubar)

    def refreshServerList(self, name=None):
        self._frameServers.refresh(name)

    def reload(self):
        ServerManager.clear()
        CFG.Load()

    def restart(self):
        try:
            os.system('start {}'.format(sys.executable))
            os.sys.exit(0)
        except NameError as e:
            logging.info(repr(e))
            pass

    def onCreateServerClick(self):
        if ServerManager.createServer():
            self.initServerList()

    def onUpdateServerClick(self):
        Profiler.START()
        for v in self.getSelectedServers():
            server = ServerManager.getServer(v)
            if server.isRunning():
                GUITool.MessageBox('请先关闭服务器')
                Profiler.ABORT()
                return
            STool.updateServerDir(v)
        Profiler.FINISH('整包更新完成', notify=True)

    def onUpdateServerDataClick(self):
        Profiler.START()
        for v in self.getSelectedServers():
            server = ServerManager.getServer(v)
            STool.updateServerDir(v, filelist=('data', 'GameConfig.ini'))
        Profiler.FINISH('数据更新完成', notify=True)

    def onStartServerClick(self):
        for v in self.getSelectedServers():
            if ServerManager.getServer(v).start():
                self.refreshServerList(v)
                if CFG.SERVER_START_WAIT_TIME > 0:
                    time.sleep(CFG.SERVER_START_WAIT_TIME)

    def onStopServerClick(self):
        for v in self.getSelectedServers():
            if ServerManager.getServer(v).exit():
                self.refreshServerList(v)

    def onHideServerConsoleClick(self):
        for v in self.getSelectedServers():
            if ServerManager.getServer(v).isRunning():
                ServerManager.getServer(v).hideConsoleWindow()

    def onTerminateServerClick(self):
        for v in self.getSelectedServers():
            if ServerManager.getServer(v).exit(bForce=True):
                self.refreshServerList(v)

    def onHotUpdateServerClick(self):
        for v in self.getSelectedServers():
            if ServerManager.getServer(v).hotUpdate():
                self.refreshServerList(v)
            else:
                continue

    def onRestartServerClick(self):
        for v in self.getSelectedServers():
            if ServerManager.getServer(v).isRunning():
                ServerManager.getServer(v).restart()

    def onTestClick(self):
        Action('Test').execute(7, 8, 9)
        pass

    def getSelectedServers(self):
        return self._frameServers.getSelected()

    def getServerListView(self) -> view.IServerListView:
        return self._frameServers


def main():
    logging.basicConfig(filename='cmd.log', filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        assert os.path.exists(CFG.SERVER_ROOT), "服务器根目录不存在"
        assert os.path.exists(CFG.SERVER_TEMPLATE), "服务器模板路径不存在"
        GUI("Server Tools")
    except:
        print(traceback.format_exc())
        logging.error(traceback.format_exc())


if __name__ == '__main__':
    main()
