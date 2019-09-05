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
			offset = float(re.search("OFFSET:(.+?);", ssc).group(1))
			print(offset)
			offset += 0.009
			print(offset)
			ssc = re.sub("OFFSET:(.+?);", f"OFFSET:{offset:.3f};", ssc, flags=(re.DOTALL | re.MULTILINE))

			with open(thing, 'w') as f:
				f.write(ssc)

	# transcode ogg
	# TODO don't assume names
	old_music = out_dir / "music.wav"
	#subprocess.run(["oggenc", "--quality=8", str(old_music)])
	old_music.unlink()

def cleanup(out_dir):
	# TODO make this suffix configurable
	subprocess.run(["find", str(out_dir), "-name", "\"__*\"", "-print", "-delete"])

def run(args):
	if not args.input_path.exists():
		logging.error(f"Input path '{args.input_path}' doesn't exist")
		raise Exception
	if args.output_path.exists():
		logging.error(f"Output path '{args.output_path}' exists and would be overwritten")
		raise Exception

	dirs = []

	# find which folders are valid
	for candidate_obj in args.input_path.iterdir():
		if not candidate_obj.is_dir():
			continue

		for thing in candidate_obj.iterdir():
			if thing.parts[-1].endswith(".ssc"):
				logging.debug(f"Candidate: {candidate_obj}")
				dirs.append(candidate_obj)
				break

	logging.info(f"Found {len(dirs)} simfile directories")

	# copy folders
	args.output_path.mkdir(parents=True)
	out_dirs = []
	for d in dirs:
		out_dir = args.output_path / d.parts[-1]
		out_dirs.append(out_dir)
		# PYDUMB
		shutil.copytree(d, str(out_dir))

	# transform folders
	for d in out_dirs:
		transform(d)

	# clean up internal files
	for d in out_dirs:
		cleanup(d)

def main():
	parser = argparse.ArgumentParser(description="Package simfiles for distribution.")
	parser.add_argument("input_path", type=Path)
	parser.add_argument("output_path", type=Path)
	args = parser.parse_args()
	logging.basicConfig(level=logging.DEBUG)
	logging.debug(args)
	run(args)

if __name__ == "__main__":
	main()
