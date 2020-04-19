import unittest
from ssc_pkg import notedata
from fractions import Fraction


class TestNoteDataSimple(unittest.TestCase):

	def setUp(self):
		self.simple = notedata.sm_to_notedata(
			# empty measure 0, staircase measure 1
			'0000\n0000\n0000\n0000\n,\n1000\n0100\n0010\n0001\n,\n'
			'0001\n0010\n0010\n1000\n0100\n0000\n0001\n0029\n'
		)
		self.simple_length = 11

		self.long_jack_interval = Fraction(3, 4)
		self.long_jack_length = 100
		self.long_jack = notedata.NoteData([
			notedata._NoteRow(self.long_jack_interval * i, '0101')
			for i in range(self.long_jack_length)
		])

	def test_validation(self):
		self.assertRaises(ValueError, lambda: notedata.sm_to_notedata(
			'00a0\n003300'
		))
		self.assertRaises(ValueError, lambda: notedata.NoteData(
			notedata._NoteRow(0, '0030') for v in range(2)
		))

	def test_len(self):
		self.assertEqual(len(self.simple), self.simple_length)
		self.assertEqual(len(self.long_jack), self.long_jack_length)

	def test_contains(self):
		self.assertFalse(0 in self.simple)
		self.assertFalse(2 in self.simple)
		self.assertTrue(4 in self.simple)
		self.assertTrue(Fraction(17, 2) in self.simple)
		self.assertFalse(Fraction(35, 4) in self.simple)
		self.assertTrue(self.long_jack_interval * 35 in self.long_jack)
		self.assertFalse(self.long_jack_interval * Fraction(37, 12) in self.long_jack)

	def test_getitem(self):
		self.assertEqual(self.simple[4], '1000')
		self.assertEqual(self.simple[Fraction(23, 2)], '0029')

	def test_getitem_invalid(self):
		# valid, but not in the container
		self.assertRaises(IndexError, lambda: self.simple[0])
		self.assertRaises(IndexError, lambda: self.simple[1])
		self.assertRaises(IndexError, lambda: self.simple[2])
		self.assertRaises(IndexError, lambda: self.simple[Fraction(21, 2)])
		self.assertRaises(IndexError, lambda: self.simple[69])
		self.assertRaises(IndexError, lambda: self.simple[Fraction(-2, 3)])

		# never valid
		self.assertRaises(TypeError, lambda: self.simple[None])
		self.assertRaises(TypeError, lambda: self.simple[[2, 4, 8, 15]])
		self.assertRaises(TypeError, lambda: self.simple[self.simple])
		self.assertRaises(TypeError, lambda: self.simple['elmo'])

	def test_getitem_slicing(self):
		# empty slices
		self.assertEqual(len(self.simple[0:0]), 0)
		self.assertEqual(len(self.simple[0:4]), 0)
		self.assertEqual(len(self.simple[4:4]), 0)
		self.assertEqual(len(self.simple[20:]), 0)
		self.assertEqual(len(self.simple[:-1]), 0)

		# occupied standard slice
		start, stop = 5, Fraction(19, 2)
		new_notedata = self.simple[start:stop]
		self.assertEqual(len(new_notedata), 6)
		self.assertEqual(self.simple[8], '0001')
		self.assertTrue(start in new_notedata)
		self.assertFalse(stop in new_notedata)

		# occupied unbounded slices
		self.assertEqual(self.simple, self.simple[:])
		self.assertEqual(self.simple[6:], self.simple[6:12])
		self.assertEqual(self.simple[:8], self.simple[2:8])

	def test_shift(self):
		# data is shifted
		self.assertEqual(self.simple.shift(20)[24], '1000')
		self.assertEqual(self.simple.shift(Fraction(-3, 2))[Fraction(17, 2)], '0100')

		# reversible
		self.assertEqual(self.simple.shift(4).shift(-4), self.simple)
		self.assertEqual(self.simple.shift(Fraction(13, 4)).shift(Fraction(-13, 4)), self.simple)

	def test_clear_range(self):
		# individual contain tests
		new_notedata = self.simple.clear_range(5, 9)

		self.assertFalse(2 in new_notedata)
		self.assertTrue(4 in new_notedata)

		self.assertFalse(5 in new_notedata)
		self.assertFalse(6 in new_notedata)
		self.assertFalse(Fraction(15, 2) in new_notedata)

		self.assertTrue(9 in new_notedata)
		self.assertTrue(10 in new_notedata)

		# slice test
		self.assertEqual(len(new_notedata[5:9]), 0)

		# idempotence
		curr = new_notedata
		for _ in range(3):
			curr = curr.clear_range(5, 9)
			self.assertEqual(curr, new_notedata)

	def test_overlay(self):
		pass

	def test_mirror(self):
		pass

	def test_density(self):
		self.assertEqual(
			self.simple.density(), [
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
