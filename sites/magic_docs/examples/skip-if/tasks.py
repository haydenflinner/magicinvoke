from invoke import task
import os


@task(skip_ifs=[task(lambda ctx: os.getenv("SKIP_MYTASK", False))])
def mytask(ctx):
    print("Didn't skip!")
