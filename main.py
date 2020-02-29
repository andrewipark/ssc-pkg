#!/usr/bin/python3

import argparse
from collections import deque
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

def args_path_sanity_check(args):
	if not args.input_dir.exists():
		raise FileNotFoundError(f"Input directory '{args.input_dir}' doesn't exist")
	input_dir_resolved = args.input_dir.resolve()
	output_dir_resolved = args.output_dir.resolve()
	if input_dir_resolved == output_dir_resolved:
		raise ValueError('Input and output directories are the same, which would overwrite files')

	err_parent, err_child = None, None
	if input_dir_resolved in output_dir_resolved.parents:
		err_parent, err_child = 'input', 'output'
	if output_dir_resolved in input_dir_resolved.parents:
		err_parent, err_child = 'output', 'input'

	if err_child:
		raise FileExistsError(f"{err_child.title()} directory is a child of the {err_parent} directory, "
			"which could overwrite files")

def get_file_list(input_dir, ignore_regex = None):
	"""Given an input directory, returns a processed listing of objects.

	The first list contains tuples of (simfile_dir, ssc_file).
	The second list is miscellaneous directories and files.

	This assumes that simfile directories are never nested inside each other.
	"""
	if ignore_regex is None:
		ignore_regex = []
	ignore_regex = [re.compile(r) for r in ignore_regex]

	simfiles = []
	non_simfiles = []

	# walk along the tree
	# DANGER if directory structure is not a tree
	explore = deque([input_dir])
	while len(explore) > 0:
		curr = explore.popleft() # BFS, but it shouldn't matter

		level = logging.DEBUG
		is_a_message = None

		ignore_matches = list(filter(None, [r.match(curr.parts[-1]) for r in ignore_regex]))
		if any(ignore_matches):
			is_a_message = 'ignored because of regexes: ' \
				+ ', '.join([
					f"'{match.re.pattern}' matched '{match.group()}'"
					for match in ignore_matches
				])

		# at this point we know that the file is not ignored
		elif curr.is_file():
			non_simfiles.append(curr)
			is_a_message = 'a miscellaneous file'
		elif curr.is_dir():
			children = list(curr.iterdir())

			# TODO no handling of sm files
			possible_ssc_candidates = list(filter(lambda p: p.parts[-1].endswith('.ssc'), children))
			if len(possible_ssc_candidates) == 0:
				explore.extend(children)
				is_a_message = 'a miscellaneous directory'
			elif len(possible_ssc_candidates) == 1:
				simfiles.append(curr)
				level = logging.INFO
				is_a_message = 'a simfile directory'
			else:
				# intentionally ignore
				level = logging.ERROR
				is_a_message = f'a malformed simfile directory with {len(possible_ssc_candidates)} step data files '\
					f'({[p.parts[-1] for p in possible_ssc_candidates]})'

		else:
			# intentionally do nothing
			level = logging.WARNING
			is_a_message = 'neither a file nor a directory'

		logging.log(level, f'\'{curr}\' is {is_a_message}')

	return (simfiles, non_simfiles)

def transform(out_dir):
	# transform ssc data
	# TODO don't assume names, have this sent down from above code
	# TODO use an actual library for this
	for thing in out_dir.iterdir():
		if thing.parts[-1].endswith(".ssc"):
			with open(thing) as f:
				ssc = f.read()

			# standardize music name
			ssc = re.sub("MUSIC:music.wav", "MUSIC:music.ogg", ssc)

			# remove labels
			ssc = re.sub("LABELS:.*?;", "LABELS:;", ssc, flags=(re.DOTALL | re.MULTILINE))

			# add ITG offset :(
			offset_regex = "OFFSET:(-?\d+?(?:\.\d+?)?);"
			offset = float(re.search(offset_regex, ssc).group(1))
			offset += 0.009
			ssc = re.sub(offset_regex, f"OFFSET:{offset:.3f};", ssc, flags=(re.DOTALL | re.MULTILINE))

			with open(thing, 'w') as f:
				f.write(ssc)

	# transcode ogg
	# TODO don't assume names
	old_music = out_dir / "music.wav"
	ogg_result = subprocess.run(["oggenc", "--quality=8", str(old_music)], capture_output=True)
	if ogg_result.returncode == 0:
		logging.error(f"oggenc failed with return code {ogg_result.returncode} and stderr\n{ogg_result.stderr}")
		return False

	old_music.unlink()
	return True

def cleanup(out_dir):
	# TODO make this configurable
	subprocess.run(["find", str(out_dir), "-name", "__*", "-print", "-delete"])
	subprocess.run(["find", str(out_dir), "-name", "*.old", "-print", "-delete"])

def run(args):
	args_path_sanity_check(args)

	logging.info(f'Exploring input directory for files')
	dirs, files = get_file_list(args.input_dir, args.ignore_regex)
	logging.info(f'Found {len(dirs)} simfile directories')

	if args.dry_run:
		return

	args.output_dir.mkdir(parents=True)

	# copy support files first
	for f in files:
		shutil.copy(f, args.output_dir / f.parts[-1])

	# copy folders
	simfile_dirs = []
	for d in dirs:
		out_dir = args.output_dir / d.parts[-1]
		simfile_dirs.append(out_dir)
		shutil.copytree(d, out_dir)

	# transform folders
	for d in simfile_dirs:
		transform(d)

	# clean up internal files
	for d in simfile_dirs:
		cleanup(d)

def main():
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

	try:
		run(args)
	except Exception as e:
		logging.critical('Unhandled exception interpreted as critical error', exc_info = e)

if __name__ == "__main__":
	main()
