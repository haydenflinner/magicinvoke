from magicinvoke import magictask, task
from invoke import Context, Config
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
    ctx = Context(Config({"test_task": {"x": 1, "y": 2}}))

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
