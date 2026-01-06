.. raw:: html

   <style>
   td {
     white-space: normal !important;
     vertical-align: unset !important;
   }
   </style>


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

   patchspec
     A YAML specification that configures how patchtree should handle (other) inputs.

   patch
     A single file (usually ``.patch`` or ``.diff``) that lists changes to make to one specific target directory.

**********************
Building clean patches
**********************

In order to generate clean patches files, patchtree needs

* the (original) :term:`target` source tree (either as a folder or .zip file)
* a set of :term:`inputs` (i.e. the patchset)

The basic syntax of the patchtree CLI is as follows:

.. code:: none

   $ patchtree TARGET [INPUT ...]

By default, the resulting patch is written to the standard output.
This behavior, along with many other default behaviors can be changed through the command-line arguments (see ``--help``) or the `configuration file <ptconfig_>`_.

.. _patchspec:

***********************
Writing patchset inputs
***********************

Each patchset input file is compared using difflib's unified_diff algorithm to the target source file of the same name, and the resulting diff is output in the clean patch.
This means that the default behavior of files placed in the patchset is to add or replace any file in the target source tree.
Because most of the time only small adjustments have to be made to the target sources, patchtree implements mechanisms for semantically describing what changes should be applied.
This is achieved by writing a :term:`patchspec`, which is located either at the start of a patchset input file or as a standalone .yml file in the patchset tree.

.. code-block:: yaml
   :caption: Patchspec header

   --- !patchspec
   foo: bar
   ...

   remaining file content

.. note::

   While patchspec headers look similar to `front matter <https://frontmatter.codes>`_, they are actually regular YAML documents (and must therefore be delimited from the remaining file content using ``...`` instead of ``---``).
   Any valid YAML document at the beginning of a file which explicitly defines a patchspec (using the ``!patchspec`` tag) is processed.
   If a YAML file is present in the patchset but does not define a patchspec, it will be treated as any other text file!

.. code-block:: yaml
   :caption: Standalone patchspec

   !patchspec
   foo: bar

The output from standalone patchspecs are compared against the file in the target of the same name **after the .yml/.yaml extension is removed**.
The file extensions trimmed from standalone patchspecs can be configured using the `configuration file <ptconfig_>`_'s :any:`patchspec_extensions <Config.patchspec_extensions>` value.
Note that a file must both have an extension from the aforementioned list as well as contain a valid patchspec in order to be handled as non-literal input.

=========
YAML tags
=========

In addition to the default tags supported by `PyYAML <https://pyyaml.org/>`_, patchtree supports the following tags:

.. list-table::
   :header-rows: 1

   * - Name
     - YAML type
     - Description
   * - ``!patchspec``
     - mapping
     - Provides patchspec type and value validation and is required in order to make patchtree use the patchspec.
   * - ``!target``
     - scalar
     - Input specification for a file in the target.
       If no filename is passed to this tag, the current filename is used.
       Creates a :any:`TargetFileInputSpec`.
   * - ``!input``
     - scalar
     - Input specification for a file in the patchset (relative to current file).
       If no filename is passed to this tag, the current filename is used.
       Creates a :any:`PatchsetFileInputSpec`.

       .. note::

          Files specified using ``!input`` are no longer treated as a literal (unprocessed) input and will not be compared to a target file of the same name.


================
Patchspec format
================

The patchspec format currently takes the following keys:

.. code-block:: yaml

   !patchspec
   # List of processors to apply (in order defined)
   processors: list[Processor]()


.. _patchspec_tags:

==========
Processors
==========

Every patchset source is first processed by 0 or more processors, which transform the input's content before it is compared to the target file's content.
This mechanism allows you to describe changes *semantically* so they can apply to multiple versions of-- or variations in the target.

Each processor takes an input and output similar to the standard input/output of command-line processes.
The only difference with patchtree is that the input/output is file-based, and carries metadata about the file's mode and whether it is binary or not.
The processors can be thought of as piped commands in the sense that (by default) each processor's input is either (a) the content of the patchset file for the first processor, or (b) the output received from the previous processor.
Some processors also take secondary input(s), usually under the name *target*.

For each process, the input and/or target can be manually specified using an *input spec*.
The input spec's default value is to use the output of the previous processor.
It can also be set to a constant string (inside the YAML patchspec) or an existing file inside the patchset or target using YAML tags (see :ref:`patchspec_tags`).

As an example, the following patchspec will set the mode of the file it is named as (with an added .yml extension) to 755 (executable):

.. code-block:: yaml

   !patchspec
   processors:
     - id: touch
       mode: 0755

The processors included with patchtree, including any configuration options they take, are documented on the :ref:`processors` page.
Custom processors can be created by inheriting from the base :any:`Process` class and registering through the `configuration file <ptconfig_>`_'s :any:`processors <Config.processors>` value.

.. _ptconfig:

******************
Configuration file
******************

The configuration file is a Python file sourced from ``ptconfig.py`` relative to the current working directory when executing the ``patchtree`` command.
This file is a regular Python source file and can contain any arbitrary code.
Any global definitions with an identical name to a member variable of the :any:`Config` class will override the global configuration instance's value.

The main method in which patchtree is configured is by creating subclasses of its internal classes and overriding its methods.
In order to facilitate this, the type of most classes is read from the :any:`Config` dataclass instead of being instantiated directly.
Please take a look at the :ref:`api` for more info.

For example:

.. code:: none

   diff_context = 0
   output_shebang = True
