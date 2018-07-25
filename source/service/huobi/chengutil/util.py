# version 2018-07-19 05:45
import gzip
import io
import json
import time
import sys
import traceback
import os


# 解压缩
def gzip_uncompress(c_data):
    buf = io.BytesIO(c_data)
    f = gzip.GzipFile(mode='rb', fileobj=buf)
    try:
        r_data = f.read()
    finally:
        f.close()
    return r_data


# 将 kline 数据调整成数据库表需要的格式
def convertKlineJson(klineStr):
    klineObj = json.loads(klineStr)
    tick = klineObj['tick']
    ch = klineObj['ch'].split('.')
    symbol = ch[1]
    period = ch[3]
    tick['symbol'] = symbol
    tick['period'] = period
    return klineObj


def convertKlineJsonByTick(tick, chanel):
    chanel = chanel.split('.')
    symbol = chanel[1]
    period = chanel[3]
    tick['symbol'] = symbol
    tick['period'] = period
    return tick


# 将日期字符串转换为时间戳
# 示例：dateStr = '2018-1-1 00:00:00'
def getTimeStamp(dateStr):
    # 转为时间数组
    timeArray = time.strptime(dateStr, "%Y-%m-%d %H:%M:%S")
    # 转为时间戳
    timeStamp = int(time.mktime(timeArray))
    return timeStamp


# 将时间戳转换为日期字符串
def getLocaleDateStr(timestamp):
    return time.strftime('%Y-%m-%d %H:%M:%S %w-%Z', time.localtime(timestamp/1000))


def getLocaleDateStrBy16(timestamp):
    return time.strftime('%Y-%m-%d %H:%M:%S %w-%Z', time.localtime(timestamp/1000000))


def getLocaleDateStrBy13(timestamp):
    return time.strftime('%Y-%m-%d %H:%M:%S %w-%Z', time.localtime(timestamp/1000))


def getLocaleDateStrBy10(timestamp):
    return time.strftime('%Y-%m-%d %H:%M:%S %w-%Z', time.localtime(timestamp))


def getLocaleDateStrDefault(timestamp, sep=' '):
    return time.strftime('%Y-%m-%d'+sep+'%H:%M:%S'+sep+'%w-%Z', time.localtime(timestamp))


# 打印抛出错误信息，并记录日志。
def printExcept(filename='', logdir='/tmp/exlog/'):

    if filename == '':
        filename = os.path.basename(sys.argv[0]).split(".")[0]

    ex_type, ex_val, ex_stack = sys.exc_info()

    log = 'EXCEPTION \n'
    log += '    EX_TYPE  : ' + str(ex_type) + ' \n'
    log += '    EX_VAL   : ' + str(ex_val) + ' \n'
    log += '    EX_TRACK : \n'
    for stack in traceback.extract_tb(ex_stack):
        log += '        ' + str(stack) + ' \n'

    prefix = 'EX_LOG_'
    if filename != '':
        prefix += filename + '_'
    logToFile(log, prefix, logdir)

    print('\033[0;30;41m', log, '\033[0m')


# 将日志信息记录在文件中
def logToFile(logStr, prefix='log_', dir='/tmp/exlog/'):

    if os.path.exists(dir) == False:
        os.makedirs(dir)

    f = open(dir + prefix + getLocaleDateStrDefault(time.time(), '_'), 'w')
    f.write(logStr)
    f.close()


def getCurrentFilename():
    return os.path.basename(sys.argv[0]).split(".")[0]


# 启动守护进程
def daemonize(func):

    # 从父进程fork一个子进程出来
    pid = os.fork()
    # 子进程的pid一定为0，父进程大于0
    if pid:
        # 退出父进程，sys.exit()方法比os._exit()方法会多执行一些刷新缓冲工作
        # print('fork pid >>>',pid)
        pidStr = 'RUN_' + getCurrentFilename() + '_pid_' + str(pid)
        logToFile(pidStr, pidStr + '_')
        sys.exit(0)

    # 子进程默认继承父进程的工作目录，最好是变更到根目录，否则回影响文件系统的卸载
    os.chdir('/')
    # 让子进程成为新的会话组长和进程组长
    os.setsid()
    # 子进程默认继承父进程的umask（文件权限掩码），重设为0（完全控制），以免影响程序读写文件
    os.umask(0)

    # 注意了，这里是第2次fork，也就是子进程的子进程，我们把它叫为孙子进程
    _pid = os.fork()
    if _pid:
        # 退出子进程
        pidStr = 'RUN_' + getCurrentFilename() + '_pid_' + str(_pid)
        logToFile(pidStr, pidStr + '_')
        sys.exit(0)

    # 此时，孙子进程已经是守护进程了，接下来重定向标准输入、输出、错误的描述符(是重定向而不是关闭, 这样可以避免程序在 print 的时候出错)

    # 刷新缓冲区先，小心使得万年船
    sys.stdout.flush()
    sys.stderr.flush()

    # dup2函数原子化地关闭和复制文件描述符，重定向到/dev/nul，即丢弃所有输入输出
    with open('/dev/null') as read_null, open('/dev/null', 'w') as write_null:
        os.dup2(read_null.fileno(), sys.stdin.fileno())
        os.dup2(write_null.fileno(), sys.stdout.fileno())
        os.dup2(write_null.fileno(), sys.stderr.fileno())

    # 执行被守护的函数
    func()
