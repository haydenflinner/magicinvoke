==================================
Welcome to MagicInvoke!
==================================
 
**MagicInvoke** is an `invoke <http://pyinvoke.org>`_ extension that
adds support for lots of goodies:

* ``*args`` *and* ``**kwargs`` support!
  See how easy it is here: :ref:`args-kwargs`. 

* **Make-like file dependency recognition and work-avoidance!**
  :ref:`make-replacement`
  For more, check out :meth:`magicinvoke.skippable`. Very useful when
  you won't want something as cryptic or platform-specific as Make or bash,
  but you also don't want to go full CMake.

* **Automatic ctx->parameter expansion!**
  Have you ever wondered why you can put ``'run': {'echo': True}`` in
  ``invoke.yaml`` and suddenly ``echo=True`` gets passed to all
  ``ctx.run`` calls, but you **can't do the same for your own tasks?**

  Wonder no longer with :meth:`magicinvoke.get_params_from_ctx`!

* **Arbitrary task filtering!**
    Implements the ``skip_ifs`` argument for tasks, a rename of ``checks`` from
    `from this issue
    <https://github.com/pyinvoke/invoke/issues/461>`_


Jump In
--------
**Beginner's Note** 
`Invoke's documentation <http://pyinvoke.org>`_ is the best place to start,
as the majority of using this library is just like using regular ``invoke``.

.. toctree::
    :maxdepth: 2
    :glob:

    examples/**

Read the doc for :mod:`magicinvoke` or check the below example projects to
see if ``magicinvoke`` can improve ``invoke`` for you!

.. _api:

API Documentation
-----------------
.. toctree::
    :maxdepth: 2
    :glob:

    api/*


Thanks to Invoke
-----------------
This module is 95% ``invoke`` code. All praise for the extensibility, durability
and readability of ``invoke``-using code goes to ``bitprophet`` and friends. 
It's a fun library to use, and here's hoping ``magicinvoke`` gives it the little
boost it needs for big, monolithic projects, and serves as a testing-grounds
for potentially breaking features like ``**kwargs`` on tasks, since I'm too lazy
to write enough tests to get into the real ``invoke`` library!

If you enjoy them (but not too often), you should also thank Anton Backer for
the very handy
``colored-traceback``.


