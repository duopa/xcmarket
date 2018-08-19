import socket
from urllib import request
# import ssl
import json
from chengutil import mysqlutil, util
import time, datetime, _thread, threading

total = 0
runCount = 0


def request_okex_kline_rest(symbol, period, since='', size=2000):
    try:
        url = 'https://www.okex.com/api/v1/kline.do?symbol=%s&type=%s&since=%s&size=%d' % (symbol, period, since, size)
        # url = 'https://www.okex.com/api/v1/ticker.do?symbol=ltc_btc'
        mysqlutil.log('okex', url)
        socket.setdefaulttimeout(20)
        # ssl._create_default_https_context = ssl._create_unverified_context
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            # 'Accept-Language': 'zh-CN,zh;q=0.8',
            'User-Agent': "Mozilla/5.0 (Windows NT 6.1; rv:32.0) Gecko/20100101 Firefox/32.0",
            # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            # "Connection": "close",
            # "Cache-Control": "no-cache"
        }
        req = request.Request(url, None, headers)
        response = request.urlopen(req)
        content = response.read().decode('utf-8')

        # mysqlutil.log('okex', content)
        # mysqlutil.log('okex', 'data len >>>', len(json.loads(content)))
        return json.loads(content)
    except:
        util.printExcept()
        return False


def get_okex_kline_history(period):
    global runCount, count, total, done, doneToken, pendingPeriods, periods

    startDate = datetime.datetime.now()

    db = mysqlutil.init()
    cursor = db.cursor()

    try:

        sql = 'SELECT symbol FROM xcm_okex_symbol'
        cursor.execute(sql)
        symbols = cursor.fetchall()

        symbolCount = 0

        for r in symbols:

            symbol = r[0]
            c = symbol.split('_')
            base = c[0]
            quote = c[1]

            symbolCount += 1
            mysqlutil.log('okex', startDate, period, 'symbol >>>', symbol, symbolCount, '/', len(symbols))

            # 获取最近的一条数据的时间戳
            sql = '''
                SELECT timestamp FROM xcm_okex_kline_history 
                WHERE symbol=%s AND period=%s 
                ORDER BY timestamp DESC LIMIT 0,1
            '''
            cursor.execute(sql, (symbol, period))
            rows = cursor.fetchall()
            lastTimestamp = 0
            if len(rows) == 0:
                since = ''
            else:
                lastTimestamp = rows[0][0]
                # mysqlutil.log('okex', startDate, period, 'last timestamp >>>', str(rows[0][0]))
                mysqlutil.log('okex', startDate, period, 'last datetime >>>', util.getLocaleDateStrBy13(rows[0][0]))
                since = str(rows[0][0] + get_period_interval(period))

            mysqlutil.log('okex', startDate, period, 'period >>>', period)
            if since != '':
                mysqlutil.log('okex', startDate, period, 'since datetime >>>', util.getLocaleDateStrBy13(int(since)))
            kdata = request_okex_kline_rest(symbol, period, since)
            if kdata is False:
                continue
            elif 'error_code' in kdata:
                mysqlutil.log('okex', startDate, period, '\033[0;30;41m error_code >>>', kdata['error_code'], '\033[0m\n')
                continue
            else:
                mysqlutil.log('okex', startDate, period, 'kdata len >>>', len(kdata))
                mysqlutil.log('okex', startDate, period, 'kdata >>>', kdata)
                mysqlutil.log('okex', startDate, period, 'kdata start datetime >>>', util.getLocaleDateStrBy13(kdata[0][0]))

            newTimestamps = []

            for k in kdata:

                newTimestamp = k[0]
                # mysqlutil.log('okex', 'newTimestamp >>>', newTimestamp)
                # TODO: 之所以重复，似乎是同一个时间间隔，有新的交易发生。需要考虑将此重复时间的数据更新到数据库中。
                if lastTimestamp == newTimestamp or newTimestamp in newTimestamps:
                    mysqlutil.log('okex', startDate, period, '\033[0;30;47m duplicated timestamp >>>', k[0], '\033[0m')
                    mysqlutil.log('okex', startDate, period, '\033[0;30;47m duplicated timestamp >>>', util.getLocaleDateStrBy13(k[0]),
                          '\033[0m')
                    continue

                newTimestamps.append(newTimestamp)

                nowTime = time.time()
                nowTime *= 10000000

                sql = '''
                    INSERT INTO xcm_okex_kline_history (
                        _id, symbol,base_currency,quote_currency,period,
                        timestamp,open,high,low,close,vol)
                    VALUES (
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s)'''
                param = (
                    nowTime, symbol, base, quote, period,
                    k[0], k[1], k[2], k[3], k[4], k[5])
                cursor.execute(sql, param)

                count += 1
                total += 1

            db.commit()
            mysqlutil.log('okex', startDate, period, 'begin date >>>', beginDate)
            mysqlutil.log('okex', startDate, period, 'start date >>>', startDate)
            mysqlutil.log('okex', startDate, period, 'current date >>>', datetime.datetime.now())
            mysqlutil.log('okex', startDate, period, 'insert done >>> {:,}'.format(count))
            mysqlutil.log('okex', startDate, period, 'period done >>>', done)
            mysqlutil.log('okex', startDate, period, 'period doneToken >>>', doneToken)
            mysqlutil.log('okex', startDate, period, 'period pending >>>', pendingPeriods)
            mysqlutil.log('okex', startDate, period, 'total >>> {:,}'.format(total))
            mysqlutil.log('okex', 'runCount >>>', runCount, '\n')

        done.append(period)
        doneToken[period] = 1
        pendingPeriods.discard(period)

    except:
        util.printExcept()
    finally:
        cursor.close()
        db.close()

    mysqlutil.log('okex', startDate, period, 'start date >>>', startDate)
    mysqlutil.log('okex', startDate, period, 'end date >>>', datetime.datetime.now())
    mysqlutil.log('okex', startDate, period, 'period done >>>', done)
    mysqlutil.log('okex', startDate, period, 'period doneToken >>>', doneToken)
    mysqlutil.log('okex', startDate, period, 'period pending >>>', pendingPeriods)
    mysqlutil.log('okex', startDate, period, 'total >>> {:,}'.format(total))

    if len(done) == len(periods):
        runCount += 1

    mysqlutil.log('okex', 'runCount >>>', runCount, '\n')


# 计算获取数据的时间间隔
# 时间间隔为当前最新数据的两倍时间
# 返回时间的单位为秒
def get_period_interval(period):
    interval = 0
    if period.find('min') > -1:
        num = int(period.replace('min', ''))
        interval = num * 60 * 1000
    elif period.find('hour') > -1:
        num = int(period.replace('hour', ''))
        interval = num * 60 * 60 * 1000
    elif period.find('day') > -1:
        num = period.replace('day', '')
        num = int(num)
        interval = num * 24 * 60 * 60 * 1000
    elif period.find('week') > -1:
        num = period.replace('week', '')
        num = int(num)
        interval = num * 7 * 24 * 60 * 60 * 1000

    return interval


def get_okex_kline_history_by_peroid():
    init()

    db = mysqlutil.init()
    cursor = db.cursor()

    try:

        global total

        if total == 0:
            sql = 'SELECT count(_id) FROM xcm_okex_kline_history'
            cursor.execute(sql)
            rows = cursor.fetchall()
            if len(rows) != 0:
                total = rows[0][0]

        mysqlutil.log('okex', '\ntotal >>> {:,}'.format(total))
    except:
        util.printExcept()
    finally:
        cursor.close()
        db.close()

    for p in periods:
        mysqlutil.log('okex', 'start period thread >>>', p)
        _thread.start_new_thread(get_okex_kline_history, (p,))


def init():
    global count, done, doneToken, pendingPeriods, periods

    count = 0
    done = []
    doneToken = {
        '1min': 0, '3min': 0, '5min': 0, '15min': 0, '30min': 0,
        '1hour': 0, '2hour': 0, '4hour': 0, '6hour': 0, '12hour': 0,
        '1day': 0,  # '3day': 0,
        '1week': 0
    }
    pendingPeriods = {
        '1min', '3min', '5min', '15min', '30min',
        '1hour', '2hour', '4hour', '6hour', '12hour',
        '1day',  # '3day',
        '1week'
    }
    periods = [
        '1min', '3min', '5min', '15min', '30min',
        '1hour', '2hour', '4hour', '6hour', '12hour',
        '1day',  # '3day',
        '1week'
    ]


if __name__ == '__main__':

    global beginDate
    beginDate = str(datetime.datetime.now())

    currentRunCount = runCount
    get_okex_kline_history_by_peroid()

    while True:
        # 等待获取线程的完成
        if currentRunCount == runCount:
            time.sleep(60)
        else:
            currentRunCount = runCount
            get_okex_kline_history_by_peroid()