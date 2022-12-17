import unittest
from fractions import Fraction
from typing import Any, Callable, Sequence, Type, TypeVar

import ssc_pkg.make.commands as c
from ssc_pkg.make.parser import ParseError, Parser
from ssc_pkg.make.util import IndexPath

from .test_parse import EXAMPLE_OBJS, ErrorIndex


_T = TypeVar('_T', bound = c.Command)


class TestParser(unittest.TestCase):
	'''Test harness for reference parser

	The test_parse_[command]_[part] functions test correct parsing of command structures within other commands.
	Their failures are only meaninfgul if all primitive tests test_parse_[command] otherwise pass.

	assertRaises doesn't work with chained exceptions.
	'''

	def _test_parse_group(
		self,
		parse_obj: Callable[[Any], Any],
		cmd_obj: Callable[[c.Group], _T],
		extract: Callable[[_T], Any],
		result_type: Type[_T],
	): # noqa: E125
		'''test helper for parse trees where a sub object is a Group'''
		blocks: Sequence[tuple[Sequence, Sequence[c.Command]]] = [
			([], []),
			([{'pragma': 'one_pragma'}], [c.Pragma('one_pragma', None)]),
			([[]], [c.Group([])]),
			([[], [[[]]]], [c.Group([]), c.Group([c.Group([c.Group([])])])]),
		]

		for block, expected in blocks:
			prepared = parse_obj(block)
			parse_result = self.parser.parse_command(prepared)
			expected_result = cmd_obj(c.Group(expected))
			self.assertIsInstance(parse_result, result_type)
			self.assertIsInstance(expected_result, result_type)
			self.assertEqual(
				extract(parse_result), # type: ignore # asserted above
				extract(expected_result),
				f'parsed command:\n{parse_result}\nexpected command:\n{expected_result}'
			)

	def _test_parse_bad_values(
		self,
		parse_obj: Callable[[Any], Any],
		bad_values: Sequence,
		indices: IndexPath,
	): # noqa: E125
		for v in bad_values:
			with ErrorIndex(self, ParseError, TypeError, indices):
				self.parser.parse_command(parse_obj(v))

	def setUp(self):
		self.parser = Parser()
		self.simple_pragma_obj = {'pragma': 'TEST'}
		self.simple_pragma_cmd = c.Pragma('TEST', None)

	# def test_parse_Copy(self): TODO

	# def test_parse_Copy_invalid(self): TODO

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

	def test_parse_Pragma_invalid(self):
		# type(w['pragma']) == str
		self._test_parse_bad_values(
			lambda v: {'pragma': v},
			EXAMPLE_OBJS[int],
			['pragma']
		)

	def test_parse_Def(self):
		result = self.parser.parse_command({'def': 'fn_name', 'is': [self.simple_pragma_obj]})
		assert isinstance(result, c.Def)
		self.assertEqual(result.name, 'fn_name')
		self.assertEqual(result.body, c.Group([self.simple_pragma_cmd]))

	# def test_parse_Def_invalid(self): TODO

	def test_parse_Def_body(self):
		self._test_parse_group(
			lambda b: {'def': 'another_name', 'is': b},
			lambda e: c.Def('another_name', e),
			lambda cm: cm.body,
			c.Def
		)

	# def test_parse_Def_body_invalid(self): TODO

	def test_parse_Group(self):
		self._test_parse_group(
			lambda b: b,
			lambda e: e,
			lambda cm: cm,
			c.Group
		)

	# def test_parse_Group_invalid(self): TODO

	def test_parse_Call(self):
		self.assertEqual(
			self.parser.parse_command({'call': 'A_FUNCTION'}),
			c.Call('A_FUNCTION')
		)

	# def test_parse_Call_invalid(self): TODO

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

	# def test_parse_Let_invalid(self): TODO

	def test_parse_For(self):
		pass # TODO currently handled by _For_Body

	def test_parse_For_body(self):
		self._test_parse_group(
			lambda b: {'for': 's', 'in': [4, 5, 2, 9], 'do': b},
			lambda e: c.For('s', [4, 5, 2, 9], e),
			lambda cm: cm.body,
			c.For
		)

	# whole-picture tests

	def test_multiple(self):
		pass # TODO

	def test_invalid(self):
		collection = [
			None,
			300,
			unittest, # the module object... yes, seriously
			{'not_a_command': 'unittest'},
		]
		for bad in collection:
			self.assertRaises(TypeError, self.parser.parse_command, bad)

		invalid_strings = [
			'',
			'pragma',
			'junk''%''unknown',
		]
		for s in invalid_strings:
			self.assertRaises(ValueError, self.parser.parse_command, s)
