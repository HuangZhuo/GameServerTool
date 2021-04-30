#!/usr/bin/python3
# -*- encoding: utf-8 -*-
"""
    基于控制台窗口的服务器管理
    ref: https://cn.bing.com/search?q=python+uiautomation
    ref：https://github.com/yinkaisheng/Python-UIAutomation-for-Windows
"""

try:
    import Tkinter as tkinter
    import tkMessageBox
except ImportError:
    import tkinter
    import tkinter.messagebox as tkMessageBox
# import fcntl
import os
import subprocess, psutil
import time
import configparser
import shutil
import uiautomation
import logging, traceback
from abc import ABCMeta, abstractmethod
import plugin


class INI:
    def __init__(self, filename='cmd.ini'):
        self.__filename = filename
        self.__parser = configparser.ConfigParser()
        self.__loaded = False
        self.Load()

    @property
    def filename(self):
        return self.__filename

    def Load(self):
        if self.__loaded:
            logging.info('配置文件[%s]重新读取', self.__filename)
        try:
            self.__parser.read(self.__filename)
            self.__loaded = True
        except Exception as e:
            GUITool.MessageBox('配置文件[%s]读取出错' % (self.__filename))
            raise e

    def Save(self):
        with open(self.__filename, 'w+') as f:
            self.__parser.write(f)

    def SaveOptionIfNotExist(self, section, key, fallback):
        if not self.__parser.has_option(section, key):
            self.__parser.set(section, key, str(fallback))
            self.Save()

    def Set(self, section, key, value):
        return self.__parser.set(section, key, value)

    def Get(self, section, key, fallback=''):
        return self.__parser.get(section, key, fallback=fallback)

    def GetInt(self, section, key, fallback=-1):
        return self.__parser.getint(section, key, fallback=fallback)

    def GetFloat(self, section, key, fallback=-1):
        return self.__parser.getfloat(section, key, fallback=fallback)

    def GetBool(self, section, key, fallback=False):
        return self.__parser.getboolean(section, key, fallback=fallback)

    def GetItems(self, section):
        # 返回(k,v)元组列表
        return self.__parser.items(section) if self.__parser.has_section(section) else []


class CMD_INI(INI):
    @property
    def SERVER_ROOT(self):
        # 所有服务器的根目录
        return os.path.abspath(self.Get('CMD', 'SERVER_ROOT', 'd:/LegendGame/game/runtime'))

    @property
    def SERVER_TEMPLATE(self):
        # 服务器模板
        return os.path.abspath(self.Get('CMD', 'SERVER_TEMPLATE', 'd:/LegendGame/game/runtime/gameserver'))

    @property
    def TEXT_EDITOR_PATH(self):
        return self.Get('CMD', 'TEXT_EDITOR_PATH', 'C:/Program Files (x86)/Notepad++/notepad++.exe')

    @property
    def SERVER_START_WAIT_TIME(self):
        # 服务器开启后等待时间（避免所有服务器同一时刻开启）
        return self.GetInt('CMD', 'SERVER_START_WAIT_TIME', 1)

    @property
    def SERVER_EXECUTE_CMD_WAIT_TIME(self):
        # 服务器执行命令等待间隔
        return self.GetInt('CMD', 'SERVER_EXECUTE_CMD_WAIT_TIME', 1)

    @property
    def SERVER_EXIT_TIMEOUT(self):
        # 服务器关闭检查超时
        return self.GetInt('CMD', 'SERVER_EXIT_TIMEOUT', 10)

    @property
    def SERVER_EXIT_CHECK_INTERVAL(self):
        # 服务器关闭检查时间间隔
        return self.GetFloat('CMD', 'SERVER_EXIT_CHECK_INTERVAL', 0.1)

    @property
    def SERVER_START_TIMEOUT(self):
        # 服务器开启检查超时
        return self.GetInt('CMD', 'SERVER_START_TIMEOUT', 5)

    @property
    def SERVER_START_CHECK_INTERVAL(self):
        # 服务器开启检查时间间隔
        return self.GetFloat('CMD', 'SERVER_START_CHECK_INTERVAL', 0.1)

    @property
    def SERVER_HIDE_ON_START(self):
        # 服务器开启时最小化
        return self.GetBool('CMD', 'SERVER_HIDE_ON_START', True)

    @property
    def SERVER_STATE_UPDATE_INTERVAL(self):
        # 服务器状态自动刷新时间间隔 单位:ms
        return self.GetInt('CMD', 'SERVER_STATE_UPDATE_INTERVAL', 1000)

    @property
    def DEBUG_MODE(self):
        # DEBUG MODE
        return self.GetBool('CMD', 'DEBUG_MODE', False)

    @property
    def FIND_WINDOW_COMPATIBLE_MODE(self):
        # 兼容模式查找窗口
        return self.GetBool('CMD', 'FIND_WINDOW_COMPATIBLE_MODE', True)

    @property
    def COMBINE_SERVER_WINDOWS_IN_TASKBAR(self):
        # 是否在任务栏合并服务器窗口（只支持兼容模式查找）
        return self.GetBool('CMD', 'COMBINE_SERVER_WINDOWS_IN_TASKBAR', True)

    def GetAction(self, key):
        return self.Get('Actions', key, None)


CFG = CMD_INI('cmd.ini')


class GUI:
    def __init__(self, title):
        self._title = title
        self._tk = tkinter.Tk()
        self._tk.title(self._title)
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
        frame = tkinter.Frame(bd=1, relief="sunken")
        frame.pack(padx=5)
        self._frameServers = frame
        self.initServerList()

        frame2 = tkinter.Frame()
        frame2.pack(padx=5, pady=5)
        self.createBtn('全选', lambda: self.setSelectAllServerItems(True), parent=frame2, grid=(0, 0))
        self.createBtn('全不选', lambda: self.setSelectAllServerItems(False), parent=frame2, grid=(0, 1))
        GUITool.GridConfig(frame2, padx=5)

        tkinter.Frame(height=2, bd=1, relief="sunken").pack(fill=tkinter.X, padx=5)

        frame3 = tkinter.Frame()
        frame3.pack(padx=5, pady=5)
        nextrow = counter()
        self.createBtn('模板目录', STool.showServerTemplateInExplorer, parent=frame3, grid=(0, nextrow()))
        self.createBtn('创建', self.onCreateServerClick, parent=frame3, grid=(0, nextrow()))
        self.createBtn('整包更新', self.onUpdateServerClick, parent=frame3, grid=(0, nextrow()))
        self.createBtn('数据更新', self.onUpdateServerDataClick, parent=frame3, grid=(0, nextrow()))
        self.createBtn('开启', self.onStartServerClick, parent=frame3, grid=(0, nextrow()))
        self.createBtn('热更', self.onHotUpdateServerClick, parent=frame3, grid=(0, nextrow()))
        self.createBtn('重启', self.onRestartServerClick, parent=frame3, grid=(0, nextrow()))
        self.createBtn('关闭', self.onStopServerClick, parent=frame3, grid=(0, nextrow()))
        self.createBtn('隐藏控制台', self.onHideServerConsoleClick, parent=frame3, grid=(0, nextrow()))
        if CFG.DEBUG_MODE:
            self.createBtn('终止', self.onTerminateServerClick, parent=frame3, grid=(0, nextrow()))['bg'] = 'red'
            tkinter.Frame(height=2, bd=1, relief="sunken").pack(fill=tkinter.X, padx=5)
            self._btnTest = self.createBtn("测试", self.onTestClick, pack=True)
        GUITool.GridConfig(frame3, padx=5)

        # 批量创建服务器插件
        plugin.PluginCreateMultiServers(self).pack(padx=5, pady=5)

    def onUpdate(self):
        self.refreshServerList()
        self._tk.after(CFG.SERVER_STATE_UPDATE_INTERVAL, self.onUpdate)

    def onXClick(self):
        self._tk.destroy()
        logging.info('Server Tools Closed!')

    def setSelectAllServerItems(self, st):
        for w in GUITool.getChildsByType(self._frameServers, tkinter.Checkbutton):
            w.select() if st else w.deselect()

    def initServerList(self):
        for i, v in enumerate(STool.getServerDirs()):
            if GUITool.getChildByWidgetName(self._frameServers, v):
                continue
            self.createServerItem(i, v)

        GUITool.GridConfig(self._frameServers, padx=5, pady=5)
        self.refreshServerList()

    def initMenu(self):
        mebubar = tkinter.Menu(self._tk)
        mebubar.add_command(label="日志", command=lambda: STool.showFileInTextEditor('cmd.log'))
        mebubar.add_command(label="配置", command=lambda: STool.showFileInTextEditor('cmd.ini'))
        mebubar.add_command(label="刷新", command=self.reload)
        self._tk.config(menu=mebubar)

    def refreshServerList(self, name=None):
        items = None
        if name:
            items = [GUITool.getChildByWidgetName(self._frameServers, name)]
        else:
            items = GUITool.getChildsByType(self._frameServers, tkinter.Checkbutton)

        for w in items:
            servername = w.widgetName
            if not STool.isServerDirExists(servername):
                # todo:delete the serveritem
                pass
            server = ServerManager.getServer(servername)
            # 修改按钮文字，颜色
            w['text'] = server.getInfo(debug=CFG.DEBUG_MODE)
            w['fg'] = 'green' if server.isRunning() else 'black'

    def reload(self):
        ServerManager.clear()
        CFG.Load()

    def createBtn(self, text, func, parent=None, pack=None, grid=None):
        parent = parent if parent else self._tk
        return GUITool.createBtn(text, func, parent, pack, grid)

    def createServerItem(self, idx, name):
        frame = self._frameServers
        var = tkinter.BooleanVar(value=True)
        btn = tkinter.Checkbutton(frame, text=name, variable=var, onvalue=True, offvalue=False)
        btn.var = var
        btn.widgetName = name
        btn.select() if ServerManager.getServer(name).isRunning() else btn.deselect()
        btn.grid(row=idx, column=0, sticky='W')
        nextrow = counter(1)
        self.createBtn('目录',
                       lambda: ServerManager.getServer(name).showInExplorer(),
                       parent=frame,
                       grid=(idx, nextrow()))
        self.createBtn('配置', lambda: self.onServerConfigClick(name), parent=frame, grid=(idx, nextrow()))
        self.createBtn('开启', lambda: ServerManager.getServer(name).start(), parent=frame, grid=(idx, nextrow()))
        self.createBtn('热更', lambda: ServerManager.getServer(name).hotUpdate(), parent=frame, grid=(idx, nextrow()))
        self.createBtn('重启', lambda: ServerManager.getServer(name).restart(), parent=frame, grid=(idx, nextrow()))
        self.createBtn('关闭', lambda: ServerManager.getServer(name).exit(), parent=frame, grid=(idx, nextrow()))
        self.createBtn('控制台',
                       lambda: ServerManager.getServer(name).showConsoleWindow(),
                       parent=frame,
                       grid=(idx, nextrow()))

        return btn

    def onServerConfigClick(self, name):
        server = ServerManager.getServer(name)
        if not server.isValid():
            GUITool.MessageBox('服务器不可用')
            return
        server.getCfg().showInEditor()

    def onCreateServerClick(self):
        if ServerManager.createServer():
            self.initServerList()

    def onUpdateServerClick(self):
        for v in self.getSelectedServers():
            server = ServerManager.getServer(v)
            if server.isRunning():
                GUITool.MessageBox('请先关闭服务器')
                return
            STool.updateServerDir(v)

    def onUpdateServerDataClick(self):
        for v in self.getSelectedServers():
            server = ServerManager.getServer(v)
            STool.updateServerDir(v, filelist=('data', 'GameConfig.ini'))

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
            ServerManager.getServer(v).restart()

    def onTestClick(self):
        Action('Test').execute(7, 8, 9)
        pass

    def getSelectedServers(self):
        ft = lambda w: isinstance(w, tkinter.Checkbutton) and w.var.get()
        ret = GUITool.getChildsByFilter(self._frameServers, ft)
        ret = list(map(lambda w: w.widgetName, ret))
        return ret


class GUITool:
    @staticmethod
    def getChildByWidgetName(root, widgetName):
        for k, v in root.children.items():
            if v.widgetName == widgetName:
                return v
        return None

    @staticmethod
    def getChildsByType(root, TYPE):
        ret = root.children.values()
        return list(filter(lambda w: isinstance(w, TYPE), ret))

    @staticmethod
    def getChildsByFilter(root, _filter):
        return list(filter(_filter, root.children.values()))

    @staticmethod
    def MessageBox(str, title='提示', ask=False):
        if ask:
            return tkMessageBox.askokcancel(title=title, message=str)
        else:
            return tkMessageBox.showinfo(title=title, message=str)

    @staticmethod
    def GridConfig(root, padx=5, pady=0):
        cols, rows = root.grid_size()
        for col in range(cols):
            root.grid_columnconfigure(col, pad=padx)
        for row in range(rows):
            root.grid_rowconfigure(row, pad=pady)
        return root

    @staticmethod
    def createBtn(text, func, parent=None, pack=None, grid=None):
        btn = tkinter.Button(parent, text=text, command=func, padx=5)
        if pack:
            btn.pack()
        elif grid:
            btn.grid(row=grid[0], column=grid[1])
        return btn


class STool:
    @staticmethod
    def getServerDirs():
        # 识别服务器根目录，返回服务器目录列表
        ret = os.listdir(CFG.SERVER_ROOT)
        ret = list(filter(STool.isServerDir, ret))
        # miao! python3移除了cmp参数
        ret.sort(key=STool.getServerDirID)
        return ret

    @staticmethod
    def isServerDir(dirname):
        # 判断是否是服务器目录，这里使用 os.path.abspath无法正常判断- -
        # dirname = os.path.abspath(dirname)
        dirname = os.path.join(CFG.SERVER_ROOT, dirname)
        # print(dirname, os.path.isdir(dirname), os.path.isfile(dirname))
        return os.path.isdir(dirname) and STool.getServerDirID(dirname) >= 0

    @staticmethod
    def isServerDirExists(dirname):
        # 服务器目录是否存在
        dirname = os.path.join(CFG.SERVER_ROOT, dirname)
        return os.path.exists(dirname)

    @staticmethod
    def getServerDirID(dirname):
        # 获取服务器路径中的数字ID
        import re
        m = re.search(r'^gameserver([0-9]+)$', os.path.basename(dirname))
        return int(m.group(1)) if m else -1

    @staticmethod
    def getNextServerDirID():
        # 返回下一个可用服务器目录id索引，规则：自增1
        tmp = STool.getServerDirs()
        if 0 == len(tmp):
            return 1
        idx = max(map(STool.getServerDirID, tmp))
        return idx + 1

    @staticmethod
    def createServerDir(id):
        # 根据服务器模板创建一个新服（目录拷贝）
        dirname = "gameserver%d" % (id)
        if STool.isServerDirExists(dirname):
            logging.error('创建服务器目录[%s]失败，目录已存在', dirname)
            return False, dirname
        shutil.copytree(CFG.SERVER_TEMPLATE,
                        os.path.join(CFG.SERVER_ROOT, dirname),
                        ignore=shutil.ignore_patterns('*.log'))
        logging.info('创建服务器目录[%s]成功', dirname)
        return True, dirname

    @staticmethod
    def updateServerDir(name, filelist=('data', 'GameServer.exe', 'GameConfig.ini')):
        # 根据服务器模板更新服务器
        dirname = os.path.join(CFG.SERVER_ROOT, name)
        # shutil.copytree(CFG.SERVER_TEMPLATE, dirname, ignore=shutil.ignore_patterns('*.log','GameServer.ini'))
        for f in filelist:
            try:
                src = os.path.join(CFG.SERVER_TEMPLATE, f)
                if os.path.isfile(src):
                    shutil.copy(src, dirname)
                elif os.path.isdir(src):
                    shutil.rmtree(os.path.join(dirname, f), ignore_errors=True)
                    shutil.copytree(src, os.path.join(dirname, f))
            except FileNotFoundError as e:
                pass
        logging.info('更新服务器目录[%s]成功，文件[%s]', name, filelist)

    @staticmethod
    def getServerExePath(dirname):
        # 获取服务器EXE完整路径
        dirname = os.path.join(dirname, "GameServer.exe")
        return os.path.normpath(dirname)

    def showServerTemplateInExplorer():
        subprocess.Popen('explorer %s' % (CFG.SERVER_TEMPLATE))

    def showFileInTextEditor(filename, wait=False):
        exe = CFG.TEXT_EDITOR_PATH if os.path.exists(CFG.TEXT_EDITOR_PATH) else 'notepad'
        proc = subprocess.Popen('%s %s' % (exe, filename))
        if wait:
            proc.wait()


def get_hwnds_for_pid(pid):
    '''
    通过PID查询句柄ID
    ref: https://blog.csdn.net/qq_40134903/article/details/88297476
    '''
    import win32gui
    import win32process

    def callback(hwnd, hwnds):
        # if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
        if found_pid == pid:
            hwnds.append(hwnd)

    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds[0] if len(hwnds) > 0 else 0


def counter(start=0):
    # 简单自增计数器
    idx = [start - 1]

    def _plus():
        idx[0] += 1
        return idx[0]

    return _plus


# 基于控制台的服务器接口
class IServer():
    __metaclass__ = ABCMeta

    @abstractmethod
    def start(self):
        # 开服
        raise NotImplementedError

    @abstractmethod
    def exit(self):
        # 安全关闭服务器
        raise NotImplementedError

    @abstractmethod
    def execute(self, cmd):
        # 服务器控制台执行命令
        raise NotImplementedError


class ServerManager:
    __servers = dict()

    @abstractmethod
    def createServer(id=None):
        id = id if id is not None else STool.getNextServerDirID()
        suc, dirname = STool.createServerDir(id)
        if not suc:
            GUITool.MessageBox('创建服务器目录失败，检查目录{}是否存在'.format(dirname))
            return None
        server = ServerV3(dirname, bCreateNew=True)
        ServerManager.__servers[dirname] = server
        return server

    @abstractmethod
    def getServer(name):
        if not ServerManager.__servers.get(name):
            ServerManager.__servers[name] = ServerV3(name)
        return ServerManager.__servers[name]

    @abstractmethod
    def isDBServerRunning(port):
        # todo:根据端口监听判断数据库是否开启
        pass

    @staticmethod
    def clear():
        logging.info('强制刷新：删除所有服务器对象')
        ServerManager.__servers.clear()


class ServerV3(IServer):
    def __init__(self, dirname, bCreateNew=False):
        logging.info('创建服务器对象:%s(bCreateNew=%s)', dirname, str(bCreateNew))
        # 服务器目录名
        self._dirname = dirname
        # 服务器完整路径
        self._serverPath = os.path.join(CFG.SERVER_ROOT, dirname)
        # 服务器EXE完整路径（查找进程）
        self._exePath = STool.getServerExePath(self._serverPath)
        # GameServer.ini 完整路径
        self._iniPath = os.path.join(self._serverPath, 'GameServer.ini')
        # GameServer.ini 配置文件对象
        self._servercfg = ServerConfig(self._iniPath) if self.isValid() else None
        # 服务器进程（查找窗口，检查服务器是否运行时会被赋值）
        self._pid = 0
        # 控制台窗口
        self._window = None
        if bCreateNew:
            # 创建新服
            self.onCreateNew()

    def onCreateNew(self):
        if not self.isValid():
            return

        # 根据配置自动更新GameServer.ini字段
        id = STool.getServerDirID(self._dirname)
        items = CFG.GetItems('GameServer')
        for k, v in items:
            sec, op = k.split('.')
            try:
                self._servercfg.Set(sec, op, v.format(id))
            except Exception as e:
                logging.error(e)
                pass
        self._servercfg.Save()

        # 执行创建脚本（如果有）
        Action('CreateGameServer').execute(id)

    def start(self):
        if not self.isValid():
            GUITool.MessageBox('服务器不可用')
            return False
        if self.isRunning():
            return False

        if CFG.COMBINE_SERVER_WINDOWS_IN_TASKBAR:
            start_bat_path = os.path.join(self._serverPath, 'start.bat')
            with open(start_bat_path, 'w') as f:
                f.write('title {0}({1}) && gameserver /console && exit'.format(self._servercfg.name,
                                                                               self._servercfg.title))
            proc = subprocess.Popen('start {0}'.format('start.bat'), shell=True, cwd=self._serverPath)
            proc.wait()
        else:
            proc = subprocess.Popen("start GameServer.exe /console", shell=True, cwd=self._serverPath)
            proc.wait()
        logging.info('服务器[%s][%s]开启成功', self._dirname, self.getCfg().name)

        # 阻塞，等完全开启后再返回
        timeout = 0
        while (not self.isRunning()):
            time.sleep(CFG.SERVER_START_CHECK_INTERVAL)
            timeout += CFG.SERVER_START_CHECK_INTERVAL
            if timeout >= CFG.SERVER_START_TIMEOUT:
                GUITool.MessageBox('服务器开启检测超时')
                return False
        if CFG.SERVER_HIDE_ON_START:
            self.hideConsoleWindow()
        return True

    def exit(self, bForce=False):
        if not self.isRunning():
            return True
        if bForce:
            # 强制终止
            try:
                psutil.Process(self._pid).terminate()
            except:
                pass
        else:
            self.execute('exit')

        # 阻塞，等完全关闭后再返回
        timeout = 0
        while (self.isRunning()):
            time.sleep(CFG.SERVER_EXIT_CHECK_INTERVAL)
            timeout += CFG.SERVER_EXIT_CHECK_INTERVAL
            if timeout >= CFG.SERVER_EXIT_TIMEOUT:
                GUITool.MessageBox('服务器关闭超时，请检查服务器窗口输出')
                return False
        logging.info('服务器[%s][%s]关闭成功,耗时%.2f秒', self._dirname, self.getCfg().name, timeout)
        return True

    def restart(self):
        self.exit()
        return self.start()

    def hotUpdate(self):
        if not self.isRunning():
            return False
        return self.execute('lua')

    def findWindow(self):
        if self._window and self._window.Exists():
            return self._window

        if CFG.FIND_WINDOW_COMPATIBLE_MODE:
            return self.__findWindowEx()

        if not self.isRunning():
            GUITool.MessageBox('服务器[{0}]未开启'.format(self._servercfg.name))
            return None
        try:
            self._window = uiautomation.WindowControl(ClassName='ConsoleWindowClass', Name=self._exePath)
            # 目前不支持通过ProcessId查找窗口，参数会被忽略
            # window = uiautomation.WindowControl(ClassName='ConsoleWindowClass', ProcessId=self._pid)
            return self._window
        except LookupError as e:
            logging.error(repr(e))
            GUITool.MessageBox('查找服务器窗口失败')
        return None

    def __findWindowEx(self):
        '''
        gameserver.exe运行方式有两种：
        第一种： start gameserver.exe 这种能够通过窗口标题查找 gameserver.exe 成为孤儿进程
            window = uiautomation.WindowControl(ClassName='ConsoleWindowClass', Name=self._exePath)
        第二种： gameserver.exe 直接在批处理中执行，这时候窗口标题是 cmd.exe，cmd.exe是父进程，无法通过窗口标题查找
            window = uiautomation.ControlFromHandle(get_hwnds_for_pid(ppid))
        '''
        if not self.isRunning():
            GUITool.MessageBox('服务器[{0}]未开启'.format(self._servercfg.name))
            return None
        if psutil.pid_exists(self._pid):
            try:
                p = psutil.Process(self._pid)
                ppid = p.ppid()
                # 检查是否作为cmd的子进程运行
                hwnd = get_hwnds_for_pid(ppid if psutil.pid_exists(ppid) else self._pid)
                if hwnd > 0:
                    self._window = uiautomation.ControlFromHandle(hwnd)
                    return self._window
                else:
                    logging.error('查找窗口句柄失败：pid=%d，ppid=%d(exist=%s)', self._pid, ppid, str(psutil.pid_exists(ppid)))
            except LookupError as e:
                logging.error(repr(e))
                GUITool.MessageBox('查找服务器窗口失败')
            except:
                pass
        return None

    def execute(self, cmd):
        window = self.findWindow()
        if window:
            window.SwitchToThisWindow()
            window.SendKeys(cmd)
            window.SendKeys('{Enter}')
            logging.info('服务器[%s][%s][pid=%s]执行命令[%s]', self._dirname, self.getCfg().name, self._pid, cmd)
            # fixme: badcode
            if cmd != 'exit' and CFG.SERVER_EXECUTE_CMD_WAIT_TIME > 0:
                time.sleep(CFG.SERVER_EXECUTE_CMD_WAIT_TIME)
            return True
        return False

    def getInfo(self, debug=False):
        if self.isValid():
            if debug:
                return {
                    'name': self.getCfg().name,
                    'id': self.getCfg().serverID,
                    'running': self.isRunning(),
                    'pid': self._pid,
                }
            else:
                return '[%s(%s)]:%s' % (self.getCfg().name, self.getCfg().title, '运行中' if self.isRunning() else '已关闭')
        else:
            return {'name': '服务器不可用'}

    def isValid(self):
        # 服务器是否可用（目录是否存在，文件完整性）
        return os.path.exists(self._exePath) and os.path.exists(self._iniPath)

    def isRunning(self):
        # 这里根据运行exe（带路径）直接查找，速度快，定位准
        if self._pid != 0 and psutil.pid_exists(self._pid):
            try:
                p = psutil.Process(self._pid)
                if self._exePath.lower() == p.exe().lower():
                    return True
            except:
                pass

        for pid in psutil.pids():
            if not psutil.pid_exists(pid):
                continue
            try:
                p = psutil.Process(pid)
                # if re.search(self._exePath, p.exe(), re.IGNORECASE):
                if self._exePath.lower() == p.exe().lower():
                    self._pid = pid
                    return True
            except psutil.NoSuchProcess as e:
                pass
            except psutil.AccessDenied as e:
                pass
        self._pid = 0
        self._window = None
        return False

    def getLastError(self):
        # 获取服务器运行错误日志
        return False

    def getCfg(self):
        return self._servercfg

    def showConsoleWindow(self):
        window = self.findWindow()
        if window:
            window.SwitchToThisWindow()
            return True
        return False

    def hideConsoleWindow(self):
        window = self.findWindow()
        if window:
            window.Minimize()
            return True
        return False

    def showInExplorer(self):
        subprocess.Popen('explorer %s' % (self._serverPath))


class Action:
    def __init__(self, name):
        self._name = name
        self._cmd = None
        action = CFG.GetAction(name)
        if action and os.path.exists(action):
            self._cmd = os.path.normpath(action)

    def execute(self, *args):
        if not self._cmd:
            logging.info('Action[%s]未配置', self._name)
            return
        cmd = '{0} {1}'.format(self._cmd, ' '.join([str(v) for v in args]))
        logging.info('Action[%s]开始执行：%s', self._name, cmd)

        tmpfilename = 'action_output.txt'
        os.system('{0} > {1}'.format(cmd, tmpfilename))
        with open(tmpfilename, 'r') as f:
            for line in f.readlines():
                logging.info('> {}'.format(line.strip()))
        os.remove(tmpfilename)
        logging.info('Action[%s]执行结束', self._name)


# 这种方式暂时没有走通
class Server(IServer):
    def __init__(self):
        assert (False)
        SERVER_PATH = 'd:/LegendGame/game/runtime/gameserver'
        os.chdir(SERVER_PATH)
        self._proc = subprocess.call(["GameServer.exe", "/console"],
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        print(self._proc.stdout.readlines())
        # flags = fcntl.fcntl(self.process.stdout, fcntl.F_GETFL)
        # fcntl.fcntl(self._proc.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def exit(self):
        self.execute("exit")

    def execute(self, cmd):
        self._proc.stdin.write(cmd)
        # self._proc.stdin.flush()


# GameServer.ini 管理
class ServerConfig(INI):
    def showInEditor(self):
        # os.system('notepad %s' % (self.filename)) 会弹出控制台
        # 以阻塞方式打开便于修改完成之后重新加载
        STool.showFileInTextEditor(self.filename, wait=True)
        self.Load()

    @property
    def name(self):
        return self.Get('server', 'name').strip('"')

    @property
    def title(self):
        return self.Get('server', 'title').strip('"')

    @property
    def serverID(self):
        return self.GetInt('server', 'server_id')


def main():
    logging.basicConfig(filename='cmd.log',
                        filemode='w',
                        level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        assert os.path.exists(CFG.SERVER_ROOT), "服务器根目录不存在"
        assert os.path.exists(CFG.SERVER_TEMPLATE), "服务器模板路径不存在"
        GUI("Server Tools")
    except:
        print(traceback.format_exc())
        logging.error(traceback.format_exc())


if __name__ == '__main__':
    main()
