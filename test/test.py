from datetime import date
import unittest
from src.common import counter


class TestCommon(unittest.TestCase):
    def test_counter(self):
        c = counter()
        self.assertEqual(c(), 0)
        self.assertEqual(c(), 1)
        c = counter(2, 3)
        self.assertEqual(c(), 2)
        self.assertEqual(c(), 5)

    def test_enum(self):
        # https://stackoverflow.com/questions/43854335/encoding-python-enum-to-json
        import json
        from enum import Enum

        class TestEnum(str, Enum):
            one = "first"
            two = "second"
            three = "third"

        test = {TestEnum.one: "This", TestEnum.two: "should", TestEnum.three: "work!"}
        print(json.dumps(test))

    def test_dict(self):
        d = dict()
        d['k'] = 'v'
        # 注意这个, 导致值是一个元组
        d['k2'] = 'v2',
        d['k3'] = ['v3']
        print(repr(d))

    def test_datetime(self):
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

    def test_fmt(self):
        print('octlog{0}'.format(5))  # octlog5
        print('octlog{:d}'.format(5))  # octlog5

    def test_array_2_dict(self):
        arr = [['a', 1], ['b', 2]]
        di = dict(arr)
        print(di)  # works well!

    def test_date(self):
        d = date.today()
        print(d)

    def test_closure(self):
        funcs = []

        def f(i):
            def k():
                return i

            return k

        for i in range(5):
            funcs.append(f(i))
        for f in funcs:
            print(f())
