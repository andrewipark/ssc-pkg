Development Roadmap
====================

0.11
-----
``make``: copy, erase, mirror commands

0.12[0]
--------
-
	add transform: verify that all the file paths in the simfile are either ``None`` (empty optional),
	or are valid on the filesystem
- Clean up stream breakdown code
-
	:mod:`~.parse`: separate get logic from type checking logic:
	``get_*`` methods implicitly call :meth:`~.parse.get`,
	``parse_*`` methods do not

0.12[1]
--------
- ``make``: add ``attrs`` class that represents a variable reference
	- add variable support to for-loops (easy)
	- add variable-enabled variants of ChartPosition and Fraction
		- add parser support: if object doesn't parse as a Fraction or whatever we needed, assume it's a variable reference instead
		- :class:`~.Manager`: add ``resolve`` method to convert variable types into base types

0.13 (other) transforms
------------------------
- ``list-transforms`` (new option)
-
	new transform: verify that all the file paths in the simfile are either ``None`` (empty optional),
	or are valid on the filesystem
- ``--transform-fail-strategy`` (new option)
	- stop all transform chains (current behavior because of exception propagation)
	- stop the transform chain of the chart whose chain failed
	- skip this transform, but keep going down the chain
- Invalid YAML should result in a failed transform, not a program crash

0.14
------
Any two of:

- Manager and Parser API
	- individual parse/run functions should be public
	- Add success and failure unit tests
- substantially complete *dev*-side documentation
- make a list available transforms option
- use multiprocessing for transforms
-
	100% coverage on non-:mod:`~ssc_pkg.make` unit tests [#unittests]_:
	every parse and run command should have both a success and a failure test

.. [#unittests]
	Probably 0.16 for non-:class:`~.Parser` tests, and 0.18 for everything.
	Writing parser tests is annoying.

1.0
----
- package an entire pack using just this tool
- Substantially complete user-facing documentation
- ``.sm`` support

1.~3
----
- pattern analysis
- ``make`` BPM gimmick tools
