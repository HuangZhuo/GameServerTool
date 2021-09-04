from common import counter


def test_counter():
    c = counter()
    print(c(), c(), c())
    c = counter()
    print(c(), c(), c())


def test_enum():
    # https://stackoverflow.com/questions/43854335/encoding-python-enum-to-json
    import json
    from enum import Enum

    class TestEnum(str, Enum):
        one = "first"
        two = "second"
        three = "third"

    test = {TestEnum.one: "This", TestEnum.two: "should", TestEnum.three: "work!"}
    print(json.dumps(test))


def test_dict():
    d = dict()
    d['k'] = 'v'
    # 注意这个, 导致值是一个元组
    d['k2'] = 'v2',
    d['k3'] = ['v3']
    print(repr(d))


def test_datetime():
    import datetime

    # 当前时间
    now = datetime.datetime.now()
    print(now)  # 2021-09-04 13:32:36.630000

    # 字符串->对象
    # 数据库中的时间格式：2021-08-04 06:08:47
    dbdatetime = '2021-08-04 06:08:47'
    pydatetime = datetime.datetime.strptime(dbdatetime, '%Y-%m-%d %H:%M:%S')
    print(pydatetime)

    # 对象->字符串
    print('strftime', pydatetime.strftime('%Y-%m-%d %H:%M:%S'))

    # 时间差值
    print((now - pydatetime).total_seconds())
    print((pydatetime - now).total_seconds())


if __name__ == '__main__':
    test_datetime()
    pass