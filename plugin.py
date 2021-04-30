#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import tkinter
import tkinter.messagebox as tkMessageBox
import re
import logging

from cmd import counter
from cmd import GUITool
from cmd import ServerManager


class PluginCreateMultiServers(tkinter.Frame):
    def __init__(self, gui):
        tkinter.Frame.__init__(self)
        self._gui = gui
        self.initUI()

    def initUI(self):
        nextrow = counter()
        tkinter.Label(self, text='批量创建:').grid(row=0, column=nextrow())
        self._edit = tkinter.Entry(self, width=16)
        self._edit.grid(row=0, column=nextrow())
        GUITool.createBtn('执行', self.onCreateMultiServerClick, parent=self, grid=(0, nextrow()))
        tkinter.Label(self, text='*支持输入格式:10|10-20|10,20', fg='red').grid(row=0, column=nextrow())
        GUITool.GridConfig(self, padx=5)

    def onCreateMultiServerClick(self):
        input = self._edit.get().strip()
        print('onCreateMultiServerClick', input)
        if len(input) == 0:
            GUITool.MessageBox('批量创建输入为空')
            return
        if input.isnumeric():
            # print(int(input))
            ServerManager.createServer(int(input))
            return

        listCreate = []
        err = '匹配序列为空'
        while True:
            # 10-20
            m = re.search(r'^([0-9]+)-([0-9]+)$', input)
            if m:
                print(m.groups())
                tmp = [int(n) for n in m.groups()]
                for i in range(tmp[0], tmp[1] + 1):
                    listCreate.append(i)
                break

            # 10,20
            tmp = input.strip(',').split(',')
            if len(tmp) > 1:
                try:
                    for n in tmp:
                        if not n.isnumeric():
                            err = '[{}]不是数字类型'.format(n)
                            raise ValueError
                    listCreate = list(set([int(n) for n in tmp]))
                    listCreate.sort()
                except:
                    break

            err = '不支持的输入格式'
            break

        if len(listCreate) == 0:
            err = '输入[{0}]错误：{1}'.format(input, err)
            logging.error(err)
            GUITool.MessageBox(err)
            return

        if not GUITool.MessageBox('即将创建以下服务器：{}'.format(listCreate), ask=True):
            return

        logging.info('开始批量创建服务器：{}'.format(listCreate))
        listSuc = []
        for id in listCreate:
            if ServerManager.createServer(id):
                listSuc.append(id)
            else:
                logging.error('创建服务器{}失败，终止批量创建'.format(id))
                break

        if len(listSuc) > 0:
            logging.info('完成批量创建服务器：{}'.format(listSuc))
            self._gui.initServerList()
