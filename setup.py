from setuptools import find_packages, setup

setup(
	name='ssc-pkg',
	version='0.1',
	
	packages=find_packages(),
	include_package_data=True,
	
	zip_safe=False,
	
	python_requires='~=3.7', # might actually be ~=3.6, who knows
	install_requires=[
		'numpy~=1.17',
		'pyyaml~=5.1',
	],
	
	classifiers=[
		'Development Status :: 1 - Planning',
		'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		'Programming Language :: Python :: 3',
		'Operating System :: OS Independent',
	],
)
