TODO: write some basic documentation

Some notes I found useful.

Running a non-installed version

  python -m openstack_executor
  
will execute the directory openstack_executor. The script openstack-executor-runner.py can also be used to run the code.

Installation:

  python setup.py install 

use --user to install to home directory
use --record <filename> to output a list of files created during install
  
to run a single test script (will show stdout):

  python openstack_executor/tests/<test_script>.py
  
to run all tests showing only results (will not show stdout):

  python setup.py test
  
