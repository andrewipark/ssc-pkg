'''miscellaneous functions that defy categorization'''

from typing import List, Optional, Sequence, Tuple, Union
from fractions import Fraction

import attr

from ssc_pkg.notedata import Position


# support types

# # concrete

IndexPath = Sequence[Union[int, str]]


Scalar = Union[int, Fraction, str]


@attr.s(auto_attribs=True)
class ChartPoint:
	'''_NotePosition with chart tag'''
	chart_index: int
	position: Position


@attr.s(auto_attribs=True)
class ChartRegion:
	'''NoteData span with chart tag'''
	start: ChartPoint
	length: Position


# # variable

VarValue = Union[Scalar, Sequence[Scalar]]


@attr.s(auto_attribs=True)
class VarRef:
	'''reference to context-defined variable'''
	name: str


@attr.s(auto_attribs=True)
class ChartPointVar:
	'''Variable-enabled version of :class:`ChartPoint`'''
	chart_index: Union[int, VarRef]
	base: Optional[VarRef]
	offset: Union[Position, VarRef]


@attr.s(auto_attribs=True)
class ChartRegionVar:
	'''Variable-enabled version of :class:`ChartRegion`'''
	start: ChartPointVar # or union with VarRef itself? TODO no resolve support in manager yet
	length: Union[Position, VarRef]


# exception-related

def exc_index_trace(e: Exception):
	'''Generates neat traceback stacks from exceptions containing index data

	The root, innermost exception may be anything.
	For the other outer exceptions,
	``args[0]`` MUST be a (possibly empty) sequence of indices.
	To avoid inadvertently swallowing unhandled exceptions,
	the types of the exceptions must be the same.

	This collapses index sequences with empty messages.
	'''

	exc_pairs: List[Tuple[list, Optional[str]]] = []
	curr_exc: Optional[BaseException] = e
	exc_type = type(e)

	while curr_exc:
		curr_index: list = []
		msg: Optional[str] = None

		args = curr_exc.args
		supports_context = args and isinstance(args[0], Sequence) and (not isinstance(args[0], str))
		is_last = curr_exc.__cause__ is None

		if not is_last:
			if type(curr_exc) is not exc_type:
				raise curr_exc # not handled properly
			if not supports_context:
				raise TypeError(f'bad context: {args}')

		if supports_context:
			curr_index = list(args[0])
			if len(args) == 2:
				msg = str(args[1])
			elif len(args) > 2:
				msg = str(args[1:])
		else:
			msg = type(curr_exc).__name__
			if (m := str(curr_exc)):
				msg += ': ' + m

		if (not exc_pairs) or (exc_pairs[-1][1]):
			exc_pairs.append((curr_index, msg))
		else:
			exc_pairs[-1][0].extend(curr_index)
			exc_pairs[-1] = (exc_pairs[-1][0], msg)

		curr_exc = curr_exc.__cause__

	return exc_pairs


def index_str(indices: IndexPath) -> str:
	'''Turns a path of indices into a JSON-like index string'''
	if not indices:
		return ''
	strings: List[str] = [f'.{i}' if isinstance(i, str) else f'[{i}]' for i in indices]
	return ''.join(strings) + ': '


def exc_index_trace_tab(e: Exception) -> str:
	'''pretty print function for exception handlers'''
	return '\n'.join(
		''.join(['\t' * i, index_str(p[0]), p[1] or 'None'])
		for i, p in enumerate(exc_index_trace(e))
	)
