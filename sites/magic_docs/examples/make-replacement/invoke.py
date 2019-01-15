from pathlib import Path

# Setup a workspace when config is loaded because why not
prefix = Path("./ws")
prefix.mkdir(exist_ok=True)

# Hardcode our sources, but we could automagically detect them.
sources = ["a.c", "b.c", "c.c"]
sources = [prefix / s for s in sources]


def replace_suffix(replacing_list, with_what):
    return list(s.with_suffix(with_what) for s in replacing_list)


# Configure an dict that will supply defaults to all of our arguments
mycompileinfo = dict(
    cfiles=sources,
    objectfiles=[source.with_suffix(".o") for source in sources],
    executable_path=prefix / "produced_executable",
)

# Turn on echoing so that we can see it work
run = {"echo": True}
