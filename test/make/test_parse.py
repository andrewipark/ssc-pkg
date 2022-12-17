import unittest
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence, Type

import attr

import ssc_pkg.make.commands as c
import ssc_pkg.make.parse as p
from ssc_pkg.make.util import IndexPath, exc_index_trace


EXAMPLE_OBJS: Mapping[type, Sequence[Any]] = { #
	int: [0, 1, -1, 3, -46, 9, 2578, 2981],
	str: [
		'352w525w2', 'aeiew irbve', 'spaces  ', '\u03f9\u39b0', 'ssc_pkg.make',
		# not fraction test cases
		'22 6', '-3 2', '--3/2', '2 22220 /', '-', '', '+',
	],
	Fraction: [Fraction(0), Fraction(-3, 49), Fraction(200, 15)],
	type(None): [None],

	# these instances of complex types intentionally do not satisfy a more stringent generic
	dict: [{3: 9, 'a': 5}, {}, {'a': 3, None: 3, (3, 4): 'zebra'}],
	list: [[], [None], [[]], [[['everstone']], 2, 9]],
}
'''A bunch of example objects so that each key is a type representing the types of the values
(i.e. ``Mapping[Type[_T], _T]``)
'''


EXAMPLE_PARSE_FRACTIONS: Mapping[str, Fraction] = {
	'0': Fraction(0),
	'2': Fraction(2),
	'5/2': Fraction(5, 2),
	'8 / 3': Fraction(8, 3),
	'2 / 725': Fraction(2, 725),
	'2222 / 3': Fraction(2222, 3),
	'5 25 / 8': Fraction(65, 8),
	'24 999 / 1000': Fraction(24999, 1000),
	'333 1 / 2': Fraction(667, 2),
}
'''Things that should parse as fractions'''


EXAMPLE_PARSE_CHARTPOINT_PREFIXES: Mapping[str, tuple] = {
	'2 ~': (2, None),
	'river ~': (c.VarRef('river'), None),
	'ba @ 3 ~ ': (c.VarRef('ba'), c.VarRef('3')),
	'nile @ va~': (c.VarRef('nile'), c.VarRef('va')),
}


@attr.s(auto_attribs = True)
class ErrorIndex:
	test: unittest.TestCase
	wrap_exc_type: Type[Exception]
	root_exc_type: Type[Exception]
	indices: IndexPath

	def __enter__(self):
		pass

	def __exit__(self, exc_type, exc_value, _):
		self.test.assertIsNotNone(exc_type, 'ParseError not raised')
		e = exc_value
		while e.__cause__ is not None:
			self.test.assertIsInstance(e, self.wrap_exc_type)
			e = e.__cause__
		self.test.assertIsInstance(e, self.root_exc_type)
		exc_indices: list = sum((p[0] for p in exc_index_trace(exc_value)), [])
		self.test.assertEqual(exc_indices, self.indices)
		return True


def types_except(*types: type) -> Iterable[type]:
	'''Returns all the types in :const:`EXAMPLE_OBJS` except for the ones specified'''
	type_set = set(types)
	for t in EXAMPLE_OBJS:
		if t not in type_set:
			yield t


class TestParse(unittest.TestCase):
	def _easy_helper(self, t: type, c):
		for v in EXAMPLE_OBJS[t]:
			self.assertEqual(c(v), v)
		for t in types_except(t):
			for v in EXAMPLE_OBJS[t]:
				with self.assertRaises(TypeError, msg=str(v)):
					c(v)

	def test_check_get_u(self):
		# even though the index type isn't strictly supported,
		# the actual impl should use dynamic typing...
		for v in EXAMPLE_OBJS:
			self.assertIs(p.get_u(EXAMPLE_OBJS, (v,)), EXAMPLE_OBJS[v]) # type: ignore
			self.assertIs(p.get_u(EXAMPLE_OBJS[v], ()), EXAMPLE_OBJS[v])
			for i in range(len(EXAMPLE_OBJS[v])):
				self.assertIs(p.get_u(EXAMPLE_OBJS, (v, i)), EXAMPLE_OBJS[v][i]) # type: ignore
				self.assertIs(p.get_u(EXAMPLE_OBJS[v], (i,)), EXAMPLE_OBJS[v][i])
				self.assertIs(p.get_u(EXAMPLE_OBJS[v][i], ()), EXAMPLE_OBJS[v][i])

	def test_check_get_u_fail(self):
		self.assertRaises(LookupError, lambda: p.get_u(EXAMPLE_OBJS, (2,)))
		self.assertRaises(LookupError, lambda: p.get_u(EXAMPLE_OBJS, ('abcd',)))

		self.assertRaises(Exception, lambda: p.get_u(None, ('abcd',)))

	def test_check_int(self):
		self._easy_helper(int, p.check_int)

	def test_check_str(self):
		self._easy_helper(str, p.check_str)

	def test_check_sequence(self):
		self._easy_helper(list, p.check_sequence)

	def test_check_sequence_type(self):
		self.assertEqual(p.check_sequence_type(EXAMPLE_OBJS[int], p.check_int), EXAMPLE_OBJS[int])
		self.assertEqual(p.check_sequence_type(EXAMPLE_OBJS[str], p.check_str), EXAMPLE_OBJS[str])
		self.assertEqual(p.check_sequence_type(EXAMPLE_OBJS[list], p.check_sequence), EXAMPLE_OBJS[list])

		self.assertEqual(
			p.check_sequence_type(list(EXAMPLE_PARSE_FRACTIONS.keys()), p.parse_Fraction),
			list(EXAMPLE_PARSE_FRACTIONS.values())
		)

	def test_check_sequence_type_fail(self):
		corrupt = [2, 3, 9, None, 6, 9]
		with ErrorIndex(self, p.ParseError, TypeError, [3]):
			p.check_sequence_type(corrupt, p.check_int),

	def test_parse_fraction(self):
		for s, ex in EXAMPLE_PARSE_FRACTIONS.items():
			for pos in ['', '+', '+ ']:
				the = pos + s
				self.assertEqual(p.parse_Fraction(the), ex, the)
			for neg in ['-', '- ']:
				the = neg + s
				self.assertEqual(p.parse_Fraction(the), -ex, the)

		for v in EXAMPLE_OBJS[int]:
			self.assertEqual(p.parse_Fraction(v), Fraction(v))

	def test_parse_fraction_fail(self):
		for v in EXAMPLE_OBJS[str]:
			with self.assertRaises(ValueError, msg=str(v)):
				p.parse_Fraction(v)
		for t in types_except(str, int):
			for v in EXAMPLE_OBJS[t]:
				with self.assertRaises(TypeError, msg=str(v)):
					p.parse_Fraction(v)

	def test_parse_scalar(self):
		for i in EXAMPLE_OBJS[int]:
			self.assertEqual(p.parse_scalar(i), i)
		for s in EXAMPLE_OBJS[str]:
			self.assertEqual(p.parse_scalar(s), s)
		for fs, f in EXAMPLE_PARSE_FRACTIONS.items():
			self.assertEqual(p.parse_scalar(fs), f)
		for t in types_except(int, str):
			for v in EXAMPLE_OBJS[t]:
				with self.assertRaises(TypeError, msg=str(v)):
					p.parse_scalar(v)

	def test_parse_ChartPoint(self):
		for pr, (ci, base) in EXAMPLE_PARSE_CHARTPOINT_PREFIXES.items():
			for fs, f in EXAMPLE_PARSE_FRACTIONS.items():
				ex = c.ChartPoint(chart_index = ci, base = base, offset = f)
				self.assertEqual(p.parse_ChartPoint(pr + fs), ex)

	def test_parse_ChartPoint_fail(self):
		for s in EXAMPLE_OBJS[str]:
			with self.assertRaises(ValueError, msg=s):
				p.parse_ChartPoint(s)
			for fs, f in EXAMPLE_PARSE_FRACTIONS.items():
				v = fs + s
				with self.assertRaises(ValueError, msg=v):
					p.parse_ChartPoint(v)
		for t in types_except(str):
			for v in EXAMPLE_OBJS[t]:
				with self.assertRaises(TypeError, msg=str(v)):
					p.parse_ChartPoint(v)

	def test_parse_ChartRegion(self):
		a = c.ChartPoint(chart_index = 2, base = c.VarRef('fc'), offset = Fraction(-39, 10))
		for fs, v in EXAMPLE_PARSE_FRACTIONS.items():
			o = {'src': '2 @ fc ~ -3 9/10', 'len': fs}
			self.assertEqual(p.parse_ChartRegion(o), c.ChartRegion(start = a, length = v))

	# def test_parse_ChartRegion_fail(self): # TODO
