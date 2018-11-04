==============================
``magicinvoke`` Documentation
==============================

.. automodule:: magicinvoke
   :members:
   :exclude-members: __colored_traceback, Path, dotdict

.. class:: Path

    Export of vendored (for Py2)
           `pathlib.Path <https://docs.python.org/3/library/pathlib.html>`_

.. class:: dotdict

   Export of vendored
           `DotMap <https://pypi.org/project/dotmap/>`_
     
.. class:: colored_traceback

   Importing ``magicinvoke`` tries to import
   `this library <https://pypi.org/project/colored-traceback/>`_
   to turn on colored
   tracebacks. If the library is unavailable, nothing is different.
   It's a great tool with no real downsides except for
   requiring ``colorama`` on Windows.

   You should also check out
   `tbvaccine <https://github.com/skorokithakis/tbvaccine>`_
