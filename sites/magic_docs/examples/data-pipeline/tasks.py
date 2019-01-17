from __future__ import print_function

from magicinvoke import Collection, Lazy, Path

ns = Collection()


@ns.magictask(params_from="ctx.people")
def get_peoples_ages(ctx,
                     names_path,
                     names_and_ages_output_path=Lazy("ctx.people.names_and_ages_path"),
                     important_flag=False
):
    o = open(names_and_ages_output_path, "w")
    for name in Path(names_path).read_text().splitlines():
        print("Getting age for {}".format(name))
        # We can pretend this is an expensive processing step where we pull
        # some numbers from a DB :)
        print("{name},{age}".format(name=name, age=39), file=o)
    print("Done writing results to {}".format(names_and_ages_output_path))


@ns.magictask(params_from="ctx.people")
def print_peoples_ages(ctx, names_and_ages_path):
    # Explicit __call__ of get_peoples_ages has same effect as putting it in
    # magictask.pre: still won't run if not necessary.
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




"""
Don't mind rest of this file :)
Our integration tests run `invoke tests` ensure examples behave as expected
"""

@ns.magictask
def test(ctx):
    from textwrap import dedent
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

    assert "cleaned all" in get_peoples_ages(ctx, clean=True).lower()

    both_ran(ctx.run("invoke print-peoples-ages").stdout)
    only_print_ran(ctx.run("invoke print-peoples-ages").stdout)

    # If you run `inv test` twice, this both_ran will fail; the fact that it's
    # not necessary to run print-peoples-ages is stored over in /tmp/.
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
    ctx.run("invoke get-peoples-ages --clean")
    both_ran(ctx.run("invoke print-peoples-ages").stdout)
    print("We're good!")
