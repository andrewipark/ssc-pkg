import logging
from collections import OrderedDict as ordered_dict
from enum import Enum, auto
from typing import Any, Callable, ClassVar, Iterable, Optional, Sequence, Type, TypeVar, Union
from warnings import warn

import attr


class MSDSyntaxError(ValueError):
	pass


def _get_validate_part(component: str):
	def __validate_part(_, attribute, val: str):
		if component in val:
			raise MSDSyntaxError(f"'{attribute.name}' contains invalid substring '{component}' in '{val}'")
	return __validate_part


@attr.s(auto_attribs=True, frozen=True, slots=True)
class MSDItem:
	'''Immutable POD for an individual MSD item, representing a tag and a value.

	The meaning of MSD is lost to the sands of time.

	NOTE 'key' ia more pythonic, but 'tag' is the canonical StepMania name per the wiki.
	'''
	# syntactical elements
	BEGIN: ClassVar[str] = '#'
	END_TAG: ClassVar[str] = ':'
	END_VALUE: ClassVar[str] = ';'
	COMMENT: ClassVar[str] = '//'

	tag: str = attr.ib(validator=_get_validate_part(END_TAG))
	value: str = attr.ib(validator=_get_validate_part(END_VALUE))

	def __str__(self):
		return f'{self.BEGIN}{self.tag}{self.END_TAG}{self.value}{self.END_VALUE}'


class _ParsingState(Enum):
	NOTHING = auto()
	TAG_DATA = auto()


def text_to_msd(text: Union[str, Iterable[str]]) -> Iterable[MSDItem]: # noqa: C901
	'''Generate structured Python MSD objects from string MSD

	NOTE Iterable[str] is provided for convenience with file objects.

	NOTE This parser is stricter than SM ``/src/MsdFile.cpp``:

	-	All items must start at the beginning of lines.
	-	Unclosed items will cause undefined behavior.
		(SM rstrips the text and soldiers on; this is too complex to replicate.)
	-	Backslash escapes are not supported.
		Behavior seems to vary across products:

		- AV ignores the backslash
		- SM3.9 doesn't support it at all
		- SM5 interprets them in standard fashion, so ``\\t`` becomes an actual tab character

	Maybe a regex-based solution would be easier to maintain than this behemoth
	'''
	if isinstance(text, str):
		text = text.splitlines(keepends = True)

	state: _ParsingState = _ParsingState.NOTHING
	tag_name: str
	current_content: str = ''

	for il, line in enumerate(text):
		il += 1 # standard text editor convention for error messages

		# trim comments first, just as in SM.
		comment_trim = line.find('//')
		if comment_trim != -1:
			line = line[:-comment_trim]

		if state is _ParsingState.NOTHING:
			if not line.strip():
				continue
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


def msd_to_lines(items: Iterable[MSDItem]) -> Iterable[str]:
	'''lazy converter of MSD items to string representation'''
	for item in items:
		yield str(item) + '\n'


def msd_to_text(items: Iterable[MSDItem]) -> str:
	'''convenience wrapper around :meth:`~.msd_to_lines`'''
	return ''.join(msd_to_lines(items))


# type variable helpers
_T_obj = TypeVar('_T_obj', bound=attr.AttrsInstance)
_T_val = TypeVar('_T_val')


# generic conversion functions

def attrs_obj_to_msd(
	attrs_obj,
	name_converter: Callable[[str], str] = lambda name: name,
	value_converter:
		Callable[[str, Type[_T_val], _T_val], str]
		= lambda name, value_type, value: str(value),
	filterer:
		Callable[[str, Type[_T_val], _T_val], bool]
		= lambda name, value_type, value: value is not None,
) -> Iterable[MSDItem]:
	'''Convert an attrs object to MSD items

	MSD is inherently a flat structure, so callers should only use this function on flat/POD objects.
	'''
	attr_field_data = attr.fields(type(attrs_obj))
	obj_data = attr.asdict(attrs_obj, dict_factory=ordered_dict, recurse=False)
	assert [a.name for a in attr_field_data] == list(obj_data.keys())

	data = list(zip(obj_data.keys(), (a.type for a in attr_field_data), obj_data.values()))

	for name, val_type, value in data:
		if val_type is None:
			warn(
				f'class {type(attrs_obj)} variable {name} has no type information,'
				f'guessing {type(value)} from given value'
			)
			val_type = type(value)
		if filterer(name, val_type, value):
			yield MSDItem(name_converter(name), value_converter(name, val_type, value))


def msd_to_attrs_obj(
	items: Iterable[MSDItem],
	attrs_class: Type[_T_obj],
	tag_converter: Callable[[str], str] = lambda tag: tag,
	value_converter:
		Callable[[str, Type[_T_val], str], Optional[_T_val]]
		= lambda tag, value_type, value_str: None # not as useful
) -> tuple[_T_obj, Sequence[MSDItem]]:
	'''Convert MSD data to an attrs object

	If there are multiple MSD items that resolve to the same field,
	the value used will be from the last MSD item,
	but the duplicate items will not be returned.
	'''
	attr_field_data = attr.fields_dict(attrs_class)

	unused_items = []
	creation_dict = {}
	for item in items:
		tag, value = item.tag, item.value

		name = tag_converter(tag)
		if name not in attr_field_data:
			unused_items.append(item)
			continue

		val_type = attr_field_data[name].type
		if val_type is None:
			warn(f'class {attrs_class} variable {name} has no type information')
			val_type = Any # type: ignore # ??
			assert val_type is not None, 'mypy'

		try:
			creation_dict[name] = value_converter(tag, val_type, value)
		except Exception as e:
			print(f'conversion failed for class {attrs_class} variable {name}')
			raise e

	return attrs_class(**creation_dict), unused_items # noqa: F821
