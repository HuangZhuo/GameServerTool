#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import tkinter
import tkinter.messagebox as tkMessageBox
import configparser
import logging
import time


# https://blog.csdn.net/qq_40134903/article/details/88297476
def get_hwnds_for_pid(pid):
    '''通过PID查询句柄ID'''
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


# https://github.com/rpowel/hass_restAPI/blob/main/src/disk.py
def get_free_space_gb(dirname):
    """Return folder/drive free space (in gigabytes)."""
    import psutil

    free_bytes = psutil.disk_usage(dirname).free  # bytes
    free_bytes = free_bytes / 1024 / 1024 / 1024  # Gigabytes
    return int(free_bytes)


def counter(start=0, step=1):
    # 简单自增计数器
    def __counter(start=0, step=1):
        while True:
            yield start
            start += step

    gen = __counter(start, step)
    return lambda: next(gen)


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
            padx = grid[2] if len(grid) > 2 else 0
            btn.grid(row=grid[0], column=grid[1], padx=padx)
        return btn


class INI:
    def __init__(self, filename):
        self._filename = filename
        self._parser = configparser.ConfigParser()
        self._loaded = False
        self.Load()

    @property
    def filename(self):
        return self._filename

    @property
    def paser(self):
        return self._parser

    def Load(self):
        if self._loaded:
            logging.info('配置文件[%s]重新读取', self._filename)
        read_ok = self._parser.read(self._filename)
        self._loaded = len(read_ok) > 0
        if not self._loaded:
            logging.warning('配置文件[%s]读取失败', self._filename)

    def Save(self):
        with open(self._filename, 'w+') as f:
            self._parser.write(f)

    def SaveOptionIfNotExist(self, section, key, fallback):
        if not self._parser.has_option(section, key):
            self._parser.set(section, key, str(fallback))
            self.Save()

    def Set(self, section, key, value):
        return self._parser.set(section, key, value)

    def Get(self, section, key, fallback=''):
        return self._parser.get(section, key, fallback=fallback)

    def GetInt(self, section, key, fallback=-1):
        return self._parser.getint(section, key, fallback=fallback)

    def GetFloat(self, section, key, fallback=-1):
        return self._parser.getfloat(section, key, fallback=fallback)

    def GetBool(self, section, key, fallback=False):
        return self._parser.getboolean(section, key, fallback=fallback)

    def HasSection(self, section):
        return self._parser.has_section(section)

    def GetItems(self, section):
        # 返回(k,v)元组列表
        return self._parser.items(section) if self._parser.has_section(section) else []


class Profiler:
    __t = 0

    @staticmethod
    def START():
        # assert Profiler.__t == 0
        Profiler.__t = time.perf_counter()

    @staticmethod
    def FINISH(text, notify=False):
        # assert Profiler.__t != 0
        t = time.perf_counter() - Profiler.__t
        msg = '{}，耗时 {:.2f}s'.format(text, t)
        if notify:
            GUITool.MessageBox(msg)
        Profiler.__t = 0

    @staticmethod
    def ABORT():
        Profiler.__t == 0