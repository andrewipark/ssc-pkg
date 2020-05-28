'''Command data structures'''

from typing import Any, Iterable, Sequence, Union, Optional
from fractions import Fraction

import attr

from ssc_pkg.notedata import NoteData, Position


# support data types

Scalar = Union[int, Fraction, str]
VarValue = Union[Scalar, Sequence[Scalar]]


@attr.s(auto_attribs=True)
class VarRef:
	'''reference to context-defined variable'''
	name: str


@attr.s(auto_attribs=True)
class ChartPoint:
	'''Variable-enabled version of :class:`ChartPoint`'''
	chart_index: Union[int, VarRef]
	base: Optional[VarRef]
	offset: Union[Position, VarRef]


@attr.s(auto_attribs=True)
class ChartRegion:
	'''Variable-enabled version of :class:`ChartRegion`'''
	start: ChartPoint # or union with VarRef itself? TODO no resolve support in manager yet
	length: Union[Position, VarRef]


# ------------------ commands ------------------

class Command:
	'''mixin for type support w/ ``mypy``'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs) # type: ignore # mypy-mixin

# actions


@attr.s(auto_attribs=True)
class Copy(Command):
	'''copy a note slice into another place in the simfile'''
	targets: Sequence[ChartPoint]
	source: ChartRegion
	overlay_mode: NoteData.OverlayMode


# managed

@attr.s(auto_attribs=True)
class Pragma(Command):
	'''arbitrary directive for the command runner'''
	name: str
	data: Any


# control structures

@attr.s(auto_attribs=True)
class Group(Command):
	'''sequence of commands to execute in a new scope'''
	commands: Sequence[Command]


@attr.s(auto_attribs=True)
class Def(Command):
	'''function definition'''
	name: str
	body: Group


@attr.s(auto_attribs=True)
class Call(Command):
	'''function call'''
	name: str


@attr.s(auto_attribs=True)
class Let(Command):
	'''variable definition (untyped)'''
	name: str
	value: VarValue


@attr.s(auto_attribs=True)
class For(Command):
	'''indexed loop construct'''
	name: str
	in_iterable: Iterable[Scalar]
	body: Group
