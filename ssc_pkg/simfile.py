from fractions import Fraction
from itertools import chain
from typing import List

import attr


_NoteType = str


@attr.s(auto_attribs=True, frozen=True, slots=True)
class _NoteRow:
	position: Fraction
	notes: _NoteType


# FIXME blocked by https://github.com/python/mypy/issues/7912 should be internal @classmethod
def _normalize_notes(notes_list: List[_NoteRow]) -> List[_NoteRow]:
	return sorted(notes_list, key = lambda r: r.position)


@attr.s(auto_attribs=True, frozen=True)
class NoteData:
	"""Class representing note data of a simfile."""

	# All the notes stored by this object, in [beat: notes] form
	_notes: List[_NoteRow] = attr.ib(default=None, converter=_normalize_notes)

	def __len__(self) -> int:
		'''Return the number of note rows'''
		return len(self._notes)

	def __index_of_row(self, position: Fraction) -> int:
		'''Returns n s.t. _notes[n].position = position'''
		for i, r in enumerate(self._notes):
			if r.position == position:
				return i
		raise IndexError

	def __getitem__(self, key) -> _NoteType:
		'''Returns the note at a given beat.'''
		if isinstance(key, slice):
			if key.step is not None:
				raise IndexError('step with slices is not sensible')
			raise NotImplementedError
		return self._notes[self.__index_of_row(key)].notes

	def shift(self, amount: Fraction) -> 'NoteData':
		'''Shifts all the notes by a given amount in time.'''
		return NoteData([_NoteRow(r.position + amount, r.notes) for r in self._notes])


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
