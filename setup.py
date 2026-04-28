from setuptools import setup, find_packages

setup(
    name='envsync-vault',
    version='0.0.1',
    description='CLI for securely sharing encrypted .env files across teams.',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    author='Joe ONeal',
    url='https://github.com/joeoneal/env-sync',
    packages=find_packages(include=['cli', 'cli.*']),
    include_package_data=True,
    python_requires='>=3.10',
    install_requires=[
        'click',
        'requests',
        'cryptography',
        'email_validator',
        'halo',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Environment :: Console',
    ],
    entry_points={
        'console_scripts': [
            'envsync=cli.main:cli',
        ],
    },
)
