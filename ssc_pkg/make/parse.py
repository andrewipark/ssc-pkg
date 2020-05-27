'''standalone structured YAML parsing functions

Also technically *structured* YAML lexer functions

All functions chain propagate index data to raised :class:`ParseError` instances
'''

from fractions import Fraction
import re
from typing import Any, Callable, List, Optional, Sequence, TypeVar

from . import util


class ParseError(Exception):
	'''Exception class for errors returned by parsing.

	Raisers MUST conform to the :meth:`~ssc_pkg.make.util.exc_index_trace` spec
	'''


# parse helpers
# help make pretty tracebacks, at the cost of tons of function calls

def get(what, indices: util.IndexPath = ()):
	'''verifies that a key path exists, and returns what is there

	Args:
		what: the structured YAML object
		indices: the index path through which to descend into the object

	argument descriptions here apply to all of the other module methods
	'''
	if indices:
		for ii, i in enumerate(indices):
			try:
				what = what[i]
			except (IndexError, KeyError) as e:
				# we can make the error message more obvious
				raise ParseError(indices[:ii], f'key {indices[ii]} missing ({type(e).__name__})') from None
	return what


def parse_int(what, indices: util.IndexPath = ()) -> int:
	what = get(what, indices)
	if not isinstance(what, int):
		raise ParseError(indices, f"expected an integer, got '{type(what).__name__}' instead")
	return what


def parse_str(what, indices: util.IndexPath = ()) -> str:
	what = get(what, indices)
	if not isinstance(what, str):
		raise ParseError(indices, f"expected a string, got '{type(what).__name__}' instead")
	return what


_FRACTION_REGEX = re.compile(
	r'(?=.)' # don't match the empty string
	r'(?P<s>\+|-)?' # sign
	r'(?P<i>\d+)?' # integer
	r'(?:' + (
		r'(?(i)\s+)' # if there was an integer part, force whitespace
		r'(?P<fn>\d+)\s*/\s*(?P<fd>\d+)' # fraction parts
	) + r')?'
)


_CHARTPOINT_REGEX = re.compile(
	r'(?P<cref>\d+)\s*@\s*'
	+ _FRACTION_REGEX.pattern
)


def _parse_Fraction_match(m: re.Match) -> Fraction:
	position = Fraction(m['i'] or 0)
	if m['fn']:
		position += Fraction(int(m['fn']), int(m['fd']))
	if m['s']:
		position *= -1
	return position


def parse_Fraction(what, indices: util.IndexPath = ()) -> Fraction:
	what = get(what, indices)
	if isinstance(what, int):
		return Fraction(what)
	if isinstance(what, str):
		m = _FRACTION_REGEX.fullmatch(str(what))
		if not m:
			raise ParseError(indices, f'invalid fraction string: {what}')
		return _parse_Fraction_match(m)

	raise ParseError(indices, f"expected a fraction, got '{type(what).__name__}' instead")


def parse_variable(what, indices: util.IndexPath = ()):
	'''parse the contents as an ``int``, ``Fraction``, and ``str``, in that order of priority'''
	what = get(what, indices)
	if isinstance(what, int):
		return what
	if isinstance(what, str):
		try:
			return parse_Fraction(what, ())
		except ParseError:
			return what # str

	raise ParseError(indices, f'invalid variable value: {what}')


# parse helpers for complex types

_T = TypeVar('_T')


def parse_list(what, indices: util.IndexPath = ()) -> Sequence:
	what = get(what, indices)
	if not isinstance(what, Sequence) or isinstance(what, str):
		raise ParseError(indices, f"expected a list, got '{type(what).__name__}' instead")
	return what


def parse_list_type(what, indices: util.IndexPath, parse_fn: Callable[[Any, util.IndexPath], _T]) -> Sequence[_T]:
	'''convenience function for parsing lists of homogenous type'''
	what = parse_list(what, indices)
	ret: List[Optional[_T]] = [None] * len(what)
	for i in range(len(what)):
		try:
			ret[i] = parse_fn(what, (i,))
		except ParseError as e:
			raise ParseError(indices) from e # pass the indices down
	return ret # type: ignore # because of callable type signature
