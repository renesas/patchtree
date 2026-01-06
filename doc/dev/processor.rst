.. _processors:

##########
Processors
##########

This page lists all built-in processor types along with descriptions of what they do and which options they take.

.. _process_touch:

*****
Touch
*****

The touch processor is used to create files (similar to ``touch``) or change the mode of existing files (similar to ``chmod``).

:Class: :any:`TouchProcess`
:Input: Content of new file.
:Output:
  The input file as-is, with the following exceptions:

  - If the input is empty, it will be set to an empty (but existent) file.
  - If the ``mode`` option is set, it will be used instead of the input mode.
:Options:
  .. code-block:: yaml

     - id: "touch"
       input: ProcessInputSpec(required=False)
       mode: int(required=False, default=<input mode>)

.. _process_cocci:

**********
Coccinelle
**********

The Coccinelle processor uses Coccinelle to apply patch(es) in the SmPL (Semantic Patch Language) format.

.. important::

   In order to use this processor, Coccinelle must be installed and ``spatch`` must be available in ``$PATH``.

:Class: :any:`CoccinelleProcess`
:Input: Coccinelle's SmPL input.
:Target: File content to apply patch to (current patchspec's target file by default).
:Output: The content of the target file after being processed by Coccinelle (not the diff returned by Coccinelle).
:Options:
  .. code-block:: yaml

     - id: "cocci"
       input: ProcessInputSpec(required=False)
       target: ProcessInputSpec(required=False)


.. _process_jinja:

**************
Jinja template
**************

The Jinja processor passes the input through the Jinja2 templating engine.

:Class: :any:`Jinja2Process`
:Input: Jinja template code.
:Output: The input after being processed by Jinja.
:Options:
  .. code-block:: yaml

     - id: "jinja"
       input: ProcessInputSpec(required=False)

.. note::

   Template variables are generated through the :any:`get_template_vars <Jinja2Process.get_template_vars>` method.
   This method returns an empty dict by default, and is meant to be implemented by implementing a custom class that derives from :any:`Jinja2Process` and registering it through the :ref:`configuration file <ptconfig>`.

.. _process_exe:

**********
Executable
**********

The executable processor passes its input to an executable and returns its standard output.

:Class: :any:`ExecProcess`
:Input: Input passed to the standard input of the command.
:Output: Any content written to the standard output by the executable.
:Options:
  .. code-block:: yaml

     - id: "exec"
       cmd: str() | list[str]()
       input: ProcessInputSpec(required=False)

  .. note::

     If the ``cmd`` option is a string, it is split **using shell syntax rules**.

.. _process_merge:

*****
Merge
*****

The merge processor merges the input with the target file, such that changes are combined with the target instead of replacing the target.

:Class: :any:`MergeProcess`
:Input: Content to merge (A).
:Target: Content to merge (B).
:Output: Merged changes.
:Options:
  .. code-block:: yaml

     - id: "merge"
       strategy: enum() # see below
       input: ProcessInputSpec(required=False)
       target: ProcessInputSpec(required=False)

==========
Strategies
==========

``ignore``
  Appends all lines from *input* to *target*, excluding any lines already present in *target*.
