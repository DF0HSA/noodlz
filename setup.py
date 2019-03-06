from setuptools import setup, find_packages

setup(
	name="noodlz",
	version="1.0",
	packages=find_packages(),

	include_package_data=True,
	zip_safe=False,
	install_requires=[
		'flask',
	],
)
