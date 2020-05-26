'''miscellaneous functions that defy categorization'''

from typing import List, Optional, Sequence, Tuple, Union


IndexPath = Sequence[Union[int, str]]


def exc_index_trace(e: Exception):
	'''Generates neat traceback stacks from exceptions containing index data

	For each exception,
	``args[0]`` MUST be a (possibly empty) sequence of indices.
	Everything else is interpreted as part of a message.

	This collapses index sequences with empty messages.

	To avoid inadvertently swallowing unhandled exceptions,
	the types of all exceptions must be the same.
	'''

	exc_pairs: List[Tuple[list, Optional[str]]] = []
	curr_exc: Optional[BaseException] = e

	exc_type = type(e)

	while curr_exc:
		curr_index: list = []
		msg: Optional[str] = None

		if not isinstance(e, exc_type):
			raise TypeError(f'unexpected {type(e)} in {exc_type} chain')

		args = curr_exc.args
		if not args:
			raise ValueError('missing context')
		if (not isinstance(args[0], Sequence)) or isinstance(args[0], str):
			raise TypeError(f'invalid context: {args[0]}')

		curr_index = list(args[0])

		if len(args) == 2:
			msg = str(args[1])
		elif len(args) > 2:
			msg = str(args[1:])

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
