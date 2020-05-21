import unittest
from fractions import Fraction

from ssc_pkg import notedata


class TestNoteDataSimple(unittest.TestCase):

	def setUp(self):
		self.simple_notes = (
			# measure 0: empty

			# measure 1: 4th L>R facing-R staircase
			[
				notedata._NoteRow(Fraction(4 + p), n)
				for p, n in enumerate(['1000', '0100', '0010', '0001'])
			]
			# measure 2: one note at the beginning
			+ [notedata._NoteRow(Fraction(8), '0110')]
			# measure 3: empty

			# measure 4: some random 8ths
			+ [
				notedata._NoteRow(Fraction(p, 2) + 16, n)
				for p, n in enumerate(['0001', '0010', '0010', '1000', '0100', '0000', '0001', '0029'])
				if n != '0000'
			]
			# measure 5: 7ths (not in vanilla SM)
			+ [notedata._NoteRow(Fraction(1, 7) + 20, '1111')]
		)
		self.simple_text = (
			'0000\n0000\n0000\n0000\n,\n'
			'1000\n0100\n0010\n0001\n,\n'
			'0110\n0000\n0000\n0000\n,\n'
			'0000\n0000\n0000\n0000\n,\n'
			'0001\n0010\n0010\n1000\n0100\n0000\n0001\n0029\n,\n'
			# all of measure 5...
			'0000\n1111\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n'
			'0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n0000\n'
		)
		self.simple = notedata.NoteData(self.simple_notes)
		self.simple_beyond = 25

		self.long_jack_interval = Fraction(3, 4)
		self.long_jack_length = 100
		self.long_jack = notedata.NoteData(
			notedata._NoteRow(self.long_jack_interval * i, '0101')
			for i in range(self.long_jack_length)
		)

	def test_validation(self):
		self.assertRaises(ValueError, lambda: notedata.sm_to_notedata(
			'00a0\n003300'
		))
		self.assertRaises(IndexError, lambda: notedata.NoteData(
			notedata._NoteRow(Fraction(0), '0030') for v in range(2)
		))

	def test_len(self):
		self.assertEqual(len(self.simple), len(self.simple_notes))
		self.assertEqual(len(self.long_jack), self.long_jack_length)

	def test_contains(self):
		self.assertFalse(0 in self.simple)
		self.assertFalse(2 in self.simple)
		self.assertTrue(4 in self.simple)
		self.assertTrue(19 in self.simple)
		self.assertTrue(Fraction(33, 2) in self.simple)
		self.assertTrue(Fraction(141, 7) in self.simple)
		self.assertFalse(Fraction(35, 4) in self.simple)
		self.assertTrue(self.long_jack_interval * (self.long_jack_length * 17 // 37) in self.long_jack)
		self.assertFalse(self.long_jack_interval * Fraction(37, 12) in self.long_jack)

	def test_getitem(self):
		self.assertEqual(self.simple[4], '1000')
		self.assertEqual(self.simple[Fraction(39, 2)], '0029')

	def test_getitem_invalid(self):
		self.assertRaises(IndexError, lambda: self.simple[0])
		self.assertRaises(IndexError, lambda: self.simple[1])
		self.assertRaises(IndexError, lambda: self.simple[2])
		self.assertRaises(IndexError, lambda: self.simple[Fraction(21, 2)])
		self.assertRaises(IndexError, lambda: self.simple[69])
		self.assertRaises(IndexError, lambda: self.simple[Fraction(-2, 3)])

	def test_getitem_slicing(self):
		# empty ==
		self.assertEqual(len(self.simple[0:0]), 0)
		self.assertEqual(len(self.simple[0:4]), 0)
		self.assertEqual(len(self.simple[4:4]), 0)

		# empty unbounded
		self.assertEqual(len(self.simple[self.simple_beyond:]), 0)
		self.assertEqual(len(self.simple[:-1]), 0)

		# occupied
		start, stop = 6, Fraction(35, 2)
		new_notedata = self.simple[start:stop] # type: ignore # mypy-slice
		self.assertEqual(len(new_notedata), 6)
		self.assertEqual(self.simple[8], '0110')
		self.assertTrue(start in new_notedata)
		self.assertFalse(stop in new_notedata)

		# occupied unbounded
		self.assertEqual(self.simple, self.simple[:])
		self.assertEqual(self.simple[18:], self.simple[18:self.simple_beyond])
		self.assertEqual(self.simple[:8], self.simple[2:8])

	def test_density(self):
		self.assertEqual(
			self.simple.density(), [
				notedata.DensityInfo(Fraction(1), 4),
				notedata.DensityInfo(Fraction(8), 1),
				notedata.DensityInfo(Fraction(1, 2), 4),
				notedata.DensityInfo(Fraction(1), 1),
				notedata.DensityInfo(Fraction(1, 2), 1),
				notedata.DensityInfo(Fraction(9, 14), 1),
			]
		)
		self.assertEqual(
			self.long_jack.density(),
			[notedata.DensityInfo(self.long_jack_interval, self.long_jack_length - 1)]
		)

	def test_shift(self):
		# data is shifted
		self.assertEqual(self.simple.shift(20)[24], self.simple[4])
		self.assertEqual(self.simple.shift(Fraction(-3, 2))[Fraction(31, 2)], self.simple[17])

		# reversible
		self.assertEqual(self.simple.shift(4).shift(-4), self.simple)
		self.assertEqual(self.simple.shift(Fraction(13, 4)).shift(Fraction(-13, 4)), self.simple)

	def test_clear_range(self):
		a, b = 6, 17

		# individual contain tests
		new_notedata = self.simple.clear_range(a, b)

		self.assertFalse(2 in new_notedata)
		self.assertTrue(4 in new_notedata)

		self.assertFalse(6 in new_notedata)
		self.assertFalse(7 in new_notedata)
		self.assertFalse(Fraction(33, 2) in new_notedata)

		self.assertTrue(17 in new_notedata)
		self.assertTrue(18 in new_notedata)

		# slice test
		self.assertEqual(len(new_notedata[a:b]), 0)

		# idempotence
		curr = new_notedata
		for _ in range(3):
			curr = curr.clear_range(a, b)
			self.assertEqual(curr, new_notedata)

	def test_overlay(self):
		new_notedata = self.simple.overlay(self.long_jack.shift(self.simple_beyond))
		self.assertEqual(new_notedata[self.simple_beyond:].shift(-self.simple_beyond), self.long_jack)

		doubled_jack = self.long_jack.overlay(self.long_jack.shift(self.long_jack_interval / 2))
		self.assertEqual(len(doubled_jack), len(self.long_jack) * 2)

		# overlay is in opposition to slicing and clear range
		a = self.long_jack_interval * self.long_jack_length / 3
		b = a * 2
		self.assertEqual(self.long_jack.clear_range(a, b).overlay(self.long_jack[a:b]), self.long_jack)

	def test_overlay_modes(self):
		OverlayMode = notedata.NoteData.OverlayMode

		conflict_pos = self.long_jack_interval * self.long_jack_length * 3 / 2
		row_one = notedata._NoteRow(conflict_pos, 'aaaa')
		row_two = notedata._NoteRow(conflict_pos, 'bbbb')

		jack_one = self.long_jack.overlay(notedata.NoteData([row_one]))
		jack_two = (
			self.long_jack.shift(self.long_jack_interval / 2)
			.overlay(notedata.NoteData([row_two]))
		)

		self.assertRaises(IndexError, lambda: jack_one.overlay(jack_two, OverlayMode.RAISE))
		jack_keep_self = jack_one.overlay(jack_two, OverlayMode.KEEP_SELF)
		jack_keep_other = jack_one.overlay(jack_two, OverlayMode.KEEP_OTHER)

		self.assertEqual(len(jack_keep_self), len(jack_keep_other))
		self.assertEqual(jack_keep_self[:conflict_pos], jack_keep_other[:conflict_pos])
		self.assertEqual(jack_keep_self[conflict_pos], row_one.notes)
		self.assertEqual(jack_keep_other[conflict_pos], row_two.notes)

	def test_sm_to_notedata(self):
		self.assertEqual(notedata.sm_to_notedata(self.simple_text), self.simple)

	def test_notedata_to_sm(self):
		self.assertEqual(notedata.notedata_to_sm(self.simple).strip(), self.simple_text.strip())
