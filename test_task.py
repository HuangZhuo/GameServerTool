# https://huey.readthedocs.io/en/latest/index.html
from huey import SqliteHuey

huey = SqliteHuey()


@huey.task()
def add(a, b):
    return a + b


def main():
    r = add.schedule((1, 2), delay=0)
    print(r(blocking=True))


if __name__ == '__main__':
    main()
