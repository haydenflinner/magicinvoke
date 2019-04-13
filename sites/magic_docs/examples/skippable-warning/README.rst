=======================================
Careful with @skippable!
=======================================

.. _skippable-warning:

Skippable Warning
-----------------
`Magicinvoke` does not keep track of transitive calls that tasks make within
their code. This isn't generally a problem as long as you only mark your
slow functions as skippable (and keep your runners / functions that iterate
over different args while calling out to slow tasks non-skippable), but
here's an example and some possible workarounds. Although it is
possible to recognize this and account for it within
``magicinvoke``, it's not implemented.

**tasks.py**

.. literalinclude:: tasks.py
   :linenos:
   :language: python

``unsafe_run_and_summarize`` will only run once as it doesn't take any input
files as arguments, even if the value of global_filenames is changed or the
file at ``./x`` is modified,
as its output will exist after running it once.

**Workarounds**

If your summary doesn't take long, you could just remove @skippable.
You could also include all of the input_files as parameters on
``run_and_summarize``.

If ``unsafe_run_and_summarize`` weren't a 'parameterizing' loop, and instead
just a step in a chain of dependencies, you could represent the dependencies
between the steps with ``pre`` and ``post`` Task properties, as demonstrated
here: :ref:`data-pipeline`.

You could also take all of your input/output files as arguments, and pass them
into ``get_tool_output``. In this particular case, you could move this hardcode
of filenames within the function and it would re-run if the list of files
were changed, though not if someone modified one of the 'input' files on disk.

Note that this problem with unrecognized transitivity applies to all checks.
For example, changing a line of code in ``unsafe_run_and_summarize`` will cause
it to be re-run, but changing a line of code in ``get_tool_output`` will fall
to the same issue as with filenames.
