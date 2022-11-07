#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import json
import logging
import os
import re
import shutil
import socket
import subprocess
import time
from abc import ABCMeta, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from enum import Enum
from hashlib import md5

import psutil
import uiautomation
from slpp import slpp

from common import INI, CoInitializer, Profiler, get_hwnds_for_pid


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
    def COMBINE_SERVER_WINDOWS_IN_TASKBAR(self):
        # 是否在任务栏合并服务器窗口（只支持兼容模式查找）
        return self.GetBool('CMD', 'COMBINE_SERVER_WINDOWS_IN_TASKBAR', True)

    @property
    def DISK_LEFT_SPACE_WARING_NUM_GB(self):
        # 磁盘剩余空间警告
        return self.GetInt('CMD', 'DISK_SPACE_WARING_NUM_GB', 10)

    @property
    def THREAD_POOL_MAX_WORKERS(self):
        return self.GetInt('CMD', 'THREAD_POOL_MAX_WORKERS', 8)

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
    def rmServerDir(dirname):
        dirname = os.path.join(CFG.SERVER_ROOT, dirname)
        shutil.rmtree(dirname)

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
    def getServerDirName(id):
        return 'gameserver{}'.format(id)

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
        dirname = STool.getServerDirName(id)
        if STool.isServerDirExists(dirname):
            logging.error('创建服务器目录[%s]失败，目录已存在', dirname)
            return False, dirname
        shutil.copytree(CFG.SERVER_TEMPLATE,
                        os.path.join(CFG.SERVER_ROOT, dirname),
                        ignore=shutil.ignore_patterns('*.log', '*.dmp'))
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
                    # shutil.rmtree(os.path.join(dirname, f), ignore_errors=True)
                    shutil.copytree(src, os.path.join(dirname, f), dirs_exist_ok=True)
            except FileNotFoundError as e:
                pass
        logging.info('更新服务器目录[%s]成功，文件[%s]', name, filelist)
        return True

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


class DB:
    '''
    采取json保存的简单数据库，支持键值对存储
    '''
    def __init__(self, dbfile) -> None:
        self._dbfile = dbfile
        self._data = dict()
        if os.path.exists(dbfile):
            with open(dbfile, 'r', encoding='utf-8') as f:
                # todo: wrong json format
                content = f.read()
                if len(content) > 0:
                    self._data = json.loads(content)

    def get(self, k, default=None):
        return self._data.get(k, default)

    def set(self, k, v):
        self._data[k] = v

    def clear(self, k=None):
        if None == k:
            self._data.clear()
            return
        if k in self._data:
            self._data.pop(k)

    def save(self):
        if len(self._data) == 0:
            # 没有数据直接删除文件
            if os.path.exists(self._dbfile):
                os.remove(self._dbfile)
        else:
            with open(self._dbfile, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=4)


class PlanType(str, Enum):
    NONE = '无计划'
    START = '开启'
    EXIT = '关闭'
    RESTART = '重启'


class Plan:
    '''
    计划任务
    '''
    TIME_FMT = '%Y-%m-%d %H:%M:%S'

    def __init__(self, db: dict = None) -> None:
        self._plan = PlanType.NONE
        self._time = None
        if db:
            try:
                self._plan = PlanType(db.get('plan'))
            except ValueError as e:
                logging.error('错误的任务类型：%s', db.get('plan'))
                return
            time = datetime.strptime(db.get('time'), self.TIME_FMT)
            now = datetime.now()
            if now > time:
                # 清理过期任务
                self._plan = PlanType.NONE
            else:
                self._time = time

    def __str__(self) -> str:
        if self._plan == PlanType.NONE:
            return '无'
        diff = timedelta(seconds=self.leftSecs)
        return '[{}]{}({})'.format(self._plan.value, self._time, diff)

    @property
    def type(self):
        return self._plan

    @property
    def name(self):
        return self._plan.value

    @property
    def empty(self):
        return self._plan == PlanType.NONE

    @property
    def leftSecs(self):
        now = datetime.now().replace(microsecond=0)
        secs = (self._time - now).total_seconds()
        return int(secs)

    def set(self, plan: PlanType, time: datetime):
        # 检查数据有效性
        self._plan = plan
        self._time = time

    def clear(self):
        self._plan = PlanType.NONE

    def get(self):
        if self._plan == PlanType.NONE:
            return None
        else:
            return {
                'plan': self._plan.value,
                'time': self._time.strftime(self.TIME_FMT),
            }


class PlanManager:
    '''
    计划任务管理
    '''
    __instance = None

    @classmethod
    def getInstance(cls):
        if not cls.__instance:
            cls.__instance = cls()
        return cls.__instance

    def __init__(self) -> None:
        dbfile = CFG.Get('Plan', 'DB', 'plan.json')
        self._db = DB(dbfile)
        self._plans = dict()

    def getPlan(self, servername) -> Plan:
        if not self._plans.get(servername):
            self._plans[servername] = Plan(self._db.get(servername))
        return self._plans[servername]

    def save(self):
        for s, plan in self._plans.items():
            if plan.empty:
                self._db.clear(s)
            else:
                self._db.set(s, plan.get())
        self._db.save()

    def check(self):
        for s, plan in self._plans.items():
            if plan.empty:
                continue
            if plan.leftSecs <= 0:
                # print('执行任务')
                server = ServerManager.getServer(s)
                cmd = None
                if plan.type == PlanType.START:
                    cmd = 'start'
                elif plan.type == PlanType.EXIT:
                    cmd = 'exit'
                elif plan.type == PlanType.RESTART:
                    cmd = 'restart'

                if not cmd:
                    logging.error('不支持的计划任务类型[%s]', plan.name)
                else:
                    ret, err = server.call(cmd)
                    if ret:
                        logging.info('服务器[%s]执行计划任务[%s]成功', s, plan.name)
                    else:
                        logging.info('服务器[%s]执行计划任务[%s]失败：%s', s, plan.name, err)
                plan.clear()
                self.save()
                # break为了一次tick只执行一个计划任务
                break


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
            self._onCreateNew()

    def _onCreateNew(self):
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

    def _findWindow(self):
        '''
        gameserver.exe运行方式有两种：
        第一种： start gameserver.exe 这种能够通过窗口标题查找 gameserver.exe 成为孤儿进程
            window = uiautomation.WindowControl(ClassName='ConsoleWindowClass', Name=self._exePath)
        第二种： gameserver.exe 直接在批处理中执行，这时候窗口标题是 cmd.exe，cmd.exe是父进程，无法通过窗口标题查找
            window = uiautomation.ControlFromHandle(get_hwnds_for_pid(ppid))
        '''
        if not self.isValid():
            return None, '服务器不可用'
        if not self.isRunning():
            return None, '服务器[{0}]未开启'.format(self._servercfg.name)
        err = None
        if psutil.pid_exists(self._pid):
            try:
                if self._window and self._window.Exists():
                    return self._window, None
                p = psutil.Process(self._pid)
                # if not p.parent():
                #     self._window = uiautomation.WindowControl(ClassName='ConsoleWindowClass', Name=self._exePath)
                #     return self._window

                # 检查是否作为cmd的子进程运行
                hwnd = get_hwnds_for_pid(p.pid if not p.parent() else p.ppid())
                if hwnd > 0:
                    self._window = uiautomation.ControlFromHandle(hwnd)
                    return self._window, None
                else:
                    err = '查找窗口句柄失败：pid={}，ppid={}(exist={})'.format(p.pid, p.ppid(), str(psutil.pid_exists(p.ppid())))
            except LookupError as e:
                logging.error(repr(e))
                err = '查找服务器窗口失败'
            except Exception as e:
                logging.error(repr(e))
                err = '查找失败'
        return None, err

    @property
    def dirname(self):
        return self._dirname

    @property
    def name(self):  # 服务器可读名称
        return f'{self.getCfg().name}-{self.getCfg().title}'

    @property
    def pid(self):
        return self._pid

    def start(self):
        if not self.isValid():
            return False, '服务器不可用'
        if self.isRunning():
            return False, '服务器已开启'

        if CFG.COMBINE_SERVER_WINDOWS_IN_TASKBAR:
            start_bat_path = os.path.join(self._serverPath, 'start.bat')
            with open(start_bat_path, 'w') as f:
                f.write('title {0}({1}) && gameserver /console \r\n exit'.format(self._servercfg.name, self._servercfg.title))
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
                return False, '服务器开启检测超时'
        if CFG.SERVER_HIDE_ON_START:
            self.hideConsoleWindow()
        return True, None

    def exit(self, bForce=False):
        if not self.isRunning():
            return True, None
        if bForce:
            # 强制终止
            try:
                psutil.Process(self._pid).terminate()
            except:
                pass
        else:
            self.execute_w('exit')

        # 阻塞，等完全关闭后再返回
        timeout = 0
        while (self.isRunning()):
            time.sleep(CFG.SERVER_EXIT_CHECK_INTERVAL)
            timeout += CFG.SERVER_EXIT_CHECK_INTERVAL
            if timeout >= CFG.SERVER_EXIT_TIMEOUT:
                return False, '服务器关闭超时'
        logging.info('服务器[%s][%s]关闭成功,耗时%.2f秒', self._dirname, self.getCfg().name, timeout)
        return True, None

    def restart(self):
        ret, err = self.exit()
        if ret:
            ret, err = self.start()
        return ret, err

    def hotUpdate(self):
        return self.execute('lua')

    def execute(self, cmd):
        if not self.isRunning():
            return False, '服务器未开启'
        ret, resp = self.execute_s(cmd)
        logging.info('服务器[%s][%s][pid=%s]执行命令[%s]|结果[%s]', self._dirname, self.getCfg().name, self._pid, cmd, resp)
        return ret, resp

    def execute_w(self, cmd):
        '''
        通过查找窗口模拟输入命令。无法获取后台返回值
        '''
        # assert (self.isRunning())
        window, err = self._findWindow()
        if not window:
            return False, err
        window.SwitchToThisWindow()
        window.SendKeys(cmd + '{Enter}')
        logging.info('服务器[%s][%s][pid=%s]执行命令[%s]', self._dirname, self.getCfg().name, self._pid, cmd)
        # fixme: badcode
        if cmd != 'exit' and CFG.SERVER_EXECUTE_CMD_WAIT_TIME > 0:
            time.sleep(CFG.SERVER_EXECUTE_CMD_WAIT_TIME)
        return True, None

    def execute_s(self, cmd):
        '''
        通过socket连接向游戏服发送命令。并返回结果
        这种方式只支持游戏服[DoSystemCommand]中的命令，不支持exit（退出游戏服）
        （参考了后台跟游戏服通信方式）
        '''
        # assert (self.isRunning())
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.SOL_TCP)
            s.settimeout(5.0)  # https://stackoverflow.com/questions/2719017/how-to-set-timeout-on-pythons-socket-recv-method
            s.connect(('localhost', self.getCfg().masterPort))

            sign = cmd + self.getCfg().masterKey
            sign = md5(sign.encode()).hexdigest()
            msg = f'{sign}{cmd}\n'
            s.send(msg.encode())
            resp = s.recv(1024)
            s.close()
            return True, resp.decode().strip()
        except Exception as e:
            return False, str(e)

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
                ver = self.getVersion()
                return '[{} V{}]:{}'.format(self.getCfg().title, ver if ver else '?', '运行中' if self.isRunning() else '已关闭')
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
                # print(p.status(), self._pid)
                if p.exe() and os.path.samefile(self._exePath, p.exe()):
                    return True
            except:
                pass

        for pid in psutil.pids():
            if pid == 0 or not psutil.pid_exists(pid):
                continue
            try:
                p = psutil.Process(pid)
                # if re.search(self._exePath, p.exe(), re.IGNORECASE):
                if p.exe() and os.path.samefile(self._exePath, p.exe()):
                    self._pid = pid
                    return True
            except FileNotFoundError as e:
                pass
            except psutil.NoSuchProcess as e:
                pass
            except psutil.AccessDenied as e:
                pass
        self._pid = 0
        self._window = None
        return False

    def getLastError(self):
        '''获取服务器运行错误日志'''
        raise NotImplementedError('功能暂未实现')

    def getExceptionDump(self):
        '''获取异常dmp文件'''
        for f in os.listdir(self._serverPath):
            f = os.path.join(self._serverPath, f)
            if not os.path.isfile(f):
                continue
            __, ext = os.path.splitext(f)
            if ext == '.dmp':
                return True
        return False

    def getCfg(self):
        return self._servercfg

    def showConsoleWindow(self):
        window, err = self._findWindow()
        if window:
            window.SwitchToThisWindow()
            return True, None
        return False, err

    def hideConsoleWindow(self):
        window, err = self._findWindow()
        if window:
            window.Minimize()
            return True, None
        return False, err

    def showInExplorer(self):
        if not os.path.exists(self._serverPath):
            return False, '服务器目录[{}]不存在'.format(self._serverPath)
        subprocess.Popen('explorer %s' % (self._serverPath))
        return True, None

    def showConfigInEditor(self):
        if not self.isValid():
            return False, '服务器不可用'
        self.getCfg().showInEditor()
        return True, None

    def getVersion(self):
        # fixme: code more flexible
        filename = os.path.join(self._serverPath, 'data/long/script/data/NDS.lua')
        if not os.path.exists(filename):
            filename = os.path.join(self._serverPath, '../../data/long/script/data/NDS.lua')
            if not os.path.exists(filename):
                return None
        str = None
        with open(filename, 'r', encoding='utf8') as f:
            str = f.read()
        m = re.search(r'return(.*)', str, re.DOTALL)
        if m:
            cfg = slpp.decode(m.group(1))
            return cfg['version']
        else:
            return None

    def call(self, funcname, *args):
        api = getattr(self, funcname)
        if not api:
            return False, NameError('[{}]接口不存在'.format(funcname))
        return api(*args)


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

    @property
    def masterPort(self):
        return self.GetInt('master', 'port')

    @property
    def masterKey(self):
        return self.Get('master', 'key')


class ServerManager:
    __servers = dict()

    @staticmethod
    def createServer(id=None):
        id = id if id is not None else STool.getNextServerDirID()
        suc, dirname = STool.createServerDir(id)
        if not suc:
            return None, '创建服务器目录失败，检查目录{}是否存在'.format(dirname)
        server = ServerV3(dirname, bCreateNew=True)
        ServerManager.__servers[dirname] = server
        return server, None

    @staticmethod
    def deleteServer(name=None, id=None):
        if id:
            name = STool.getServerDirName(id)
        if not name:
            return False, '参数错误'
        if not STool.isServerDirExists(name):
            return False, '服务器目录不存在:{}'.format(name)
        if ServerManager.getServer(name).isRunning():
            return False, '请先关闭服务器:{}'.format(name)
        try:
            STool.rmServerDir(name)
            return True, None
        except Exception as e:
            return False, repr(e)

    @staticmethod
    def getServer(name=None, id=None, pid=None) -> ServerV3:
        if pid:  # 通过进程id查询
            for _, s in ServerManager.__servers.items():
                if s.pid == pid: return s
            return None
        if id:
            name = STool.getServerDirName(id)
        if not ServerManager.__servers.get(name):
            assert (STool.isServerDirExists(name))
            ServerManager.__servers[name] = ServerV3(name)
        return ServerManager.__servers[name]

    @staticmethod
    def isDBServerRunning(port):
        # todo:根据端口监听判断数据库是否开启
        raise NotImplementedError('功能暂未实现')

    @staticmethod
    def clear(name=None):
        if name == None:
            logging.info('强制刷新：删除所有服务器对象')
            ServerManager.__servers.clear()
        else:
            if name in ServerManager.__servers:
                ServerManager.__servers.pop(name)

    @staticmethod
    def getCount():
        '''获取总服务器（目录）数'''
        return len(ServerManager.__servers)


# 主任务线程
class _TaskExecutor:
    # 用于执行对服务器的批量操作，默认多线程执行
    _multi_exe = ThreadPoolExecutor(max_workers=1, thread_name_prefix='multi_task')
    # 用于执行服务器状态定时刷新，仅当进程空闲时执行
    _single_exe = ThreadPoolExecutor(max_workers=1, thread_name_prefix='single_task')
    _single_task = None
    _multi_task = None

    OK = 0  # 准备执行
    BUSY = 1  # 线程忙，忽略执行

    def submit(
        self,
        func,
        args: list,
        onProgress,
        notify=None,
        max_workers=CFG.THREAD_POOL_MAX_WORKERS,
        work_delay=0,
    ):
        if max_workers > 1 and work_delay > 0:
            logging.error('延时型任务只能单线程执行')
            max_workers = 1

        @CoInitializer
        @Profiler(notify)
        def _wrapper_single():
            finished = 0
            for v in args:
                if not func(v): break  # 任务执行失败时中断
                finished += 1
                onProgress(finished, len(args))
                time.sleep(work_delay)
            time.sleep(0.1)
            onProgress(0, len(args))

        @CoInitializer
        @Profiler(notify)
        def _wrapper_multi():
            with ThreadPoolExecutor(max_workers=max_workers) as t:
                tasks = []
                for v in args:
                    tasks.append(t.submit(func, v))
                finished = 0
                for future in as_completed(tasks):
                    # 这个循环实际上会阻塞当前线程直到所有任务完成
                    # future.result()
                    finished += 1
                    onProgress(finished, len(args))
            time.sleep(0.1)
            onProgress(0, len(args))

        if self._multi_task and not self._multi_task.done():
            return self.BUSY
        self._multi_task = self._multi_exe.submit(_wrapper_multi if max_workers > 1 else _wrapper_single)
        return self.OK

    def run_if_idle(self, func):
        if self._single_task and not self._single_task.done():
            return self.BUSY
        if self._multi_task and not self._multi_task.done():
            return self.BUSY
        self._single_task = self._single_exe.submit(func)
        return self.OK


TaskExecutor = _TaskExecutor()
del _TaskExecutor
