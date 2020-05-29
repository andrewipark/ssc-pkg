#!/usr/bin/python3
"""Command-line runner for ssc-pkg"""

import argparse
import logging
import re
import shutil
from collections import deque
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Callable, Iterable, List, Optional

from . import simfile, transforms
from .transform import abc


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
	filter_function: Optional[Callable[[Path], bool]] = None,
	handler: Optional[Callable[[Path], Any]] = None,
	ignore_handler: Optional[Callable[[Path, Any], Any]] = None
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
		logging.warning(f"'{path}' is an unexpected object statted as:\n{path.stat()}")


def ignore_regex_log_helper(path: Path, matches: List[re.Match]):
	"""Output helpful information about regex matches"""
	logging.debug(f"'{path}' ignored because of regexes: "
		+ ', '.join([
			f"'{match.re.pattern}' matched '{match.group()}'"
			for match in matches
		]))


def _run_copy(args, files):
	time_original = perf_counter_ns()

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

	time_elapsed = perf_counter_ns() - time_original
	logging.info(f"copied {len(files)} objects ({time_elapsed / 1000000 :.0f} ms)")


def _load_metatransform_data(transform_obj, target: Path, original: Path, max_depth: int = 8):
	time_original = perf_counter_ns()

	file_path, key_path = transform_obj.data_path()
	try_paths = [p / file_path for p in [target.parent, original.parent]]
	try:
		load_file_path = next(p for p in try_paths if p.exists())
		transform_obj.logger.debug(
			f"using metadata file '{load_file_path}'"
		)
	except StopIteration:
		try_paths_str = ', '.join("'" + str(p) + "'" for p in try_paths)
		transform_obj.logger.debug(
			f"metadata '{file_path}' not available"
			f"(searched [{try_paths_str}])"
		)
		return None

	# standard YAML sequence
	from yaml import load
	try:
		from yaml import CLoader as Loader
	except ImportError:
		from yaml import Loader # type: ignore

	with open(load_file_path, encoding='utf-8') as f:
		data = load(f, Loader = Loader)

	# too bad if this file doesn't have what we want, even if another one does

	path_so_far: List[str] = []
	for key in key_path:
		try:
			data = data[key]
		except KeyError:
			transform_obj.logger.debug(f"metadata '{load_file_path}' did not have '{key}' at {path_so_far}")
			return None

		path_so_far.append(key)
		if len(path_so_far) > max_depth:
			raise RecursionError(
				f'transform {type(transform_obj).__name__} requested a key too deep ({max_depth})'
			)

	time_elapsed = perf_counter_ns() - time_original
	transform_obj.logger.debug(f"loaded transform metadata ({time_elapsed / 1000000 :.0f} ms)")

	return data


def _run_transform_obj(
	transform_obj,
	sf: simfile.Simfile,
	target: Path,
	original: Path,
) -> Optional[simfile.Simfile]:
	'''type-specific handling of transform step'''
	if isinstance(transform_obj, abc.SimfileTransform):
		return transform_obj.transform(sf)
	if isinstance(transform_obj, abc.FileTransform):
		return transform_obj.transform(sf, target)
	if isinstance(transform_obj, abc.MetaTransform):
		return transform_obj.transform(
			sf, target,
			_load_metatransform_data(transform_obj, target, original)
		)

	raise TypeError(f'transform {type(transform_obj).__name__} not recognized')


def _run_transform_action(transform_obj, target: Path, original: Path):
	'''Run the provided transform with the paths provided'''

	time_start = perf_counter_ns()

	# load
	# NOTE it might be faster not to load very large simfiles
	# with FileTransform impls that ignore the object anyways...
	with open(target, encoding='utf-8') as f:
		sf_orig = simfile.text_to_simfile(f)

	# modify
	transform_obj.logger.debug(
		# avoid strange characters
		f"start: '{sf_orig.title_transliterated or sf_orig.title}' located at '{target}'"
	)
	sf_new = _run_transform_obj(transform_obj, sf_orig, target, original)

	if sf_new is not None:
		# atomically swap the result over the old file
		target_new = target.parent / (target.name + '.transformed')
		with open(target_new, 'x', encoding='utf-8') as f:
			f.write(simfile.simfile_to_ssc(sf_new))
		target_new.replace(target)

	if isinstance(transform_obj, abc.Cleanable):
		transform_obj.clean()

	time_elapsed = perf_counter_ns() - time_start
	transform_obj.logger.debug(f"transformed '{target}' ({time_elapsed / 1000000 :.0f} ms)")


def _run_transform(args, simfiles):
	'''Run some transforms over all simfiles'''

	time_original = perf_counter_ns()

	simfiles_generated = [(args.output_dir / (s.relative_to(args.input_dir)), s) for s in simfiles]
	# t[1] is original

	# transform
	transform_objs = []
	for i, t in enumerate(args.transforms):
		try:
			transform_objs.append(transforms.__dict__[t]())
		except KeyError:
			logging.error(f"unknown transform '{t}' at index {i}")

	for target, original in simfiles_generated:
		time_original_curr = perf_counter_ns()

		for tobj in transform_objs:
			try:
				_run_transform_action(tobj, target, original)
			except Exception:
				logging.error(f"transform '{type(tobj).__name__}' failed on simfile '{target}'")
				raise

		time_elapsed = perf_counter_ns() - time_original_curr
		logging.debug(f"transformed {target} ({time_elapsed / 1000000 :.0f} ms)")

	time_elapsed = perf_counter_ns() - time_original
	logging.info(f"transformed {len(simfiles)} simfiles ({time_elapsed / 1000000 :.0f} ms)")


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

	# TODO add dupes check
	simfiles = [p for p in files if p.suffix == '.ssc']
	logging.info(f'Found {len(simfiles)} simfiles:\n'
		+ '\n'.join(['\t' + str(p.parent) for p in simfiles]))

	if args.list_only:
		return

	_run_copy(args, files)

	_run_transform(args, simfiles)

	logging.info('finished')


def main():
	"""Initial command line entry point to set up logging and argument parsing"""
	parser = argparse.ArgumentParser(description='Package simfiles for distribution.')
	parser.add_argument("input_dir", type=Path)
	parser.add_argument("output_dir", type=Path)
	parser.add_argument('-v', '--verbose', action='count', default=0,
		help='output more detail (stacks)')
	parser.add_argument('-q', '--quiet', action='count', default=0,
		help='output less detail (stacks)')
	parser.add_argument('--list-only', action='store_true',
		help='list discovered simfile directories and stop')
	parser.add_argument('--ignore-regex', nargs='*', type=str, default=['^__', r'.*\.old$'],
		help="object names that match a regex will not be considered (default: '%(default)s')")
	parser.add_argument('-t', '--transforms', nargs='*', type=str, default=[],
		help='transform(s) to run on the simfiles')
	args = parser.parse_args()

	# set up logging
	log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
	requested_log_level = 2 + args.verbose - args.quiet
	requested_log_level = max(0, min(requested_log_level, len(log_levels) - 1))
	logging.basicConfig(level=log_levels[requested_log_level])
	logging.debug(args)

	run(args)
