Basic Usage
============

Install the package.
In a terminal, choose an input directory containing simfiles,
and an output directory for the results of packaging the simfiles.

Then, run:

.. code-block:: sh

	ssc-pkg [input_directory] [output_directory]

This will copy the input directory to the output directory.

.. attention::
	``ssc-pkg`` will not run if the input and output directories are the same, or contained within each other.
	This prevents recursive copying on successive runs of the program, or overwriting the original data.

Ignoring Files
---------------

``ssc-pkg`` will ignore ``.old`` files, which are usually outdated copies of simfiles,
and files prefixed with ``__``, which the developer uses as a 'private file' marker.
You can change this behavior with the ``--ignore-regex`` argument.
Files or folders that match any of the patterns you specify will not be copied.
For more syntax details, see Python's regular expression reference.
.. TODO use intersphinx to generate a link

Transforms
-----------

``ssc-pkg`` can apply transforms to your simfiles and automate otherwise tedious tasks.

(This section is currently unfinished, and will probably be its own page eventually.)

Make
-----

``ssc-pkg``'s Make tool uses user-specified directives to compile a simfile from a skeleton.

Caveats
--------

-
	Only ``.ssc`` files are recognized as simfiles.
	``.sm`` files will be copied, but are not transformed.
- ``oggenc`` is really slow
