'''Standalone structured YAML parsing functions.

This is also technically a lexer of structured YAML data.'''

from typing import Sequence

from .util import IndexPath


class ParseError(Exception):
	'''Exception class for errors returned by parsing.

	Raisers MUST conform to the exc_index_trace spec.
	'''


# parse helpers
# help make pretty tracebacks, at the cost of tons of function calls

def get(what, indices: IndexPath = ()):
	'''verifies that a key path exists, and returns what is there'''
	if indices:
		for ii, i in enumerate(indices):
			try:
				what = what[i]
			except (IndexError, KeyError) as e:
				# we can make the error message more obvious
				raise ParseError(indices[:ii], f'key {indices[ii]} missing ({type(e).__name__})') from None
	return what


def parse_str(what, indices: IndexPath = ()) -> str:
	what = get(what, indices)
	if not isinstance(what, str):
		raise ParseError(indices, f"expected a string, got '{type(what).__name__}' instead")
	return what


def parse_list(what, indices: IndexPath = ()) -> Sequence:
	what = get(what, indices)
	if not isinstance(what, Sequence) or isinstance(what, str):
		raise ParseError(indices, f"expected a list, got '{type(what).__name__}' instead")
	return what
