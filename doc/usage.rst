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

By default, ``ssc-pkg`` will ignore ``.old`` files,
which are usually outdated backup copies of simfiles,
and files prefixed with ``__``, which the developer uses as a 'private file' marker.

You can change this behavior with the ``--ignore-regex`` argument.
Files or folders that match any of the patterns you specify will not be copied.
For more syntax details, see Python's regular expression reference.

.. TODO use intersphinx to generate a link

Transforms
-----------

``ssc-pkg`` can apply transforms to your simfiles and automate otherwise tedious tasks.

This section is currently unfinished. See the :mod:`~ssc_pkg.transforms` module for more details.

Logging
--------

Use the ``-v`` (``--verbose``) and ``-q`` (``--quiet``) flags to increase or decrease the level of output.
The rough descriptions of the output of each level is as follows:

- critical: unrecoverable program crashes only
- error: serious issues with simfiles, e.g. audio or banner is missing
- warning (default): minor issues with simfiles, e.g. issues found while checking
- info: ncie to have details, e.g. what simfiles were found
- debug: minutely detailed information about the program

Debug output is not recommended for general use.

Make
-----

``ssc-pkg``'s Make transform reads user-specified directives to compile a simfile from a skeleton.
See :doc:`make` for more details.

Caveats
--------

-
	Only ``.ssc`` files are recognized as simfiles.
	``.sm`` files will be copied, but are not transformed.
- ``oggenc`` is really slow
