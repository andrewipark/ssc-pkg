import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .simfile import Simfile


class _logger:
	'''stub for transform logging'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs) # type: ignore # mypy-mixin
		self.logger = logging.getLogger(f'transform.{type(self).__name__}')


class SimfileTransform(ABC, _logger):
	'''ABC for transforms that (only) need the data within the simfile'''

	@abstractmethod
	def transform(self, target: Simfile) -> Simfile:
		'''Run the transform on the given simfile'''
		pass


class FileTransform(ABC, _logger):
	'''ABC for transforms that need filesystem data'''

	@abstractmethod
	def transform(self, target: Path, original: Optional[Path]) -> None:
		'''Run the transform on the given simfile paths'''
		pass
