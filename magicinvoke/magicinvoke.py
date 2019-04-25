from __future__ import print_function
import collections
import os
from functools import partial
import functools
import hashlib
import itertools
import logging
import pickle

try:
    from pathlib import Path  # Py3
    from inspect import signature, Parameter
except:
    from pathlib2 import Path  # Py2
    from funcsigs import signature, Parameter
from invoke.config import names_for_ctx
from invoke.util import raise_from
from invoke.vendor.six.moves import filterfalse
from invoke import Collection, task, Lazy, run  # noqa
from invoke.tasks import Task
from invoke.vendor.decorator import decorate
from invoke.exceptions import reraise_with_context

import cachepath  # noqa Add .rm to Paths
from cachepath import CachePath

from .exceptions import SaveReturnvalueError, DerivingArgsError

def enable_logging(disable_invoke_logging=True):
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    logging.getLogger("invoke").setLevel(logging.WARNING)


LOG_FORMAT = "%(name)s.%(module)s.%(funcName)s: %(message)s"
if os.getenv("MAGICINVOKE_DEBUG"):
    enable_logging()


log = logging.getLogger("magicinvoke")
debug = "dummy"  # noqa
for x in ("debug",):
    globals()[x] = getattr(log, x)

if os.getenv("MAGICINVOKE_TEST_DEBUG"):
    globals()["debug"] = print


def get_params_from_ctx(func=None, path=None, derive_kwargs=None):
    """
    Derive parameters for this function from ctx, if possible.

    :param str path:
        A path in the format ``'ctx.arbitraryname.unpackthistomyparams'``
        to use to find defaults for the function.
        Default: ``'ctx.mymodulename.myfuncname'``

        It's good to pass this explicitly to make it clear where your arguments
        are coming from.


    :param Callable derive_kwargs:
        Overkill. Is passed ``ctx`` as first arg, expected to
        return dict of the format ``{'argname': 'defaultvalueforparam'}``.

    **Examples**::

        @get_params_from_ctx(path='ctx.randompath')  # just 'ctx' works as well
        def myfuncname(ctx, requiredparam1, namedparam2='trulyoptional'):
            print(requiredparam1, namedparam2)

    If your default is a callable we will call it with ``args[0]``. This is how
    :meth:`invoke.config.Lazy` works under the hood.
    That is, this is a valid function::

        @get_params_from_ctx
        def myfuncname(ctx,
                       namedparam0=Lazy('ctx.mynamedparam0'),
                       namedparam1=lambda ctx: ctx.myvalue * 4):
            print(namedparam1)  # 4, if myvalue == 1 :)

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

        ns.configure({"tasks": {"myfuncname" : {"requiredparam1" : 392}}})

    The semantics of the raw python function now match the cmd-line task:

    * You can call it with no arguments, and as long as a proper value is
      found in ctx or in the signature of the function, it will run just like
      you called it from the cmd-line.

    * If no value was passed, and no default can be found, you will get a normal
      Python error.

    The cascading order for finding an argument value is as follows:

        1. directly passed (i.e. ``task(ctx, 'arghere')`` or ``--arg arghere`` on cmd line
        2. from config (``ctx`` arg) (defaults to ctx.__module__.func.__name__)
        3. function defaults (``def myfunc(ctx, default=1)``) - default parameter values
           that are callable are called
           with callable(ctx) to get the value that should be used for a default.


    .. versionadded:: 0.1
    """
    if func is None:  # Dirty hack taken from the wrapt documentation :)
        return partial(
            get_params_from_ctx, derive_kwargs=derive_kwargs, path=path
        )

    # Only up here to we can use it to generate ParseError when decorated func gets called.
    sig = signature(func)
    func_name = _get_full_name(func)
    func.ctx_path = path or 'ctx.{}'.format(func_name)
    debug("Set {}() param ctx-path to {!r}".format(func_name, func.ctx_path))

    if path:
        if path.endswith("."):
            raise ValueError(
                "Path can't end in .! Try 'ctx' instead of 'ctx.'."
            )
        if path.split(".")[0] not in names_for_ctx:
            raise ValueError(
                "Path {!r} into ctx for {}()'s args must start with 'ctx.' or 'c.'"
                .format(path, func_name)
            )
    user_passed_path = path  # Necessary because otherwise doesn't go into closure on py2.


    @functools.wraps(func)
    def customized_default_decorator(*args, **kwargs):
        """
        Creates a decorated function with the same argument list,
        but with almost every parameter optional. When called,
        looks for actually required params in ctx. Finally, calls
        original function.
        """

        # Will throw here if too many args/kwargs
        directly_passed = get_directly_passed(func, sig, args, kwargs)

        # Task.__call__ will error before us if ctx wasn't passed
        # Might want a non-task to be skippable, so just try to carry on without ctx.
        ctx = args[0] if args else None

        class fell_through:  # Cheapest sentinel I can come up with
            pass
        cache = {'derived': {}, 'ctx_argdict': {}}  # Don't have nonlocal in py2

        def get_directly_passed_arg(param_name):
            return directly_passed.pop(param_name, fell_through)

        def call_derive_kwargs_or_error(param_name):
            if not derive_kwargs:
                return fell_through
            if not cache['derived']:
                cache['derived'] = derive_kwargs(ctx)
            result = cache['derived']
            return result.get(param_name, fell_through)

        def traverse_path_for_argdict():
            # Could just use eval(path) with a similar trick to invoke.Lazy.
            if user_passed_path is None and not ctx:
                return {}  # that's fine
            elif user_passed_path and not ctx:
                # If explicitly ask us to traverse (with a path), but
                # don't give ctx, what can we do?
                # msg = "You gave path {!r} for {!r} args but 'ctx' (arg[0]) was {!r}.".format(path, func_name, ctx)
                msg = "'ctx' (arg[0]) was {!r}. Cannot get dict from {} for args of {!r}.".format(
                    ctx, user_passed_path, func_name
                )
                raise DerivingArgsError(msg)

            path = func.ctx_path
            seq = path.split(".")
            looking_in = ctx.get('config', ctx)  # Gracefully handle Configs (not usual Contexts)
            seq.pop(0)
            while seq:
                key = seq.pop(0)
                try:
                    looking_in = looking_in[key]
                except (KeyError, AttributeError) as e:
                    msg = "while traversing path {!r} for {}() args.".format(path, func_name),
                    if user_passed_path:
                        reraise_with_context(
                            e,
                            msg,
                            DerivingArgsError
                        )
                    else:
                        debug("Ignoring {!r} {}".format(type(e).__name__, msg))
                        return {}
            return looking_in

        def get_from_ctx(param_name):
            if not cache['ctx_argdict']:
                cache['ctx_argdict'] = traverse_path_for_argdict()
            return cache['ctx_argdict'].get(param_name, fell_through)

        param_name_to_callable_default = {
            param_name: param.default
            for param_name, param in signature(func).parameters.items()
            if param.default is not param.empty and callable(param.default)
        }

        def call_callable_default(param_name):
            if param_name in param_name_to_callable_default:
                return param_name_to_callable_default[param_name](ctx)
            return fell_through

        # Decide through cascading what to use as the value for each parameter
        args_passing = {}
        expecting = sig.parameters
        for param_name in expecting:
            possibilities = (
                # First, positionals and kwargs
                get_directly_passed_arg,
                # Then check ctx
                get_from_ctx,
                call_derive_kwargs_or_error,  # Not really used/tested
                call_callable_default,
            )

            passing = fell_through
            for p in possibilities:
                try:
                    passing = p(param_name)
                except Exception as e:
                    if type(e) is DerivingArgsError:
                        raise
                    reraise_with_context(
                        e,
                        "in {!r} step of deriving args for param {!r} of {}()".format(
                            p.__name__, param_name, func_name
                        ),
                        DerivingArgsError
                    )
                if passing is not fell_through:
                    debug("{}(): {} found value {:.25}... for param {!r}".format(
                        func_name, p.__name__, str(passing), param_name)
                    )
                    break
                else:
                    debug("{}(): {} failed to find value for param {!r}".format(func_name, p.__name__, param_name))

            if passing is not fell_through:
                args_passing[param_name] = passing

        # Now, bind and supply defaults to see if any are still missing.
        # Partial bind and then error because funcsigs error msg succ.
        ba = sig.bind_partial(**args_passing)
        # getcallargs isn't there on funcsig version.
        missing = []
        for param in sig.parameters.values():
            if param.name not in ba.arguments and param.default is param.empty:
                missing.append(param.name)
        # TODO contribute these improved error messages back to funcsigs
        if missing:
            msg = "{!r} did not receive required positional arguments: {}".format(
                func_name,
                ", ".join(
                    missing
                )
            )
            raise TypeError(msg)

        # Now that we've generated a kwargs dict that is everything we know about how to call
        # this function, call it!
        # debug("Derived params {}".format({a: v for a, v in args_passing.items()
        # if a != 'ctx' and a != 'c'}))
        # TODO We get an 'unexpected kwarg clean' here in Py2 if try to use it.
        # Funcsigs bug of not respecting __signature__? Review both sources
        return func(**args_passing)

    # myparams = (ctx=None, arg1=None, optionalarg1=olddefault)
    myparams = [
        p.replace(default=None) if p.default is p.empty else p
        for p in sig.parameters.values()
    ]
    if not myparams or myparams[0].name not in names_for_ctx:
        raise ValueError("Can't have a derive_kwargs_from_ctx function that doesn't have a context arg!")
    # Don't provide default for ctx
    myparams[0] = list(sig.parameters.values())[0]
    mysig = sig.replace(parameters=myparams)
    generated_function = customized_default_decorator
    generated_function.__signature__ = mysig
    # print('sig here ', mysig.parameters)

    return generated_function


InputPath = "input"
OutputPath = "output"

def _get_full_name(func):
    return "{}.{}".format(
        func.__module__,
        getattr(func, "__qualname__", func.__name__)
    )


def _hash_str(obj):
    return hashlib.sha224(bytes(obj)).hexdigest()


def _hash_int(obj):
    return int(_hash_str(obj), 16)


class CallInfo(object):
    def __repr__(self):
        return "CallInfo({!r})".format(self.name)

    def __init__(self, func):
        self.name = _get_full_name(func)
        self.code_hash = _hash_str(func.__code__.co_code)
        sig = signature(func)
        self.sig = sig
        self.params_that_are_filenames = []
        self.output_params = self._look_for_params_with(
            OutputPath, [str(OutputPath)]
        )
        self.input_params = self._look_for_params_with(
            InputPath, [str(InputPath), "path", "file"]
        )
        self.params_modify_behavior = [
            param_name
            for param_name in self.sig.parameters
            if not param_name.startswith("_")
            and param_name not in names_for_ctx
            and param_name not in self.output_params
            and param_name not in self.input_params
        ]
        debug(
            "For func {!r}, detected signature: "
            "input_params: {!r}, "
            "output_params: {!r}, "
            "params_modify_behavior: {!r}".format(
                self.name,
                self.input_params,
                self.output_params,
                self.params_modify_behavior,
            )
        )

    def bind(self, args, kwargs):
        # bind here to throw error for too many arguments...
        ba = self.sig.bind(*args, **kwargs)
        # Since we don't have getcallargs on Py2
        self.ba = ba
        for param in self.sig.parameters.values():
            if param.name not in ba.arguments:
                ba.arguments[param.name] = param.default

        self.flags = [
            (param_name, argument_value)
            for param_name, argument_value in self.ba.arguments.items()
            if param_name in self.params_modify_behavior
        ]
        # Input_paths gets mutated later!
        self.output_paths = self._coerce_paths(self.output_params, self.flags)
        self.input_paths = self._coerce_paths(self.input_params, self.flags)
        return self

    def identify(self):
        """Things that make this call to the function unique."""
        yield self.name
        for x in itertools.chain(self.input_paths, self.output_paths, self.flags):
            yield str(x)
        yield self.code_hash

    def persistent_hash(self):
        return sum(_hash_int(x.encode('utf-8')) for x in self.identify())

    def _to_list_if_not_already(self, val):
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

    def _coerce_paths(self, param_names, params_change_behavior):
        returning_paths = []
        for name in param_names:
            runtime_value = self.ba.arguments[name]
            paths = self._to_list_if_not_already(runtime_value)
            # Try to coerce before timestamp_differ to avoid cryptic error
            rejected_values = []
            for p in paths:
                try:
                    returning_paths.append(Path(p))
                except (ValueError, TypeError) as e:
                    msg = (
                        "Received invalid path {!r} "
                        "for path-taking parameter {!r} of {}().".format(p, name, self.name)
                    )
                    # Somewhat complex logic here to allow optional (None) paths as well as required paths,
                    # while not having function mistakenly skipped.
                    if not p:
                        debug(msg)
                        rejected_values.append(p)
                    else:
                        raise type(e)(msg)
            if rejected_values:
                params_change_behavior.append((name, rejected_values))

        return returning_paths

    def _look_for_params_with(self, type_annotation, words_to_match):
        """If param name looks like a filename, returns its arg value."""
        returning = []
        for param_name in self.sig.parameters:
            if param_name in ["ctx", "c"]:
                continue
            # Assume whole list is of one type, that is List<type(list[0])>.
            # Don't write more complex annotations than that, please :)
            annotation = self._to_list_if_not_already(
                self.sig.parameters[param_name].annotation
            )[0]
            if (
                annotation
                and annotation is type_annotation
                or any(w in param_name.lower() for w in words_to_match)
                and not param_name.startswith("_")
            ) and param_name not in self.params_that_are_filenames:
                self.params_that_are_filenames.append(param_name)
                returning.append(param_name)
        return returning

class FileFlagChecker(object):
    """
    Writes a file whose name represents the last call-args used for a task.
    """

    def can_skip(self, ci):
        call_str = "task={}\nflags={}".format(
            ci.name,
            ", ".join(
                "{}:{!r}".format(param_name, argument_value)
                for param_name, argument_value in ci.flags
            )
        )
        debug("Determined call_str {!r} for {!r}".format(call_str, ci))
        self.care_about = _hash_str(call_str.encode('utf-8'))

        self.last_result_path = CachePath(".minv", ci.name, str(ci.persistent_hash()))
        ci.output_paths.append(self.last_result_path)

        if not ci.flags:
            return SkipResult(True, "has no flags")

        failed_path = None
        for output_path in ci.output_paths:
            if not output_path.exists():
                return SkipResult(
                    False, "output {!r} doesn't exist yet".format(output_path)
                )
            # Assumes non-root, but if folder, still works!
            flags_path = self._file_path_for_path(output_path)
            # debug("Checking {!r} for {!r}".format(flags_path, call_str))
            if (
                flags_path.exists()
                and flags_path.read_bytes().decode() != self.care_about
            ):
                failed_path = output_path
        can_skip = not failed_path
        return SkipResult(
            can_skip,
            "{} last generated with {} flags".format(
                ("%s was" % repr(failed_path)) if failed_path else "no files were",
                "same" if can_skip else "different",
            ),
        )

    def _file_path_for_path(self, path):
        """
        Possible schemes:
          1. /tmp/minv/path/goes/here
          2. actualpath.parent/.minv/actualpath.name
          3. A database lol

        We go with 2 here because 1 felt too magic, didn't allow absolute vs
        rel paths, wasn't visible to user.
        """
        p = Path(path.parent, ".minv", path.name)
        p.parent.mkdir(exist_ok=True)
        return p

    def clean(self, ci):
        for path in ci.output_paths:
            self._file_path_for_path(path).rm()
        CachePath(".minv", ci.name).rm()

    def after_run(self, ci):
        """
        """
        for path in ci.output_paths:
            fp_for_path = self._file_path_for_path(path)
            debug("Logging flags for {!r} to {!r}".format(path, fp_for_path))
            fp_for_path.write_bytes(self.care_about.encode())
        try:
            pickle.dump(ci.result, self.last_result_path.open("wb"))
        except Exception as e:
            raise SaveReturnvalueError(*e.args)
        debug(
            "Done logging return value {!r} to {}".format(
                ci.result, self.last_result_path
            )
        )

    def load(self, ci):
        debug(
            "Loading return value for {!r} from {!r}".format(
                ci.name, self.last_result_path
            )
        )
        return pickle.load(self.last_result_path.open("rb"))


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

    3. Params that aren't otherwise classified, but that have ``path``/``file``
       in their name, will be classified as 'inputs' for the sake of
       determining if we should run your function or not. This is a concession
       to Py2, but also helps if you're taking the path of an executable and
       don't want to annotate it as an ``InputPath``.::

           @skippable
           def run_complex_binary(config_path, binary_path, output_paths):
               pass

       would be interpreted by this decorator as

           ``{'inputs': [config_path, binary_path], 'outputs': output_path}``

    4. ``@skippable(extra_deps=lambda ctx:
       ctx.buildconfig.important_executable_path)`` *TODO support this*
       For now, you must just list a .pre which takes that path as an input
       (not as painful as you might imagine) thanks to get_params_from_ctx

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

    """
    Here's the plan:
      Create two lists; one for filenames and one for arguments that don't start with _.
      Pass the filenames through to the original content of this function;
      Last_Ran with these parameters must be newer than input_filenames
      Fresh last_ran per set of parameters. Database?
    """
    # Make sure it has in and out parameters,
    # get some helpful info like output_params
    func.checker = FileFlagChecker()

    # Convince invoke to pass us --clean and --force-run flags
    # I tried pos_or_kwarg here to try to fix PY2; no dice.
    # Perhaps follow_wrapped=False, and contribute that to funcsigs backport
    sig = signature(func)
    myparams = collections.OrderedDict(sig.parameters)
    myparams["_clean"] = Parameter(
        name="_clean", kind=Parameter.KEYWORD_ONLY, default=False
    )
    myparams["_force_run"] = Parameter(
        name="_force_run", kind=Parameter.KEYWORD_ONLY, default=False
    )
    func.__signature__ = sig.replace(parameters=myparams.values())

    return decorate(func, _skippable)


SkipResult = collections.namedtuple("SkipResult", ["skippable", "reason"])


def _skippable(func, *args, **kwargs):
    ci = CallInfo(func).bind(args, kwargs)
    force_run = kwargs.pop("_force_run", False)
    clean = kwargs.pop("_clean", False)

    if clean:
        debug("Cleaning {!r}: {!r}!".format(ci.name, ci.output_paths))
        for p in ci.output_paths:
            p.rm()
        func.checker.clean(ci)
        if not force_run:
            return "Cleaned all {} output files!".format(len(ci.output_paths))

    # Future alternative could be DBFileChecker
    check_result = func.checker.can_skip(ci)
    debug(
        "for func {}, inputs: {} outputs: {}".format(
            ci.name, ci.input_paths, ci.output_paths
        )
    )
    fs_result = _timestamp_differ(ci)

    failing_result = next(
        filterfalse(lambda x: x.skippable, (check_result, fs_result)), None
    )
    # Just use the logs from fs checker if no one complained and forced a run
    result = failing_result if failing_result is not None else fs_result
    debug(
        "{}skipping {!r} because {}".format(
            "not " if not result.skippable else "",
            func.__name__,
            result.reason,
        )
    )

    if result.skippable and not force_run:
        try:
            return func.checker.load(ci)
        except Exception as e:
            # Never seen this happen, but I imagine we would rather degrade
            # to calling the function again rather than quitting or returning
            # a bad value.
            debug("Failed to load cached result for {!r}.".format(ci.name))
            debug(e)

    ci.result = func(*args, **kwargs)
    func.checker.after_run(ci)

    return ci.result


def _timestamp_differ(ci):
    res = timestamp_differ(ci.input_paths, ci.output_paths)
    return SkipResult(res[0], res[1])


def timestamp_differ(input_filenames, output_filenames):
    """
    :returns: Two-tuple:
      [0] -- True if all input files are older than output files and all files exist
      [1] -- Path of youngest input.
      [2] -- Why we're able to skip (or not).
    """
    # Always run things that don't produce a file
    if not output_filenames:
        # No longer covered in tests since magicinvoke.skippable gives a dummy
        # output_filename file for each function for storing its return value.
        # Preserved in case that changes + so that timestamp differ can remain
        # usable outside of its use in this module.
        return (
            False,
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
            # HACK Not the youngest input, but it currently doesn't matter
            return False, "{} missing".format(p)
    if not input_filenames:
        return True, "task's outputs exist, but no inputs required"

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
        # TODO contribute these better error messages back to:
        #   funcsigs or  /usr/lib64/python3.7/inspect.py:3022
        # inspect already has _too_many, but only for getcallargs.
        # Which is basically what this is. So, port getcallargs
        # to funcsigs, use it?
        if "too many" in e.args[0]:
            msg = "{}{} takes {} arguments but {} were given".format(
                func.__name__,
                sig,
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
            raise_from(TypeError(msg), e)
        elif "unexpected keyword" in e.args[0]:
            msg = "{!r} {}".format(func.__name__, e.args[0])
            # from None -- handy trick to get rid of that crappy default error
            raise_from(TypeError(msg), None)
        raise

    return ba.arguments


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

    Note the ``path`` argument on :meth:`magicinvoke.get_params_from_ctx` has been
    renamed to ``params_from`` in this decorator for clearer code.

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
    _skippable = kwargs.pop("skippable", False)
    get_params_args = {
        arg: kwargs.pop(arg, None) for arg in ("params_from", "derive_kwargs")
    }
    get_params_args["path"] = get_params_args.pop("params_from", None)

    # @task -- no options were (probably) given.
    if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Task):
        if _skippable:
            t = klass(get_params_from_ctx(skippable(args[0])), **kwargs)
        else:
            t = klass(get_params_from_ctx(args[0]), **kwargs)
        if collection is not None:
            collection.add_task(t)
        return t

    # @task(options)
    def inner(inner_obj):
        if _skippable:
            obj = klass(
                get_params_from_ctx(skippable(inner_obj), **get_params_args),
                **kwargs
            )
        else:
            obj = klass(
                get_params_from_ctx(inner_obj, **get_params_args), **kwargs
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
