from pathlib import Path

# Hardcode our sources, but we could automagically detect them.
sources = ["a.c", "b.c", "c.c"]


# Setup a workspace.
prefix = Path("./ws")
prefix.mkdir(exist_ok=True)
sources = [prefix / s for s in sources]


# Configure an dict that will supply defaults to all of our arguments
def replace_suffix(replacing_list, with_what):
    return list(s.with_suffix(with_what) for s in replacing_list)


myinfo = dict(
    cfiles=sources,
    objectfiles=replace_suffix(sources, ".o"),
    executable_path=prefix / "produced_executable",
)


# Explicitly point out that these functions take ^ that info dict.
# In the future, it might make sense to do something like a class-based structure,
# where each task is just a method on a class, and the class's member variables
# get populated from config / cmd-line args. For now, since ctx doesn't live past
# task changes, I'm not sure how best to do that.
clean = (
    mycompile
) = invokemycompile = link = run = touch = write_all_the_programs = myinfo
run["echo"] = True
run["pty"] = False
