from invoke.tasks import task
from magicinvoke import magictask


@task
def foo(c):
    print("Hm")


@magictask
def mfoo(c):
    print("Hm")
