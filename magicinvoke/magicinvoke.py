import collections
import os
from functools import partial
import functools
import hashlib
import itertools
import logging

try:
    from pathlib import Path  # Py3
    from inspect import signature
except:
    from funcsigs import signature
    from pathlib2 import Path  # Py2

from invoke import Collection, task, Lazy, run  # noqa
from invoke.tasks import Task
from invoke.vendor.decorator import decorator, getfullargspec

from cachepath import CachePath


def enable_logging(disable_invoke_logging=True):
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    logging.getLogger("invoke").setLevel(logging.WARNING)


LOG_FORMAT = "%(name)s.%(module)s.%(funcName)s: %(message)s"
if os.getenv("MAGICINVOKE_DEBUG"):
    enable_logging()


log = logging.getLogger("magicinvoke")
for x in ("debug",):
    globals()[x] = getattr(log, x)


def get_params_from_ctx(func=None, path=None, derive_kwargs=None):
    """
    Derive parameters for this function from ctx, if possible.

    :param str path:
        A path in the format ``'ctx.arbitraryname.unpackthistomyparams'``
        to use to find defaults for the function.
        Default: ``'ctx.myfuncname'``

        You shouldn't need to pass this unless you rename your function and don't
        want to modify old configs, or if you'd like to pull the config for a lot
        of tasks from the same place in ctx.

    :param Callable derive_kwargs:
        Overkill. Is passed ``ctx`` as first arg, expected to
        return dict of the format ``{'argname': 'defaultvalueforparam'}``.
        Default: ``ctx.get(func.__name__)``.

    **Why do I need this?** Suppose this configuration\:

    ``ctx = {"myfuncname" : {"requiredparam1" : 392, "namedparam2" : 199}}``

    And this task, where it's important that we always have a value
    for some parameter, but we don't always want to supply
    it from the command-line::

        @task
        def myfuncname(ctx, requiredparam=None, namedparam2=None):
            requiredparam1 = requiredparam1 or ctx.myfuncname.requiredparam1
            if not requiredparam1:
                raise ValueError("Need a value for requiredparam1, but didn't want
                                user to always have to give one.")
            namedparam2 = namedparam2 or ctx.myfuncname.namedparam2
            print(requiredparam1, namedparam2)

    This task can be invoked from the command line like so::

        $ invoke myfuncname
        (392, 199)

    Other functions/tasks can re-use our task with custom parameters, and
    the cmd-line user can override our config's defaults if he or she wishes.

    However, the semantics of this function are hidden behind the boilerplate
    of finding values for each argument.

    ``Requiredparam1`` and ``namedparam2`` are really required, we just can't
    reveal that in the function signature, or ```invoke``` will force the user
    to give one every time they call our task, even though we have a default in
    the config we defined.

    One solution is something like this::

        def myfuncname(ctx, requiredparam1, namedparam2):
            print(param1, requiredparam1)::

        @task(name=myfuncname)
        def myfuncname_task(ctx, requiredparam1=None, namedparam2=None)
            requiredparam1 = namedparam1 or ctx.myfuncname.namedparam1
            namedparam2 = namedparam2 or ctx.myfuncname.namedparam2
            myfuncname(ctx, requiredparam1, namedparam2)

    This solution decouples the core of your code from invoke, which
    could be seen as a plus. However, if we were going to write this much
    boiler-plate and passing stuff around, we could have stuck with argparse.

    Also, notice that each parameter name appears *6 times*, and the function name
    appears *3 times*. Maybe it's not the worst nightmare for maintainability,
    but it sure gives writing a new re-usable task quite a lot of friction, so
    most just won't do it. They'll write the task, and you'll either get runtime
    ``Nones`` because you forgot to load a newly added param from the ctx, or you'll
    have a cmd-line experience so painful that people generate calls to your
    task from their own configs and scripts.

    Here's a better solution. It mirrors the logic of the above pair of functions,
    but with a simple decorator instead.::

        @task
        @get_params_from_ctx
        def myfuncname(ctx, requiredparam1, namedparam2='trulyoptional')
            print(requiredparam1, namedparam2)

        ns.configure({"myfuncname" : {"requiredparam1" : 392}})

    The semantics of the raw python function now match the cmd-line task:

    * You can call it with no arguments, and as long as a proper value is
      found in ctx or in the signature of the function, it will run just like
      you called it from the cmd-line.

    * If no value was passed, and no default can be found, you will get a normal
      Python error.

    The cascading order for finding an argument value is as follows:

    * directly passed (i.e. task(ctx, 'arghere') or --arg arghere on cmd line

    * config (ctx) (defaults to ctx.func.__name__)

    * derive_kwargs your callable that you shouldn't ever need :)

    * callable defaults - default parameter values that are callable are called
      with callable(ctx) to get the value that should be used for a default.

    * actual defaults - the regular defaults in the function header.


    **Advanced Usage** The source is relatively simple, but you can imagine
    it works like this:

    ``**user_provided_args_and_kwargs.update(ctx[yourfunctionname])``

    with more error checking. As such, you can tell us where to look for
    arguments, if you'd like. This is equivalent to the default::

        @get_params_from_ctx(path='ctx.myfuncname')
        def myfuncname(ctx, requiredparam1, namedparam2='trulyoptional'):
            print(requiredparam1, namedparam2)

    Note that you can add an arbitrary number of dots to this. That is:
    'ctx.another_level.xyz.myfuncnameargs' is a valid value for the path.

    Secret way: If your default is a callable (which doesn't mean anything
    for most Invoke tasks), we will call it with ctx. That is::

        @get_params_from_ctx(path='ctx.myfuncname')
        def myfuncname(ctx, requiredparam1,
            namedparam1=lambda ctx: ctx.othertask.controlflag):
            print(requiredparam1, namedparam1)

    You can also provide a function for derive_kwargs, which augments
    the user passed kwargs.

    .. versionadded:: 0.1
    """
    if func is None:  # Dirty hack taken from the wrapt documentation :)
        return partial(
            get_params_from_ctx, derive_kwargs=derive_kwargs, path=path
        )

    if path and path.endswith("."):
        raise ValueError(
            "Path can't end in .! Try 'ctx' instead of 'ctx.', if you want the global namespace."
        )

    # Only up here to we can use it to generate ParseError when decorated func gets called.
    sig = signature(func)

    @functools.wraps(func)
    def customized_default_decorator(*args, **kwargs):
        """
        Creates a decorated function with the same argument list,
        but with almost every parameter optional. When called,
        looks for actually required params in ctx. Finally, calls
        original function.
        """

        # TODO re-write most of stuff that uses get_directly_passed
        # with funcsigs
        directly_passed = get_directly_passed(func, sig, args, kwargs)

        # Task.__call__ will error before us if ctx wasn't passed
        # If you error here, rename your first arg (c) or (ctx) :)
        ctx = args[0]

        class fell_through:  # Cheapest sentinel I can come up with
            pass

        def try_directly_passed(param_name):
            if param_name in directly_passed:
                returning = directly_passed.pop(param_name)
                return returning
            return fell_through

        def call_derive_kwargs_or_error(param_name):
            err = None
            result_cache = None
            try:
                result_cache = derive_kwargs(ctx) if derive_kwargs else {}
            except AttributeError as e:
                err = (
                    "Failed to get parameter values from your derive_kwargs function!\n"
                    "Exception encountered:\n{}".format(e.args[0])
                )
            if err:
                raise AttributeError(err)

            return result_cache.get(param_name, fell_through)

        def traverse_path(param_name):
            if path is None:
                # TODO Maybe have access to namespaced name by now?
                return ctx.config.get(func.__name__, {}).get(
                    param_name, fell_through
                )
            seq = path.split(".")
            looking_in = ctx.config
            seq.pop(0)
            while seq:
                key = seq.pop(0)
                looking_in = looking_in[key]
            return looking_in.get(param_name, fell_through)

        param_name_to_callable = {
            param_name: param.default
            for param_name, param in signature(func).parameters.items()
            if param.default is not param.empty and callable(param.default)
        }

        def call_callable(param_name):
            if param_name in param_name_to_callable:
                return param_name_to_callable[param_name](ctx)
            return fell_through

        args_passing = {}
        expecting = getfullargspec(func).args
        for param_name in expecting:
            # Decide through cascading what to use as the value for each parameter
            possibilities = (
                # First, positionals and kwargs
                try_directly_passed,
                # Then check ctx
                traverse_path,
                # ...
                call_derive_kwargs_or_error,
                call_callable,
            )

            passing = fell_through
            for p in possibilities:
                passing = p(param_name)
                if passing is not fell_through:
                    break

            if passing is not fell_through:
                args_passing[param_name] = passing

        ba = sig.bind_partial(**args_passing)
        # Apply defaults isn't there on funcsig version.
        missing = []
        for param in sig.parameters.values():
            if param.name not in ba.arguments and param.default is param.empty:
                missing.append(param.name)
        if missing:
            msg = "{!r} did not receive required positional arguments: {}".format(
                func.__name__,
                ", ".join(
                    repr(p_name)
                    for p_name, p in list(sig.parameters.items())[1:]
                    if (
                        p.kind is p.POSITIONAL_ONLY
                        or p.kind is p.POSITIONAL_OR_KEYWORD
                    )
                    and p_name not in ba.arguments
                ),
            )
            raise TypeError(msg)
        if directly_passed:
            msg = "{!r} received arguments it didn't recognize: {}".format(
                func.__name__,
                ", ".join(repr(p_name) for p_name in directly_passed.keys()),
            )
            raise TypeError(msg)
        # Now that we've generated a kwargs dict that is everything we know about how to call
        # this function, call it!
        # debug("Derived params {}".format({a: v for a, v in args_passing.items() if a != 'ctx' and a != 'c'}))
        return func(**args_passing)

    myparams = [
        p.replace(default=None) if p.default is p.empty else p
        for p in sig.parameters.values()
    ]
    # Don't provide default for ctx
    myparams[0] = list(sig.parameters.values())[0]
    mysig = sig.replace(parameters=myparams)
    generated_function = customized_default_decorator
    generated_function.__signature__ = mysig
    # print('sig here ', mysig.parameters)

    return generated_function


InputPath = "input"
OutputPath = "output"
Skipped = "Skipped because output files newer than all input files."


def _hash(obj):
    # Hope your __str__ doesn't include things that don't matter :)
    import re

    # TODO automated coverage of plain; it's the one I use so usually good,
    # but doesn't hurt
    if os.getenv("MAGICINVOKE_PLAINTEXT_ARGS"):
        s = obj
        s = str(s).strip().replace(" ", "_")
        # TODO make sure:
        # func name gets included in this that way colliding param lists don't
        # cause issues
        # and pretty this up, it's horrid. Make it
        # func.__name arg1 arg2 arg3 --kv 1 --kv2 2
        return re.sub(r"(?u)[^-\w.]", "-", s)
    return hashlib.sha224(obj.encode("utf-8")).hexdigest()


@decorator
def skippable(func, *args, **kwargs):
    """
    Decorator to skip function if input files are older than output files.

    You can use this to write functions that are like make-targets.

    We derive your input and output paths from a combo of three ways:

    1. A parameter name has 'input', or 'output' in it. For example::

           @skippable
           def mytask(input_path, outputpath1, myoutput):
               pass

       would be interpreted by this decorator as

           ``{'inputs': [input_path], 'outputs': [outputpath1, myoutput]}``

       but note that in the future we might also require ``path`` to be in the name
       to allow passing open file descriptors or other things that happen to be
       named similarly.

    2. A parameter is type-annotated with ``magicinvoke.InputPath``/
       ``magicinvoke.OutputPath`` or ``[InputPath/OutputPath]``::

           from magicinvoke import InputPath, skippable
           @skippable
           def mytask(path1: InputPath, input_paths: [InputPath]):
                pass

    3. Params that aren't otherwise classified, but that have ``path`` in their
       name, will be classified as 'inputs' for the sake of determining if we
       should run your function or not. This is mostly a concession to Py2,
       but also helps if you're taking the path of an executable and don't want
       to annotate it as an ``InputPath``.::

           @skippable
           def run_complex_binary(config_path, binary_path, output_paths):
               pass

       would be interpreted by this decorator as

           ``{'inputs': [config_path, binary_path], 'outputs': output_path}``

    4. ``@skippable(extra_deps=lambda ctx:
       ctx.buildconfig.important_executable_path)`` *TODO support this*

    How it works: We use the timestamps of your input filenames and output
    filenames in much the same way as make (i.e. just compare modified timestamp)
    However, we also put a file in $TMPDIR that records the arguments given to
    your function. That way, a function like this works as expected::

        def get_output(input_path, output_path, flag_that_changes_output):
            pass

    By default, _all_ arguments that aren't filepaths are considered significant
    (except first arg if named c/ctx i.e. invoke-style). However, you can mark an
    argument as not-significant to the output by starting its name with an
    underscore::

        def get_output(input_path, output_path, _flag_that_doesnt_affect_output):
            pass

    .. versionadded:: 0.1
    """

    def to_list_if_not_already(val):
        """
        >>>to_list_if_not_already('xyz')
        ['xyz']
        >>>to_list_if_not_already(['xyz'])
        ['xyz']
        """
        if not (isinstance(val, list) or isinstance(val, tuple)):
            # I don't like checking types explicitly in python, but I can't think of a more
            # reliable way that wouldn't include strings in py2.
            return [val]
        else:
            return val

    """
    Here's the plan:
      Create two lists; one for filenames and one for arguments that don't start with _.
      Pass the filenames through to the original content of this function;
      Last_Ran with these parameters must be newer than input_filenames
      Fresh last_ran per set of parameters. Database?
    """
    sig = signature(func)
    # bind here to get the error..
    ba = sig.bind(*args, **kwargs)
    # Since we don't have getcallargs on Py2
    for param in sig.parameters.values():
        if param.name not in ba.arguments:
            ba.arguments[param.name] = param.default
    # Name ctx so that we can try to support regular functions, not just Tasks. Untested.
    if len(ba.arguments.items()) == 0:
        raise ValueError(
            "This shouldn't be a skippable task, it has no in or out params or ctx."
        )

    # This is where we hack popping out ctx if the function is a task. Could
    # probably drop this; what are the odds someone uses @skippable on a
    # regular function.
    name_and_args = (
        list(ba.arguments.items())[1:]
        if list(ba.arguments.keys())[0] in ["c", "ctx"]
        else ba.arguments.items()
    )

    params_that_are_filenames = []

    def look_for_variables_with(type_annotation, words_to_match):
        returning = []
        for param_name, runtime_value in name_and_args:
            # Assume whole list is of one type, that is List<type(list[0])>.
            # Don't write more complex annotations than that, please :)
            annotation = to_list_if_not_already(
                sig.parameters[param_name].annotation
            )[0]
            if (
                annotation
                and annotation is type_annotation
                or any(w in param_name.lower() for w in words_to_match)
            ) and param_name not in params_that_are_filenames:
                params_that_are_filenames.append(param_name)
                returning.extend(to_list_if_not_already(runtime_value))
        return returning

    output_filenames = look_for_variables_with(OutputPath, [str(OutputPath)])
    input_filenames = look_for_variables_with(
        InputPath, [str(InputPath), "path", "file"]
    )

    could_change_behavior = [
        (param_name, argument_value)
        for param_name, argument_value in name_and_args
        # if param_name not in params_that_are_filenames and
        if not param_name.startswith("_")
    ]
    care_about = ", ".join(
        "{}:{!r}".format(param_name, argument_value)
        for param_name, argument_value in could_change_behavior
    )
    if care_about:
        last_ran_with_these_params = str(
            CachePath("magicinvoke", _hash(care_about))
        )
        input_filenames.append(last_ran_with_these_params)

    # Gonna leave these here in case anyone wants to use them later :D
    func.outputs = output_filenames
    func.inputs = input_filenames

    debug(
        "for func {}, inputs: {} outputs: {}".format(
            func.__name__, input_filenames, output_filenames
        )
    )
    # Try to coerce before tiemstamp_differ to avoid cryptic error msg
    for p in itertools.chain(input_filenames, output_filenames):
        try:
            Path(p)
        except:
            # TODO could keep around the info about which param name caused it
            # If you wanted to, you could monkeypatch magicinvoke.Input/Output
            # :)
            raise ValueError(
                "Unable to coerce {} to Path. Do you have a "
                "parameter with 'input' or 'output' in its name "
                "that is not meant to be a Path?".format(p)
            )
    skippable, youngest_input, reason = timestamp_differ(
        input_filenames, output_filenames
    )
    debug(
        "{}skipping {} because {}".format(
            "not " if not skippable else "", func.__name__, reason
        )
    )
    if skippable:
        return Skipped
    result = func(*args, **kwargs)
    if not care_about:  # There were no flags that could affect output.
        return result
    """
    There could be a racy condition here if someone changes one of the output
    files between your function returning and us creating this file. But if
    that happens, why are you writing the file at all?
    """
    # TODO do these touches with raw python
    if youngest_input:
        # All files existed, so we can just use the timestamp of the youngest input
        # for our 'last ran' file.
        run(
            "touch -r '{}' '{}'".format(
                youngest_input, last_ran_with_these_params
            )
        )
    else:
        # Could be a few cases.
        # All of the params were valid and the function ran;
        #     We'd prefer a last_ran older than our oldest output
        # Some of the params were invalid and the function ran non-ideally
        #     We don't want to create a last_ran.
        # To figure out which case we're in, we'll just re-use timestamp differ :)
        input_filenames.remove(last_ran_with_these_params)
        skippable, youngest_input, _ = timestamp_differ(
            input_filenames, output_filenames
        )
        if skippable and youngest_input:  # All is well, all files were found!
            run(
                "touch -r '{}' '{}'".format(
                    youngest_input, last_ran_with_these_params
                )
            )

    return result

    # TODO Write something that cds to all the example folders and runs them :)


def timestamp_differ(input_filenames, output_filenames):
    """
    :returns: Two-tuple:
      [0] -- True if all input files are older than output files and all files exist
      [1] -- Path of youngest input.
      [2] -- Why we're able to skip (or not).
    """
    # Always run things that don't produce a file or depend on files.
    if not input_filenames or not output_filenames:
        return (
            False,
            None,
            "has_inputs:{} has_outputs:{}".format(
                bool(input_filenames), bool(output_filenames)
            ),
        )

    # If any files are missing (whether inputs or outputs),
    # run the task. We run when missing inputs because hopefully
    # their task will error out and notify the user, rather than silently
    # ignore that it was supposed to do something.
    paths = itertools.chain(input_filenames, output_filenames)
    for p in paths:
        if not Path(p).exists():
            return False, None, "{} missing".format(p)

    # All exist, now make sure oldest output is older than youngest input.
    PathInfo = collections.namedtuple("PathInfo", ["path", "modified"])

    def sort_by_timestamps(l):
        l = (PathInfo(path, Path(path).stat().st_mtime) for path in l)
        return sorted(l, key=lambda pi: pi.modified)

    oldest_output = sort_by_timestamps(output_filenames)[0]
    youngest_input = sort_by_timestamps(input_filenames)[-1]
    skipping = youngest_input.modified < oldest_output.modified
    return (
        skipping,
        youngest_input.path,
        "youngest_input={}, oldest_output={}".format(
            youngest_input, oldest_output
        ),
    )


def get_directly_passed(func, sig, args, kwargs):
    """Matches up *args and **kwargs to the variable names that the function expects.
    >>>def mytest(ctx, required0, named0=None):
    >>>    pass
    >>>get_directly_passed(mytest, args=['lolctx', 'requiredval0'], kwargs={'named0': 'val0'})
    {'ctx': 'lolctx', 'required0': 'requiredval0', 'named0': 'val0'}

    Don't call it on itself! Or do, I'm not the cops.
    """

    try:
        ba = sig.bind_partial(*args, **kwargs)
    except TypeError as e:
        if "too many" in e.args[0]:
            msg = "{!r} accepts {} arguments but received {}".format(
                func.__name__,
                len(
                    [
                        p
                        for p in sig.parameters.values()
                        if p.kind is p.POSITIONAL_OR_KEYWORD
                        or p.kind is p.POSITIONAL_ONLY
                    ]
                ),
                # Might not be 100% correct
                len(args) + len(kwargs),
            )
            raise TypeError(msg) from None
        if "unexpected keyword" in e.args[0]:
            msg = "{!r} ".format(func.__name__)
            # from None -- handy trick to get rid of that crappy default error
            raise TypeError(msg + e.args[0]) from None
        raise

    for param in sig.parameters.values():
        if param.name not in ba.arguments:
            ba.arguments[param.name] = param.default

    expecting = getfullargspec(func).args
    name_to_posarg = {name: arg for name, arg in zip(expecting, args)}
    # Throw in all of kwargs so that we still error out if someone gives us extra kwargs.
    for k, v in kwargs.items():
        if k not in expecting:
            # Actually this is probably kwargs but oh well, it works
            msg = "{!r} does not accept these arguments {}".format(
                func.__name__, ", ".join(repr(k))
            )
            raise TypeError(msg)
        name_to_posarg[k] = v
    name_to_posarg.update(kwargs)
    return name_to_posarg


def magictask(*args, **kwargs):
    """
    An ``invoke.task`` replacement that supports make-like file dependencies and
    convenient arg defaulting from the ctx.

    .. important::
        List of extras over `invoke.Task`

        1. You can configure your Tasks just like you configure invoke's `run`
           function. See :meth:`magicinvoke.get_params_from_ctx` for more::

               @magictask
               def thisisatask(ctx, arg1):
                   print(arg1)
               ns.configure({'arg1':'default for a positional arg! :o'})

        2. Your task won't run if its output files are newer than its input files.
           See :meth:`magicinvoke.skippable`'s documentation for more details and help.

    This decorator is just a wrapper for the sequence::

        @task
        @get_params_from_ctx
        @skippable
        def mytask(ctx):
            pass

    .. versionadded:: 0.1
    """
    # Shamelessly stolen from `invoke.task` :)
    klass = kwargs.pop("klass", Task)
    collection = kwargs.pop("collection", None)
    get_params_args = {
        arg: kwargs.pop(arg, None) for arg in ("path", "derive_kwargs")
    }
    # @task -- no options were (probably) given.
    if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Task):
        t = klass(get_params_from_ctx(skippable(args[0])), **kwargs)
        if collection is not None:
            collection.add_task(t)
        return t
    # @task(options)
    def inner(inner_obj):
        obj = klass(
            get_params_from_ctx(skippable(inner_obj), **get_params_args),
            # Pass in any remaining kwargs as-is.
            **kwargs
        )
        if collection is not None:
            collection.add_task(obj)
        return obj

    return inner


def _ns_task(self, *args, **kwargs):
    # @task -- no options were (probably) given.
    if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Task):
        t = task(args[0])
        self.add_task(t)
        return t
    # All other invocations are just task arguments, without the function to wrap:
    def inner(f):
        t = task(f, *args, **kwargs)
        self.add_task(t)
        return t

    return inner


def _ns_magictask(self, *args, **kwargs):
    return magictask(*args, collection=self, **kwargs)


# Monkeypatch Collection :)
Collection.task = _ns_task
Collection.magictask = _ns_magictask