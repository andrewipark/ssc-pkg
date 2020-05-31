from decimal import Decimal
from pathlib import PurePosixPath
from typing import List, Mapping, Optional, Tuple

import attr

from ssc_pkg import notedata


_TimingPosition = Decimal # somewhat tied to SM


# class definitions

@attr.s(auto_attribs=True)
class TimingData:
	'''Timing data (e.g. BPM, stops) of (possibly part of) a simfile'''
	@attr.s(auto_attribs=True)
	class ComboMultiplier:
		'''combo multiplier timing segment'''
		hit: int
		miss: int

	# sm, minimum information
	bpm: Mapping[_TimingPosition, Decimal] = attr.Factory(lambda: {Decimal(0): Decimal(120)})  # common default value
	offset: _TimingPosition = Decimal(0)
	stops: Mapping[_TimingPosition, Decimal] = attr.Factory(dict)

	# ssc
	delays: Optional[Mapping[_TimingPosition, Decimal]] = None
	warps: Optional[Mapping[_TimingPosition, Decimal]] = None
	time_signatures: Optional[Mapping[_TimingPosition, Tuple[int, int]]] = None
	tick_counts: Optional[Mapping[_TimingPosition, int]] = None
	combo_multipliers: Optional[Mapping[_TimingPosition, ComboMultiplier]] = None
	speeds: Optional[Mapping[_TimingPosition, Tuple[Decimal, Decimal, str]]] = None
	scrolls: Optional[Mapping[_TimingPosition, Decimal]] = None
	fakes: Optional[str] = None # TODO unsupported

	labels: Mapping[_TimingPosition, str] = attr.Factory(dict)

	# sm
	preview_start: _TimingPosition = Decimal(0)
	preview_length: _TimingPosition = Decimal(0)
	display_bpm: Optional[str] = None # TODO probably want a separate class

	# rarely used, sm
	background_changes: Mapping[_TimingPosition, str] = attr.Factory(dict) # TODO unsupported, = separated
	foreground_changes: Mapping[_TimingPosition, str] = attr.Factory(dict) # TODO unsupported, = separated

	keysounds: Optional[str] = None # TODO unsupported, poorly documented
	attacks: Optional[str] = None # TODO unsupported


@attr.s(auto_attribs=True)
class Chart:
	'''Chart with notes and metadata'''

	game_type: str = 'unknown' # semantic chart type

	# difficulty data
	meter: Optional[int] = None # sm: 1
	difficulty: Optional[str] = 'Edit' # 'Edit' is the only one allowed multiple times

	# descriptor fields
	# TODO how do .sm files handle the one lone field they are allowed to have?
	credit: Optional[str] = None
	description: Optional[str] = None
	chart_name: Optional[str] = None

	chart_style: Optional[str] = None

	# radar values intentionally ignored because they are derived from note data, not a property of it

	timing_data: Optional[TimingData] = None

	notes: notedata.NoteData = attr.Factory(notedata.NoteData)


@attr.s(auto_attribs=True)
class Simfile:
	'''Song and artist display metadata, and associated charts'''

	# common information
	title: str = ''
	subtitle: Optional[str] = None
	artist: Optional[str] = None
	title_transliterated: Optional[str] = None
	subtitle_transliterated: Optional[str] = None
	artist_transliterated: Optional[str] = None
	genre: Optional[str] = None
	credit: Optional[str] = None
	music: Optional[PurePosixPath] = None

	# sm resources
	banner: Optional[PurePosixPath] = None
	background: Optional[PurePosixPath] = None
	lyrics: Optional[PurePosixPath] = None
	cd_title: Optional[PurePosixPath] = None

	# ssc resources
	preview_video: Optional[PurePosixPath] = None
	jacket: Optional[PurePosixPath] = None
	cd_image: Optional[PurePosixPath] = None
	disc_image: Optional[PurePosixPath] = None

	# ssc, not a resource and no one uses it
	origin: Optional[str] = None

	# sm, not really relevant (on default SM5 installs)
	selectable: str = 'YES'

	timing_data: TimingData = attr.Factory(TimingData)

	charts: List[Chart] = attr.Factory(list)

	def is_split_timing(self) -> bool:
		''''split timing' := any charts have their own timing data,
		instead of inheriting the data from the top-level simfile
		'''
		return any(c.timing_data for c in self.charts)
