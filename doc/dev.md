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

### 任务计划功能
支持定时对服务器执行计划任务
- 选择服务器id，选择行为（开、关、重启），选择时间，显示剩余时间
- 存储计划，计划分配/修改/执行日志
- 在服务器列表上对有计划任务的服务器突出显示
大意了，居然tk自己并不支持日历时间控件

### 开启webservice
#### 框架选择
提供web接口，使得可以通过网页后台进行服务器管理，暂时不需要考虑性能，主要考虑易于部署，最好能直接集成到GUI中，实现0部署

| 考虑方案                              |                                                     |
| ------------------------------------- | --------------------------------------------------- |
| cgi-bin                               | 需要额外配置和部署                                  |
| socket                                | 不够"高级"                                          |
| fastapi                               | 需要借助外部命令`$uvicorn`启动                      |
| [flask](https://read.helloflask.com/) | 实际上也应该借助`$flask`，不过也可以直接`app.run()` |

[请不要把 Flask 和 FastAPI 放到一起比较](https://zhuanlan.zhihu.com/p/369591096)

#### 线程or进程
最开始考虑的是线程，但是当UI关闭的时候，web服务并不会一起关闭，同时，线程并没有关闭/终止接口。于是转而使用进程，进程的使用是更加麻烦的，一开始使用就碰到内存数据不共享的尴尬问题，而且查找窗口在子进程中也无法正确运行（DLL加载问题？），只能使用命令队列让主线程读取命令并运行。回到关闭web服务问题，进程虽然有终止接口，不过了解到了`deamon`，设置为`True`即可随着父进程一起关闭。线程和进程实在太相似了，甚至也有`serDeamon`方法，于是又花1min将代码修改成线程运行，而原来依赖查找窗口的功能，也得以以同步方式实现。一切都运行良好。
[一篇文章搞定Python多进程](https://zhuanlan.zhihu.com/p/64702600)