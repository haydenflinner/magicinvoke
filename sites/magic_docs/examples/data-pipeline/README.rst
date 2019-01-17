=======================================
Cache slow steps transparently!
=======================================
.. _data-pipeline:

Data pipeline
--------------
``invoke print-peoples-ages``

``invoke print-peoples-ages``

You should observe that the 'expensive' get step only happened the first time.

**tasks.py**

Below is a relatively simple tasks file that defines two tasks. One which
does something 'expensive', like get a list of peoples' ages from a database.
The next which just prints those results. The thing to notice
(besides the ns.task decorator and params_from kwarg) is that calling
get_peoples_ages from print_peoples_ages doesn't actually result in the
ages being re-calculated, since :meth:`magicinvoke.skippable` recognizes that
the output
would not change since the inputs haven't changed.

.. literalinclude:: tasks.py
   :linenos:
   :language: python
