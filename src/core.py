#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import os
import subprocess, psutil
import logging
import uiautomation
import time
import shutil
from abc import ABCMeta, abstractmethod

from common import get_hwnds_for_pid
from common import INI
from common import GUITool


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
        # 文本编辑器配置
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

    def GetPlugin(self, key):
        return self.Get('Plugin', key, None)

    def GetView(self, key):
        return self.Get('View', key, None)


CFG = CMD_INI('cmd.ini')


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
        shutil.copytree(CFG.SERVER_TEMPLATE, os.path.join(CFG.SERVER_ROOT, dirname), ignore=shutil.ignore_patterns('*.log'))
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

    @staticmethod
    def showServerTemplateInExplorer():
        subprocess.Popen('explorer %s' % (CFG.SERVER_TEMPLATE))

    @staticmethod
    def showFileInTextEditor(filename, wait=False):
        exe = CFG.TEXT_EDITOR_PATH if os.path.exists(CFG.TEXT_EDITOR_PATH) else 'notepad'
        proc = subprocess.Popen('%s %s' % (exe, filename))
        if wait:
            proc.wait()


# 自定义行为配置扩展
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
                value = ''
                if v.find('${id}') < 0:
                    # 兼容旧配置
                    value = v.format(id)
                else:
                    # 新配置采用eval()方法实现
                    v = v.replace('${id}', str(id))
                    value = str(eval(v))
                self._servercfg.Set(sec, op, value)
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
                f.write('title {0}({1}) && gameserver /console && exit'.format(self._servercfg.name, self._servercfg.title))
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
        if not self.isValid():
            GUITool.MessageBox('服务器不可用')
            return None
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
            except Exception as e:
                logging.error(repr(e))
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
            return '服务器不可用'

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


class ServerManager:
    __servers = dict()

    @staticmethod
    def createServer(id=None):
        id = id if id is not None else STool.getNextServerDirID()
        suc, dirname = STool.createServerDir(id)
        if not suc:
            GUITool.MessageBox('创建服务器目录失败，检查目录{}是否存在'.format(dirname))
            return None
        server = ServerV3(dirname, bCreateNew=True)
        ServerManager.__servers[dirname] = server
        return server

    @staticmethod
    def getServer(name) -> ServerV3:
        if not ServerManager.__servers.get(name):
            ServerManager.__servers[name] = ServerV3(name)
        return ServerManager.__servers[name]

    @staticmethod
    def isDBServerRunning(port):
        # todo:根据端口监听判断数据库是否开启
        pass

    @staticmethod
    def clear():
        logging.info('强制刷新：删除所有服务器对象')
        ServerManager.__servers.clear()
