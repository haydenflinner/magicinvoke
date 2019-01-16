from __future__ import print_function
from invoke import task


@task
def myfunc(ctx, *args, **kwargs):
    """Note there is a bug where we couldn't do
    def mine(ctx, myvar, *args, **kwargs):

    But something is better than nothing :) Search "todo args"
    to find the comment describing my expected fix.
    """
    print(args, kwargs)
