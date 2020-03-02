from decimal import Decimal
from pathlib import Path
from typing import Mapping, Optional, Tuple

import attr

from . import notedata


_TimingPosition = Decimal


@attr.s(auto_attribs=True)
class Chart:
	'''Mutable POD representing a complete chart'''
	meter: Optional[int] = None
	difficulty: Optional[str] = None # sane default since it is the only one allowed multiple times

	# TODO how do .sm files handle the one lone field they are allowed to have
	credit: Optional[str] = None
	description: Optional[str] = None
	chart_name: Optional[str] = None

	chart_style: Optional[str] = None

	# radar values intentionally ignored because they are derived from note data, not a property of it

	notes: notedata.NoteData = attr.Factory(notedata.NoteData)


@attr.s(auto_attribs=True)
class TimingData:
	'''Mutable POD for representing the timing data of a simfile'''
	@attr.s(auto_attribs=True)
	class ComboMultiplier:
		hit: int
		miss: int

	offset: _TimingPosition = Decimal(0)
	preview_start: _TimingPosition = Decimal(0)
	preview_length: _TimingPosition = Decimal(0)
	bpm: Mapping[_TimingPosition, Decimal] = attr.Factory(lambda: {Decimal(0): Decimal(120)})  # common default value
	stops: Mapping[_TimingPosition, Decimal] = attr.Factory(dict)

	# begin SSC only data
	delays: Mapping[_TimingPosition, Decimal] = attr.Factory(dict)
	warps: Mapping[_TimingPosition, Decimal] = attr.Factory(dict)
	time_signatures: Mapping[_TimingPosition, Tuple[int, int]] = attr.Factory(dict)
	tick_counts: Mapping[_TimingPosition, int] = attr.Factory(dict)
	combo_multipliers: Mapping[_TimingPosition, ComboMultiplier] = attr.Factory(dict)
	speeds: Mapping[_TimingPosition, Tuple[Decimal, Decimal, str]] = attr.Factory(dict)
	scrolls: Mapping[_TimingPosition, Decimal] = attr.Factory(dict)
	fakes: str = '' # TODO

	labels: Mapping[_TimingPosition, str] = attr.Factory(dict)
	background_changes: Mapping[_TimingPosition, Path] = attr.Factory(dict)
	keysounds: str = '' # TODO
	attacks: str = '' # TODO


@attr.s(auto_attribs=True)
class Simfile:
	# variables from MSD data
	title: str
	subtitle: Optional[str] = None
	artist: Optional[str] = None
	title_transliterated: Optional[str] = None
	subtitle_transliterated: Optional[str] = None
	artist_transliterated: Optional[str] = None
	genre: Optional[str] = None
	origin: Optional[str] = None
	credit: Optional[str] = None

	music: Optional[Path] = None
	banner: Optional[Path] = None
	background: Optional[Path] = None
	cd_title: Optional[Path] = None

	# begin SSC only data
	preview_video: Optional[Path] = None
	jacket: Optional[Path] = None
	cd_image: Optional[Path] = None
	disc_image: Optional[Path] = None
	lyrics: Optional[Path] = None

	selectable: str = 'YES' # occasionally not a bool in 3.95. Just let it be.

	additional_parameters: Mapping[str, str] = {}
