from setuptools import find_packages, setup # type: ignore

setup(
	name='ssc-pkg',
	version='0.10',

	packages=find_packages(),
	include_package_data=True,

	python_requires='~=3.8',
	# 3.8: required for type introspection and fast local copy
	# 3.9: (might be) required for less annoying type annotations

	install_requires=[
		'pyyaml~=5.3',
		'attrs~=19.3',
	],

	extras_require={
		'lint': [ # unit, type, code style testing
			'mypy~=0.770',
			'flake8~=3.8,>=3.8.2',
			'flake8-tabs~=2.2.1',
		],
	},

	classifiers=[
		'Development Status :: 2 - Pre-Alpha',
		'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		'Programming Language :: Python :: 3',
		'Operating System :: OS Independent',
	],

	entry_points={
		'console_scripts': [
			'ssc-pkg = ssc_pkg.main:main'
		],
	},
)
