'''context manager and command line runner'''

from logging import getLogger
from typing import Any, Callable, Dict, Iterable, List, Mapping, Union, get_type_hints

import attr

from ssc_pkg.simfile import Simfile, Chart
from ssc_pkg import notedata

from . import commands, util


class CommandError(Exception):
	'''Exception class for errors caused by commands.

	Raisers MUST conform to the :meth:`~ssc_pkg.make.util.exc_index_trace` spec
	'''


def _chart_from_index(simfile: Simfile, chart_index: int, indices) -> Chart:
	if chart_index < len(simfile.charts):
		return simfile.charts[chart_index]

	raise CommandError(indices, f'no source chart at index {chart_index}')


_GAME_TYPE_COLUMNS_TABLE = {
	'dance-single': 4,
	'dance-double': 8,
	'pump-single': 5,
	'pump-double': 10,
	# there's definitely more...
}

# curiously, mirroring "horizontally" means that the flip is actually across the vertical axis...
_MIRROR_TRANSLATE_TABLE = {
	'dance-single': { # 0-3
		'horizontal': [3, 1, 2, 0],
		'vertical': [0, 2, 1, 3],
		'oblique': [2, 3, 0, 1],
		'antioblique': [1, 0, 3, 2],
	},
	'pump-single': {
		'horizontal': [4, 3, 2, 1, 0],
		'vertical': [1, 0, 2, 4, 3],
		'oblique': [0, 4, 2, 3, 1],
		'antioblique': [3, 1, 2, 0, 4],
	},
	# TODO: doubles mode support
}


@attr.s(auto_attribs=True)
class _Context:
	'''The equivalent of a stack frame for the manager'''

	variables: Dict[str, Union[util.VarValue, commands.Def]] = attr.Factory(dict)


@attr.s(auto_attribs=True)
class Manager:
	'''Reference manager class'''

	frames: List[_Context] = attr.Factory(lambda: [_Context()])

	def lookup(self, name: str):
		'''searches for a variable in the context frames'''
		for i in range(len(self.frames)):
			frame = self.frames[len(self.frames) - i - 1] # search frames from top down
			if name in frame.variables:
				return frame.variables[name]
		raise KeyError(name)

	def __enter__(self):
		'''makes this manager enter a new, fresh context'''
		self.frames.append(_Context())

	def __exit__(self, exc_type, exc_info, _):
		'''makes this manager exit its current context'''
		self.frames.pop()
		return False

	def __attrs_post_init__(self):
		self.logger = getLogger(f'{__name__}.{type(self).__name__}')

	def _run_Copy(self, copy: commands.Copy, simfile: Simfile):
		src = copy.source
		source: notedata.NoteData = _chart_from_index(simfile, src.start.chart_index, ('source')).notes
		source = source[src.start.position: src.start.position + src.length] # type: ignore # mypy-slice

		for i, d in enumerate(copy.targets):
			dest_chart = _chart_from_index(simfile, d.chart_index, ('target', i))
			dest_chart.notes = dest_chart.notes.overlay(
				source.shift(d.position - src.start.position),
				mode = copy.overlay_mode
			)

	def _run_Pragma(self, pragma: commands.Pragma, _: Simfile):
		if pragma.name == 'echo':
			self.logger.info(f'{pragma.data}')
		elif pragma.name == 'vars':
			for var, val in self.frames[-1].variables.items():
				self.logger.info(f"'{var}' = {val}")
		elif pragma.name == 'raise':
			raise CommandError((), f'unconditional raise via pragma: {pragma.data}')
		elif pragma.name == 'callable':
			# for debug use only!
			cmd, args = pragma.data[0], pragma.data[1:]
			result = cmd(self, *args)
			self.logger.debug(f'callable pragma with args:\n{args}\nreturned:\n{result}')
		else:
			raise CommandError((), f"unknown pragma '{pragma.name}'")

	def _run_Group(self, group: commands.Group, simfile: Simfile):
		with self:
			self.run_many(group.commands, simfile)

	def _run_Def(self, c_def: commands.Def, _: Simfile):
		self.frames[-1].variables[c_def.name] = c_def

	def _run_Call(self, call: commands.Call, simfile: Simfile):
		try:
			what = self.lookup(call.name)
		except KeyError:
			raise CommandError(('Call',), f"function '{call.name}' does not exist") from None
		if not isinstance(what, commands.Def):
			raise CommandError(
				('Call',),
				f"variable '{call.name}' is not a function, but {type(what).__name__} instead"
			)
		try:
			self._run_Group(what.body, simfile)
		except CommandError as e:
			raise CommandError(('<fn>' + call.name,), "error during function call") from e

	def _run_Let(self, let: commands.Let, _: Simfile):
		self.frames[-1].variables[let.name] = let.value

	def _run_For(self, c_for: commands.For, simfile: Simfile):
		for i, value in enumerate(c_for.in_iterable):
			try:
				# Each iteration gets its own scope, and we don't try to undo the group scope,
				# so unlike Python, it is forbidden to reference dangling values from the last loop iteration
				# this is implementation-defined and may change
				with self:
					self._run_Let(commands.Let(c_for.name, value), simfile)
					self._run_Group(c_for.body, simfile)
			except CommandError as e:
				raise CommandError((i,), f"'{c_for.name}': {type(value).__name__} := {value}") from e

	def run(self, command: commands.Command, simfile: Simfile):
		'''run a command on the simfile, potentially modifying it in-place'''

		cmd_type_fn: Mapping[type, Callable[[Any, Simfile], None]] = {
			commands.Copy: self._run_Copy,

			commands.Pragma: self._run_Pragma,
			commands.Group: self._run_Group,
			commands.Def: self._run_Def,
			commands.Call: self._run_Call,
			commands.Let: self._run_Let,
			commands.For: self._run_For,
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
			except Exception:
				# print out whatever failed since it may not be obvious from stack trace
				print(command)
				raise

		else:
			raise CommandError((), f"unhandled command '{command}'")

	def run_many(self, cmds: Iterable[commands.Command], simfile: Simfile):
		'''convenience function to run a stream of commands'''
		for i, c in enumerate(cmds):
			try:
				self.run(c, simfile)
			except CommandError as e:
				raise CommandError((i,)) from e
