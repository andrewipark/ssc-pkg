from typing import ClassVar, Iterable, Union
from enum import Enum, auto
import logging

import attr


class MSDSyntaxError(ValueError):
	pass


@attr.s(auto_attribs=True, frozen=True, slots=True)
class MSDItem:
	'''Immutable POD for an individual MSD item, representing a tag and a value.

	NOTE the pythonic name would be 'key', but 'tag' is the name used on the StepMania wiki.
	I also don't know where 'MSD' comes from.
	'''

	def __validate_part(self, _, tag):
		if self.END_TAG in tag:
			raise MSDSyntaxError(f"A component '{tag}' contains end tag delimiter '{self.END_TAG}'")
		if self.END_VALUE in tag:
			raise MSDSyntaxError(f"A component '{tag}' contains end value delimiter '{self.END_VALUE}'")

	tag: str = attr.ib(validator=__validate_part)
	value: str = attr.ib(validator=__validate_part)

	# syntactical elements
	BEGIN: ClassVar[str] = '#'
	END_TAG: ClassVar[str] = ':'
	END_VALUE: ClassVar[str] = ';'
	COMMENT: ClassVar[str] = '//'

	def __str__(self):
		return f'{self.BEGIN}{self.tag}{self.END_TAG}{self.value}{self.END_VALUE}\n'


class _ParsingState(Enum):
	NOTHING = auto()
	TAG_DATA = auto()


def lines_to_msd_items(lines: Union[str, Iterable[str]]) -> Iterable[MSDItem]:
	'''Generate structured Python data from textual MSD.

	NOTE The input lines must preserve the line endings,
	and each string (except the last) must have only one line break, and only at the end of the string.
	This is for convenience with file objects.

	NOTE For simplicity, this parser is more restrictive on its input than SM `/src/MsdFile.cpp`.
	All items must start at the beginning of lines,
	and we do not attempt to rescue unclosed items.
	(SM apparently rstrips them; this is too complex to replicate.)

	TODO This parser doesn't currently support
	* backslash escape: non-operational in AV, e.g. \\t does not turn into the tab character,
	unconditional escape in SM. we'll need to add escape/unescape fn's to MSDItem.
	'''
	if isinstance(lines, str):
		lines = lines.splitlines(keepends = True)

	state: _ParsingState = _ParsingState.NOTHING
	tag_name: str
	current_content: str = ''

	for il, line in enumerate(lines):
		il += 1 # text editor convention

		# trim comments first, just as in SM.
		comment_trim = line.find('//')
		if comment_trim != -1:
			line = line[:-comment_trim]

		if state is _ParsingState.NOTHING:
			if not line.startswith(MSDItem.BEGIN):
				raise MSDSyntaxError(
					f"Line {il}: expected '{MSDItem.BEGIN}' to start a new item, "
					f"but got '{line[:len(MSDItem.BEGIN)]}' instead"
				)
			line = line[len(MSDItem.BEGIN):]
			if MSDItem.END_TAG not in line:
				raise MSDSyntaxError(
					f"Line {il}: expected a '{MSDItem.END_TAG}' to end item tag, "
					f"but got '{line}' instead"
				)
			tag_name, line = line.split(MSDItem.END_TAG, 1)
			state = _ParsingState.TAG_DATA

		# if state is _ParsingState.TAG_DATA:
		line_end = line.split(MSDItem.END_VALUE, 1)
		if len(line_end) > 1:
			if line_end[1].strip():
				raise MSDSyntaxError(
					f"Line {il}: after ending item value there should be no content'"
					f"but got '{line_end[1]}' instead"
				)
			else:
				current_content += line_end[0]
				yield MSDItem(tag_name, current_content)
				state = _ParsingState.NOTHING
				current_content = ''
				tag_name = ''
		else:
			current_content += line

	if state is not _ParsingState.NOTHING:
		logging.warning('parse warning: unexpected EOF while reading item')
		yield MSDItem(tag_name, current_content)


def msd_items_to_lines(items: Iterable[MSDItem]) -> Iterable[str]:
	for item in items:
		for line in (str(item)).splitlines(keepends=True):
			yield line
