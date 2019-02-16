import itertools
from textwrap import dedent

from magicinvoke import (
    magictask,
    get_params_from_ctx,
    InputPath,
    OutputPath,
    Lazy,
)

"""Yes, I'm aware that this should not be used as a build tool :)"""


@magictask(params_from="ctx.mycompileinfo", skippable=True)
def write_all_the_programs(
    ctx, cfiles, executable_cfile=Lazy("ctx.mycompileinfo.cfiles[0]")
):
    """First, write a .c file with a ``main`` and some other ones to be 'libraries'."""
    ctx.run("echo 'int main(void){return 255;}' > " + str(executable_cfile))
    ctx.run("touch " + " ".join(str(x) for x in cfiles))


@magictask(params_from="ctx.mycompileinfo", skippable=True)
def mycompile(ctx, cfiles, objectfiles: [OutputPath]):
    """Then compile them"""
    for c, o in zip(cfiles, objectfiles):
        ctx.run("gcc -c {} -o {}".format(c, o))


@magictask(params_from="ctx.mycompileinfo", pre=[mycompile], skippable=True)
def link(ctx, objectfiles: [InputPath], executable_path: OutputPath):
    """Now we link them into our final executable..."""
    ctx.run(
        "gcc -o {} {}".format(
            executable_path, " ".join(str(f) for f in objectfiles)
        )
    )


@magictask(params_from="ctx.mycompileinfo", pre=[link], skippable=True)
def run(ctx, executable_path: InputPath):
    """And finally run the executable, exiting with exitcode=255."""
    # Calling link(ctx) here would would work just as well as pre=[link], but
    #  rather than invoke checking if link needs to run _once_ when the application
    #  starts,  for all tasks that depend on it (see task-deduping page),
    #  we have to check if it needs to be run each time someone calls it.
    #  Given that checking file timestamps is pretty fast, this probably isn't a big deal.
    ctx.run("{}".format(executable_path))


@magictask(params_from="ctx.mycompileinfo")
def touch(ctx, cfiles):
    """
    This task provided so that you can poke the files yourself and see that we
    only run the tasks that are necessary :)
    """
    for f in cfiles:
        ctx.run("touch {}".format(f))


@magictask(params_from="ctx.mycompileinfo")
def clean(ctx, cfiles, objectfiles, executable_path):
    removing = " ".join(
        str(p) for p in itertools.chain(cfiles, objectfiles, [executable_path])
    )
    ctx.run("rm {}".format(removing), warn=True)


@magictask
def test(ctx):
    """Don't mind me; used by automated tests to ensure the example stays working!"""
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
    # The semantics of calling a task from Python now match the cmd-line semantics.
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
    ctx.run("touch {}".format(ctx.mycompileinfo.objectfiles[0]))
    res = ctx.run("invoke run", warn=True)
    assert expected_stdout.strip() == res.stdout.strip()

    print("All tests succeeded.")
