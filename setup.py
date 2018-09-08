#!/usr/bin/python
import sys

from setuptools import setup, find_packages

setup(
    name='MusicBar',
    version='1.0',
    description='A macOS menu bar item which shows your currently playing music.',
    url='https://github.com/russelg/musicbar',
    author='russelg',
    author_email='drew.isaac2@gmail.com',
    license='GPL-3.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 3',
    ],
    keywords='music',
    packages=find_packages(),
    install_requires=['rumps', 'pyobjc', 'py-applescript'],
    scripts=['bin/musicbar']
)

autostart = str(input("\nWould you like to enable now and on login? [y/n] ")).upper()

if autostart == "Y" or autostart == "YES":
    import autorun

    sys.argv.append("enable")
    autorun.main()
