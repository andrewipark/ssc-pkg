from enum import Enum, auto
from fractions import Fraction
from itertools import chain, groupby
from math import gcd
from typing import Iterable, List, Sequence, Union, overload

import attr


_NotePosition = Fraction
_NoteType = Sequence # SM: str


# NOTE blocked https://github.com/python/mypy/issues/3186
# mypy doesn't work with numbers tower, so we have to write out types explicitly
_NotePosSafe = Union[_NotePosition, int]


_SM_TEXT_BEATS_PER_MEASURE = 4 # regardless of time signature data elsewhere
_SM_TEXT_MEASURE_SEP = ','


@attr.s(auto_attribs=True, frozen=True, slots=True)
class DensityInfo:
	delta: _NotePosition
	count: int


@attr.s(auto_attribs=True, frozen=True, slots=True)
class _NoteRow:
	position: _NotePosition # = attr.ib(converter=Fraction)
	# causes slowdown, and caller should know better anyways?
	notes: _NoteType


# NOTE blocked https://github.com/python/mypy/issues/7912 should be internal @classmethod
def _normalize_notes(notes_list: Iterable[_NoteRow]) -> List[_NoteRow]:
	return sorted(notes_list, key = lambda r: r.position)


@attr.s(auto_attribs=True, frozen=True)
class NoteData:
	'''Class representing note data of a simfile. Data is stored by row.

	This is intended as a container class and doesn't store nor handle
	semantic data about what notes actually mean.
	'''

	def __validate_notes(self, _, notes_list: List[_NoteRow]):
		if len(note_row_lengths := set(len(r.notes) for r in notes_list)) > 1:
			raise ValueError(
				f'note rows have different lengths ({list(note_row_lengths)}) and are not homogenous'
			)

		for i in range(1, len(notes_list)):
			prev, curr = notes_list[i - 1], notes_list[i]
			if prev.position == curr.position:
				raise IndexError(f'rows {i-1} and {i} have identical position {prev.position}')

	# all the notes stored by this object, in [beat: notes] form
	_notes: List[_NoteRow] = attr.ib(factory=list, converter=_normalize_notes, validator=__validate_notes)

	# access

	def __len__(self) -> int:
		'''Return the number of note rows'''
		return len(self._notes)

	def __index_of_row(self, position: _NotePosSafe) -> int:
		'''Return n s.t. _notes[n].position = position, or insert location if absent'''
		lo, hi = 0, len(self._notes)
		while lo < hi:
			c = (lo + hi) // 2
			if self._notes[c].position < position:
				lo = c + 1
			else:
				hi = c
		return lo

	def __index_of_row_must_exist(self, position: _NotePosSafe) -> int:
		i = self.__index_of_row(position)
		if self._notes[i].position != position:
			raise IndexError
		return i

	def __contains__(self, position: _NotePosSafe) -> bool:
		i = self.__index_of_row(position)
		return (i < len(self._notes)) and (self._notes[i].position == position)

	@overload
	def __getitem__(self, key: slice) -> 'NoteData':
		'''Slice the notedata at the given boundaries, and return a contiguous subset'''
	@overload
	def __getitem__(self, key: _NotePosSafe) -> _NoteType:
		'''Return the note at a given beat'''

	def __getitem__(self, key):
		if isinstance(key, slice):
			if key.step is not None:
				raise IndexError('slice with step parameter not sensible')

			if key.start is None:
				slice_start = 0
			else:
				slice_start = self.__index_of_row(key.start)

			if key.stop is None:
				slice_stop = len(self._notes)
			else:
				slice_stop = self.__index_of_row(key.stop)

			return attr.evolve(self, notes = self._notes[slice_start:slice_stop])

		return self._notes[self.__index_of_row_must_exist(key)].notes

	def __delta_generator(self):
		if len(self._notes) <= 1:
			raise IndexError('invalid operation, chart has too few notes')
		i = 1
		while i < len(self._notes):
			yield self._notes[i].position - self._notes[i - 1].position
			i += 1

	def density(self) -> Iterable[DensityInfo]:
		'''Return the density of the note data'''
		if len(self._notes) == 1:
			return []
		return [DensityInfo(k, sum(1 for _ in g)) for k, g in groupby(self.__delta_generator())]

	# mutation

	def shift(self, amount: _NotePosSafe) -> 'NoteData':
		'''Shift all the notes by a given amount in time'''
		return attr.evolve(self, notes = [_NoteRow(r.position + amount, r.notes) for r in self._notes])

	def clear_range(self, start: _NotePosSafe, stop: _NotePosSafe) -> 'NoteData':
		'''Removes all the notes in the specified half-open range [start, stop)'''
		antislice_start, antislice_stop = (self.__index_of_row(x) for x in (start, stop))
		return attr.evolve(self, notes = chain(self._notes[:antislice_start], self._notes[antislice_stop:]))

	class OverlayMode(Enum):
		KEEP_SELF = auto()
		KEEP_OTHER = auto()
		RAISE = auto()

	def overlay(self, other: 'NoteData', mode: OverlayMode = OverlayMode.RAISE) -> 'NoteData':
		'''Overlay another NoteData object onto this one'''

		if mode == self.OverlayMode.RAISE:
			return attr.evolve(self, notes = chain(self._notes, other._notes))

		# bastardized 'merge' of mergesort
		rows = []
		i_s, i_o = 0, 0
		while i_s < len(self._notes) and i_o < len(other._notes):
			# print(i_s, i_o)
			if self._notes[i_s].position < other._notes[i_o].position:
				rows.append(self._notes[i_s])
				i_s += 1
			elif other._notes[i_o].position < self._notes[i_s].position:
				rows.append(other._notes[i_o])
				i_o += 1
			else:
				if mode == self.OverlayMode.KEEP_SELF:
					rows.append(self._notes[i_s])
				else: # elif mode == self.OverlayMode.KEEP_OTHER:
					rows.append(other._notes[i_o])
				# unlike merge sort, we only keep one of the elements in a tie
				i_s += 1
				i_o += 1

		# sweep up remaining elements
		rows.extend(self._notes[i_s:])
		rows.extend(other._notes[i_o:])

		return attr.evolve(self, notes = rows)


def sm_to_notedata(data: str) -> NoteData:
	measures: List[List[str]] = [m.strip().split() for m in data.split(_SM_TEXT_MEASURE_SEP)]
	measure_notes: List[List[_NoteRow]] = [
		[
			_NoteRow((Fraction(row_index, len(measure)) + measure_index) * _SM_TEXT_BEATS_PER_MEASURE, row)
			for row_index, row in enumerate(measure)
			# filter out empty rows
			if any(note != '0' for note in row)
		]
		for measure_index, measure in enumerate(measures)
	]
	return NoteData(chain(*measure_notes))


# NOTE blocked py3.9 lcm
def _lcm(it):
	curr_lcm = 1
	for i in it:
		the_gcd = gcd(curr_lcm, i)
		curr_lcm //= the_gcd
		curr_lcm *= i
	return curr_lcm


def notedata_to_sm(data: NoteData) -> str:
	measures_text: List[str] = []
	EMPTY_ROW = '0' * len(data._notes[0].notes)

	# group notes by measure
	for index, rs in groupby(data._notes, key=lambda r: r.position // _SM_TEXT_BEATS_PER_MEASURE):
		rows = list(rs)

		# fill in missing measures with empty data
		for _ in range(len(measures_text), index):
			measures_text.append('\n'.join([EMPTY_ROW] * _SM_TEXT_BEATS_PER_MEASURE))

		# set up text array
		measure_rows_count = (_lcm(r.position.denominator for r in rows) * _SM_TEXT_BEATS_PER_MEASURE)
		measure_rows = [EMPTY_ROW] * measure_rows_count

		for r in rows:
			dest_index = (r.position / _SM_TEXT_BEATS_PER_MEASURE % 1) * measure_rows_count
			assert dest_index.denominator == 1, dest_index
			measure_rows[dest_index.numerator] = r.notes
		measures_text.append('\n'.join(measure_rows))

	return ('\n' + _SM_TEXT_MEASURE_SEP + '\n').join(measures_text)
