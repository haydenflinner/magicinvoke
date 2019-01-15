from __future__ import print_function

from magicinvoke import Collection, Lazy, Path

ns = Collection()


# This addition (ns.task decorator) courtesy of @judy2k :)
@ns.magictask(path="ctx.people")
def get_peoples_ages(
    ctx,
    names_path,
    # You could just use no default and type-annotate as an OutputPath
    # instead of ensuring `output` is in the name, but that breaks Py2
    names_and_ages_output_path=Lazy("ctx.people.names_and_ages_path"),
    important_flag=False,
):
    """
    names_path: File where each line is a person's name
    names_and_ages_path: Output file where each line is person's name,age
    important_flag: Doesn't actually change output, but magicinvoke
    will treat it like it does because it doesn't start with `_`.
    """
    o = open(names_and_ages_output_path, "w")
    for name in Path(names_path).read_text().splitlines():
        print("Getting age for {}".format(name))
        # We can pretend this is an expensive processing step where we pull
        # some numbers from a DB :)
        print("{name},{age}".format(name=name, age=39), file=o)
    print("Done writing results to {}".format(names_and_ages_output_path))


@ns.magictask(path="ctx.people")
def print_peoples_ages(ctx, names_and_ages_path):
    """
    names_and_ages_path: File where each line is a person's name, age
    Prints the names and ages found therein
    """
    # Explicit __call__ has same effect as putting it in .pre, still won't run
    # if not necessary.
    get_peoples_ages(ctx)
    print("Reading results from {}".format(names_and_ages_path))
    for line in Path(names_and_ages_path).read_text().splitlines():
        name, age = line.split(",")
        print("{name}'s age is {age}".format(name=name, age=age))
    print("Done!")


ns.configure(
    {
        "people": {
            "names_path": "people.txt",
            "names_and_ages_path": "people-with-ages.txt",
        }
    }
)


@ns.magictask(path="ctx.people")
def test(ctx):
    from textwrap import dedent

    """Don't mind me; I'm just here to ensure examples behave as expected :)"""
    only_print_expected_stdout = dedent(
        """
        Reading results from people-with-ages.txt
        Tom's age is 39
        Jerry's age is 39
        Bill Nye's age is 39
        Done!
        """
    )
    both_stdout = dedent(
        """
        Getting age for Tom
        Getting age for Jerry
        Getting age for Bill Nye
        Done writing results to people-with-ages.txt
        Reading results from people-with-ages.txt
        Tom's age is 39
        Jerry's age is 39
        Bill Nye's age is 39
        Done!
        """
    )

    def only_print_ran(stdout):
        assert stdout.strip() == only_print_expected_stdout.strip()

    def both_ran(stdout):
        assert stdout.strip() == both_stdout.strip()

    # TODO add a MagicTask.clean so that don't have accidents like when I just
    # deleted people.txt lol
    ctx.run("rm {}".format(ctx.people.names_and_ages_path), warn=True)

    # print(repr(ctx.run('invoke print-peoples-ages').stdout.strip))
    # print(repr(both_stdout))
    both_ran(ctx.run("invoke print-peoples-ages").stdout)
    only_print_ran(ctx.run("invoke print-peoples-ages").stdout)
    # If you run this test twice, this both_ran will not work; the fact that it's
    # not necessary is held over in /tmp/. Delete it.
    both_ran(
        ctx.run(
            "invoke -D people.important_flag=True print-peoples-ages"
        ).stdout
    )
    only_print_ran(
        ctx.run(
            "invoke -D people.important_flag=True print-peoples-ages"
        ).stdout
    )
    only_print_ran(ctx.run("invoke print-peoples-ages").stdout)
    only_print_ran(ctx.run("invoke print-peoples-ages").stdout)
    print("We're good!")
