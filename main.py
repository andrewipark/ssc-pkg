#!/usr/bin/python3

import argparse
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

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
	if not args.input_path.exists():
		raise FileNotFoundError(f"Input path '{args.input_path}' doesn't exist")
	if args.output_path.exists():
		raise FileExistsError(f"Output path '{args.output_path}' exists and would be overwritten")

	# TODO untangle this
	dirs = []
	files = []

	# TODO can't this be a separate function?
	# copy over valid folders
	for candidate_obj in args.input_path.iterdir():
		if candidate_obj.parts[-1].startswith(args.internal_prefix):
			continue

		if candidate_obj.is_file():
			logging.debug(f"Found misc. root file '{candidate_obj}'")
			files.append(candidate_obj)

		elif candidate_obj.is_dir():
			for thing in candidate_obj.iterdir():
				if thing.parts[-1].endswith(".ssc"):
					logging.debug(f"Found simfile directory '{candidate_obj}'")
					dirs.append(candidate_obj)
					break
			else:
				logging.warning(f"Directory '{candidate_obj}' has no chart file")

		else:
			logging.warning(f"Unknown object '{candidate_obj}'")

	logging.info(f"Found {len(dirs)} simfile directories")

	args.output_path.mkdir(parents=True)

	# copy support files first
	for f in files:
		shutil.copy(f, args.output_path / f.parts[-1])

	# copy folders
	simfile_dirs = []
	for d in dirs:
		out_dir = args.output_path / d.parts[-1]
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
	parser.add_argument("input_path", type=Path)
	parser.add_argument("output_path", type=Path)
	parser.add_argument('-v', '--verbose', action='count', default=0,
		help='Output more details (stacks)')
	parser.add_argument('-q', '--quiet', action='count', default=0,
		help='Output less details (stacks)')
	parser.add_argument("--internal-prefix", type=str, default="__",
		help="Objects with this internal prefix will not show up in the output folder (default: '%(default)s')")
	args = parser.parse_args()

	# set up logging
	log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
	requested_log_level = 2 + args.verbose - args.quiet
	requested_log_level = min(0, max(requested_log_level, len(log_levels) - 1))
	logging.basicConfig(level=log_levels[requested_log_level])

	logging.debug(args)

	try:
		run(args)
	except Exception as e:
		logging.critical('Unhandled exception interpreted as critical error', exc_info = e)

if __name__ == "__main__":
	main()
