.. _processors:

##########
Processors
##########

This page lists all built-in processor types along with descriptions of what they do and which options they take.
On this page, **output** refers to what the processor returns, while **input** refers to how the processor treats its input.
This input is either (a) the content of the patchset file for the first processor, or (b) the output received from the previous processor.
**Arguments** are any options explicitly given to the processor through the filename, e.g. ``filename#processor,arg,arg2=value,arg3#processor2``.
Note that some processors may take positional arguments, while others may use key/value based options instead.

.. _process_id:

********
Identity
********

The identity processor is used to "touch" files, change the mode of existing files, or add arbitrary identifiers to patchset source filenames by passing arbitrary arguments.

:Class: :any:`ProcessIdentity`
:Identifier: ``id``
:Input: Ignored.
:Output:
  A file with the *content* of the target file and *mode* of the patchset input.
:Arguments: Any arguments passed to this processor are ignored.

.. _process_cocci:

**********
Coccinelle
**********

The Coccinelle processor uses Coccinelle to apply patch(es) in the SmPL (Semantic Patch Language) format.

.. important::

   In order to use this processor, Coccinelle must be installed and ``spatch`` must be available in ``$PATH``.

:Class: :any:`ProcessCoccinelle`
:Identifier: ``cocci``
:Input: Coccinelle's SmPL input.
:Output: The contents of the target file after being processed by Coccinelle (not the diff returned by Coccinelle).
:Arguments: Reserved.

.. _process_jinja:

**************
Jinja template
**************

The Jinja processor passes the input through the Jinja2 templating engine.

:Class: :any:`ProcessJinja2`
:Identifier: ``jinja``
:Input: Jinja template code.
:Output: The input after being processed by Jinja.
:Arguments: Reserved.

.. note::

   Template variables are generated through the :any:`get_template_vars <ProcessJinja2.get_template_vars>` method.
   This method returns an empty dict by default, and is meant to be implemented by implementing a custom class that derives from ProcessJinja2 and registering it through the :ref:`configuration file <ptconfig>`.

.. _process_exe:

**********
Executable
**********

The executable processor runs the input as an executable, passes the target file to its standard input, and returns its standard output.

:Class: :any:`ProcessExec`
:Identifier: ``exec``
:Input:
  Executable script.

  .. important::

     The executable *must* contain a shebang line to specify what interpreter to use.

:Output: Any content written to the standard output by the executable.
:Arguments: Reserved.

.. _process_merge:

*****
Merge
*****

The merge processor merges the input with the target file, such that changes are combined with the target instead of replacing the target.

:Class: :any:`ProcessMerge`
:Identifier: ``merge``
:Input: Content to merge.
:Output: Merged changes.
:Arguments: Positional.

  1. Merge strategy:

     ``ignore``
       Appends all lines from the input to the output excluding any lines already present in the output.
