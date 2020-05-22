'''reference parsing code for make'''

from typing import Any, Callable, Iterable, Iterator, List, Mapping, Sequence, Tuple

from . import commands
from . import parse as p
from .commands import Command
from .parse import ParseError


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
		return commands.Pragma(p.parse_str(raw_command, ('pragma',)), raw_command.get('data', None))

	def _parse_Group(self, raw_command) -> commands.Group:
		return commands.Group(list(self.parse_commands(raw_command)))

	def _parse_Def(self, raw_command) -> commands.Def:
		BODY_KEY = 'is'
		try:
			body = self.parse_command(p.get(raw_command, (BODY_KEY,)))
		except ParseError as e:
			raise ParseError((BODY_KEY,), 'error in function definition') from e
		return commands.Def(p.parse_str(raw_command['def']), body)

	def _parse_Call(self, command) -> commands.Call:
		return commands.Call(p.parse_str(command))

	# type helpers

	def _parse_mapping(self, raw_command: Mapping) -> Command:
		keys = raw_command.keys()

		key_to_func: Mapping[str, Callable[[Any], Command]] = {
			'pragma': self._parse_Pragma,
			'def': self._parse_Def,
			'call': self._parse_Call,
		}
		no_recurse_obj = {'pragma', 'def', 'group'}

		for k in key_to_func:
			if k in keys:
				command = raw_command
				if k not in no_recurse_obj:
					command = command[k]
				try:
					return key_to_func[k](command)
				except ParseError as e:
					if k in no_recurse_obj:
						raise ParseError((), f'failed to parse {k} command') from e

					raise ParseError((k,)) from e
					# would it be helpful to pretty print the content here?

		raise ParseError((), f'unknown complex command: {raw_command}')

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
				raise ParseError(f'pragma name missing: {raw_command} -> {try_command}')
			return self._parse_mapping({'pragma': args[0], 'data': args[1:]})

		raise ParseError((), f'unknown string command: {raw_command}')

	# top level functions

	def parse_command(self, raw_command) -> Command:
		'''Parse a single command'''

		if isinstance(raw_command, Mapping):
			return self._parse_mapping(raw_command)
		if isinstance(raw_command, str):
			return self._parse_str(raw_command)
		if isinstance(raw_command, Sequence):
			return self._parse_Group(raw_command)

		raise ParseError((), f'unknown type of command: {raw_command}')

	def parse_commands(self, commands: Iterable) -> Iterable[Command]:
		'''Parse a lot of commands'''
		for i, raw_command in enumerate(commands):
			try:
				yield self.parse_command(raw_command)
			except ParseError as e:
				raise ParseError(i) from e
