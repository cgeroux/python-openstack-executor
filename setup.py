import re
from setuptools import setup

version = re.search(
  '^__version__\s*=\s*"(.*)"',
  open('openstack_executor/openstack_executor.py').read(),
  re.M
  ).group(1)

with open("README.md", "rb") as f:
  long_descr = f.read().decode("utf-8")
    
setup(
  name="openstack_executor",
  packages=["openstack_executor"],
  entry_points={"console_scripts":['openstack-executor=openstack_executor.openstack_executor:main']},
  version=version,
  description="Used to specify a number of actions to perform on an OpenStack Tenent, similar to Heat, but is meant to be run on the command line. It is useful for automating various OpenStack actions.",
  long_description=long_descr,
  author="Chris Geroux",
  author_email="chris.geroux@ace-net.ca",
  url="",
  test_suite='nose.collector',
  test_require=['nose'],
  include_package_data=True
  )