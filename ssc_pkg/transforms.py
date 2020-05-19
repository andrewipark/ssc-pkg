import re
import subprocess
from pathlib import Path

from .simfile import Simfile
from .transform_abc import FileTransform, SimfileTransform


class Nothing(SimfileTransform):

	def transform(self, target: Simfile) -> Simfile:
		self.logger.debug('But nothing happened!')
		return target


class OggConvert(FileTransform):
	'''Convert the audio to Ogg Vorbis, the optimal format for Stepmania'''

	def transform(self, target: Path, _):
		# TODO hardcoded file path
		old_music = target.parent / 'music.wav'
		if not old_music.exists():
			self.logger.error(f"music file '{old_music}' doesn't exist!")
			return

		try:
			# TODO make parametrizable
			subprocess.run(["oggenc", "--quality=8", str(old_music)], capture_output=True, check=True)
			old_music.unlink()
		except subprocess.CalledProcessError as exc:
			self.logger.error(f'oggenc failed with return code {exc.returncode} and stderr as follows:\n{exc.stderr}')
		except FileNotFoundError:
			self.logger.error('oggenc unavailable')


class NameLinter(FileTransform):
	'''Check that filenames exactly match given regex.'''

	def transform(self, target: Path, _):
		# TODO customizable? move to constructor
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
