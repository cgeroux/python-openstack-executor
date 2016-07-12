Overview
========

The openstack-executor package provides a command line executable which takes 
as input an xml file describing actions to perform on an OpenStack project and 
performs them.

These actions can do the following:

+ terminate a vm
+ create images from volumes
+ download images to the local machine
+ upload images from a local machine
+ create volumes from images
+ create a new VM which boots from a volume
+ associate public ip with a VM
+ attach a volume to a VM

and more actions may be added with time as need arises.

The below instructions describe how to setup and use the openstack-executor 
in the ACENET environment. While they can be followed for other Linux 
distributions and environments, some steps may need to be modified for the 
specific Linux environment.


Requirements
============

+ Python2.6+

  Already available on ACENET machines and most current Linux 
  distributions. Tested specifically with Python3.4.1 and Python2.7.10

+ pip

  Already available on ACENET machines, if not on an ACENET machine 
  search within your Linux distribution package manager for pip (e.g. 
  "apt-cache search pip" and installed with "apt-get install 
  <pip-package-name>" in Ubuntu)
  
+ lxml
  
+ OpenStack python clients

  These clients change rapidly, so it is likely important to use the same
  version this code was developed and tested with. Currently that is 2.6.0.
  See below installation instructions on how to get the correct version.

+ An OpenStack rc file

  Downloaded from your OpenStack dashboard under Project->Compute->
  Access & Security->API Access->Download OpenStack RC File
  or on east cloud this is now "Download OpenStack RC File v3" the
  "Download OpenStack RC File v2" option will not work for most users.


Setting up your environment
---------------------------

On ACENET machines you need to load the module for the version of python you 
wish to use with

```shell
module purge
module load gcc pythonX.Y
```

Which set environment variables to use version X.Y of python. If installing 
packages locally, which is what most users will do as they don't have 
administrative privileges, the paths for locally installed libraries and 
binaries will need to be added to the environment variables, PYTHONPATH and 
PATH respectively. The commands:

```
$ export PATH=${HOME}/.local/bin:${PATH}
$ export PYTHONPATH=${HOME}/.local/lib/pythonX.Y/site-packages:${PYTHONPATH}
```

will do this if using the bash shell. These lines can be added to your 
".bashrc" file in your home directory to have these commands executed each 
time you log into the machine.

Finally you must source your openstack rc file and provide your OpenStack 
password.

Installing lxml
---------------

To install to your home directory with pip:

```
$ pip install --user lxml
```

Getting OpenStack python clients
--------------------------------

As with lxml the command is:

```
$ pip install --user python-openstackclient==2.6.0
```

Installation openstack-executor
===============================

From inside the python-openstack-executor directory run:

```
$ python setup.py install --user
```

to install to your home directory. The --record <filename> option will output 
a list of files created during install.


Usage
=====

To run the program use the command:

```
$openstack-executor ACTIONS.XML
```

where the ACTIONS.xml file describes the actions you wish to perform. A "-h" 
or "--help" option can be specified to also describe usage and available 
options. The "examples_action_xml_files" directory contains a number of 
examples of this ACTIONS.xml input file. This directory can be found either 
in the original source code under the 
"python-openstack-executor/openstack_executor" directory or in the case of a 
user install in 

"${HOME}/.local/lib/pythonX.Y/site-packages/openstack_executor-A.B.C-pyX.Y.egg
/openstack_executor/"

where X.Y is the major and minor versions of python, and A.B.C is the version 
of openstack-executor. At the time of this writing it would be 1.0.0.

These example XML files show all the available actions illustrated in a few 
usage cases. Each type of action has XML comments (<!-- comment -->) 
describing what it is doing and the available options. These examples can
contain multiple instances of the same action type and only the first of these
action types is documented.

For further details on the structure of these xml action files, have a look at
the xml schema files (W3 schools describes the xsd format used). These files 
are in the "xmlSchema" directory. In the original source code this is
"python-openstack-executor/openstack_executor/xmlSchema". In the user 
installed version this is in 

"${HOME}/.local/lib/pythonX.Y/site-packages/openstack_executor-A.B.C-pyX.Y.egg
/openstack_executor/"


Development/Debugging Notes
===========================

If you developing openstack-executor these might be helpful notes.

+ Running a non-installed version from the root package directory 
  "python-openstack-executor"

```
$ python -m openstack_executor ACTIONS.xml
```

  will execute the directory openstack_executor.

+  The script openstack-executor-runner.py can also be used to run the code as:

```
$ ./openstack-executor-runner.py ACTIONS.xml
```

+ To run a single test script (will show stdout):

```
$ python openstack_executor/tests/<test_script>.py
```

  This however, will import modules from the installation location so for changes 
  in your tested code to take effect they must be "installed" first.
  
+ To run all tests showing only results (will not show stdout):

```
$ python setup.py test
```
  
  
Integration Testing
-------------------

+ run the example xml files in openstack_executor/example_action_xml_files

+ this requires that at the very least
+ + a bootable volume named "root"
+ + an attachable volume named "data"
+ + the ip address 206.12.96.177 available to associate with a VM
+ + the flavor "c4-15gb-205" 

+ the expected order is 
+ + backup_server.xml
+ + delete_server_volumes_and_images.xml
+ + restore_from_backup.xml
