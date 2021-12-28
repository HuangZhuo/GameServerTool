#!/usr/bin/python3
# -*- encoding: utf-8 -*-
"""
    传奇游戏服多服运维工具
"""

import tkinter
import os
import time
import logging, traceback

from common import counter, get_free_space_gb
from common import GUITool
from common import Profiler
from core import Action
from core import STool
from core import PlanManager
from core import ServerManager
from core import CFG
import view
import plugin
import tkicon

TITLE = '传奇游戏服管理'
VERSION = '3.4.1'


class GUI(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.title('{} v{} [{}]'.format(TITLE, VERSION, CFG.SERVER_ROOT))
        self.resizable(False, False)
        tkicon.use(self.iconbitmap)

        logging.info('Server Tools Opend!')
        self.initMenu()
        self.initUI()
        self.initPlugins()
        self._planWindow = None
        self.protocol("WM_DELETE_WINDOW", self.onXClick)

        if CFG.SERVER_STATE_UPDATE_INTERVAL > 0:
            self.after(0, self.onUpdate)

    def initMenu(self):
        mebubar = tkinter.Menu(self)
        mebubar.add_command(label="日志", command=lambda: STool.showFileInTextEditor('cmd.log'))
        mebubar.add_command(label="配置", command=lambda: STool.showFileInTextEditor('cmd.ini'))
        mebubar.add_command(label="刷新", command=self.reload)
        mebubar.add_command(label="重启", command=self.restart)
        mebubar.add_command(label="计划", command=self.plan)
        self.config(menu=mebubar)

    def initUI(self):
        self._lblState = tkinter.Label(self)
        self._lblState.pack(fill=tkinter.X)
        self._frameServers = view.ServerListViewFixedMultiCol(self)
        self._frameServers.pack(padx=5)

        plugin.PluginServerSelector(self).pack(padx=5, pady=5)

        tkinter.Frame(height=2, bd=1, relief="sunken").pack(fill=tkinter.X, padx=5)

        frame3 = tkinter.Frame()
        frame3.pack(padx=5, pady=5)
        nextcol = counter()
        GUITool.createBtn('模板目录', STool.showServerTemplateInExplorer, parent=frame3, grid=(0, nextcol()))
        GUITool.createBtn('创建', self.onCreateServerClick, parent=frame3, grid=(0, nextcol()))
        GUITool.createBtn('删除', self.onDeleteServerClick, parent=frame3, grid=(0, nextcol()))
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

    def initPlugins(self):
        # 显示扩展功能
        if CFG.GetBool('Plugin', 'EnableExtendOperations', True):
            plugin.PluginExtendOperations(self).pack(padx=5, pady=5)
        # 批量创建服务器插件
        if CFG.GetBool('Plugin', 'EnableCreateMultiServers', True):
            plugin.PluginCreateMultiServers(self).pack(padx=5, pady=5)
        # 执行命令插件
        if CFG.GetBool('Plugin', 'EnableExecuteCommand', False):
            plugin.PluginExecuteCommand(self).pack(padx=5, pady=5)
        # Web服务插件
        plugin.PluginWebService(self).pack()

    def onUpdate(self):
        PlanManager.getInstance().check()
        gb = get_free_space_gb(CFG.SERVER_ROOT)
        self._lblState['text'] = '磁盘剩余空间 [{} GB]'.format(gb)
        self._lblState['fg'] = 'black' if gb > CFG.DISK_LEFT_SPACE_WARING_NUM_GB else 'red'
        self.refreshServerList()
        self.after(CFG.SERVER_STATE_UPDATE_INTERVAL, self.onUpdate)

    def onXClick(self):
        self.destroy()
        logging.info('Server Tools Closed!')

    def initServerList(self):
        '''强制重新初始化服务器器列表
        - 创建/删除服务器时
        - 游戏服目录在资源管理器发生变更时
        '''
        self._frameServers.init()

    def refreshServerList(self, name=None):
        '''刷新列表内服务器状态'''
        self._frameServers.refresh(name)

    def reload(self):
        ServerManager.clear()
        CFG.Load()

    def restart(self):
        try:
            os.system('start {}'.format(os.sys.executable))
            os.sys.exit(0)
        except NameError as e:
            logging.info(repr(e))
            pass

    def plan(self):
        '''计划任务窗口'''
        if self._planWindow:
            self._planWindow.destroy()
        self._planWindow = view.PlanWindow(self)
        # w.grab_set()  # switch to modal window

    def onCreateServerClick(self):
        ret, err = ServerManager.createServer()
        if ret:
            self.initServerList()
        else:
            GUITool.MessageBox(err)

    def onDeleteServerClick(self):
        servers = self.getSelectedServers()
        if len(servers) == 0:
            GUITool.MessageBox('请选择需要删除的服务器')
            return
        if not GUITool.MessageBox('是否删除以下服务器目录：\n{}'.format(servers), ask=True):
            return
        for v in servers:
            ret, err = ServerManager.deleteServer(name=v)
            if not ret and err:
                GUITool.MessageBox(err)
                break
        self.initServerList()

    def onUpdateServerClick(self):
        Profiler.START()
        for v in self.getSelectedServers():
            if ServerManager.getServer(v).isRunning():
                GUITool.MessageBox('请先关闭服务器')
                Profiler.ABORT()
                return
            STool.updateServerDir(v)
        Profiler.FINISH('整包更新完成', notify=True)

    def onUpdateServerDataClick(self):
        Profiler.START()
        for v in self.getSelectedServers():
            STool.updateServerDir(v, filelist=('data', 'GameConfig.ini'))
        Profiler.FINISH('数据更新完成', notify=True)

    def onStartServerClick(self):
        for v in self.getSelectedServers():
            ret, err = ServerManager.getServer(v).start()
            if ret:
                self.refreshServerList(v)
                if CFG.SERVER_START_WAIT_TIME > 0:
                    time.sleep(CFG.SERVER_START_WAIT_TIME)
            else:
                GUITool.MessageBox(err)
                break

    def onStopServerClick(self):
        for v in self.getSelectedServers():
            ret, err = ServerManager.getServer(v).exit()
            if ret:
                self.refreshServerList(v)
            else:
                # https://stackoverflow.com/questions/16083491/make-a-tkinter-toplevel-active
                self.focus_force()
                if GUITool.MessageBox(f'{err}，是否强制关闭?', ask=True):
                    ServerManager.getServer(v).exit(bForce=True)
                else:
                    break

    def onHideServerConsoleClick(self):
        for v in self.getSelectedServers():
            if not ServerManager.getServer(v).isRunning():
                continue
            ret, err = ServerManager.getServer(v).hideConsoleWindow()
            if not ret:
                GUITool.MessageBox(err)
                break

    def onTerminateServerClick(self):
        for v in self.getSelectedServers():
            ret, err = ServerManager.getServer(v).exit(bForce=True)
            if ret:
                self.refreshServerList(v)
            else:
                GUITool.MessageBox(err)
                break

    def onHotUpdateServerClick(self):
        for v in self.getSelectedServers():
            if ServerManager.getServer(v).hotUpdate():
                self.refreshServerList(v)
            else:
                continue

    def onRestartServerClick(self):
        for v in self.getSelectedServers():
            if not ServerManager.getServer(v).isRunning():
                continue
            ret, err = ServerManager.getServer(v).restart()
            if not ret:
                self.focus_force()
                GUITool.MessageBox(err)
                break

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
        if not os.path.exists(CFG.SERVER_ROOT):
            GUITool.MessageBox('服务器根目录不存在')
            return
        if not os.path.exists(CFG.SERVER_TEMPLATE):
            GUITool.MessageBox('服务器模板路径不存在')
            return
        GUI().mainloop()
    except:
        logging.error(traceback.format_exc())
        GUITool.MessageBox(traceback.format_exc())
        return


if __name__ == '__main__':
    main()
