from magicinvoke import magictask, task, get_params_from_ctx
from magicinvoke.exceptions import DerivingArgsError
from cachepath import CachePath
from invoke import Context, Config
from invoke.config import Lazy
import six

import pytest


def forgot_ctx():
    with pytest.raises(TypeError):

        @task
        def _bad_test_task(*args, **kwargs):
            pass

    with pytest.raises(TypeError):

        @task
        def _bad_test_task_2(ctx, *args, **kwargs):
            pass

        _bad_test_task_2("x")


@pytest.fixture
def ctx():
    return Context()


def args_kwargs(ctx):
    @task
    def _test_task(ctx, *args, **kwargs):
        return args, kwargs

    r = _test_task(ctx, "hi", mykwarg="hi")
    assert "hi" in r[0] and "mykwarg" in r[1]


def expand_ctx(ctx):
    ctx = Context(Config({"magic": {"test_task": {"x": 1, "y": 2}}}))
    # Dirty remap since qualname on py3 does a better job.
    ctx.magic.expand_ctx = {"<locals>": {"test_task": lambda ctx: ctx.magic.test_task}}

    @magictask
    def test_task(ctx, x, y=None):
        return x, y

    r = test_task(ctx)
    assert r[0] == 1 and r[1] == 2


def expand_ctx_path():
    ctx = Context(Config({"random": {"test_task": {"x": 1, "y": 2}}}))

    @magictask(params_from="ctx.random.test_task")
    def test_task(ctx, x, y=None):
        return x, y

    r = test_task(ctx)
    assert r[0] == 1 and r[1] == 2


def callable_default():
    ctx = Context(Config({"x": 1, "z": 2}))

    @magictask(params_from="ctx")
    def test_task(ctx, x, y=lambda ctx: ctx.z):
        return x, y

    r = test_task(ctx)
    assert r[0] == 1 and r[1] == 2


def proper_order_false():
    ctx = Context(Config({"x": False}))

    @magictask(params_from="ctx")
    def test_task(ctx, x=True):
        return x

    r = test_task(ctx)
    assert not r

def test_task_without_ctx():
    @task(no_ctx=True)
    def test_task():
        return
    assert test_task() is None

def call_calls_pres():
    global_d = {}

    @task
    def pre(ctx):
        global_d["pre"] = True

    @task
    def post(ctx):
        global_d["post"] = True

    @task
    def skip_if(ctx):
        global_d["skip_if"] = True
        return False

    @magictask(pre=[pre], post=[post], skip_ifs=[skip_if])
    def hi2(ctx):
        return

    hi2(Context())
    assert global_d["pre"] and global_d["post"] and global_d["skip_if"]


from magicinvoke import skippable


def test_class_methods_skippable():
    class _MyClass(object):
        @skippable
        # @staticmethod
        # TypeError: <staticmethod object> is not a callable object
        # Python sucks sometimes :(
        def func(self, val):
            self.ran = True
            return val

    def test_case(m0):
        assert not hasattr(m0, "ran")
        assert m0.func(True)
        assert m0.ran

        m0.ran = False
        m0.func(True)
        assert not m0.ran
        m0.func(False)
        assert m0.ran

        m0.ran = False
        m0.func(True)
        m0.func(False)
        assert not m0.ran

    # Have to use non-temp objects to prevent interpreter giving us
    # same address (and thus same __repr__) for multiple "self"s.
    m0 = _MyClass()
    m1 = _MyClass()
    m2 = _MyClass()

    test_case(m0)
    test_case(m1)
    test_case(m2)


def test_doesnt_call_non_lazy_ctx_values():
    c = Config(defaults={"bad": lambda x, y: True})
    assert c.bad(1, 2)

class test_nice_errors_for_skippables():
    def _raise_func(self, ctx):
        raise ValueError('good!')

    def test_raising_param_default(self):
        @get_params_from_ctx
        def myfunc(ctx, x=self._raise_func):
            return x

        with pytest.raises(DerivingArgsError):
            myfunc()
    def test_config_instead_context(self):
        @task
        @get_params_from_ctx
        def myfunc(cfg, x=Lazy('ctx.x')):
            return x
        assert myfunc(Config(defaults={'x': True})) is True

        # To test error msgs
        # @task
        # def myfunc(cfg, x=Lazy('ctx.x')):
        # raise ValueError("crap")
        # myfunc(Config())

    def test_fail_to_pickle_exception(self):
        from magicinvoke.exceptions import SaveReturnvalueError
        @skippable
        def fail_to_pickle(x=lambda: None):
            return x
        with pytest.raises(SaveReturnvalueError):
            fail_to_pickle()

    def test_forgot_ctx_param(self):
        with pytest.raises(ValueError) as exc:
            @get_params_from_ctx(path='ctx.abc')
            def a():
                pass
        assert 'context arg' in str(exc.value)

    def test_forgot_to_pass_ctx(self):
        @magictask
        def myfunc(ctx, x):
            pass
        with pytest.raises(TypeError) as exc:
            myfunc(Context())
        assert "myfunc' did not receive required positional arguments: x" in str(exc)

    def test_bad_path_to_skippable(self):
        @skippable
        def myfunc(output_path):
            pass
        # Also implicitly tests that myfunc(None) doesn't cause
        # myfunc(badpath) to be skipped
        myfunc(None)  # Allowed
        with pytest.raises(TypeError) as exc:
            myfunc(lambda z: 'x')  # Allowed
        assert 'invalid path' in str(exc.value)
        # @get_params_from_ctx(myarg=Lazy('x.y.z'))

    def test_too_many_args(self):
        @get_params_from_ctx
        def mine(ctx):
            pass
        with pytest.raises(TypeError) as e:
            mine(x=2, y=3, z=4)
        assert 'unexpected keyword' in str(e) if six.PY3 else 'takes 1 arguments but 3 were given' in str(e)
        with pytest.raises(TypeError) as e:
            mine(1, 2, 3, 4)
        assert 'mine(ctx) takes 1 arguments but 4 were given' in str(e)

    def misc_test_coverage(self):
        @skippable
        def optional_param(opt=1):
            pass
        optional_param()

        @get_params_from_ctx(path='ctx')
        def test(ctx, a):
            pass
        with pytest.raises(DerivingArgsError) as e:
            test(None)
        assert 'Cannot get dict from' in str(e.value)

        # assert 'did not receive required' in str(e.value)

        with pytest.raises(ValueError) as e:
            @get_params_from_ctx(path='x')
            def test1(ctx, a):
                pass
        assert 'must start with' in str(e.value)

        @get_params_from_ctx(path='ctx.a.b.c')
        def test(ctx, a):
            pass
        with pytest.raises(DerivingArgsError) as e:
            test(Context())
        assert 'while traversing path' in str(e.value)

    def test_flags_change_recall(self):
        @skippable
        def build(output_path, flag=True):
            output_path.touch()
            return flag
        p = CachePath('lol')
        assert build(p)
        assert not build(p, False)

    def test_can_pass_cfg(self):
        @get_params_from_ctx
        def myfunc(cfg, x=Lazy('c.x')):
            return x
        assert myfunc(Config(defaults={'x': True}))



# ------ Integration-y tests; run the examples
@pytest.mark.parametrize(
    "folder, cmd, expected_output, py2_only",
    [
        ("args-kwargs", "invoke myfunc x --z 1", "('x',) {'z': '1'}\n", False),
        (
            "data-pipeline",
            "pytest --capture=no -k test_this",
            "We're good!",
            False,
        ),
        ("make-replacement", "invoke test", "All tests succeeded.", True),
        ("skip-if", "invoke mytask", "Didn't skip!", False),
    ],
)
def test_full_integration(folder, cmd, expected_output, py2_only, tmpdir):
    # --durations=10, you will see each one gets run twice, maybe fix?
    ctx = Context()
    assert ctx.pformat()
    with ctx.cd("sites/magic_docs/examples/{}".format(folder)):
        result = ctx.run(
            "TMPDIR={} {}".format(tmpdir, cmd), hide=True, warn=py2_only
        ).stdout
        try:
            assert expected_output in result
        except:
            if py2_only and six.PY2:
                pytest.xfail("We knew that.")
            raise
