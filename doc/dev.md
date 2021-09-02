# DEV

## 参考
https://docs.python.org/zh-cn/3/library/tkinter.html

## DEV_LOG
### Action 执行问题
```python
    def execute(self, *args):
        if not self._cmd:
            logging.info('Action[%s]未配置', self._name)
            return
        cmd = 'call {0} {1}'.format(self._cmd, ' '.join([str(v) for v in args]))
        logging.info('Action[%s]开始执行：%s', self._name, cmd)

        # p = os.popen(cmd)
        # for line in p.readlines():
        #     logging.info('> {}'.format(line.strip()))
        # p.close()

        # p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        # out, err = p.communicate()
        # for line in out.splitlines():
        #     logging.info('> {}'.format(line.decode().strip()))

        os.system(cmd)
        logging.info('Action[%s]执行结束', self._name)
```
注释掉的两个代码块均无法运行和获得输出，VS调试环境可以，打包成EXE不行，和打包的时候去掉了控制台有关，可以用输出重定向做
```python
    tmpfilename = 'action_output.txt'
    os.system('{0} > {1}'.format(cmd, tmpfilename))
    with open(tmpfilename, 'r') as f:
        for line in f.readlines():
            logging.info('> {}'.format(line.strip()))
    os.remove(tmpfilename)
```

### 多线程拷贝
```python
    from concurrent.futures import ThreadPoolExecutor

    def onUpdateServerDataClick(self):
        t = time.perf_counter()
        with ThreadPoolExecutor(max_workers=8) as pool:
            for v in self.getSelectedServers():
                future = pool.submit(STool.updateServerDir, v, filelist=('data', 'GameConfig.ini'))
                future.result()
        t = time.perf_counter() - t
        GUITool.MessageBox('更新完成，耗时 {:.2f}s'.format(t))
```

### 项目名称
之前项目有一个很不合理的名字`CMD`，因为当时游戏服都是控制台启动，于是这个应用相当于是一个控制台窗口管理工具。后面改名为`GameServerTool`，更为直观。