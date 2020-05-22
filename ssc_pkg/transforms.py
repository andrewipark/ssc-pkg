import re
import subprocess
from pathlib import Path

from . import simfile, transform_abc


class OggConvert(transform_abc.FileTransform):
	'''Convert the audio to Ogg Vorbis, the optimal format for Stepmania'''

	def transform(self, target: Path):
		# load
		with open(target, encoding='utf-8') as f:
			sf = simfile.text_to_simfile(f)

		# tons of preconditions
		if not sf.music:
			self.logger.warning(f"simfile '{target}' did not specify an audio file")
			return

		old_music = target.parent / Path(sf.music)
		if not old_music or not old_music.exists():
			# TODO what if transform on a different simfile in the folder already clobbered the audio?
			self.logger.error(
				f"simfile '{target.name}' in '{target.parent}' referenced "
				f"nonexistent music '{sf.music}'"
			)
			return
		if old_music.suffix.lower() == '.ogg':
			# assume it's not lying
			# TODO check: "Vorbis audio" in file (old_music)
			self.logger.info('audio is already Ogg Vorbis, doing nothing')
			return

		try:
			# modify
			subprocess.run(["oggenc", "--quality=8", str(old_music)], capture_output=True, check=True)
		except subprocess.CalledProcessError as exc:
			self.logger.error(f'oggenc failed with return code {exc.returncode} and stderr as follows:\n{exc.stderr}')
		except FileNotFoundError:
			self.logger.error('oggenc unavailable')

		# swap
		sf.music = sf.music.parent / (sf.music.stem + '.ogg')
		target_new = target.parent / (target.name + '.transformed')
		with open(target_new, 'x', encoding='utf-8') as f:
			f.write(simfile.simfile_to_ssc(sf))
		target_new.replace(target)
		old_music.unlink()


####################
# Check transforms
#
# These transforms verify properties of the given simfile or file,
# and must not modify either.
# They are not really transforms so much as checkers.


class Nothing(transform_abc.SimfileTransform):
	def transform(self, target: simfile.Simfile) -> None:
		self.logger.debug(f"nothing happened to '{target.title}'")


class NameRegex(transform_abc.FileTransform):
	'''Check that filenames exactly match given regex.'''

	def transform(self, target: Path):
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


class NeatOffset(transform_abc.SimfileTransform):
	'''Check that the offset value is an exact multiple of one second

	This makes it easy to tell at a glance whether the ITG offset was applied or not,
	and if that is done automatically, this transform should be earlier.
	'''
	def transform(self, target: simfile.Simfile) -> None:
		if target.timing_data.offset % 1 != 0:
			self.logger.warning(
				f"simfile '{target.title}' offset {target.timing_data.offset} is messy"
			)
		for c in target.charts:
			if not c.timing_data:
				continue
			if c.timing_data.offset % 1 != 0:
				self.logger.warning(
					f"simfile '{target.title}' "
					f"chart {c.game_type} {c.difficulty} {c.meter} '{c.description or c.credit} "
					f'offset {target.timing_data.offset} is messy'
				)
