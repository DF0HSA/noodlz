from noodlz import __version__
from setuptools import setup, find_packages

setup(
	name="noodlz",
	version=__version__,
	packages=find_packages(),

	include_package_data=True,
	zip_safe=False,
	install_requires=[
		'Flask',
		'Flask-SQLAlchemy',
		'passlib',
	],

	entry_points={
		'console_scripts': [
			'noodlz = noodlz.__main__:main',
			'noodlz_import_json = noodlz.import_from_json:main',
		]
	},
)
