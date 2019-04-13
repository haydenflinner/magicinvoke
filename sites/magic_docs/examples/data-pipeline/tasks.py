from magicinvoke import Collection, Lazy, Path

ns = Collection()

"""
Two types of skippable tasks are demonstrated here:
    1. get_people, which is clearly skippable, because its output goes into a file.
    2. get_peoples_ages, which doesn't create an output file but returns a value.
      a) Magicinvoke implicitly creates a file to cache the return value
         of this function. Your return values must be pickleable.
"""


@ns.magictask(skippable=True)
def get_people(ctx, names_output_path=Lazy("ctx.people.names_path")):
    print("get_people called")
    Path(names_output_path).write_text(u"Tom\nJerry\nBill Nye\n")
    print("Wrote {}".format(names_output_path))


@ns.magictask(params_from="ctx.people", pre=[get_people], skippable=True, autoprint=True)
def get_peoples_ages(ctx,
                     names_path,
                     important_flag=False
):
    results = []
    print("get_peoples_ages called")
    for name in Path(names_path).read_text().splitlines():
        print("Getting age for {}".format(name))
        # We can pretend this is an expensive processing step where we pull
        # some numbers from a DB :)
        results.append((name, 39))
    print("Done pulling results!")
    return results


@ns.magictask
def print_peoples_ages(ctx):
    print("print_peoples_ages called")
    names_and_ages = get_peoples_ages(ctx)
    for tup in names_and_ages:
        print("{name}'s age is {age}".format(name=tup[0], age=tup[1]))
    print("Done!")


ns.configure(
    {
        "people": {
            "names_path": "people.txt",
        }
    }
)


