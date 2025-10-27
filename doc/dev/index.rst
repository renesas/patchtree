Developer docs
==============

Installation
************

.. note::

   Patchtree is developed and tested on \*NIX-like operating systems.
   Windows compatibility is not tested or guaranteed.
   The output .patch files can of course be used anywhere where ``git apply`` works.

Make sure you have the following dependencies installed:

* Python 3 and pip
* Coccinelle (optional)

Installation can be done by cloning this repository and running

.. code::

   $ pip install .

This will install any missing Python dependencies automatically as well.

Generating clean patches
************************

In order to generate a clean .patch file, patchtree needs

* the original source tree (either as a folder or .zip file)
* a list of patch files placed in the same structure as the original source tree

Writing patch sources
*********************



.. _config:

Configuration
*************

.. currentmodule:: patchtree.config

The configuration file is a Python file sourced from ``ptconfig.py`` relative to the current working directory when executing the ``patchtree`` command.
This file can contain arbitrary Python code.
Certain global variables influence the behavior of patchtree when defined.
These variables are the member variables of the :class:`Config` class.

Processors
**********

.. currentmodule:: patchtree.process

The processors included with patchtree are listed below.
Custom processors can be created by inheriting from the base :py:class:`Process` class and registering through the `configuration file <config_>`_.

.. toctree::
   :maxdepth: 1

   processor.rst

Diff engines
************

The diff engines included with patchtree are listed below.

.. toctree::
   :maxdepth: 1

   diff.rst
