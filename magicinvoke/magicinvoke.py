import collections
from functools import partial
import itertools

try:
    from pathlib import Path  # Py3
except:
    from pathlib2 import Path  # Py2

from invoke import task, Collection
from invoke.tasks import Task
from invoke.vendor.decorator import (
    decorator,
    getfullargspec,
    FunctionMaker,
    decorate,
)


def get_params_from_ctx(func=None, path=None, derive_kwargs=None):
    """
    Derive parameters for this function from ctx, if possible.

    :param str path:
        A path in the format ``'ctx.arbitraryname.unpackthistomyparams'``
        to use to find defaults for the function.
        Default: ``'ctx.{}'.format(func.__name__)``

        You shouldn't need to pass this unless you rename your function and don't
        want to modify old configs, or if you'd like to pull the config for a lot
        of tasks from the same place in a ctx.

    :param bool derive_kwargs:
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
            return myfuncname(ctx, requiredparam1, namedparam2)

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
            return print(requiredparam1, namedparam2)

        ns.configure({"myfuncname" : {"requiredparam1" : 392}})

    The semantics of the raw python function now match the cmd-line task:

    * You can call it with no arguments, and as long as a proper value is
      found in ctx or in the signature of the function, it will run just like
      you called it from the cmd-line.

    * If no value was passed, and no default can be found, you will get a normal
      Python error.

    The cascading order for finding an argument value is as follows::

        passing = (directly_passed.get(param_name, None) # First, positionals and kwargs
                    or ctx.config.get(path or func.__name__, {}).get(param_name, None)
                    or call_callback_or_throw(param_name)
                    or fell_through)

    **Advanced Usage** The source is relatively simple, but you can imagine
    it works like this:

    ``**user_provided_args_and_kwargs.update(ctx[yourfunctionname])``

    with more error checking. As such, you can tell us where to look for
    arguments, if you'd like. This is equivalent to the default::

        @get_params_from_ctx(path='ctx.myfuncname')
        def myfuncname(ctx, requiredparam1, namedparam2='trulyoptional')
            return print(requiredparam1, namedparam2)

    Note that you can add an arbitrary number of dots to this. That is:
    'ctx.another_level.xyz.myfuncnameargs' is a valid value for ctx_defaults.

    You can also provide a function, which is a last resort after we check
    in ``ctx`` for your function's name.

    .. versionadded:: 0.1
    """
    if func is None:  # Dirty hack taken from the wrapt documentation :)
        return partial(
            get_params_from_ctx, derive_kwargs=derive_kwargs, path=path
        )

    def create_decorator():
        """
        A decorator that wraps a function in a function with the same argument list,
        but with every parameter optional. When called, this decorator tries to
        find values for each parameter from `ctx.`
        """
        # Have to define the function we're before we can modify
        # its signature ;)
        def customized_default_decorator(*args, **kwargs):
            # __call__ on Task will handle the error before us if ctx wasn't passed
            directly_passed = get_directly_passed(func, args, kwargs)
            ctx = directly_passed["ctx"]

            def call_callback_or_error(param_name):
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

                return result_cache.get(param_name, None)

            def fell_through():  # Cheapest sentinel I can come up with
                pass

            args_passing = {}
            expecting = getfullargspec(func).args
            for param_name in expecting:
                # Decide through cascading what to use as the value for each parameter
                passing = (
                    directly_passed.get(
                        param_name, None
                    )  # First, positionals and kwargs
                    or ctx.config.get(path or func.__name__, {}).get(
                        param_name, None
                    )
                    or call_callback_or_error(param_name)
                    or fell_through
                )
                if passing != fell_through:
                    args_passing[param_name] = passing

            # Now that we've generated a kwargs dict that is everything we know about how to call
            # this function, call it!
            return func(**args_passing)

        # Basically, now that we've generated a decorator that will derive the right values for
        # arguments to pass through to the task, we need to generate a function with the same signature
        # as the originally wrapped task, but with different defaults. We wouldn't need to do this if
        # we could modify the `defaults` section of the arguments to our decorated function (or even
        # the original function before we decorate it) at runtime, but such is life.
        params = getfullargspec(func)
        defaults = params.defaults or ()  # replace None with ()
        num_posargs = (
            len(params.args) - len(defaults) - 1
        )  # -1 -> don't provide default for ctx

        # As far as I can tell from reading the decorator module's documentation, there is no
        # way to generate a function with a runtime-decided header in Python in a similar way to
        # how we manipulate everything else in Python. What we _can_ do, however, is `exec` a
        # declaration :). That's what FunctionMaker does internally, which is why it takes this
        # cryptic looking string as an argument. I copied this from the decorator internals with
        # one modification.
        evaldict = dict(_call_=customized_default_decorator, _func_=func)
        generated_function = FunctionMaker.create(
            func,
            "return _call_(%(shortsignature)s)",
            evaldict,
            __wrapped__=func,
            # Prepend to real function's defaults with Nones. We have to do this because invoke
            # will make the user provide positional arguments, even if there's a good value in ctx.
            # We zip with original defaults (instead of just all None) to get proper type-hinting
            # for cmd-line help.
            # TODO py3 - use defaults of same type as annotation for each param
            # (since None defaults to string in invoke)
            defaults=tuple(
                itertools.chain(itertools.repeat(None, num_posargs), defaults)
            ),
        )
        return generated_function

    return create_decorator()


InputPath = "input"
OutputPath = "output"
Skipped = "Skipped because output files newer than all input files."


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

    .. versionadded:: 0.1
    """

    name_to_arg = get_directly_passed(func, args, kwargs)
    argspec = getfullargspec(func)

    def from_list(val):
        """
        >>>from_list('xyz')
        ('xyz')
        >>>from_list(['xyz'])
        ('xyz')
        """
        if not (isinstance(val, list) or isinstance(val, tuple)):
            # I don't like checking types explicitly in python, but I can't think of a more
            # reliable way that wouldn't include strings in py2.
            # Could try the *operator on each value
            # to a dummy function, but that would behave funny with short / 0/1 length strings.
            return [val]
        else:
            return val

    filtered_args = lambda tester: itertools.chain.from_iterable(
        from_list(runtime_value)
        for argname, runtime_value in name_to_arg.items()
        if tester(argname, runtime_value)
    )

    def tester(type_annotation, words_to_match, argname, runtime_value):
        # Runtime_value could be either a string, or a list of strings!
        annot = from_list(getattr(argspec, 'annotations', {}).get(argname))[0]
        return (
            annot and annot is type_annotation
            or any(w in argname.lower() for w in words_to_match)
        )

    output_filenames = list(
        filtered_args(partial(tester, OutputPath, [OutputPath]))
    )
    input_filenames = list(
        filtered_args(partial(tester, InputPath, [InputPath, "path", "file"]))
    )
    # Because we suck in anything that has 'path' or 'file' in the name as Inputs, we've probably matched
    # with some output variables too. Let's just discard those.
    input_filenames = set(input_filenames) ^ set(output_filenames)

    # Gonna leave these here in case anyone wants to use them later :D
    func.outputs = output_filenames
    func.inputs = input_filenames

    skippable = timestamp_differ(input_filenames, output_filenames)
    if skippable:
        return Skipped
    return func(*args, **kwargs)


def timestamp_differ(input_filenames, output_filenames):
    """
    Returns True if all input files are older than output files, or there
    are none of either (i.e. a source or sink).
    """
    # Always run things that don't produce a file or depend on files.
    if not input_filenames or not output_filenames:
        # log.debug(event="ts_differ.have_to_run", skipping=False)
        return False

    # If any files are missing (whether inputs or outputs),
    # run the task. We run when missing inputs because hopefully
    # their task will error out and notify the user, rather than silently
    # ignore that it was supposed to do something.
    paths = itertools.chain(input_filenames, output_filenames)
    if any(not Path(p).exists() for p in paths):
        # log.debug(event="ts_differ.filemissing", skipping=False, paths=paths)
        return False

    # All exist, now make sure oldest output is older than youngest input.
    PathInfo = collections.namedtuple("PathInfo", ["path", "modified"])

    def sort_by_timestamps(l):
        l = (PathInfo(path, Path(path).stat().st_mtime) for path in l)
        return sorted(l, key=lambda pi: pi.modified)

    oldest_output = sort_by_timestamps(output_filenames)[0]
    youngest_input = sort_by_timestamps(input_filenames)[-1]
    skipping = youngest_input.modified < oldest_output.modified
    # log.debug(event="ts_differ.all_files_exist",
    # youngest_input=youngest_input.path, oldest_output=oldest_output.path,
    # skipping=skipping)
    return skipping


def get_directly_passed(func, args, kwargs):
    """Matches up *args and **kwargs to the variable names that the function expects.
    >>>def mytest(ctx, required0, named0=None):
    >>>    pass
    >>>get_directly_passed(mytest, args=['lolctx', 'requiredval0'], kwargs={'named0': 'val0'})
    {'ctx': 'lolctx', 'required0': 'requiredval0', 'named0': 'val0'}

    Don't call it on itself! Or do, I'm not the cops.
    """
    expecting = getfullargspec(func).args
    name_to_posarg = {name: arg for name, arg in zip(expecting, args)}
    # Throw in all of kwargs so that we still error out if someone gives us extra kwargs.
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
    get_params_args = {
        arg: kwargs.pop(arg, None) for arg in ("path", "derive_kwargs")
    }
    # @task -- no options were (probably) given.
    if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Task):
        return klass(get_params_from_ctx(skippable(args[0])), **kwargs)
    # @task(options)
    def inner(inner_obj):
        obj = klass(
            get_params_from_ctx(skippable(inner_obj), **get_params_args),
            # Pass in any remaining kwargs as-is.
            **kwargs
        )
        return obj

    return inner
