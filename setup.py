from setuptools import find_packages, setup # type: ignore

setup(
	name='ssc-pkg',
	version='0.11',

	packages=find_packages(),
	include_package_data=True,

	python_requires='~=3.10',

	install_requires=[
		'pyyaml>=6.0',
		'attrs~=21.4', # TODO weird mypy error with 22.1, probably my fault
	],

	extras_require={
		'lint': [ # unit, type, code style testing
			'mypy~=0.991',
			'flake8==3.9.2', # b/c flake8-tabs: ~=3.0
			'flake8-tabs~=2.3,>=2.3.2',
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
