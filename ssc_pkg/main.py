#!/usr/bin/python3
"""Command-line runner for ssc-pkg"""

import argparse
from collections import deque
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Iterable, Callable, Any


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
	"""Log the basic type of an object"""
	log_level = logging.DEBUG
	if path.is_file():
		is_a_message = 'a file'
	elif path.is_dir():
		is_a_message = 'a directory'
	else:
		log_level = logging.WARNING
		is_a_message = f'something else statted as:\n{path.stat()}'
	logging.log(log_level, f"'{path}' is {is_a_message}")


def ignore_regex_log_helper(path: Path, matches: List[re.Match]):
	"""Output helpful information about regex matches"""
	logging.debug(f"'{path}' ignored because of regexes: "
		+ ', '.join([
			f"'{match.re.pattern}' matched '{match.group()}'"
			for match in matches
		]))


def transform(out_dir: Path):
	"""TODO rearchitect this entire piece of junk"""
	for thing in out_dir.iterdir():
		if thing.suffix == '.ssc':
			with open(thing) as f:
				ssc = f.read()

			# standardize music name
			ssc = re.sub("MUSIC:music.wav", "MUSIC:music.ogg", ssc)

			# remove labels
			ssc = re.sub("LABELS:.*?;", "LABELS:;", ssc, flags=(re.DOTALL | re.MULTILINE))

			# add ITG offset :(
			offset_regex = r'OFFSET:(-?\d+?(?:\.\d+?)?);'
			offset_match = re.search(offset_regex, ssc)
			if offset_match:
				offset = float(offset_match.group(1))
			else:
				offset = 0
			offset += 0.009
			ssc = re.sub(offset_regex, f"OFFSET:{offset:.3f};", ssc, flags=(re.DOTALL | re.MULTILINE))

			with open(thing, 'w') as f:
				f.write(ssc)

	# transcode ogg
	# TODO don't assume names of files
	try:
		old_music = out_dir / "music.wav"
		subprocess.run(["oggenc", "--quality=8", str(old_music)], capture_output=True, check=True)
		old_music.unlink()
	except subprocess.CalledProcessError as exc:
		logging.error(f"oggenc failed with return code {exc.returncode} and stderr\n{exc.stderr}")
	except FileNotFoundError:
		# TODO raise TransformException('oggenc unavailable')
		logging.error('oggenc unavailable')
	return True


def run(args):
	"""Top-level command to start the build process"""
	args_path_sanity_check(args)

	# explore
	files = list(get_file_list(
		args.input_dir,
		filter_function = regex_path_name_match(args.ignore_regex),
		handler = what_is_log_helper,
		ignore_handler = ignore_regex_log_helper
	))
	# TODO check for multiple simfiles in same directory
	# strategies: highest sort name, immediately raise
	simfiles = [p for p in files if p.suffix == '.ssc']

	logging.info(f'Found {len(simfiles)} simfile directories:\n'
		+ '\n'.join([str(p.parent) for p in simfiles]))

	if args.dry_run:
		return

	# copy
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

	# transform
	for simfile in simfiles:
		transform(simfile.parent)


def main():
	"""Initial command line entry point to set up logging and argument parsing"""
	parser = argparse.ArgumentParser(description="Package simfiles for distribution.")
	parser.add_argument("input_dir", type=Path)
	parser.add_argument("output_dir", type=Path)
	parser.add_argument('-v', '--verbose', action='count', default=0,
		help='Output more details (stacks)')
	parser.add_argument('-q', '--quiet', action='count', default=0,
		help='Output less details (stacks)')
	parser.add_argument('--dry-run', action='store_true',
		help='List files and folders to be copied without doing anything else')
	parser.add_argument("--ignore-regex", nargs='+', type=str, default=["^__", '.*\\.old$'],
		help="Objects matching any regex will not be considered (default: '%(default)s')")
	args = parser.parse_args()

	# set up logging
	log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
	requested_log_level = 2 + args.verbose - args.quiet
	requested_log_level = max(0, min(requested_log_level, len(log_levels) - 1))
	logging.basicConfig(level=log_levels[requested_log_level])
	logging.debug(args)

	run(args)


if __name__ == "__main__":
	main()
