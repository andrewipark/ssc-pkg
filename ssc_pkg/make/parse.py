'''standalone structured YAML parsing functions

Also technically *structured* YAML lexer functions
'''

import re
from fractions import Fraction
from typing import Any, Callable, List, Sequence, TypeVar, Union, cast

from . import commands
from .util import IndexPath


class ParseError(Exception):
	'''Exception class for errors returned by parsing.

	Raisers MUST conform to the :meth:`~ssc_pkg.make.util.exc_index_trace` spec
	'''


_T = TypeVar('_T')


def get_u(what, indices: IndexPath) -> Any:
	'''verifies that a key path exists, and returns what is there

	Args:
		what: the structured YAML object
		indices: the index path through which to descend into the object
	'''

	for ii, i in enumerate(indices):
		try:
			what = what[i]
		except LookupError:
			# in this and the next case, we can make the error message nicer
			# and something else is probably wrong if it's not one of these three
			raise LookupError(indices[:ii], f"key missing: {indices[ii]}") from None
		except TypeError:
			raise TypeError(indices[:ii], f'{type(what).__name__} not indexable') from None
	return what


def get(what, indices: IndexPath, check: Callable[[Any], _T]) -> _T:
	'''Type-safe version of :meth:`~get` with check function'''
	what = get_u(what, indices)
	try:
		return check(what)
	except Exception as e:
		raise ParseError(indices) from e


def get_sequence(what, indices: IndexPath, check: Callable[[Any], _T]) -> Sequence[_T]:
	'''syntactic sugar wrapper for :meth:`get` and :meth:`check_sequence_type`'''
	return get(what, indices, lambda v: check_sequence_type(v, check))


# simple check methods

def check_int(what) -> int:
	if not isinstance(what, int):
		raise TypeError(f"expected an integer, got {type(what).__name__} instead: {what}")
	return what


def check_str(what) -> str:
	'''Because Python 3's :obj:`int` is unlimited size,
	we can assume that YAML strings never represent an :obj:`int`
	'''
	if not isinstance(what, str):
		raise TypeError(f"expected a string, got {type(what).__name__} instead: {what}")
	return what


def check_sequence(what) -> Sequence:
	if not isinstance(what, Sequence) or isinstance(what, str):
		raise TypeError(f"expected a sequence, got {type(what).__name__} instead: {what}")
	return what


def check_sequence_type(what, check: Callable[[Any], _T]) -> Sequence[_T]:
	'''check function for :func:`get` with lists of expected homogenous type'''
	# looks sort of like a get variant...
	what = check_sequence(what)
	ret: List[_T] = [cast(_T, None)] * len(what)
	# by the end, all the Nones will be overwritten so the list invariant is still ok
	for i in range(len(what)):
		try:
			ret[i] = check(what[i])
		except Exception as e:
			raise ParseError((i,)) from e
	return ret


# non-trivial parse methods

# # helpers

FRACTION_REGEX = re.compile(
	r'(?=.)' # don't match the empty string
	r'(?:(?P<s>\+|-)\s*)?' # sign
	r'(?P<i>\d+)?' # integer
	r'(?:' + (
		r'(?(i)\s+)' # if there was an integer part, force whitespace
		r'(?P<fn>\d+)\s*/\s*(?P<fd>\d+)' # fraction parts
	) + r')?'
)
'''regex object to match a (possibly signed) fraction'''


CHARTPOINT_REGEX = re.compile(
	r'(?P<cref>\w+)\s*@\s*'
	r'(?:(?P<base>\w+)\s+)?'
	+ FRACTION_REGEX.pattern
)
'''regex object to match a `class`:~.ChartPointVar:'''


def match_to_Fraction(m: re.Match) -> Fraction:
	'''Converts a match object returned from :const:`FRACTION_REGEX`'''
	position = Fraction(m['i'] or 0)
	if m['fn']:
		position += Fraction(int(m['fn']), int(m['fd']))
	if m['s'] == '-':
		position *= -1
	return position


def match_to_ChartPoint(m: re.Match) -> commands.ChartPoint:
	'''Converts a match object returned from :const:`FRACTION_REGEX`'''
	base = commands.VarRef(m['base']) if m['base'] else None
	try:
		chart_index: Union[int, commands.VarRef] = int(m['cref'])
	except ValueError:
		chart_index = commands.VarRef(m['cref'])
	offset = match_to_Fraction(m)

	return commands.ChartPoint(chart_index = chart_index, base = base, offset = offset)


# # actual parse methods

def parse_Fraction(what) -> Fraction:
	if isinstance(what, int):
		return Fraction(what) # does user strictly need a fraction?
	if isinstance(what, str):
		m = FRACTION_REGEX.fullmatch(str(what))
		if not m:
			raise ValueError(f'invalid fraction string: {what}')
		return match_to_Fraction(m)

	raise TypeError(f"expected a fraction, got {type(what).__name__} instead: {what}")


def parse_scalar(what) -> commands.Scalar:
	'''parse the contents as an ``int``, ``Fraction``, and ``str``, in that order of priority

	|WARNING| experimental
	'''
	if isinstance(what, int):
		return what
	if isinstance(what, str):
		try:
			return parse_Fraction(what)
		except ValueError:
			return what # str

	raise TypeError(f'expected a scalar, got {type(what).__name__} instead: {what}')


def parse_ChartPoint(what) -> commands.ChartPoint:
	s = check_str(what)
	m = CHARTPOINT_REGEX.fullmatch(s)
	if not m:
		raise ValueError(f'invalid chart point string: {s}')
	return match_to_ChartPoint(m)


def parse_ChartRegion(what) -> commands.ChartRegion:
	start = get(what, ('src',), parse_ChartPoint)
	length = get(what, ('len',), parse_Fraction)
	return commands.ChartRegion(start = start, length = length)


# parse helpers for complex types
