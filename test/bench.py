#!/usr/bin/env python3

from timeit import Timer
from typing import List, Tuple
import sys

if __name__ == '__main__':
	TEST_SIZE = int(sys.argv[1])
	REPEATS = max(10000 // TEST_SIZE, 1)
	setup = '''
from ssc_pkg import notedata
ssc = '0001\\n0001\\n0001\\n0002\\n,\\n' * 25000 + '0001\\n0001\\n0001\\n0002'
import attr
attr.set_run_validators(False)
	'''

	# print('sm to notedata: {:.4e}'.format(min(Timer('notedata.sm_to_notedata(ssc)', setup).repeat(10, 1))))

	setup = f'''
from ssc_pkg import notedata
from fractions import Fraction
a = [notedata._NoteRow(Fraction(i, 4), '0000') for i in range({TEST_SIZE})]
import attr
attr.set_run_validators(False)
	'''
	print(
		'direct notedata (ordered): {:.3e}'.format(
			min(Timer('v = notedata.NoteData(a)', setup).repeat(10, REPEATS))
		)
	)

	setup += '\nv = notedata.NoteData(a)'

	d: List[Tuple[str, str, str]] = [
		# ('shift', 'v.shift(20)'),
		('clear_range', '', 'v.clear_range(420, 7000)'),
		('slice-mid-60', '', f'v[{TEST_SIZE // 20} : {TEST_SIZE // 5}]'),
		('overlay-all', '', 'v.overlay(v, v.OverlayMode.KEEP_OTHER)'),
		(
			'overlay-mid-50',
			f'v2 = notedata.NoteData(v._notes[{TEST_SIZE // 4} : {(TEST_SIZE * 3) // 4}])',
			'v.overlay(v2, v.OverlayMode.KEEP_OTHER)'
		),
		(
			'overlay-first-10',
			f'v2 = notedata.NoteData(v._notes[: {TEST_SIZE // 10}])',
			'v.overlay(v2, v.OverlayMode.KEEP_OTHER)'
		),
		(
			'overlay-last-10',
			f'v2 = notedata.NoteData(v._notes[-{TEST_SIZE // 10}:])',
			'v.overlay(v2, v.OverlayMode.KEEP_OTHER)'
		),
	]

	for i in d:
		result = Timer(i[2], setup + '\n' + i[1] + '\n').repeat(10, REPEATS)
		print(
			f'{i[0]}:  '
			f'lowest: {min(result) / REPEATS:.3e}, median: {sorted(result)[len(result) // 2] / REPEATS:.3e}'
		)
