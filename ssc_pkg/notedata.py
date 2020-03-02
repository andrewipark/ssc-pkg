from fractions import Fraction
from itertools import chain, groupby
from typing import List, Iterable, Union

import attr


_NotePosition = Fraction
_NoteType = str


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
	"""Class representing note data of a simfile."""

	def __validate_notes(self, _, notes_list: List[_NoteRow]):
		# TODO: check note rows for duplicate values
		pass

	# All the notes stored by this object, in [beat: notes] form
	_notes: List[_NoteRow] = attr.ib(default=None, converter=_normalize_notes, validator=__validate_notes)

	def __len__(self) -> int:
		'''Return the number of note rows'''
		return len(self._notes)

	def __index_of_row(self, position: _NotePosition) -> int:
		'''Returns n s.t. _notes[n].position = position'''
		# NOTE perf O(n)
		for i, r in enumerate(self._notes):
			if r.position == position:
				return i
		raise IndexError

	def __contains__(self, position: _NotePosition) -> bool:
		try:
			self.__index_of_row(position)
			return True
		except IndexError:
			return False

	def __getitem__(self, key: Union[_NotePosition, slice]) -> Union[_NoteType, 'NoteData']:
		'''Returns the note at a given beat.'''
		if isinstance(key, slice):
			if key.step is not None:
				raise IndexError('step with slices is not sensible')

			# NOTE perf O(n), using bisection would still need O(n) array building
			slice_start = 0
			while slice_start < len(self._notes) and self._notes[slice_start].position < key.start:
				slice_start += 1
			slice_stop = slice_start
			while slice_stop < len(self._notes) and self._notes[slice_stop].position < key.stop:
				slice_stop += 1
			return attr.evolve(self, notes = self._notes[slice_start:slice_stop])

		return self._notes[self.__index_of_row(key)].notes

	def shift(self, amount: _NotePosition) -> 'NoteData':
		'''Shifts all the notes by a given amount in time.'''
		return attr.evolve(self, notes = [_NoteRow(r.position + amount, r.notes) for r in self._notes])

	def clear_range(self, start: _NotePosition, stop: _NotePosition) -> 'NoteData':
		'''Removes all the notes in the specified half-open range [start, stop).'''
		return attr.evolve(self, notes = [r for r in self._notes if not (start <= r.position < stop)])

	def overlay(self, other: 'NoteData', preserve_self: bool = False) -> 'NoteData':
		'''Overlays another NoteData object onto this one.'''
		raise NotImplementedError

	def mirror(self, axes: List[str] = None) -> 'NoteData':
		'''Applies the mirror transformation to the data.'''
		raise NotImplementedError

	def __delta_generator(self):
		if len(self._notes) <= 1:
			raise IndexError('invalid operation, chart has too few notes')
		i = 1
		while i < len(self._notes):
			yield self._notes[i].position - self._notes[i - 1].position
			i += 1

	def density(self) -> Iterable[DensityInfo]:
		'''Return the density of the note pattern.'''
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
