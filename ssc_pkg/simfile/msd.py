''':class:`~.MSDItem` ↔ rich Python object conversion for simfiles'''

from collections.abc import Mapping as MappingABC
from decimal import Decimal
from enum import Enum, auto
from pathlib import PurePath
from typing import (
	Callable, Iterable, List, Mapping, Optional, Tuple, Type, TypeVar, Union, cast, get_args, get_origin
)

from ssc_pkg import msd, notedata
from .structs import Chart, Simfile, TimingData


# data for MSD conversions

def _SM_msd_tables() -> Tuple[Mapping[str, str], Mapping[str, str]]:
	table = [
		# TimingData
		('bpm', 'BPMS'),
		('preview_start', 'SAMPLESTART'),
		('preview_length', 'SAMPLELENGTH'),
		('combo_multipliers', 'COMBOS'),
		('background_changes', 'BGCHANGES'),
		('foreground_changes', 'FGCHANGES'),

		# Chart
		('game_type', 'STEPSTYPE'),

		# Simfile
		('title_transliterated', 'TITLETRANSLIT'),
		('subtitle_transliterated', 'SUBTITLETRANSLIT'),
		('artist_transliterated', 'ARTISTTRANSLIT'),
		('lyrics', 'LYRICSPATH'),
		('preview_video', 'PREVIEWVID'),
	]

	allcaps_easy = [
		# TimingData
		'display_bpm', 'time_signatures', 'tick_counts', 'combo_multipliers',

		# Chart
		'chart_name', 'chart_style',

		# Simfile
		'cd_title', 'cd_image', 'disc_image',
	]

	for i in allcaps_easy:
		table.append((i, i.upper().replace('_', '')))

	return (
		dict(table),
		{tag: field for field, tag in table}
	)


_SM_tables = _SM_msd_tables()
_SM_items_to_msd: Mapping[str, str] = _SM_tables[0]
_SM_msd_to_items: Mapping[str, str] = _SM_tables[1]


def _SM_name_converter(name: str) -> str:
	return _SM_items_to_msd.get(name, name.upper())


def _SM_tag_converter(tag: str) -> str:
	return _SM_msd_to_items.get(tag, tag.lower())


class MSDValueError(ValueError):
	pass


_UNHANDLED_TYPE_MSG = "unhandled conversion of tag '{}' to value type '{}'"


# typing helpers

# probably doesn't belong here, but no one else uses it...
def undo_optional(t: type) -> type:
	'''Optional[X] -> X'''
	type_args = get_args(t)
	if get_origin(t) != Union or len(type_args) != 2:
		raise TypeError(f'{t} is not an Optional type')
	return cast(type, type_args[0] or type_args[1]) # short circuit None


_T_val = TypeVar('_T_val')


# MSD to python

# # TimingData

def _msd_td_mapping(tag: str, key_type, value_type, data: Iterable[Tuple[str, str]]) -> Mapping:
	value_conv: Callable = lambda x: x
	key_conv: Callable = key_type

	if value_type is Decimal or value_type is str or value_type is int:
		value_conv = value_type
	else:
		pass
		# TODO deliberately broken!
		# print('unhandled', tag, key_type, value_type, data)

	return {key_conv(k): value_conv(v) for k, v in data}


def _msd_to_timing_data_vcv(tag: str, value_type, value: str):
	try:
		value_type = undo_optional(value_type)
	except TypeError:
		pass

	if get_origin(value_type) == MappingABC:
		value = value.strip()
		if not value:
			return {}
		key_type, val_type = get_args(value_type)
		data: List[Tuple[str, str]] = [
			cast(Tuple[str, str], v.strip().split('=', 1)) # split only ever returns max len 2
			for v in value.strip().split(',')
		]
		return _msd_td_mapping(tag, key_type, val_type, data)
	if value_type is str or value_type is Decimal:
		return value_type(value)

	raise AssertionError(_UNHANDLED_TYPE_MSG.format(tag, value_type))


def _msd_to_timing_data(items: Iterable[msd.MSDItem]):
	return msd.msd_to_attrs_obj(
		items, TimingData,
		tag_converter = _SM_tag_converter,
		value_converter = _msd_to_timing_data_vcv
	)


def _timing_data_to_msd_vcv(name: str, value_type: Type[_T_val], value: _T_val) -> str:
	# None should not be emitted
	try:
		value_type = undo_optional(value_type)
	except TypeError:
		pass
	assert value is not None

	if isinstance(value, MappingABC):
		return ',\n'.join(f'{k}={v}' for k, v in value.items())

	return str(value)


def _timing_data_to_msd(timing_data: TimingData) -> Iterable[msd.MSDItem]:
	'''py > ssc msd'''
	return msd.attrs_obj_to_msd(
		timing_data,
		name_converter = _SM_name_converter,
		value_converter = _timing_data_to_msd_vcv,
	)


# # Chart

def _msd_to_chart_vcv(tag: str, value_type, value: str):
	try:
		value_type = undo_optional(value_type)
	except TypeError:
		pass

	if issubclass(value_type, notedata.NoteData):
		return notedata.sm_to_notedata(value)
	if value_type is int or value_type is str:
		return value_type(value)

	raise AssertionError(_UNHANDLED_TYPE_MSG.format(tag, value_type))


def _msd_to_chart(items: Iterable[msd.MSDItem]) -> Chart:
	chart, excess = msd.msd_to_attrs_obj(
		items, Chart,
		tag_converter = _SM_tag_converter,
		value_converter = _msd_to_chart_vcv
	)
	if excess:
		# not (yet) relevant
		excess = list(filter(lambda x: x.tag != 'RADARVALUES', excess))
	if excess:
		# don't create chart-specific timing unless we're sure we need it
		chart.timing_data, excess = _msd_to_timing_data(excess)
	if excess:
		raise MSDValueError(f"extraneous tags '{[e.tag for e in excess]}' in chart")
	return chart


def _chart_to_msd_vcv(name: str, value_type: Type[_T_val], value: _T_val) -> str:
	if isinstance(value, notedata.NoteData):
		return ''.join(['\n', notedata.notedata_to_sm(value), '\n'])
	return str(value)


def _chart_to_msd(chart: Chart) -> Iterable[msd.MSDItem]:
	'''py > ssc msd'''
	items = [msd.MSDItem('NOTEDATA', '')]
	if chart.timing_data:
		items.extend(_timing_data_to_msd(chart.timing_data))
	items.extend(msd.attrs_obj_to_msd(
		chart,
		name_converter = _SM_name_converter,
		value_converter = _chart_to_msd_vcv,
		filterer = lambda n, _, v: (n != 'timing_data') and (v is not None)
	))
	return items


# # Simfile (only direct fields and TimingData field object)

def _msd_to_simfile_skel_vcv(tag: str, value_type, value: str):
	is_optional = False
	try:
		value_type = undo_optional(value_type)
		is_optional = True
	except TypeError:
		pass

	if issubclass(value_type, PurePath) or value_type is str:
		if is_optional and not value:
			# swallow empty optional strings, and prevent empty paths from turning into spurious '.'
			return None
		return value_type(value)

	raise AssertionError(_UNHANDLED_TYPE_MSG.format(tag, value_type))


def _msd_to_simfile_skel(items: Iterable[msd.MSDItem]) -> Simfile:
	simfile, excess = msd.msd_to_attrs_obj(
		items, Simfile,
		tag_converter = _SM_tag_converter,
		value_converter = _msd_to_simfile_skel_vcv
	)
	simfile.timing_data, excess = _msd_to_timing_data(excess)
	if excess:
		excess = list(filter(lambda x: 'VERSION' not in x.tag, excess))
	if excess:
		raise MSDValueError(f"extraneous tags '{[e.tag for e in excess]}' in simfile header")
	return simfile


def _simfile_skel_to_msd(
	simfile: Simfile,
	version_tag: Optional[msd.MSDItem] = msd.MSDItem('VERSION', '0.83')
) -> Iterable[msd.MSDItem]:
	items: List[msd.MSDItem] = []
	if version_tag is not None:
		items.append(version_tag)
	items.extend(msd.attrs_obj_to_msd(
		simfile,
		name_converter = _SM_name_converter,
		# everything is str-convertible!
		filterer = lambda n, _, v: (n not in {'timing_data', 'charts'}) and (v is not None) # type: ignore
		# mypy-generic-fn
	))
	items.extend(_timing_data_to_msd(simfile.timing_data))
	return items


# Simfile (whole object)

# # still helper stuff

class SMParseError(Exception):
	pass


class _ParsingState(Enum):
	BEGIN = auto()
	CHARTS_SM = auto()
	CHARTS_SSC = auto()


# # actually useful functions

def text_to_simfile(text: Union[str, Iterable[str]]) -> Simfile: # noqa: C901
	'''Converts a simfile in sm or ssc format to a Python object'''
	curr_items: List[msd.MSDItem] = []
	state: _ParsingState = _ParsingState.BEGIN

	simfile: Simfile

	for item in msd.text_to_msd(text):
		if state is _ParsingState.BEGIN:
			if item.tag == 'NOTES':
				state = _ParsingState.CHARTS_SM
				simfile = _msd_to_simfile_skel(curr_items)
				curr_items.clear()
				# fall through and immediately process the chart tag
			elif item.tag == 'NOTEDATA':
				state = _ParsingState.CHARTS_SSC
				if item.value:
					raise SMParseError('unexpected content in NOTEDATA tag')
				simfile = _msd_to_simfile_skel(curr_items)
				curr_items.clear()
				continue
			else:
				curr_items.append(item)
				continue

		# should really be an elif, but NOTES is not a separator tag...
		if state is _ParsingState.CHARTS_SM:
			if item.tag != 'NOTES':
				raise SMParseError(f"expected NOTES tag, but got '{item.tag}' instead")
			fields = [r.strip() for r in item.value.split(':', 5)]
			if len(fields) != 6:
				raise SMParseError('chart is missing fields')
			steps_type, description, difficulty, meter, _, notes_text = fields
			simfile.charts.append(Chart(
				game_type = steps_type,
				description = description,
				difficulty = difficulty,
				meter = int(meter),
				notes = notedata.sm_to_notedata(notes_text)
			))
		else: # elif state is _ParsingState.CHARTS_SSC:
			if item.tag == 'NOTEDATA':
				if item.value:
					raise SMParseError('unexpected content in NOTEDATA tag')
				simfile.charts.append(_msd_to_chart(curr_items))
				curr_items.clear()
			else:
				curr_items.append(item)
				continue

	# get any leftovers
	if state is _ParsingState.BEGIN:
		# TODO add unit test for header-only simfile
		return _msd_to_simfile_skel(curr_items)

	if state is _ParsingState.CHARTS_SSC:
		simfile.charts.append(_msd_to_chart(curr_items))

	return simfile


SM_INDENT = '     ' # why is the convention this particular string?


def _chart_header(_: Chart) -> str:
	return '\n// ' + ('-' * 30) + '\n'


def simfile_to_sm(sf: Simfile) -> str:
	if sf.is_split_timing():
		raise ValueError('split timing charts cannot be converted to sm')

	text: List[str] = []
	text.append(msd.msd_to_text(_simfile_skel_to_msd(sf)))

	for c in sf.charts:
		notes = (
			'\n'
			f'{SM_INDENT}{c.game_type}{msd.MSDItem.END_TAG}\n'
			f'{SM_INDENT}{c.description}{msd.MSDItem.END_TAG}\n'
			f'{SM_INDENT}{c.difficulty}{msd.MSDItem.END_TAG}\n'
			f'{SM_INDENT}{c.meter}{msd.MSDItem.END_TAG}\n'
			f'{SM_INDENT}0,0,0,0,0{msd.MSDItem.END_TAG}\n' # hardcoded radar values
		) + notedata.notedata_to_sm(c.notes)
		text.extend([str(msd.MSDItem('NOTES', notes)), ''])

	return ''.join(text)


def simfile_to_ssc(sf: Simfile) -> str:
	text: List[str] = []
	text.append(msd.msd_to_text(_simfile_skel_to_msd(sf)))

	for c in sf.charts:
		text.append(_chart_header(c))
		text.append(msd.msd_to_text(_chart_to_msd(c)))

	return ''.join(text)
