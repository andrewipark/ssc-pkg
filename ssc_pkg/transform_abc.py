import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .simfile import Simfile


class _logger:
	'''mixin specially cased for logging'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs) # type: ignore # mypy-mixin
		self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')


class SimfileTransform(ABC, _logger):
	'''ABC for transforms that operate directly on simfile objects'''

	@abstractmethod
	def transform(self, target: Simfile) -> Optional[Simfile]:
		'''Transform the simfile, returning the resulting objects

		Simfile is mutable, so object identity may still be the same
		even though the values are different.
		A None return value indicates specifically that the input value wasn't changed.

		TODO zen this is probably a weird way to indicate ownership,
		and the None thing is entirely based on trust. I'm open to suggestions.
		'''


class FileTransform(ABC, _logger):
	'''ABC for transforms that use the filesystem'''

	@abstractmethod
	def transform(self, target: Path) -> None:
		'''Transform the simfile using the provided paths'''
