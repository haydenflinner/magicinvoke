from invoke import task

@task
def myfunc(ctx, *args, **kwargs):
    print(args, kwargs)
