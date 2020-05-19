#!/usr/bin/python3
"""Command-line runner for ssc-pkg"""

import argparse
import logging
import re
import shutil
from collections import deque
from pathlib import Path
from typing import Any, Callable, Iterable, List

from . import transform_abc, transforms


# list file

def args_path_sanity_check(args):
	"""Do basic sanity checks for input and output directories"""
	if not args.input_dir.exists():
		raise FileNotFoundError(f"Input directory '{args.input_dir}' doesn't exist")
	input_dir_resolved = args.input_dir.resolve()
	output_dir_resolved = args.output_dir.resolve()
	if input_dir_resolved == output_dir_resolved:
		raise ValueError(f"Input and output directories both resolve to '{input_dir_resolved}', "
			'which would overwrite files')

	err_parent, err_child = None, None
	if input_dir_resolved in output_dir_resolved.parents:
		err_parent, err_child = 'input', 'output'
	if output_dir_resolved in input_dir_resolved.parents:
		err_parent, err_child = 'output', 'input'

	if err_child:
		raise FileExistsError(f"{err_child.title()} directory is a child of the {err_parent} directory, "
			"which could overwrite files")


def get_file_list(
	input_dir: Path,
	filter_function: Callable[[Path], bool] = None,
	handler: Callable[[Path], Any] = None,
	ignore_handler: Callable[[Path, Any], Any] = None
) -> Iterable[Path]:
	"""Walk an input directory and return a processed listing of objects.

	A partial replacement for os.walk on Path objects.
	There is no followlinks equivalent,
	so if a symbolic link points to a parent directory of itself,
	infinite recursion will occur.

	The functions must be as follows:
	filter_function(curr)
	handler(curr)
	ignore_handler(curr, filter_function(path))
	"""

	explore = deque([input_dir])
	while len(explore) > 0:
		curr = explore.popleft()

		if filter_function:
			filter_result = filter_function(curr)
			if filter_result:
				if ignore_handler:
					ignore_handler(curr, filter_result)
				continue

		if curr.is_dir():
			explore.extend(list(curr.iterdir()))
		if handler:
			handler(curr)
		yield curr


def regex_path_name_match(regex: List[str]) -> Callable[[Path], bool]:
	"""Return a function that:
	Given a path, return regex matches.
	"""
	regex_compiled = [re.compile(r) for r in regex]

	def filter_function(path):
		return list(filter(None, [r.match(path.name) for r in regex_compiled]))
	return filter_function


def what_is_log_helper(path: Path):
	'''filter for non-file, non-directory objects, which shouldn't show up in normal usage'''
	if not (path.is_file() or path.is_dir()):
		logging.warn(f"'{path}' is an unexpected object statted as:\n{path.stat()}")


def ignore_regex_log_helper(path: Path, matches: List[re.Match]):
	"""Output helpful information about regex matches"""
	logging.debug(f"'{path}' ignored because of regexes: "
		+ ', '.join([
			f"'{match.re.pattern}' matched '{match.group()}'"
			for match in matches
		]))


def _run_copy(args, files):
	try:
		args.output_dir.mkdir(parents=True)
	except FileExistsError:
		logging.warning(f"Output directory '{args.output_dir}' already exists and will be overwritten")

	for path in files:
		dest = args.output_dir / (path.relative_to(args.input_dir))
		if path.is_file():
			shutil.copy(path, dest)
		elif path.is_dir():
			dest.mkdir(exist_ok=True)


def _run_transform(args, simfiles):
	simfiles_generated = [(args.output_dir / (s.relative_to(args.input_dir)), s) for s in simfiles]
	# t[1] is original

	# transform
	transform_objs = []
	for i, t in enumerate(args.transforms):
		try:
			transform_objs.append(transforms.__dict__[t]())
		except KeyError:
			logging.error(f"transform '{t}' at index {i} does not exist")

	for t, o in simfiles_generated:
		for tr in transform_objs:
			if isinstance(tr, transform_abc.SimfileTransform):
				pass # TODO
			elif isinstance(tr, transform_abc.FileTransform):
				tr.transform(t, o)
			else:
				raise AssertionError('transform subclassing check failed')


def run(args):
	"""Top-level command to start the build process"""
	args_path_sanity_check(args)

	# list files
	files = list(get_file_list(
		args.input_dir,
		filter_function = regex_path_name_match(args.ignore_regex),
		handler = what_is_log_helper,
		ignore_handler = ignore_regex_log_helper
	))

	simfiles = [p for p in files if p.suffix == '.ssc']
	logging.info(f'Found {len(simfiles)} simfiles:\n'
		+ '\n'.join([str(p.parent) for p in simfiles]))

	if args.list_only:
		return

	_run_copy(args, files)

	_run_transform(args, simfiles)


def main():
	"""Initial command line entry point to set up logging and argument parsing"""
	parser = argparse.ArgumentParser(description="Package simfiles for distribution.")
	parser.add_argument("input_dir", type=Path)
	parser.add_argument("output_dir", type=Path)
	parser.add_argument('-v', '--verbose', action='count', default=0,
		help='Output more details (stacks)')
	parser.add_argument('-q', '--quiet', action='count', default=0,
		help='Output less details (stacks)')
	parser.add_argument('--list-only', action='store_true',
		help='List discovered simfile directories and stop')
	parser.add_argument("--ignore-regex", nargs='+', type=str, default=["^__", r'.*\.old$'],
		help="Objects matching any regex will not be considered (default: '%(default)s')")
	parser.add_argument('-t', '--transforms', nargs='*', type=str,
		help='Transform(s) to run on the simfiles')
	args = parser.parse_args()

	# set up logging
	log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
	requested_log_level = 2 + args.verbose - args.quiet
	requested_log_level = max(0, min(requested_log_level, len(log_levels) - 1))
	logging.basicConfig(level=log_levels[requested_log_level])
	logging.debug(args)

	run(args)
