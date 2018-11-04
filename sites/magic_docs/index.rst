==================================
Welcome to MagicInvoke!
==================================

This site covers MagicInvoke only. For most beginner questions,
you're likely better off on
`Invoke's documentation <http://pyinvoke.org>`_.

MagicInvoke is an ``invoke`` extension that adds support for lots of goodies.

Q1. Have you ever wondered why you can put
    ``'run': {'echo': True}``
    in your ``invoke.yaml`` and suddenly all ``ctx.run``'s that didn't specify
    otherwise magically acted as if you put that kwarg in all your calls to run,
    but you can't do the same for your own custom tasks?

A1. Now you can, check :meth:`magicinvoke.get_params_from_ctx`!

Q2. Are you using ``invoke`` for something like a general build assistant, either
    because Makefiles suck or because you enjoy the comfort of Python?
    Or are you building a custom data / testing pipeline and tired of managing
    the chain of steps in your head, or re-rerunning the entire pipeline every
    time, even if un-necessary?

A2. Fear not: Check out :meth:`magicinvoke.skippable`!


.. _api:

Jump In
--------

.. toctree::
    :maxdepth: 2
    :glob:

    api/*

Getting Started & Examples
-----------------------------

`Invoke's documentation <http://pyinvoke.org>`_ is the best place to start,
as the majority of using this library is just like using regular ``invoke``.

Read the doc for :mod:`magicinvoke` or check the below example projects to
see if ``magicinvoke`` can improve ``invoke`` for you!

.. toctree::
    :maxdepth: 2
    :glob:

    examples/**


Thanks to Invoke
-----------------
This module is 95% ``invoke`` code. All praise for the extensibility, durability
and readability of ``invoke``-using code goes to ``bitprophet`` and friends. 
It's a fun library to use, and here's hoping ``magicinvoke`` gives it the little
boost it needs for big, monolithic projects, and serves as a testing-grounds
for potentially breaking features like ``**kwargs`` on tasks, since I'm too lazy
to write enough tests to get into the real ``invoke`` library!

If you enjoy them, you should also thank Anton Backer for the very handy
``colored-traceback``


