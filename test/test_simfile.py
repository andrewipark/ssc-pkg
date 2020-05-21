import unittest
from pathlib import Path

from ssc_pkg import simfile


class TestSimfile(unittest.TestCase):

	def _get_file(self, o) -> Path:
		return (Path(__file__).parent) / Path(o)

	def test_easy(self):
		with open(self._get_file('easy.ssc')) as f:
			text = f.read()
		loaded = simfile.text_to_simfile(text)
		self.assertTrue(loaded) # TODO

	def test_kitchen_sink(self):
		pass # TODO blocked because some simfile_msd conversions aren't working

	def test_sm_ssc_loading(self):
		'''loading equivalent sm and ssc files generate equivalent objects'''
		with open(self._get_file('easy.sm')) as sm, open(self._get_file('easy.ssc')) as ssc:
			self.assertEqual(simfile.text_to_simfile(sm), simfile.text_to_simfile(ssc))

	def test_sm_ssc_conversions(self):
		'''saving an sm-compatible file in sm and ssc format saves equivalent data'''
		with open(self._get_file('easy.ssc')) as f:
			text = f.read()
		original = simfile.text_to_simfile(text)
		ssc_text = simfile.simfile_to_ssc(original)
		sm_text = simfile.simfile_to_sm(original)
		self.assertEqual(original, simfile.text_to_simfile(ssc_text))
		self.assertEqual(original, simfile.text_to_simfile(sm_text))
