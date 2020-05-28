Make
=====

In homage to GNU's ``make``, the Make transform here builds simfiles using a series of instructions.

(This section is just assorted notes.)

Primer on YAML syntax
----------------------

Please see the *very* basics of `YAML syntax <https://en.wikipedia.org/wiki/YAML#Syntax>`_.
The YAML standard is complicated, but Make relies only on the following elements:

- Lists
- Mappings (``key: value`` collections)
- Integers
- Strings

Adding commands
----------------

``ssc-pkg`` finds  ``__metadata.yaml`` file in the same folder as the simfile,
and then reads Make commands from the top-level ``make`` key.

Writing commands
-----------------

Available commands: :mod:`~.commands`

Canonical ways to write commands: :mod:`~.parser`, matching ``parse_[command]`` method

Parser may also define other ways to write commands (see: string pragma)

Final note
-----------

This is designed to be a quicker, convenient tool,
not a replacement for writing a Python script
and using the library part of this project.
