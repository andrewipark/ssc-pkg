'''reference parsing code for make'''

from typing import Any, Callable, Iterable, Iterator, List, Mapping, Sequence, Tuple

from . import commands
from . import parse as p
from .commands import Command
from .parse import ParseError
from .util import VarValue


# unused
# utility-fn
def _enum_flatten_list(obj: Iterable) -> Iterable[Tuple[List[int], Any]]:
	'''An enumerate that flattens the list along the way'''

	stack: List[Iterator] = [iter(obj)]
	indices: List[int] = [0]

	while stack:
		curr: Any = stack[-1]

		try:
			curr = next(curr)
		except StopIteration:
			stack.pop()
			indices.pop()
			continue

		if isinstance(curr, Iterable) and (not isinstance(curr, (str, Mapping))):
			stack.append(iter(curr))
			indices.append(0)
		else:
			yield indices, curr
			indices[-1] += 1


class Parser:
	'''Reference parser class for make instructions'''

	# individual commands (for ease in stack traces)

	def _parse_Pragma(self, raw_command) -> commands.Pragma:
		return commands.Pragma(
			name = p.get(raw_command, ('pragma',), p.check_str),
			data = raw_command.get('data', None),
		)

	def _parse_Group(self, raw_commands) -> commands.Group:
		return commands.Group(commands = list(self.parse_commands(raw_commands)))

	def _parse_Group_h(self, what, indices, msg) -> commands.Group:
		'''like the helper methods in parse.py,
		but for parse errors, attach the string provided
		(to make the structural relation of the error more obvious)
		'''
		what = p.get(what, indices, p.check_sequence)
		try:
			return self._parse_Group(what)
		except Exception as e:
			raise ParseError(indices, msg) from e

	def _parse_Def(self, raw_command) -> commands.Def:
		return commands.Def(
			name = p.get(raw_command, ('def',), p.check_str),
			body = self._parse_Group_h(raw_command, ('is',), 'definition of function body'),
		)

	def _parse_Call(self, command) -> commands.Call:
		return commands.Call(name = p.get(command, (), p.check_str))

	def _parse_Let(self, raw_command) -> commands.Let:
		VALUE_KEY = 'is'
		name = p.get(raw_command, ('let',), p.check_str)
		try_value = p.get_u(raw_command, (VALUE_KEY,))
		value: VarValue
		# only supports scalars and lists right now
		try:
			if not isinstance(try_value, str) and isinstance(try_value, Sequence):
				value = p.get_sequence(try_value, (), p.parse_scalar)
			else:
				value = p.get(try_value, (), p.parse_scalar)
		except Exception as e:
			raise ParseError((VALUE_KEY,), 'declaration value') from e
		return commands.Let(name = name, value = value)

	def _parse_For(self, raw_command) -> commands.For:
		return commands.For(
			name = p.get(raw_command, ('for',), p.check_str),
			in_iterable = p.get_sequence(raw_command, ('in',), p.parse_scalar),
			body = self._parse_Group_h(raw_command, ('do',), 'for-loop body'),
		)

	# type helpers

	def _parse_mapping(self, raw_command: Mapping) -> Command:
		keys = raw_command.keys()

		key_to_func: Mapping[str, Callable[[Any], Command]] = {
			'pragma': self._parse_Pragma,
			'def': self._parse_Def,
			'call': self._parse_Call,
			'let': self._parse_Let,
			'for': self._parse_For,
		}
		no_recurse_obj = {'pragma', 'def', 'let', 'for'}

		for k in key_to_func:
			if k in keys:
				command = raw_command
				if k not in no_recurse_obj:
					command = command[k]
				try:
					return key_to_func[k](command)
				except Exception as e:
					if k in no_recurse_obj:
						raise ParseError((), f'failed to parse {k} command') from e

					raise ParseError((k,)) from e
					# would it be helpful to pretty print the content here?

		raise TypeError(f'unknown complex command: {raw_command}')

	def _parse_str(self, raw_command: str) -> Command:
		'''Parse a string command in standard format

		command := name ('%' item)*
		name, item := [string]

		This only handles the simple cases.
		'''

		try_command = [c.strip() for c in raw_command.split('%')]
		if len(try_command) < 1:
			raise ValueError('empty command')
		name = try_command[0].lower()
		args = try_command[1:]

		if name == 'pragma':
			if len(args) < 1:
				raise ValueError(f'pragma name missing: {raw_command} -> {try_command}')
			return self._parse_mapping({'pragma': args[0], 'data': args[1:]})

		raise ValueError(f'unknown string command: {raw_command}')

	# top level functions

	def parse_command(self, raw_command) -> Command:
		'''Parse a single command'''

		if isinstance(raw_command, Mapping):
			return self._parse_mapping(raw_command)
		if isinstance(raw_command, str):
			return self._parse_str(raw_command)
		if isinstance(raw_command, Sequence):
			return self._parse_Group(raw_command)

		raise TypeError(f'unknown type of command: {raw_command}')

	def parse_commands(self, raw_commands: Iterable) -> Iterable[Command]:
		'''convenience function to parse a stream of commands'''
		for i, raw_command in enumerate(raw_commands):
			try:
				yield self.parse_command(raw_command)
			except Exception as e:
				raise ParseError((i,)) from e
