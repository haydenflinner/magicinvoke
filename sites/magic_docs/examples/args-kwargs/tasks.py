from __future__ import print_function
from invoke import task
from pprint import pformat


@task
def myfunc(ctx, *args, **kwargs):
    """
    Note there is a bug where we couldn't do
       def mine(ctx, mypositionalarg, *args, **kwargs):
           pass

    But something is better than nothing :) Search "TODO 531"
    to find the comment describing our options.
    Keyword optional args work but they can be filled by positional args
    (because they're not KEYWORD_ONLY!) so we don't recommend their use.
    """
    print("args: {}".format(args))
    print("kwargs: {}".format(pformat(kwargs)))
