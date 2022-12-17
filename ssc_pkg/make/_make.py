from pathlib import Path
from typing import Iterable

from ssc_pkg.simfile import Simfile
from ssc_pkg.transform.abc import MetaTransform

from . import util
from .manager import CommandError, Manager
from .parser import ParseError, Parser


class MakeTransform(MetaTransform):
	'''wraps the functionality of :class:`~.parser.Parser`
	and :class:`~.manager.Manager` into a transform'''

	def data_path(self) -> tuple[Path, Iterable[str]]:
		retval = super().data_path()
		return (retval[0], ['make'])

	def transform(self, sim: Simfile, target: Path, obj):
		if obj is None:
			self.logger.info('no make data specified')
			return None

		# NOTE could be extracted
		parser = Parser()
		manager = Manager()

		try:
			manager.run_many(parser.parse_commands(obj), sim)
		except ParseError as e:
			raise Exception(
				'failed to parse data:\n'
				+ util.exc_index_trace_tab(e)
			) from None
		except CommandError as e:
			raise Exception(
				'failed to run command:\n'
				+ util.exc_index_trace_tab(e)
			) from None

		return sim
