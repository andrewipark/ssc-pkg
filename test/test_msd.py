import unittest
from numbers import Number

import attr

from ssc_pkg import msd
from ssc_pkg.msd import MSDItem


class TestMSD(unittest.TestCase):

	@attr.s(auto_attribs=True)
	class Simple:
		a_value: int
		a_string: str
		a_list: list

	def setUp(self):
		self.some_text = '\n'.join([
			'#SIMPLETAG:SIMPLEVALUE;',
			'#LONGTAGTHANKSplzzzzzzzzzzzzzzzzzzzz:SHORTVALUE;',
			'#ATAG:VALUE',
			'ON',
			'FOUR',
			'LINES;',
			'', # force \n at end
		])

		lower_alpha = ''.join(chr(c + ord('a')) for c in range(26))
		unicode_range = ''.join(chr(c) for c in range(400, 10000, 44))

		self.msd_items = [
			MSDItem('tag', 'value'),
			MSDItem(lower_alpha, unicode_range),
			MSDItem('anothertag', 'VALUE\nWITH\nembedded\n\n\n\n\n\n\nnnewlines')
		]

		self.simple = self.Simple(400, lower_alpha + '\n\n\n\n\n\n' + unicode_range, [2, 6, 5, 8, 68])

		self.simple_msd = [MSDItem(k, str(v)) for k, v in attr.asdict(self.simple).items()]

	def test_msd_item_str(self):
		for i in self.msd_items:
			self.assertEqual(str(i), f'#{i.tag}:{i.value};')

	def test_text_to_msd(self):
		msd_items = list(msd.text_to_msd(self.some_text))
		self.assertEqual(len(msd_items), 3)
		self.assertEqual(msd_items[0].tag, 'SIMPLETAG')
		self.assertEqual(msd_items[0].value, 'SIMPLEVALUE')
		self.assertEqual(msd_items[1].tag, 'LONGTAGTHANKSplzzzzzzzzzzzzzzzzzzzz')
		self.assertEqual(msd_items[1].value, 'SHORTVALUE')
		self.assertEqual(msd_items[2].value, '\n'.join(['VALUE', 'ON', 'FOUR', 'LINES']))

	def test_text_to_msd_cycle(self):
		msd_items_a = list(msd.text_to_msd(self.some_text))
		text_a = msd.msd_to_text(msd_items_a)
		self.assertEqual(self.some_text, text_a)
		msd_items_b = list(msd.text_to_msd(text_a))
		self.assertEqual(msd_items_a, msd_items_b)
		text_b = msd.msd_to_text(msd_items_b)
		self.assertEqual(text_a, text_b)

	def test_attrs_obj_to_msd(self):
		self.assertEqual(
			list(msd.attrs_obj_to_msd(self.simple)),
			[
				MSDItem('a_value', str(self.simple.a_value)),
				MSDItem('a_string', self.simple.a_string),
				MSDItem('a_list', str(self.simple.a_list)),
			]
		)

	def test_attrs_obj_to_msd_name_converter(self):
		self.assertEqual(
			list(msd.attrs_obj_to_msd(self.simple, name_converter = lambda x: x[2:])),
			[
				MSDItem('value', str(self.simple.a_value)),
				MSDItem('string', self.simple.a_string),
				MSDItem('list', str(self.simple.a_list)),
			]
		)

		d = 'duplicates_are_allowed'
		self.assertEqual(
			list(msd.attrs_obj_to_msd(self.simple, name_converter = lambda x: d)),
			[
				MSDItem(d, str(self.simple.a_value)),
				MSDItem(d, self.simple.a_string),
				MSDItem(d, str(self.simple.a_list)),
			]
		)

	def test_attrs_obj_to_msd_value_converter(self):
		self.assertEqual(
			list(msd.attrs_obj_to_msd(
				self.simple,
				value_converter = lambda vn, vt, v: str(vt), # type: ignore # mypy-generic-fn
			)),
			[MSDItem(str(a.name), str(a.type)) for a in attr.fields(type(self.simple))]
		)

		self.assertEqual(
			list(msd.attrs_obj_to_msd(
				self.simple,
				value_converter = lambda vn, vt, v: str(v * 3), # type: ignore # mypy-generic-fn
			)),
			[
				MSDItem('a_value', str(self.simple.a_value * 3)),
				MSDItem('a_string', self.simple.a_string * 3),
				MSDItem('a_list', str(self.simple.a_list * 3)),
			]
		)

	def test_attrs_obj_to_msd_filterer(self):
		self.assertEqual(
			list(msd.attrs_obj_to_msd(
				self.simple,
				filterer = lambda vn, vt, v: True, # type: ignore # mypy-generic-fn
			)),
			list(msd.attrs_obj_to_msd(self.simple)),
		)

		class _EveryOther:

			def __init__(self):
				self.x = 0

			def filterer(self, *args) -> bool:
				self.x += 1
				return self.x % 2 == 1

		f = _EveryOther()
		self.assertEqual(
			list(msd.attrs_obj_to_msd(self.simple, filterer = f.filterer)),
			list(msd.attrs_obj_to_msd(self.simple))[::2],
		)

	@classmethod
	def _simple_vc(_, tag, value_type, value):
		if value_type is str:
			return value
		if issubclass(value_type, Number):
			return value_type(value)
		assert value_type is list
		return [int(v.strip()) for v in value[1:-1].split(',')]

	def test_msd_to_attrs_obj_tag_converter(self):
		converted, excess = msd.msd_to_attrs_obj(self.simple_msd, self.Simple, value_converter = self._simple_vc)
		self.assertEqual(converted, self.simple)
		self.assertEqual(len(excess), 0)

		# excess item insert
		clobber = 'legible'
		self.simple_msd.append(MSDItem('a_string', clobber))
		converted, excess = msd.msd_to_attrs_obj(self.simple_msd, self.Simple, value_converter = self._simple_vc)
		self.assertEqual(converted, attr.evolve(self.simple, a_string = clobber))

	def test_msd_to_attrs_obj_value_converter(self):
		self.simple_msd = [MSDItem(i.tag[::-1], i.value) for i in self.simple_msd]

		converted, excess = msd.msd_to_attrs_obj(
			self.simple_msd, self.Simple,
			tag_converter = lambda x: x[::-1],
			value_converter = self._simple_vc
		)
		self.assertEqual(converted, self.simple)
		self.assertEqual(len(excess), 0)
