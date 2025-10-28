##############
Developer docs
##############

This page contains information useful to people wanting to contribute changes to a :term:`patchset`.

************
Installation
************

.. note::

   Patchtree is developed and tested on \*NIX-like operating systems.
   Windows compatibility is not tested or guaranteed.
   The output .patch files can of course be used anywhere where ``git apply`` works.

Make sure you have the following dependencies installed:

* Python 3 and pip
* Coccinelle (optional, see :ref:`processors`)

Installation can be done by cloning this repository and running

.. code::

   $ pip install .

This will install any missing Python dependencies automatically as well.

To check if the installation was successful, run:

.. code::

   $ patchtree -h

************
Nomenclature
************

.. glossary::

   target
     A directory of files to be modified (e.g. SDK or library releases).

   inputs
   patchset
     A set of files that describe how to change the target source tree(s), placed in the same structure as the original source tree.

   patch
     A single file (usually ``.patch`` or ``.diff``) that lists changes to make to one specific target directory.

**********************
Building clean patches
**********************

In order to generate clean patches files, patchtree needs

* the (original) :term:`target` source tree (either as a folder or .zip file)
* a set of :term:`inputs`

The basic syntax of the patchtree CLI is as follows:

.. code:: none

   $ patchtree TARGET INPUT [INPUT ...]

.. note::

   The inputs are interpreted as globs.

By default, the resulting patch is written to the standard output.
This behavior, along with many other default behaviors can be changed through the command-line arguments (see ``--help``) or the `configuration file <ptconfig_>`_.

************************
Writing patchset sources
************************

Each patchset source file is compared to the target source file of the same name, and the resulting diff is output in the clean patch.
This means that the default behavior of files placed in the patchset is to add or replace any file in the target source tree.

Because most of the time only small adjustments have to be made to the target sources, patchtree uses so-called :ref:`processors <processors>`.
Every patchset source is first processed by 0 or more processors, which transform the input's content before it is compared to the target file's content.
These have access to the global :any:`Context` instance, the target file's content, and the (possibly processed) input's content.
This mechanism allows you to describe changes *semantically* so they can apply to multiple versions of-- or variations in the target.

.. _processors:

Processors
==========

Processors are indicated using the hash symbol (``#``) in the filename, and each process the input's contents in a chain.
Processors may optionally take argument(s) separated by a comma (``,``), and arguments may optionally take a value delimited by an equal sign (``=``)
After processing, the resulting file content is compared to the target source's content using difflib's unified_diff algorithm.

For example:

.. code:: none

   sdk/middleware/adapters/src/ad_crypto.c#cocci#jinja
   \_____________________________________/\__________/
           target source file path         processors

In the above example, the input is first processed by jinja, and the resulting file content is piped into Coccinelle as if a file with the output from jinja existed under the name ``ad_crypto.c#cocci``.
Coccinelle will in this case output a modified copy of ``ad_crypto.c``, which will be compared to the original to produce the diff for this file.

All processors included with patchtree are listed below:

.. toctree::
   :maxdepth: 1

   processor.rst

Custom processors can be created by inheriting from the base :any:`Process` class and registering through the `configuration file <ptconfig_>`_'s :any:`processors <Config.processors>` value.

.. _ptconfig:

******************
Configuration file
******************

The configuration file is a Python file sourced from ``ptconfig.py`` relative to the current working directory when executing the ``patchtree`` command.
This file is a regular Python source file and can contain any arbitrary code.
Any global definitions with an identical name to a member variable of the :any:`Config` class will override the global configuration instance's value.

For example:

.. code:: none

   diff_context = 0
   output_shebang = True
