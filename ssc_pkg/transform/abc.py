'''Abstract base classes and mixins for transform objects'''

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar, Iterable, Optional

from ssc_pkg.simfile import Simfile


class _Logger:
	'''mixin to set up logging in __init__'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.logger = logging.getLogger(f'transform.{type(self).__name__}')


class Cleanable:
	'''mixin for transforms that need clean up'''
	def clean(self) -> None:
		'''clean any detritus this object created

		For transforms, each successful transform call MAY be followed by a single cleanup call
		'''


class SimfileTransform(ABC, _Logger):
	'''ABC for transforms that operate directly on simfile objects'''

	@abstractmethod
	def transform(self, sim: Simfile) -> Optional[Simfile]:
		'''Transform the simfile, and return the result

		The transform MUST NOT have changed the input on returning None

		If the transform meaningfully changes the simfile,
		and the identity of the returned object is different (i.e. result is not original),
		then the input simfile MUST NOT be modified.

		NOTE In-place and out-of-place transforms are currently indistinguishable,
		but it is generally assumed that transforms are in-place

		TODO zen this is probably a weird way to indicate ownership,
		and the None thing is entirely based on trust. I'm open to suggestions.
		'''


class FileTransform(ABC, _Logger):
	'''ABC for transforms that use the filesystem'''

	@abstractmethod
	def transform(self, sim: Simfile, target: Path) -> Optional[Simfile]:
		'''Transform the simfile using the provided paths

		The passed in simfile object MUST be equivalent to the result of
		loading the simfile from the provided target path.

		WARNING A None return can also mean that the simfile changed on disk,
		but the simfile object did not.
		Implementations MUST note if this behavior is possible.
		'''


class MetaTransform(ABC, _Logger):
	'''ABC for transforms that use both the filesystem and arbitrary config data
	as well as arbitrary configuration data TODO ??
	'''

	DEFAULT_METADATA: ClassVar[str] = '__metadata.yaml'

	def data_path(self) -> tuple[Path, Iterable[str]]:
		'''Return the location of the data expected

		The Path value must refer to a file,
		and is interpreted relatively to the simfile directory

		The iterable is a """path""" within the file.
		'''
		return Path(self.DEFAULT_METADATA), []

	@abstractmethod
	def transform(self, sim: Simfile, target: Path, obj) -> None:
		'''Transform the simfile using the provided paths and data.

		The data object should be loaded from the data path provided.

		Otherwise, behaves like FileTransform.
		'''
