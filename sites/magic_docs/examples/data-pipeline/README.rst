=======================================
Easily caching expensive tasks
=======================================
.. _data-pipeline:

Data pipeline
--------------
``invoke test``

You should observe that the 'expensive' get step only happened the first time.

**tasks.py**

Below is a relatively simple tasks file that defines a few tasks. A couple
which do something expensive, and cache their results on the filesystem:

  * get_people - Writes a list of names to ``people.txt`` in line-separated form
  * get_peoples_ages - Writes a list of names + ages to ``people-with-ages.txt``
    in line-separated form
  * print-peoples-ages - Prints the data found in ``people-with-ages.txt``


These tasks depend on :meth:`magicinvoke.skippable` to recognize that they
don't need to actually execute if their output files are newer than
any input files (or in the case of ``get_people``, the output file exists).
That is, once calling ``print-peoples-ages`` once, ``get-people`` and
``get-peoples-ages`` should be skipped every subsequent time, unless
someone modifies ``people.txt`` or the parameters to ``get-peoples-ages``
changes.

.. literalinclude:: tasks.py
   :linenos:
   :language: python
