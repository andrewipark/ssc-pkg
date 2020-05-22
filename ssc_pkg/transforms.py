import re
import subprocess
from pathlib import Path
from typing import Optional

from . import simfile
from .transform import abc


class OggConvert(abc.FileTransform, abc.Cleanable):
	'''Convert the audio to Ogg Vorbis, the optimal format for Stepmania'''

	old_music: Optional[Path]

	def transform(self, sim: simfile.Simfile, target: Path) -> Optional[simfile.Simfile]:
		# tons of preconditions
		self.old_music = None

		if not sim.music:
			self.logger.warning(f"simfile '{target}' did not specify an audio file")
			return None

		old_music = target.parent / Path(sim.music)
		if not old_music.exists():
			# TODO what if transform on a different simfile in the folder already clobbered the audio?
			self.logger.error(
				f"simfile '{target.name}' in '{target.parent}' referenced "
				f"nonexistent music '{sim.music}'"
			)
			return None
		if old_music.suffix.lower() == '.ogg':
			# assume it's not lying
			# TODO check: "Vorbis audio" in `file (old_music)`
			self.logger.info('audio is already Ogg Vorbis, doing nothing')
			return None

		try:
			# modify
			subprocess.run(["oggenc", "--quality=8", str(old_music)], capture_output=True, check=True)
		except subprocess.CalledProcessError as exc:
			self.logger.error(f'oggenc failed with return code {exc.returncode} and stderr as follows:\n{exc.stderr}')
		except FileNotFoundError:
			self.logger.error('oggenc unavailable')

		sim.music = sim.music.parent / (sim.music.stem + '.ogg')
		self.old_music = old_music
		return sim

	def clean(self) -> None:
		'''remove now-obsolete audio file'''
		if not self.old_music:
			return

		try:
			self.old_music.unlink()
		except FileNotFoundError:
			pass

		del self.old_music


####################
# Check transforms
#
# These transforms verify properties of the given simfile or file,
# and must not modify either.
# They are not really transforms so much as checkers.


class Nothing(abc.SimfileTransform):
	def transform(self, sim: simfile.Simfile) -> None:
		self.logger.debug(f"nothing happened to '{sim.title}'")


class NameRegex(abc.FileTransform):
	'''Check that filenames exactly match given regex.'''

	def transform(self, _, target: Path):
		# TODO customizable?
		regex: re.Pattern = re.compile(r'[a-z0-9\-_.]*')

		for child in target.parent.iterdir():
			name = child.name
			m = regex.match(name)
			if (not m) or m.end() == 0:
				self.logger.warning(
					f"regex '{regex.pattern}' does not match '{name}' "
					f"(located at '{child}')"
				)
			elif m.end() < len(name):
				self.logger.warning(
					f"regex '{regex.pattern}' stopped matching at '{name[m.end():]}' "
					f"(located at '{child}')"
				)


class NeatOffset(abc.SimfileTransform):
	'''Check that the offset value is an exact multiple of one second

	This makes it easy to tell at a glance whether the ITG offset was applied or not,
	and if that is done automatically, this transform should be earlier.
	'''
	def transform(self, sim: simfile.Simfile) -> None:
		if sim.timing_data.offset % 1 != 0:
			self.logger.warning(
				f"simfile '{sim.title}' offset {sim.timing_data.offset} is messy"
			)
		for c in sim.charts:
			if not c.timing_data:
				continue
			if c.timing_data.offset % 1 != 0:
				self.logger.warning(
					f"simfile '{sim.title}' "
					f"chart {c.game_type} {c.difficulty} {c.meter} '{c.description or c.credit} "
					f'offset {sim.timing_data.offset} is messy'
				)
