import unittest
from pathlib import Path

from ssc_pkg import simfile


class TestSimfile(unittest.TestCase):

	def _get_file(self, o) -> Path:
		return (Path(__file__).parent) / Path(o)

	def test_easy(self):
		with open(self._get_file('easy.ssc')) as f:
			loaded = simfile.text_to_simfile(f)
		self.assertTrue(loaded) # TODO

	def test_kitchen_sink(self):
		with open(self._get_file('kitchen_sink.ssc')) as f:
			loaded = simfile.text_to_simfile(f)
		self.assertTrue(loaded) # TODO

	def test_sm_ssc_loading(self):
		'''loading equivalent sm and ssc files generate equivalent objects'''
		with open(self._get_file('easy.sm')) as sm, open(self._get_file('easy.ssc')) as ssc:
			self.assertEqual(simfile.text_to_simfile(sm), simfile.text_to_simfile(ssc))

	def test_sm_ssc_conversions(self):
		'''saving an sm-compatible file in sm and ssc format saves equivalent data'''
		with open(self._get_file('easy.ssc')) as f:
			original = simfile.text_to_simfile(f)
		ssc_text = simfile.simfile_to_ssc(original)
		sm_text = simfile.simfile_to_sm(original)
		self.assertEqual(original, simfile.text_to_simfile(ssc_text))
		self.assertEqual(original, simfile.text_to_simfile(sm_text))

	def test_ssc_roundtrip(self):
		'''repeated conversions are lossless'''
		with open(self._get_file('kitchen_sink.ssc')) as f:
			original_loaded = simfile.text_to_simfile(f)
		original_saved = simfile.simfile_to_ssc(original_loaded)
		again_loaded = simfile.text_to_simfile(original_saved)
		again_saved = simfile.simfile_to_ssc(again_loaded)
		self.assertEqual(original_loaded, again_loaded)
		self.assertEqual(original_saved, again_saved)
