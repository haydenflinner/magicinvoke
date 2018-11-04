Welcome to magicinvoke!
==================

Magicinvoke is a Python (2.7 and 3.4+) library based on
`Invoke <http://pyinvoke.org>`_.

It adds ``get_params_from_ctx``, ``skippable``, and ``magictask``. 

Other included goodies are
``import magicinvoke.colored_traceback``, which will work
if 
`colored_traceback <https://pypi.org/project/colored-traceback/>`_
is installed and is a no-op otherwise,
and
`DotMap <https://pypi.org/project/dotmap/>`_ as ``magicinvoke.dotdict``.

For examples of what magicinvoke can do you for you, please see the docstrings
for the `magicinvoke` module and `magictask` decorator.

For getting started with a project, we recommend you start with ``invoke``
and then switch your imports to ``magicinvoke`` once you feel the need
for a bit more power. See ``examples`` for techniques available with
``magicinvoke``.

For a high level introduction, including example code, please see `invoke's main
project website <http://pyinvoke.org>`_; or for detailed API docs, see `their
versioned API website <http://docs.pyinvoke.org>`_. or the sourcecode of
magicinvoke.
