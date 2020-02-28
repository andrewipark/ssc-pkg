from setuptools import find_packages, setup

setup(
	name='ssc-pkg',
	version='0.2',
	
	packages=find_packages(),
	include_package_data=True,
	
	zip_safe=False,
	
	# These are just based on what I have installed and are probably conservative
	python_requires='~=3.7', # ~=3.6?
	install_requires=[
		'numpy~=1.18',
		'pyyaml~=5.3',
	],
	
	classifiers=[
		'Development Status :: 1 - Planning',
		'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		'Programming Language :: Python :: 3',
		'Operating System :: OS Independent',
	],
)
