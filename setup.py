from setuptools import setup

setup(
    name='dcos-pytest',
    description='Wraps pytest to move and execute DC/OS integration tests on a remote master',
    install_requires=[
        'requests'
    ],
    scripts=['dcos-pytest']
)
