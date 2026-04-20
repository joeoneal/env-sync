from setuptools import setup, find_packages

setup(
    name='envsync',
    version='0.0.1a1',  # Bumped to a1 so PyPI accepts it if you already pushed 'a'
    # THIS IS THE MAGIC FIX:
    packages=find_packages(include=['cli', 'cli.*']),
    include_package_data=True,
    install_requires=[
        'click',
        'requests',
        'cryptography',
    ],
    entry_points={
        'console_scripts': [
            'envsync=cli.main:cli',
        ],
    },
)