'''Make transform for easy copy-paste'''

from pathlib import Path
from typing import Iterable, Tuple

from ssc_pkg.simfile import Simfile
from ssc_pkg.transform.abc import MetaTransform

from . import util
from .manager import CommandError, Manager
from .parser import ParseError, Parser


class MakeTransform(MetaTransform):
	'''top-level manager to interact with ssc-pkg'''

	def data_path(self) -> Tuple[Path, Iterable[str]]:
		retval = super().data_path()
		return (retval[0], ['make'])

	def transform(self, sim: Simfile, target: Path, obj) -> None: # noqa: C901
		if obj is None:
			return None

		# NOTE could be extracted
		parser = Parser()
		manager = Manager()

		try:
			for command in parser.parse_commands(obj):
				manager.run(command, sim)
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

		# return sim
		return None
