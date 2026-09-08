Welcome to MagicInvoke!
=========================

Magicinvoke is a Python (2.7 and 3.4+) library based on
`Invoke <http://pyinvoke.org>`_.

It adds ``get_params_from_ctx``, ``skippable``, and ``magictask``,
as well as support for ``*args`` and ``**kwargs`` on tasks,
some clearer exceptions, and some minor bugfixes.

WARNING
-------

Installing magicmock will REPLACE the source code of any existing invoke installation
with the patched copie of invoke included in magicmock. However, it does not update the
.dist-info directory, so it will appear that you have  whatever version of invoke you
installed (e.g. 1.7.3) but the code will in fact be magicmock's patched copy, which is
currently at 1.2.

You can check with:

.. code-block:: python

  >>> import invoke
  >>> invoke.__version__
  '1.2.0'


This may lead to unexpected behaviour, and features added after 1.2 will not be available.

Parallel installers (such as poetry) may also mangle the file in invoke as a result of this.

We are looking into alternative ways of implementing magicmock's functionality, but until then,
please use with caution.

For docs and to see what magicinvoke has to offer you,
`see here <https://magicinvoke.readthedocs.io>`_.

Report issues and help out `here <https://github.com/haydenflinner/magicinvoke>`_.

For getting started , we recommend you start with ``invoke``
and then start mixing in ``magicinvoke`` once you feel the need
for a bit more power. See the
`examples <https://magicinvoke.readthedocs.io/en/latest/#jump-in>`_
page of the ``magicinvoke`` doc.
