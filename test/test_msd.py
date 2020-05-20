import unittest

from ssc_pkg import msd
from ssc_pkg.msd import MSDItem


class TestMSD(unittest.TestCase):

	def setUp(self):
		self.some_text = '\n'.join([
			'#SIMPLETAG:SIMPLEVALUE;',
			'#LONGTAGTHANKSplzzzzzzzzzzzzzzzzzzzz:SHORTVALUE;',
			'#ATAG:VALUE',
			'ON',
			'FOUR',
			'LINES;',
			'', # force \n at end
		])

		lower_alpha = ''.join(chr(c + ord('a')) for c in range(26))
		unicode_range = ''.join(chr(c) for c in range(400, 10000, 44))

		self.msd_items = [
			MSDItem('tag', 'value'),
			MSDItem(lower_alpha, unicode_range),
			MSDItem('anothertag', 'VALUE\nWITH\nembedded\n\n\n\n\n\n\nnnewlines')
		]

	def test_msd_item_str(self):
		for i in self.msd_items:
			self.assertEqual(str(i), f'#{i.tag}:{i.value};')

	def test_text_to_msd(self):
		msd_items = list(msd.text_to_msd(self.some_text))
		self.assertEqual(len(msd_items), 3)
		self.assertEqual(msd_items[0].tag, 'SIMPLETAG')
		self.assertEqual(msd_items[0].value, 'SIMPLEVALUE')
		self.assertEqual(msd_items[1].tag, 'LONGTAGTHANKSplzzzzzzzzzzzzzzzzzzzz')
		self.assertEqual(msd_items[1].value, 'SHORTVALUE')
		self.assertEqual(msd_items[2].value, '\n'.join(['VALUE', 'ON', 'FOUR', 'LINES']))

	def test_text_to_msd_cycle(self):
		msd_items_a = list(msd.text_to_msd(self.some_text))
		text_a = msd.msd_to_text(msd_items_a)
		self.assertEqual(self.some_text, text_a)
		msd_items_b = list(msd.text_to_msd(text_a))
		self.assertEqual(msd_items_a, msd_items_b)
		text_b = msd.msd_to_text(msd_items_b)
		self.assertEqual(text_a, text_b)
