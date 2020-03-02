import unittest
from ssc_pkg import simfile
from fractions import Fraction

class TestNoteData(unittest.TestCase):

	def setUp(self):
		self.the = simfile.sm_to_notedata(
			# empty measure 0, staircase measure 1
			'0000\n0000\n0000\n0000\n,\n1000\n0100\n0010\n0001\n,\n'
			'0001\n0010\n0010\n1000\n0100\n0000\n0001\n0029\n'
		)

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

		# never valid
		self.assertRaises(IndexError, lambda: self.the[Fraction(-2, 3)])
		self.assertRaises(IndexError, lambda: self.the[None])

	def test_shift(self):
		self.assertEqual(self.the.shift(4).shift(-4), self.the)
		self.assertEqual(self.the.shift(Fraction(13, 4)).shift(Fraction(-13, 4)), self.the)
		self.assertEqual(self.the.shift(20)[24], '1000')
