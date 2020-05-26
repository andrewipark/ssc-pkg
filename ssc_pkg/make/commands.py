'''Command data structures'''

from typing import Any, Sequence

import attr


class Command:
	'''mixin for type support w/ ``mypy``'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs) # type: ignore # mypy-mixin


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
	'''sequence of commands to execute in a new scope'''
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
	'''variable definition (untyped)'''
	name: str
	value: Any
