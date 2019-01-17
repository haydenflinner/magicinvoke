==================================
Welcome to MagicInvoke!
==================================
 
**MagicInvoke** is an `invoke <http://pyinvoke.org>`_ extension that
adds support for lots of goodies:

* ``*args`` **and** ``**kwargs`` **support!**
  See how easy it is here: :ref:`args-kwargs`. 

* **Make-like file dependency recognition and work-avoidance!**
  Check out a basic
  :ref:`data-pipeline`.
  or a Py3-specific, more advanced 
  :ref:`make-replacement`.

  For more, check out :meth:`magicinvoke.skippable`. Very useful when
  you won't want something as cryptic or platform-specific as Make and bash,
  but you also want to use Python tools like matplotlib or numpy.

* **Automatic ctx->parameter expansion!**
  Have you ever wondered why you can put ``'run': {'echo': True}`` in
  ``invoke.yaml`` and suddenly ``echo=True`` gets passed to all
  ``ctx.run`` calls, but you **can't do the same for your own tasks?**

  Wonder no longer with :meth:`magicinvoke.get_params_from_ctx`! Here's how you
  would implement a task like ctx.run::
      @magictask(params_from='ctx')
      def myrun(ctx, cmd, echo=False):
          pass

* **Arbitrary task filtering!**
    Implements the ``skip_ifs`` argument for tasks, a rename of ``checks`` from
    `from this issue
    <https://github.com/pyinvoke/invoke/issues/461>`_

* **Single-step namespaced tasks!**
    Merges the very helpful
    `patch <https://github.com/pyinvoke/invoke/pull/527#issue-189000872>`_
    written by @judy2k.

* **Bugfixes**

  * Fix cryptic error when doing ``ctx.cd(pathlib.Path)`` (#454)
    
  * Fix help documentation for mis-spelled variable names silently being ignored (#409)

  * Fix help documentation with - instead of _ being silently being ignored (#398)

  * Fix silently ignoring config file path  (#560)

  * Fix cryptic error when task passed ``pre=func`` instead of ``pre=[func]``

  * Fix cryptic error when ``@task('func')`` instead of ``@task(func)`` (#598)


Jump In
--------
**Beginner's Note** 
`Invoke's documentation <http://pyinvoke.org>`_ is the best place to start,
as the majority of using this library is just like using regular ``invoke``.
However, you should still install ``pip install magicinvoke`` to get the
improved error messages while you learn.

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
``colored-traceback``, which will be automatically activated if installed.


