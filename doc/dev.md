# DEV

## REF
https://docs.python.org/zh-cn/3/library/tkinter.html


## TODO
- [x] 服务器状态实时刷新
    * 每秒1次，支持配置
- [x] 服务器配置文件读写
- [x] 进程运行监测优化
    * 将遍历获得的进程ID缓存
- [x] 工具界面关闭保留服务器进程（工具出了BUG后不影响服务器继续运行）
- [x] 创建服务器后自动修改ID
- [x] 界面美化，按钮间隔
- [x] 热更新需要更新脚本
- [x] 完善操作日志输出
- [x] CFG配置优化
- [x] 多服务器分页显示or列表控件
    先实现多列配置显示，修改配置后重启生效
- [x] 配置文件读取容错->出错提示
- [x] 在资源管理器中打开服务器目录，模板目录
- [x] 创建服务器GameServer.ini预配置
    * [x] 根据服务器ID生成值，配置规则
    * [x] 支持为创建事件定义批处理方式 `Actions`
    * [x] 配置规则拓展 eval(${id})
- [x] 命令执行间隔时间配置
- [x] 重启->工具重新加载
- [x] 打开配置文件应用可配置
- [ ] 服务器目录删除时同步UI同步刷新，目前为服务器不可用提示
    * 需要删除tkinter创建的控件
- [x] 开启的控制台窗口合并显示
    * 本质是同一个exe进程会合并在一起
    * COMBINE_SERVER_WINDOWS_IN_TASKBAR 新增可配置
- [x] 默认启动时只勾选正在运行的服务器
- [x] 开启服务器时最小化服务器控制台
    * SERVER_HIDE_ON_START 新增可配置
- [x] window对象缓存，避免重复查找
- [ ] 读取控制台窗口内容，读取异常dump文件，显示服务器运行错误等内容
    * 还是用输出重定向的思路
- [x] create-db.bat支持连接远程数据库
    * `mysql -uroot -p123456 -P3310 -h127.0.0.1 `
- [x] 创建服务器目录支持指定数字索引
    * 引入插件设计，拓展功能

## BUG
- [x] 目录识别`gameserver5-new`也会被匹配
    * r'^gameserver([0-9]+)$'
- [x] 偶现执行命令时没有回车{Enter}
    * 可能是切换窗口过快，添加执行命令间隔时间配置
    * 最后定位原因：只要服务器窗口在后台必现
- [x] 偶现查找不到窗口
    * 先添加相关错误日志
- [x] 连续单击单个服务器执行，造成窗口失去焦点，命令丢失
    * 暂未出现

## NEXT
- [x] 无法通过PID查找窗口，只能通过窗口标题
    * 一种思路是使用`win32gui`遍历窗口得到句柄ID，`uiautomation.ControlFromHandle`通过句柄可以查找到窗口
- [ ] 将阻塞试for循环优化成任务队列，使得UI有机会及时刷新

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