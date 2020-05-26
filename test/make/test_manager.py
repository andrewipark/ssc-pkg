import unittest
from typing import ClassVar, Iterable, Sequence
from fractions import Fraction

import attr

import ssc_pkg.make.commands as c
from ssc_pkg.make.manager import CommandError, Manager
from ssc_pkg.simfile import Simfile

from .test_parser import ErrorIndex


@attr.s(auto_attribs=True)
class _LogExecContext:
	'''Wraps a buffer to allow verification that commands executed'''

	buf: list = attr.Factory(list)

	def get_command(self, obj) -> c.Pragma:
		'''Return a pragma that will append some object onto this manager's internal buffer'''
		return c.Pragma('callable', [(lambda _, a: self.buf.append(a)), obj])

	def get_commands(self, o: Iterable) -> Sequence[c.Pragma]:
		return [self.get_command(obj) for obj in o]


class TestManagerObj(unittest.TestCase):

	GROUP_SIZE: ClassVar[int] = 4

	def mgr_run(self, command: c.Command):
		'''convenience method to run commands without a simfile attached'''
		self.manager.run(command, Simfile())

	def setUp(self):
		self.manager = Manager()

	def test_run_pragma_echo(self):
		collection = [
			None,
			1234567890420692565128888888888833314444155555,
			'BLAH BLAH BLAH',
			{'complex': 'not really'},
		]
		with self.assertLogs(self.manager.logger) as lm:
			for item in collection:
				self.mgr_run(c.Pragma('echo', item))
		self.assertEqual(len(lm.output), len(collection))
		for i in range(len(collection)):
			self.assertIn(str(collection[i]), lm.output[i])

	def test_run_pragma_vars(self):
		pass # TODO

	def test_run_pragma_raise(self):
		pass # TODO

	def test_run_pragma_callable(self):
		'''if this test fails, a lot of the control structure tests are useless'''
		ctx = _LogExecContext()
		self.mgr_run(ctx.get_command(666666))
		self.assertEqual(ctx.buf, [666666])

	def test_run_pragma_invalid(self):
		self.assertRaises(CommandError, lambda: self.mgr_run(c.Pragma('NO', None)))

	def test_run_group(self):
		ctx_single = _LogExecContext()
		for i in range(self.GROUP_SIZE):
			self.mgr_run(ctx_single.get_command(i))

		ctx_group = _LogExecContext()
		self.mgr_run(c.Group(ctx_group.get_commands(range(self.GROUP_SIZE))))

		self.assertEqual(ctx_single.buf, ctx_group.buf)

	# def and call are inseparable

	def test_run_def_call_simple(self):
		# basically the same as group, except now we have to define the function beforehand
		ctx_single = _LogExecContext()
		for i in range(self.GROUP_SIZE):
			self.mgr_run(ctx_single.get_command(i))

		ctx_def = _LogExecContext()
		commands = c.Group(ctx_def.get_commands(range(self.GROUP_SIZE)))
		self.mgr_run(c.Def('run_def_call_simple', commands))

		self.assertEqual([], ctx_def.buf)
		for i in range(1, 6):
			self.mgr_run(c.Call('run_def_call_simple'))
			self.assertEqual(ctx_single.buf * i, ctx_def.buf)

	def test_run_def_call_scope_visibility(self):
		'''Test that objects defined within Group scopes are not visible outside'''
		define_blah = c.Def('blah', c.Group([
			c.Def('blah2', c.Group([])),
			c.Call('blah2')
		]))

		self.mgr_run(define_blah)
		self.mgr_run(c.Call('blah'))
		with ErrorIndex(self, CommandError, ['Call']):
			self.mgr_run(c.Call('blah2')) # not visible from outside 'blah'

	def test_run_call_invalid(self):
		with ErrorIndex(self, CommandError, ['Call']):
			self.mgr_run(c.Call('not_existent_yet'))
		with ErrorIndex(self, CommandError, ['Call']):
			self.mgr_run(c.Call('might_exist'))

		self.mgr_run(c.Def('might_exist', c.Group([])))
		self.mgr_run(c.Call('might_exist'))

	def test_run_let(self):
		value_test = {
			'a_variable': 35,
			'a_list': [3, 5, 20],
			'a_mapping': {'a': 3, 'b': 63},
			'a_None': None,
			'a_Fraction': Fraction(42069, 17),
		}

		for name, value in value_test.items():
			self.mgr_run(c.Let(name, value))
			self.assertEqual(self.manager.frames[-1].variables[name], value)

	def test_run_let_scope_shadowing(self):
		'''Test that objects defined within scopes shadow objects defined outside the scope'''
		n = 'gamma'
		self.mgr_run(c.Let(n, 1))
		self.assertEqual(self.manager.lookup(n), 1)

		# shadowed assignment in group
		self.mgr_run(c.Group([
			c.Let(n, 2),
			c.Pragma('callable', [lambda m: self.assertEqual(m.lookup(n), 2)]),
		]))

		# no longer there outside group
		self.assertEqual(self.manager.lookup(n), 1)
