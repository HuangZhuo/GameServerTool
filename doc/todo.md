## 功能
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
- [x] 开启的控制台窗口合并显示
    * 本质是同一个exe进程会合并在一起
    * COMBINE_SERVER_WINDOWS_IN_TASKBAR 新增可配置
- [x] 默认启动时只勾选正在运行的服务器
- [x] 开启服务器时最小化服务器控制台
    * SERVER_HIDE_ON_START 新增可配置
- [x] window对象缓存，避免重复查找
- [x] create-db.bat支持连接远程数据库
    * `mysql -uroot -p123456 -P3310 -h127.0.0.1 `
- [x] 创建服务器目录支持指定数字索引
    * 引入插件设计，拓展功能
- [x] 无法通过PID查找窗口，只能通过窗口标题
    * 一种思路是使用`win32gui`遍历窗口得到句柄ID，`uiautomation.ControlFromHandle`通过句柄可以查找到窗口


## 代码优化
- [ ] Profiler使用装饰器机制
- [ ] 将阻塞试for循环优化成任务队列，使得UI有机会及时刷新

## 低优先级
- [ ] 服务器目录删除时同步UI同步刷新，目前为服务器不可用提示
    * 需要删除tkinter创建的控件
- [ ] 读取控制台窗口内容，读取异常dump文件，显示服务器运行错误等内容
    * 还是用输出重定向的思路
- [x] 使用socket和游戏服连接发送命令，不查找窗口