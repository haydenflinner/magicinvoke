=======================================
``*args`` and ``**kwargs`` support!
=======================================
.. _args-kwargs:

Try it!
--------
``invoke run mytask these are positional --flag1 keyword!``::

    invoke myfunc pos args --flag1 hi --flag2 there
    ('pos', 'args') {'flag1': 'hi', 'flag2': 'there'}

tasks.py
--------

.. literalinclude:: tasks.py
   :linenos:
   :language: python
