from setuptools import setup, find_packages

setup(
    name='envsync-vault',
    version='0.0.1a1',
    packages=find_packages(include=['cli', 'cli.*']),
    include_package_data=True,
    install_requires=[
        'click',
        'requests',
        'cryptography',
        'email_validator',
        'halo',
    ],
    entry_points={
        'console_scripts': [
            'envsync=cli.main:cli',
        ],
    },
)
