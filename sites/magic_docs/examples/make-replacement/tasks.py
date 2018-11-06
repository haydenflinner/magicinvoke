import itertools
from textwrap import dedent

from magicinvoke import magictask, get_params_from_ctx, InputPath, OutputPath

"""Yes, I'm aware that this should not be used as a build tool :)"""

# First, write a .c file with a ``main`` and some other ones to be 'libraries'.
@magictask(derive_kwargs=lambda ctx: dict(executable_cfile=ctx.sources[0]))
def write_all_the_programs(ctx, executable_cfile, cfiles):
    ctx.run("echo 'int main(void){return 255;}' > " + str(executable_cfile))
    ctx.run("touch " + " ".join(str(x) for x in cfiles))


# Then compile them
@magictask
def mycompile(ctx, cfiles, objectfiles: [OutputPath]):
    [
        ctx.run("gcc -c {} -o {}".format(c, o))
        for c, o, in zip(cfiles, objectfiles)
    ]


# This function re-uses our original compile, letting mycompile fall back to
# defaults defined in ctx.
@magictask
def testmycompile(ctx):
    return mycompile(ctx)


# Now we link them into our final executable...
@magictask(pre=[mycompile])
def link(ctx, objectfiles: [InputPath], executable_path: OutputPath):
    ctx.run(
        "gcc -o {} {}".format(
            executable_path, " ".join(str(f) for f in objectfiles)
        )
    )


# And finally run the executable without warn=True, so we should exit with
# an error code.
@magictask(pre=[link])
def run(ctx, executable_path: InputPath):
    # We could have also just called
    # link(ctx) here, because of how @skippable is implemented it has no real
    # dependency on invoke
    ctx.run("{}".format(executable_path))


# This task provided so that you can poke the files yourself and see that we
# only run the tasks that are necessary :)
@magictask
def touch(ctx, cfiles):
    for f in cfiles:
        ctx.run("touch {}".format(f))


@magictask
def clean(ctx, cfiles, objectfiles, executable_path, dry_run=False):
    removing = " ".join(
        str(p) for p in itertools.chain(cfiles, objectfiles, [executable_path])
    )
    if dry_run:
        print(removing)
        return
    ctx.run("rm {}".format(removing), warn=True)


# It's awful, but since the output changes when you import structlog,
# and I wrote these 'tests' assuming no color (i.e. raw string matching)
# we have to import structlog for this test to work.
import structlog

@magictask
def test(ctx):
    # Whole pipeline should run when c sources change.
    expected_stdout = dedent(
        """
        gcc -c ws/a.c -o ws/a.o
        gcc -c ws/b.c -o ws/b.o
        gcc -c ws/c.c -o ws/c.o
        gcc -o ws/produced_executable ws/a.o ws/b.o ws/c.o
        ws/produced_executable
    """
    )
    # Note how we don't have to pass all the defaults in from ``ctx`` here :)
    clean(ctx)
    write_all_the_programs(ctx)

    res = ctx.run("invoke run", warn=True)
    assert expected_stdout.strip() == res.stdout.strip()

    # Test 2, Only last step should run if next to last step's output changed.
    expected_stdout = dedent(
        """
        gcc -o ws/produced_executable ws/a.o ws/b.o ws/c.o
        ws/produced_executable
    """
    )
    ctx.run("touch {}".format(ctx.link.objectfiles[0]))
    res = ctx.run("invoke run", warn=True)
    assert expected_stdout.strip() == res.stdout.strip()

    print("All tests succeded.")
