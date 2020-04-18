import unittest
from ssc_pkg import notedata
from fractions import Fraction


class TestNoteDataSimple(unittest.TestCase):

	def setUp(self):
		self.the = notedata.sm_to_notedata(
			# empty measure 0, staircase measure 1
			'0000\n0000\n0000\n0000\n,\n1000\n0100\n0010\n0001\n,\n'
			'0001\n0010\n0010\n1000\n0100\n0000\n0001\n0029\n'
		)

		self.long_jack_interval = Fraction(3, 4)
		self.long_jack_length = 100
		self.long_jack = notedata.NoteData([
			notedata._NoteRow(self.long_jack_interval * i, '0101')
			for i in range(self.long_jack_length)
		])

	def test_len(self):
		self.assertEqual(len(self.the), 11)
		self.assertEqual(len(self.long_jack), self.long_jack_length)

	def test_contains(self):
		self.assertFalse(0 in self.the)
		self.assertFalse(2 in self.the)
		self.assertTrue(4 in self.the)
		self.assertTrue(Fraction(17, 2) in self.the)
		self.assertFalse(Fraction(35, 4) in self.the)
		self.assertTrue(self.long_jack_interval * 35 in self.long_jack)
		self.assertFalse(self.long_jack_interval * Fraction(37, 12) in self.long_jack)

	def test_getitem(self):
		self.assertEqual(self.the[4], '1000')
		self.assertEqual(self.the[Fraction(23, 2)], '0029')

	def test_getitem_invalid(self):
		# valid on others, but not this one
		self.assertRaises(IndexError, lambda: self.the[0])
		self.assertRaises(IndexError, lambda: self.the[1])
		self.assertRaises(IndexError, lambda: self.the[2])
		self.assertRaises(IndexError, lambda: self.the[Fraction(21, 2)])
		self.assertRaises(IndexError, lambda: self.the[69])
		self.assertRaises(IndexError, lambda: self.the[Fraction(-2, 3)])

		# never valid
		self.assertRaises(IndexError, lambda: self.the[None])

	def test_getitem_slicing(self):
		# easy empty cases
		self.assertEqual(len(self.the[0:0]), 0)
		self.assertEqual(len(self.the[0:4]), 0)
		self.assertEqual(len(self.the[4:4]), 0)
		self.assertEqual(len(self.the[20:]), 0)
		self.assertEqual(len(self.the[:-1]), 0)

		# non empty cases
		self.assertEqual(self.the, self.the[:])
		self.assertEqual(self.the[6:], self.the[6:12])
		self.assertEqual(self.the[:8], self.the[2:8])

		# standard
		start, stop = 5, Fraction(19, 2)
		new_notedata = self.the[start:stop]
		self.assertEqual(len(new_notedata), 6)
		self.assertEqual(self.the[8], '0001')
		self.assertTrue(start in new_notedata)
		self.assertFalse(stop in new_notedata)

	def test_shift(self):
		# reversible
		self.assertEqual(self.the.shift(4).shift(-4), self.the)
		self.assertEqual(self.the.shift(Fraction(13, 4)).shift(Fraction(-13, 4)), self.the)

		self.assertEqual(self.the.shift(20)[24], '1000')
		self.assertEqual(self.the.shift(Fraction(-3, 2))[Fraction(17, 2)], '0100')

	def test_clear_range(self):
		new_notedata = self.the.clear_range(5, 9)

		self.assertFalse(2 in new_notedata)
		self.assertTrue(4 in new_notedata)

		self.assertFalse(5 in new_notedata)
		self.assertFalse(6 in new_notedata)
		self.assertFalse(Fraction(15, 2) in new_notedata)

		self.assertTrue(9 in new_notedata)
		self.assertTrue(10 in new_notedata)

	def test_clear_range_empty(self):
		# FIXME
		pass

	def test_overlay(self):
		pass

	def test_mirror(self):
		pass

	def test_density(self):
		self.assertEqual(
			self.the.density(), [
				notedata.DensityInfo(1, 4),
				notedata.DensityInfo(Fraction(1, 2), 4),
				notedata.DensityInfo(1, 1),
				notedata.DensityInfo(Fraction(1, 2), 1),
			]
		)
		self.assertEqual(
			self.long_jack.density(),
			[notedata.DensityInfo(self.long_jack_interval, self.long_jack_length - 1)]
		)
