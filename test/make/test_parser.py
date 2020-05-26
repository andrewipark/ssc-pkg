import unittest
from fractions import Fraction
from typing import Any, Hashable, Iterable, Sequence, Tuple, Type

import attr

import ssc_pkg.make.commands as c
from ssc_pkg.make.parser import ParseError, Parser
from ssc_pkg.make.util import exc_index_trace


@attr.s(auto_attribs = True)
class ErrorIndex:
	test: unittest.TestCase
	wanted_exc_type: Type[Exception]
	indices: list

	def __enter__(self):
		pass

	def __exit__(self, exc_type, exc_value, _):
		self.test.assertIsNotNone(exc_type, 'ParseError not raised')
		self.test.assertIs(exc_type, self.wanted_exc_type)
		exc_indices: list = sum((p[0] for p in exc_index_trace(exc_value)), [])
		self.test.assertEqual(exc_indices, self.indices)
		return True


class TestParser(unittest.TestCase):
	'''Test harness for reference parser

	The test_parse_[command]_[part] functions test correct parsing of command structures within other commands.
	Their failures are only meaninfgul if all primitive tests test_parse_[command] otherwise pass.

	assertRaises doesn't work with chained exceptions.
	'''

	def _test_parse_multi(self, parse_obj, cmd_obj, extract, result_type):
		'''test helper for parse trees where a sub object is a Group'''
		blocks: Sequence[Tuple[Any, Sequence[c.Command]]] = [
			([], []),
			([{'pragma': 'one_pragma'}], [c.Pragma('one_pragma', None)]),
		]

		for block, expected in blocks:
			prepared = parse_obj(block)
			parse_result = self.parser.parse_command(prepared)
			expected_result = cmd_obj(c.Group(expected))
			self.assertIsInstance(parse_result, result_type)
			self.assertIsInstance(expected_result, result_type)
			self.assertEqual(
				extract(parse_result), extract(expected_result),
				f'parsed command:\n{parse_result}\nexpected command:\n{expected_result}'
			)

	def _test_only_type(self, obj, indices, allowed_types: Iterable[Hashable]):
		pass # TODO

	def setUp(self):
		self.parser = Parser()
		self.simple_pragma_obj = {'pragma': 'TEST'}
		self.simple_pragma_cmd = c.Pragma('TEST', None)

	def test_parse_Pragma(self):
		obj: list = [2, None]
		obj[1] = obj

		self.assertEqual(self.parser.parse_command(self.simple_pragma_obj), self.simple_pragma_cmd)
		self.assertEqual(
			self.parser.parse_command({'pragma': 'TEST', 'data': obj}),
			c.Pragma('TEST', obj)
		)
		self.assertEqual(
			self.parser.parse_command('pragma % blah blah blah % blah % blah 2'),
			c.Pragma('blah blah blah', ['blah', 'blah 2'])
		)

		with ErrorIndex(self, ParseError, ['pragma']):
			self.parser.parse_command({'pragma': None})
		with ErrorIndex(self, ParseError, ['pragma']):
			self.parser.parse_command({'pragma': None, 'data': obj})
		# TODO pragma type must be string

	def test_parse_Def(self):
		result = self.parser.parse_command({'def': 'fn_name', 'is': [self.simple_pragma_obj]})
		assert isinstance(result, c.Def)
		self.assertEqual(result.name, 'fn_name')
		self.assertEqual(result.group, c.Group([self.simple_pragma_cmd]))

	def test_parse_Def_body(self):
		self._test_parse_multi(
			lambda b: {'def': 'another_name', 'is': b},
			lambda e: c.Def('another_name', e),
			lambda cm: cm.group,
			c.Def
		)

	def test_parse_Group(self):
		self._test_parse_multi(
			lambda b: b,
			lambda e: e,
			lambda cm: cm.commands,
			c.Group
		)

	def test_parse_Call(self):
		self.assertEqual(
			self.parser.parse_command({'call': 'A_FUNCTION'}),
			c.Call('A_FUNCTION')
		)

	def test_parse_Let(self):
		let_table: dict = {
			3: 3,
			-3920: -3920,
			'3/5': Fraction(3, 5),
			'abc': 'abc',
			'': '',
		}

		for orig, ex in let_table.items():
			self.assertEqual(
				self.parser.parse_command({'let': f'probably_a_{ex}', 'is': orig}),
				c.Let(f'probably_a_{ex}', ex)
			)
			self.assertEqual(
				self.parser.parse_command({'let': f'probably_a_{ex}', 'is': [orig] * 5}),
				c.Let(f'probably_a_{ex}', [ex] * 5)
			)

	# whole-picture tests

	def test_multiple(self):
		pass # TODO

	def test_invalid(self):
		collection = [
			None,
			(i for i in range(300)),
			300,
			attr, # the module object... yes, seriously
		]
		for bad in collection:
			self.assertRaises(ParseError, lambda _: self.parser.parse_command(bad), str(bad))
