#!/usr/bin/python3
# -*- encoding: utf-8 -*-
"""
传奇游戏服多服运维工具
"""

import logging
import os
import tkinter
import tkinter.ttk
import traceback
from logging.handlers import RotatingFileHandler

import plugin
import tkicon
import view
from common import GUITool, counter
from core import CFG, Action, PlanManager, ServerManager, STool, TaskExecutor

TITLE = '传奇游戏服管理'
VERSION = '3.7.2'


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
        menubar = tkinter.Menu(self)
        menubar.add_command(label="日志", command=lambda: STool.showFileInTextEditor('cmd.log'))
        menubar.add_command(label="配置", command=lambda: STool.showFileInTextEditor('cmd.ini'))
        menubar.add_command(label="刷新", command=self.reload)
        menubar.add_command(label="重启", command=self.restart)
        menubar.add_command(label="计划", command=self.plan)
        self.config(menu=menubar)

    def initUI(self):
        plugin.PluginDiskFreeSpace(self).pack()
        self._frameServers = view.ServerListViewFixedMultiCol(self)
        self._frameServers.pack(padx=5)

        plugin.PluginServerSelector(self).pack(padx=5, pady=5)

        self._bar = tkinter.ttk.Progressbar(mode='determinate', style="fp.Horizontal.TProgressbar")
        self._bar.pack(fill=tkinter.X, padx=5)

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
        GUITool.createBtn('强制关闭', self.onTerminateServerClick, parent=frame3, grid=(0, nextcol()))['fg'] = 'gray'
        if CFG.DEBUG_MODE:
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

        self._plugins = {
            'PluginWebService': plugin.PluginWebService(self).pack(side=tkinter.LEFT, padx=10),  # Web服务插件
            'PluginServerMgr': plugin.PluginServerMgr(self).pack(side=tkinter.LEFT, padx=10),  # 自动开服插件
            'PluginServerMonitor': plugin.PluginServerMonitor(self).pack(side=tkinter.LEFT, padx=10),
            'PluginDingTalkRobot': plugin.PluginDingTalkRobot(self).pack(side=tkinter.LEFT, padx=10),
        }

    def callPlugin(self, plugin_name, func_name, *args):
        plugin = self._plugins[plugin_name] if plugin_name in self._plugins else None
        if not plugin or not plugin.enabled:
            return
        api = getattr(plugin, func_name)
        if api: return api(*args)

    def onUpdate(self):
        PlanManager.getInstance().check()
        TaskExecutor.run_if_idle(self.refreshServerList)
        self.after(CFG.SERVER_STATE_UPDATE_INTERVAL, self.onUpdate)

    def onXClick(self):
        self.destroy()
        logging.info('Server Tools Closed!')

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
        if not ret:
            GUITool.MessageBox(err)

    def onDeleteServerClick(self):
        servers = self.getSelectedServers()
        if len(servers) == 0:
            GUITool.MessageBox('请选择需要删除的服务器')
            return
        if not GUITool.MessageBox('是否删除以下服务器目录：\n{}'.format(servers), ask=True):
            return

        def _do(server_name):
            return ServerManager.deleteServer(name=server_name)

        if TaskExecutor.BUSY == TaskExecutor.submit(_do, self.getSelectedServers(), self.onProgress):
            GUITool.MessageBox('请等待当前任务完成')

    def onUpdateServerClick(self):
        def _do(server_name):
            if ServerManager.getServer(server_name).isRunning():
                return False
            return STool.updateServerDir(server_name)

        if TaskExecutor.BUSY == TaskExecutor.submit(_do, self.getSelectedServers(), self.onProgress, notify='整包更新完成'):
            GUITool.MessageBox('请等待当前任务完成')

    def onUpdateServerDataClick(self):
        def _do(server_name):
            return STool.updateServerDir(server_name, ('data', 'GameConfig.ini'))

        if TaskExecutor.BUSY == TaskExecutor.submit(_do, self.getSelectedServers(), self.onProgress, notify='数据更新完成'):
            GUITool.MessageBox('请等待当前任务完成')

    def onStartServerClick(self):
        def _do(s):
            server = ServerManager.getServer(s)
            ret, err = server.start()
            if ret:
                self.refreshServerList(name=server.dirname)
            else:
                GUITool.MessageBox(err)
            return ret

        TaskExecutor.submit(
            _do,
            self.getSelectedServers(),
            self.onProgress,
            max_workers=1,
            work_delay=CFG.SERVER_START_WAIT_TIME,
        )

    def onStopServerClick(self):
        def _do(s):
            server = ServerManager.getServer(s)
            ret, err = server.exit()
            if ret:
                self.refreshServerList(name=server.dirname)
                return True
            else:
                # https://stackoverflow.com/questions/16083491/make-a-tkinter-toplevel-active
                self.focus_force()
                if GUITool.MessageBox(f'{err}，是否强制关闭?', ask=True):
                    ret, err = ServerManager.getServer(s).exit(bForce=True)
                    if ret: self.refreshServerList(name=server.dirname)
                    else: GUITool.MessageBox(err)
                    return ret
                else:
                    return False

        TaskExecutor.submit(
            _do,
            self.getSelectedServers(),
            self.onProgress,
            max_workers=1,
            work_delay=CFG.SERVER_START_WAIT_TIME,
        )

    def onHideServerConsoleClick(self):
        for v in self.getSelectedServers():
            if not ServerManager.getServer(v).isRunning():
                continue
            ret, err = ServerManager.getServer(v).hideConsoleWindow()
            if not ret:
                GUITool.MessageBox(err)
                break

    def onTerminateServerClick(self):
        if not GUITool.MessageBox('是否强制关闭所选服务器？', ask=True): return

        TaskExecutor.submit(
            lambda s: ServerManager.getServer(s).exit(bForce=True),
            self.getSelectedServers(),
            self.onProgress,
        )

    def onHotUpdateServerClick(self):
        TaskExecutor.submit(
            lambda s: ServerManager.getServer(s).hotUpdate(),
            self.getSelectedServers(),
            self.onProgress,
        )

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

    def onProgress(self, cur, total=100):
        self._bar['value'] = cur
        self._bar['maximum'] = total

    def getSelectedServers(self):
        return self._frameServers.getSelected()

    def getServerListView(self) -> view.IServerListView:
        return self._frameServers


def initLogger():
    handler = RotatingFileHandler(
        filename='cmd.log',
        maxBytes=2 * 1024 * 1024,
        backupCount=1,
    )
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[handler],
    )


def main():
    initLogger()
    try:
        if not os.path.exists(CFG.SERVER_ROOT):
            GUITool.MessageBox('服务器根目录不存在')
            return
        if not os.path.exists(CFG.SERVER_TEMPLATE):
            GUITool.MessageBox('服务器模板路径不存在')
            return
        GUI().mainloop()
    except SystemExit:
        return
    except:
        logging.error(traceback.format_exc())
        GUITool.MessageBox(traceback.format_exc())
        return


if __name__ == '__main__':
    main()
