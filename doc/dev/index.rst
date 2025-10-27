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

Each patchset source applies to exactly one target source file, and describes any changes that should be made to that file.
When possible, patchset source files should describe changes *semantically* so they can apply to multiple versions of or variations in the target.
Patchtree allows you to do using a combination of :ref:`processors <processors>` and :ref:`diff engines <diffs>`.

Every patchset source is first processed by 0 or more processors.
These are indicated using the hash symbol (``#``) in the filename, and each process the input's contents sequentially from right to left.
After processing, the resulting file content is compared to the target source's content using a diff engine.
The diff engine is selected based on the file extension.

Example:

.. code:: none

                                file extension (.c)
                                        /\
   sdk/middleware/adapters/src/ad_crypto.c#cocci#jinja
   \_____________________________________/\__________/
           target source file path         processors
                                        (jinja -> cocci)

.. _processors:

Processors
==========

Processors transform the input's content before it is compared to the target file's content.
They can be chained, and are applied in reverse order (i.e. from right to left) from how they appear in the filename.
Each processor has access to the global :any:`Context` instance, the target file's content, and the (possibly processed) input's content.

The processors included with patchtree are listed below.

.. toctree::
   :maxdepth: 1

   processor.rst

Custom processors can be created by inheriting from the base :any:`Process` class and registering through the `configuration file <ptconfig_>`_'s :any:`processors <Config.processors>` value.

.. _diffs:

Diff engines
============

Diff engines dictate how the diff delta is calculated from the (possibly processed) input and the target file's content.

.. TODO: Diff engines are stupid, merge strategies can just as well be handled
   by processors since they have access to the appropriate state and variables

The diff engines included with patchtree are listed below.

.. toctree::
   :maxdepth: 1

   diff.rst

Similar to processors, custom diff engines can be created by inheriting from the base :any:`Diff` class and registering through the `configuration file <ptconfig_>`_'s :any:`diff_strategies <Config.diff_strategies>` value.

.. _ptconfig:

******************
Configuration file
******************

The configuration file is a Python file sourced from ``ptconfig.py`` relative to the current working directory when executing the ``patchtree`` command.
This file can contain arbitrary Python code.
Certain global variables influence the behavior of patchtree when defined.
These variables are the member variables of the :any:`Config` class.
