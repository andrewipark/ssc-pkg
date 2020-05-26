'''Command data structures'''

from typing import Any, Sequence

import attr


class Command:
	'''Mixin for mypy support'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs) # type: ignore # pylint: disable=W0235 # mypy-mixin


# actions

# (nothing)


# managed

@attr.s(auto_attribs=True)
class Pragma(Command):
	'''arbitrary directive for the command runner'''
	name: str
	data: Any


# control structures

@attr.s(auto_attribs=True)
class Group(Command):
	'''sequence of commands in its own scope'''
	commands: Sequence[Command]


@attr.s(auto_attribs=True)
class Def(Command):
	'''function definition'''
	name: str
	group: Group


@attr.s(auto_attribs=True)
class Call(Command):
	'''function call'''
	name: str


@attr.s(auto_attribs=True)
class Let(Command):
	name: str
	value: Any
