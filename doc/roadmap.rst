Development Roadmap
====================

0.12
-----
``make``: erase, mirror commands

0.13
------
Any of:

-
	add transform: verify that all the file paths in the simfile are either ``None`` (empty optional),
	or are valid on the filesystem
- ``breakdown`` module for stream breakdown support (etc)
- ``make``: add variable support to for-loops
- ``list-available-transforms``
- ``transform-fail-strategy``
	- ``STOP_ALL`` stop all transform chains (current behavior because of exception propagation)
	- ``STOP`` stop the transform chain of the chart whose chain failed
	- ``SKIP`` skip this transform, but keep going down the chain

0.15
------
Any two of:

- Manager and Parser API
	- individual parse/run functions should be public
	- Unit tests should call methods directly
- substantially complete *dev*-side documentation
- make a list available transforms option
- use multiprocessing for transforms
-
	100% coverage on non-:mod:`~ssc_pkg.make` unit tests [#unittests]_:
	every parse and run command should have both a success and a failure test

1.0
----
- package an entire pack using just this tool
- Substantially complete user-facing documentation
- ``.sm`` support

1.~3
----
- pattern analysis
- ``make`` BPM gimmick tools
