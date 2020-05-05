from typing import ClassVar, Iterable, Union
from enum import Enum, auto
import logging

import attr


class MSDSyntaxError(ValueError):
	pass


@attr.s(auto_attribs=True, frozen=True, slots=True)
class MSDItem:
	'''Immutable POD for an individual MSD item, representing a tag and a value.

	The meaning of MSD is lost to the sands of time.

	NOTE 'key' ia more pythonic, but 'tag' is the canonical StepMania name per the wiki.
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

	NOTE Iterable[str] is provided for convenience with file objects.

	NOTE This parser is stricter than SM `/src/MsdFile.cpp`
	* All items must start at the beginning of lines.
	* Unclosed items will cause undefined behavior.
	(SM rstrips the text and soldiers on; this is too complex to replicate.)
	* Backslash escapes are not supported.
	Behavior seems to vary across products:
		AV ignores the backslash
		SM 3.9 doesn't support it at all
		SM5 parses it to... something.
	'''
	if isinstance(lines, str):
		lines = lines.splitlines(keepends = True)

	state: _ParsingState = _ParsingState.NOTHING
	tag_name: str
	current_content: str = ''

	for il, line in enumerate(lines):
		il += 1 # standard text editor convention for error messages

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
