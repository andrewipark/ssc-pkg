'''context manager and command line runner'''

from logging import getLogger
from typing import Any, Callable, Dict, Iterable, Mapping, get_type_hints

import attr

from ssc_pkg.simfile import Simfile

from . import commands


class CommandError(Exception):
	'''Exception class for errors caused by commands.

	Raisers MUST conform to the exc_index_trace spec.
	'''


@attr.s(auto_attribs=True)
class Manager:
	'''Reference manager class to apply commands onto a simfile in place'''

	variables: Dict[str, Any] = attr.Factory(dict)

	def __attrs_post_init__(self):
		self.logger = getLogger(f'{__name__}.{type(self).__name__}')

	def _run_Pragma(self, pragma: commands.Pragma, _: Simfile):
		if pragma.name == 'echo':
			self.logger.info(f'\n{pragma.data}')
		elif pragma.name == 'vars':
			for var, val in self.variables.items():
				self.logger.info(f"'{var}' = {val}")
		elif pragma.name == 'raise':
			raise CommandError((), f'unconditional raise via pragma: {pragma.data}')
		elif pragma.name == 'callable':
			# for debug use only!
			cmd, args = pragma.data[0], pragma.data[1:]
			result = cmd(*args)
			self.logger.debug(f'callable pragma with args:\n{args}\nreturned:\n{result}')
		else:
			raise CommandError((), f"unknown pragma '{pragma.name}'")

	def _run_Group(self, group: commands.Group, simfile: Simfile):
		self.run_many(group.commands, simfile)

	def _run_Def(self, c_def: commands.Def, _: Simfile):
		self.variables[c_def.name] = c_def

	def _run_Call(self, call: commands.Call, simfile: Simfile):
		if call.name not in self.variables:
			raise CommandError(('Call',), f"function '{call.name}' not defined")
		what = self.variables[call.name]
		if not isinstance(what, commands.Def):
			raise CommandError(
				('Call',),
				f"variable '{call.name}' is not a function, but {type(what).__name__} instead"
			)
		try:
			self.run(what.command, simfile)
		except CommandError as e:
			raise CommandError((call.name,), "error during function call") from e

	def run(self, command: commands.Command, simfile: Simfile):
		'''run a command on the simfile, potentially modifying it in-place'''

		cmd_type_fn: Mapping[type, Callable[[Any, Simfile], None]] = {
			commands.Pragma: self._run_Pragma,
			commands.Group: self._run_Group,
			commands.Def: self._run_Def,
			commands.Call: self._run_Call,
		}
		# static type checking equivalent: Mapping[Type[_T], Callable[[_T, Simfile], None]]
		# 'unbound type variable' :(
		assert all(
			t == list(get_type_hints(fn).values())[0] # ordered dict dependence
			for t, fn in cmd_type_fn.items()
		)

		ct = type(command)
		if ct in cmd_type_fn:
			try:
				cmd_type_fn[ct](command, simfile)
			except CommandError as e:
				if ct is commands.Group or ct is commands.Call:
					# these are structural, we don't care about the name
					raise e
				raise CommandError((ct.__name__, )) from e

		else:
			raise CommandError((), f"unhandled command '{command}'")

	def run_many(self, commands: Iterable[commands.Command], simfile: Simfile):
		for i, c in enumerate(commands):
			try:
				self.run(c, simfile)
			except CommandError as e:
				raise CommandError((i,)) from e
