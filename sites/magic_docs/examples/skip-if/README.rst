=======================================
``skip_ifs`` addition to ``invoke``!
=======================================

Try it!
--------
Test with ``SKIP_MYTASK=1 invoke mytask``

Note that you should really use invoke's ctx for getting things from
env / config.

I don't like that skip_ifs have to be tasks, but I'm too lazy to
fix since I added ``@skippable.``

I also don't like that skip_ifs is required to be a list
(why not skip_if?)
why not skip_ifs with func instead of iterable?

tasks.py
--------

.. literalinclude:: tasks.py
   :linenos:
   :language: python
