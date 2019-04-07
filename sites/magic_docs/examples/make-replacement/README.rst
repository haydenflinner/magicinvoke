=======================================
GNU Make Replacement
=======================================
.. _make-replacement:

Make replacement
-----------------
``invoke write-all-the-programs run``

You should end up with an executable under ``ws/`` that exits with code 255.

**tasks.py**

Note the function ``testcompile``, which is just a wrapper for compile
that doesn't have to know anything about the parameters it takes!
That's because of :meth:`magicinvoke.get_params_from_ctx`, which was applied by
:meth:`magicinvoke.magictask`.

.. literalinclude:: tasks.py
   :linenos:
   :language: python

**invoke.py**

.. literalinclude:: invoke.py
   :linenos:
   :language: python
