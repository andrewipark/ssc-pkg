from setuptools import find_packages, setup

setup(
	name='ssc-pkg',
	version='0.5',
	
	packages=find_packages(),
	include_package_data=True,
	
	zip_safe=False,
	
	# these requirements are intentionally aggressive.
	python_requires='~=3.8', # needed for type introspection and fast local copy

	install_requires=[
		# 'numpy~=1.18',
		'pyyaml~=5.3',
		'attr>=0.3.1, <1',
	],

	extras_require={
		'lint': [
			'flake8~=3.7.9',
			'flake8-tabs~=2.2.1',
			'mypy~=0.761',
		],
	},
	
	classifiers=[
		'Development Status :: 1 - Planning',
		'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		'Programming Language :: Python :: 3',
		'Operating System :: OS Independent',
	],
)
