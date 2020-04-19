from fractions import Fraction
from itertools import chain, groupby
from typing import List, Iterable, Sequence, overload

import attr


_NotePosition = Fraction
_NoteType = Sequence # SM: str


@attr.s(auto_attribs=True, frozen=True, slots=True)
class DensityInfo:
	delta: _NotePosition
	count: int


@attr.s(auto_attribs=True, frozen=True, slots=True)
class _NoteRow:
	position: _NotePosition
	notes: _NoteType


# FIXME blocked by https://github.com/python/mypy/issues/7912 should be internal @classmethod
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
				raise ValueError(f'rows {i-1} and {i} have identical position {prev.position}')

	# All the notes stored by this object, in [beat: notes] form
	_notes: List[_NoteRow] = attr.ib(factory=list, converter=_normalize_notes, validator=__validate_notes)

	def __len__(self) -> int:
		'''Return the number of note rows'''
		return len(self._notes)

	def __index_of_row(self, position: _NotePosition) -> int:
		'''Return n s.t. _notes[n].position = position, or insert location if absent'''
		lo, hi = 0, len(self._notes)
		while lo < hi:
			c = (lo + hi) // 2
			if self._notes[c].position < position:
				lo = c + 1
			else:
				hi = c
		return lo

	def __index_of_row_must_exist(self, position: _NotePosition) -> int:
		i = self.__index_of_row(position)
		if self._notes[i].position != position:
			raise IndexError
		return i

	def __contains__(self, position: _NotePosition) -> bool:
		i = self.__index_of_row(position)
		return (i < len(self._notes)) and (self._notes[i].position == position)

	@overload
	def __getitem__(self, key: slice) -> 'NoteData':
		'''Slice the notedata at the given boundaries, and return a contiguous subset'''
	@overload
	def __getitem__(self, key: _NotePosition) -> _NoteType:
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

	def shift(self, amount: _NotePosition) -> 'NoteData':
		'''Shift all the notes by a given amount in time'''
		return attr.evolve(self, notes = [_NoteRow(r.position + amount, r.notes) for r in self._notes])

	def clear_range(self, start: _NotePosition, stop: _NotePosition) -> 'NoteData':
		'''Removes all the notes in the specified half-open range [start, stop)'''
		return attr.evolve(self, notes = [r for r in self._notes if not (start <= r.position < stop)])

	def overlay(self, other: 'NoteData', preserve_self: bool = False) -> 'NoteData':
		'''Overlay another NoteData object onto this one'''
		raise NotImplementedError

	def mirror(self, axes: List[str] = None) -> 'NoteData':
		'''Apply the mirror transformation to the note data'''
		raise NotImplementedError

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


def sm_to_notedata(data: str) -> NoteData:
	# split out data
	measures: List[List[str]] = [m.strip().split() for m in data.split(',')]
	measure_notes: List[List[_NoteRow]] = [
		[
			# measures in SM text are 4 beats regardless of TS data
			_NoteRow((Fraction(measure_subindex, len(measure)) + measure_index) * 4, row)
			for measure_subindex, row in enumerate(measure)
			# filter out empty rows
			if any([note != '0' for note in row])
		]
		for measure_index, measure in enumerate(measures)
	]
	# since we converted to beat numbers we don't care about measures anymore
	return NoteData(list(chain(*measure_notes)))


def notedata_to_sm(data: NoteData) -> str:
	raise NotImplementedError
