from timeit import Timer
from typing import List, Tuple

if __name__ == '__main__':
	setup = '''
	from ssc_pkg import notedata
	ssc = '0001\\n0001\\n0001\\n0002\\n,\\n' * 10000 + '0001\\n0001\\n0001\\n0002'
	import attr
	attr.set_run_validators(False)
	'''

	print('{:.4e}'.format(min(Timer('notedata.sm_to_notedata(ssc)', setup).repeat(10, 1))))

	setup += '\n'
	setup += 'notedata = notedata.sm_to_notedata(ssc)'

	d: List[Tuple[str, str, int, int]] = [
		('shift', 'notedata.shift(20)', 10, 1),
		('clear_range', 'notedata.clear_range(420, 7000)', 10, 1),
		('slice', 'notedata[3:5000]', 10, 1),
	]

	for i in d:
		result = Timer(i[1], setup).repeat(i[2], i[3])
		print(i[0], f'lowest: {min(result):.4e}, median: {sorted(result)[len(result) // 2]:.4e}')
