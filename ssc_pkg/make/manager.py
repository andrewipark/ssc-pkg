'''context manager and command line runner'''

from fractions import Fraction
from logging import getLogger
from typing import Any, Callable, Dict, Iterable, List, Mapping, Type, TypeVar, Union, get_type_hints

import attr

from ssc_pkg import notedata
from ssc_pkg.simfile import Chart, Simfile

from . import commands


_T = TypeVar('_T')


class CommandError(Exception):
	'''Exception class for errors caused by commands.

	Raisers MUST conform to the :meth:`~ssc_pkg.make.util.exc_index_trace` spec
	'''


def _chart_from_index(simfile: Simfile, chart_index: int, indices) -> Chart:
	if chart_index < len(simfile.charts):
		return simfile.charts[chart_index]

	raise CommandError(indices, f'no source chart at index {chart_index}')


# this is not strictly manager related and could probably go somewhere else...

_GAME_TYPE_COLUMNS_TABLE = {
	'dance-single': 4,
	'dance-double': 8,
	'pump-single': 5,
	'pump-double': 10,
	# TODO a lot is missing
}


# curiously, mirroring "horizontally" means that the flip is actually across the vertical axis...
_MIRROR_TRANSLATE_TABLE_PACKED = {
	'dance-single': { # 0-3
		('horizontal', 'horiz', 'h'): [3, 1, 2, 0],
		('vertical', 'vert'): [0, 2, 1, 3],
		('oblique',): [2, 3, 0, 1],
		('antioblique',): [1, 0, 3, 2],
	},
	'pump-single': {
		('horizontal', 'horiz', 'h'): [4, 3, 2, 1, 0],
		('vertical', 'vert'): [1, 0, 2, 4, 3],
		('oblique',): [0, 4, 2, 3, 1],
		('antioblique',): [3, 1, 2, 0, 4],
	},
	# TODO: missing doubles and most other game modes
}


_MIRROR_TRANSLATE_TABLE = {
	gt: {
		k: v for ki, v in t.items() for k in ki
	} for gt, t in _MIRROR_TRANSLATE_TABLE_PACKED.items()
}


@attr.s(auto_attribs=True)
class _Context:
	'''The equivalent of a stack frame for the manager'''

	variables: Dict[str, Union[commands.VarValue, commands.Def]] = attr.Factory(dict)


# concrete versions of commands data structures

@attr.s(auto_attribs=True)
class ChartPoint:
	'''concrete version of :class:`~.commands.ChartPoint`'''
	chart_index: int
	position: notedata.Position


@attr.s(auto_attribs=True)
class ChartRegion:
	'''concrete version of :class:`~.commands.ChartRegion`'''
	start: ChartPoint
	length: notedata.Position


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
		raise KeyError(f"'{name}' not defined")

	def lookup_typed(self, name: str, t: Type[_T]) -> _T:
		'''convenience lookup function with guaranteed return type (caveat: generic subscripting)'''
		test = self.lookup(name)
		if issubclass(t, Fraction): # special case convertible types
			if isinstance(test, int):
				test = Fraction(test)
		if not isinstance(test, t):
			raise TypeError(f"'{name}' is a {type(test).__name__}, not {t.__name__}")
		return test

	def resolve(self, what: Union[_T, commands.VarRef], t: Type[_T]) -> _T:
		'''Another convenience lookup function for converting Union[variable, object] to assured object'''
		if isinstance(what, commands.VarRef):
			return self.lookup_typed(what.name, t)
		return what

	def reduce_ChartPoint(self, chart_point: commands.ChartPoint) -> ChartPoint:
		'''resolves all variable references in a :class:`~.commands.ChartPoint`'''
		base = self.lookup_typed(chart_point.base.name, Fraction) if chart_point.base else Fraction(0)
		return ChartPoint(
			chart_index = self.resolve(chart_point.chart_index, int),
			position = base + self.resolve(chart_point.offset, Fraction),
		)

	def reduce_ChartRegion(self, chart_region: commands.ChartRegion) -> ChartRegion:
		'''resolves all variable references in a :class:`~.commands.ChartRegion`'''
		return ChartRegion(
			start = self.reduce_ChartPoint(chart_region.start),
			length = self.resolve(chart_region.length, Fraction),
		)

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
		src = self.reduce_ChartRegion(copy.source)
		source: notedata.NoteData = _chart_from_index(simfile, src.start.chart_index, ('source')).notes
		source = source[src.start.position: src.start.position + src.length] # type: ignore # mypy-slice

		for i, dv in enumerate(copy.targets):
			try:
				d = self.reduce_ChartPoint(dv)
				dest_chart = _chart_from_index(simfile, d.chart_index, ('target', i))
				dest_chart.notes = dest_chart.notes.overlay(
					source.shift(d.position - src.start.position),
					mode = copy.overlay_mode
				)
			except Exception as e:
				raise CommandError((i,)) from e

	def _run_Erase(self, erase: commands.Erase, simfile: Simfile):
		t = self.reduce_ChartRegion(erase.target)
		target = _chart_from_index(simfile, t.start.chart_index, ('target',))
		target.notes = target.notes.clear_range(
			t.start.position,
			t.start.position + t.length
		)

	def _run_ColumnSwap(self, column_swap: commands.ColumnSwap, simfile: Simfile):
		target = self.reduce_ChartRegion(column_swap.target)
		chart = _chart_from_index(simfile, target.start.chart_index, ('source'))
		if chart.game_type not in _MIRROR_TRANSLATE_TABLE:
			raise NotImplementedError(chart.game_type)
		start = target.start.position
		stop = start + target.length
		notes_region = chart.notes[start:stop] # type: ignore # mypy-slice
		if not notes_region:
			self.logger.info(f'column_swap: chart {target.start.chart_index}, span {start} to {stop} is empty')
			return

		# calculate column recombination
		columns = list(range(_GAME_TYPE_COLUMNS_TABLE[chart.game_type]))
		for i, m in enumerate(column_swap.methods):
			try:
				translate_table = _MIRROR_TRANSLATE_TABLE[chart.game_type][m]
			except KeyError:
				raise CommandError((i,), f'unknown method: {m}') from None
			columns = [columns[new_index] for new_index in translate_table]

		# TODO: need a dedicated 'replace' command
		chart.notes = chart.notes.overlay(
			notes_region.column_swap(columns),
			mode = notedata.NoteData.OverlayMode.KEEP_OTHER
		)

	def _run_DeleteChart(self, delete_chart: commands.DeleteChart, simfile: Simfile):
		_chart_from_index(simfile, delete_chart.index, ('index',)) # index check
		del simfile.charts[delete_chart.index]

	def _run_Pragma(self, pragma: commands.Pragma, simfile: Simfile):
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
		elif pragma.name == 'labels_as_vars':
			for t, l in simfile.timing_data.labels.items():
				self._run_Let(commands.Let(l, Fraction(t)), simfile)
		else:
			raise CommandError((), f"unknown pragma '{pragma.name}'")

	def _run_Group(self, group: commands.Group, simfile: Simfile):
		with self:
			self.run_many(group.commands, simfile)

	def _run_Def(self, c_def: commands.Def, _: Simfile):
		self.frames[-1].variables[c_def.name] = c_def

	def _run_Call(self, call: commands.Call, simfile: Simfile):
		# this exception handling logic is wayyyyy more convoluted than it needs to be...
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
		except Exception as e:
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
			except Exception as e:
				raise CommandError((i,), f"'{c_for.name}': {type(value).__name__} := {value}") from e

	def run(self, command: commands.Command, simfile: Simfile):
		'''run a command on the simfile, potentially modifying it in-place'''

		cmd_type_fn: Mapping[type, Callable[[Any, Simfile], None]] = {
			commands.Copy: self._run_Copy,
			commands.Erase: self._run_Erase,
			commands.ColumnSwap: self._run_ColumnSwap,
			commands.DeleteChart: self._run_DeleteChart,

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
			except Exception as e:
				if ct is commands.Group or ct is commands.Call:
					# these are structural, we don't care about the name
					raise e
				raise CommandError((ct.__name__,)) from e

		else:
			raise TypeError((), f"unhandled command '{command}'")

	def run_many(self, cmds: Iterable[commands.Command], simfile: Simfile):
		'''convenience function to run a stream of commands'''
		for i, c in enumerate(cmds):
			try:
				self.run(c, simfile)
			except Exception as e:
				raise CommandError((i,)) from e
