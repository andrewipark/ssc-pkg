from setuptools import find_packages, setup

setup(
	name='ssc-pkg',
	version='0.7',
	
	packages=find_packages(),
	include_package_data=True,
	
	zip_safe=False,
	
	python_requires='~=3.8', # needed for type introspection and fast local copy

	install_requires=[
		# 'numpy~=1.18',
		'pyyaml~=5.3',
		'attrs~=19.3',
	],

	extras_require={
		'lint': [
			'mypy~=0.770',
			'flake8~=3.7.9', # PyCQA slow release schedule
			'flake8-tabs~=2.2.1',
			# FIXME blocked https://github.com/PyCQA/pycodestyle/issues/911
			'pycodestyle @ git+https://github.com/PyCQA/pycodestyle.git',
			# FIXME blocked flake8 did not update its dependency properly
			# flake8 incompatible error message is spurious
			'pyflakes~=2.2',
		],
	},
	
	classifiers=[
		'Development Status :: 1 - Planning',
		'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		'Programming Language :: Python :: 3',
		'Operating System :: OS Independent',
	],
)
