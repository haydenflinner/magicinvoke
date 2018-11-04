=======================================
File dependency resolution!
=======================================

Try it!
--------
``pip install structlog`` 

``invoke run``

This was a test project used to test the file timestamp recognition,
pasted here for reference.

invoke.py
----------

.. literalinclude:: invoke.py
   :linenos:
   :language: python

 
tasks.py
--------

Note the function ``testcompile``, which is just a wrapper for compile
that doesn't have to know anything about the parameters it takes!

.. literalinclude:: tasks.py
   :linenos:
   :emphasize-lines: 25-27
   :language: python
