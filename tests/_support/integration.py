"""
A semi-integration-test style fixture spanning multiple feature examples.

If we're being honest, though, the new 'tree' fixture package is a lot bigger.
"""

from invoke.tasks import task
from magicinvoke import magictask, Lazy


@task
def print_foo(c):
    print("foo")


@task
def print_name(c, name):
    print(name)


@magictask(params_from="ctx.x.y")
def print_x_y_z(ctx, z):
    # Tests both parameter expansion and used to test -D x.y.z syntax
    print(z)


@magictask
def callable_defaults(ctx, z=lambda ctx: ctx.x.y.z):
    # Tests both callable defaults and callables in ctx.
    print(z)
    ctx.x.y.z = lambda ctx: 5
    print(ctx.x.y.z)
    ctx.mylazy = Lazy("ctx.x.y.z")
    print(ctx.mylazy)


@task
def print_underscored_arg(c, my_option):
    print(my_option)


@task
def foo(c):
    print("foo")


@task(foo)
def bar(c):
    print("bar")


@task
def post2(c):
    print("post2")


@task(post=[post2])
def post1(c):
    print("post1")


@task(foo, bar, post=[post1, post2])
def biz(c):
    print("biz")


@task(bar, foo, post=[post2, post1])
def boz(c):
    print("boz")
