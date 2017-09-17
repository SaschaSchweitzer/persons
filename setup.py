from setuptools import setup, find_packages

setup(name='persons',
      version='0.1a',
      description='Graph-based author disambiguation. Identifies distinct persons by matching forenames and surnames. Supports known persons, year data, and others.',
      url='https://github.com/SaschaSchweitzer/persons',
      author='Sascha Schweitzer',
      author_email='sascha.schweitzer@gmail.com',
      license='Apache License, Version 2.0',
      packages=find_packages(),
      long_description=open('README.md').read(),
      install_requires=[
          'pytz',
      ],
      extras_require = {
              'xlsx support':  ["pandas"],
              'pandas support':  ["pandas"]
          },
      zip_safe=False)