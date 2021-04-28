# https://huey.readthedocs.io/en/latest/index.html

from huey.contrib.mini import MiniHuey

huey = MiniHuey()
huey.start()


@huey.task()
def add(a, b):
    return a + b


def test1():
    r = add.schedule((1, 2), delay=1)
    print(r())


def test2():
    task = add.s(1, 2)
    result = huey.enqueue(task)


if __name__ == '__main__':
    test2()
    huey.stop()
