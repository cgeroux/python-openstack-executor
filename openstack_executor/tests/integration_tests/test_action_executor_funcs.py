#!/usr/bin/env python
import unittest
import openstack_executor
import os

class Temp(object):
  """Just a dummy class
  """
  pass

options=Temp()
options.alreadyExistsGlobal=None

#make sure we can check OS_AUTH_URL
envVars=os.environ.keys()
if "OS_AUTH_URL" not in envVars:
  raise Exception("Missing environment variable \"OS_AUTH_URL\" "
    +"did you forget to source the openstack RC file?")

#test which cloud we are connecting to
if "west" in os.environ['OS_AUTH_URL']:
  imageName="ubuntu-server-16.04-amd64"
  flavor="p1-1.5gb"
elif "east" in os.environ['OS_AUTH_URL']:
  imageName="ubuntu-xenial-server-cloudimg-amd64-2016-04-20"
  flavor="p1-0.75gb"
else:
  raise Exception("couldn't figure out which cloud you are using based on "
    +"OS_AUTH_URL="+os.environ['OS_AUTH_URL'])

vmName="openstack-executor-integration-test-vm"
osc=openstack_executor.getOSClients()

#TODO: 
# I should have more stringent tests for success conditions (e.g. 
# actually check that a vm or volume was created as expected) 
# rather than just assume everything went OK if an exception wasn't thrown 
# or just trying to watch what happens in the openstack dashboard.
# ^^^ this issue is actually quite a bit better now, however there are somethings
#     which I do not specifically test for still, such as weather an IP address has_key
#     been associated with a VM or not, or if a cloud-init script ran correctly
#
# add tests for functions:
#  downloadImage
#  attachVolume
#  uploadImage
#  createVolume (not from an image)
#  addSecurityGroup
#  
# In addition I could also exercise the various functions under different
# conditions e.g. overwriting something, skipping etc.

class TestPersistentVMTasks(unittest.TestCase):

  def test_00_volumeCreateFromImage(self):
    """
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>create-root-volume-test-00</id>
          <dependencies>
          </dependencies>
          <parameters>
            <create-volume>
              <volume-name>"""+vmName+"""-root</volume-name>
              <image>"""+imageName+"""</image>
              <size>2</size>
              <already-exists>overwrite</already-exists>
            </create-volume>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
    clients={}#seems that queering information such as if a VM is around or
      #not sometimes lags behind, by forcing a re-initalization of clients 
      #it seems to help this
    volume=openstack_executor.action_executor_funcs.getVolume(osc,clients
      ,vmName+"-root")
    assert openstack_executor.action_executor_funcs.isActive(volume)
  def test_01_imageCreateFromVolume(self):
    """
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>create-image-from-volume-test01</id>
          <dependencies>
          </dependencies>
          <parameters>
            <create-image-from-volume>
              <volume>"""+vmName+"""-root</volume>
              <image-name>"""+vmName+"""-image</image-name>
              <format>vmdk</format>
              <already-exists>overwrite</already-exists>
            </create-image-from-volume>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
    clients={}#seems that queering information such as if a VM is around or
      #not sometimes lags behind, by forcing a re-initalization of clients 
      #it seems to help this
    image=openstack_executor.action_executor_funcs.getImage(osc,clients
      ,vmName+"-image")
    assert openstack_executor.action_executor_funcs.isActive(image)
  def test_02_deleteImage(self):
    """
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>delete-image-test02</id>
          <dependencies>
          </dependencies>
          <parameters>
            <delete-image>
              <image>"""+vmName+"""-image</image>
            </delete-image>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
    clients={}#seems that queering information such as if a VM is around or
      #not sometimes lags behind, by forcing a re-initalization of clients 
      #it seems to help this
    image=openstack_executor.action_executor_funcs.getImage(osc,clients
      ,vmName+"-image")
    assert image==None
  def test_03_bootVMFromVolume(self):
    """Tests the creation of a VM
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>boot-from-volume-test03</id>
          <parameters>
            <create-instance>
              <name>"""+vmName+"""</name>
              <flavor>"""+flavor+"""</flavor>
              <instance-boot-source>
                <volume>"""+vmName+"""-root</volume>
              </instance-boot-source>
              <already-exists>overwrite</already-exists>
            </create-instance>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
    clients={}#seems that queering information such as if a VM is around or
      #not sometimes lags behind, by forcing a re-initalization of clients 
      #it seems to help this
    vm=openstack_executor.action_executor_funcs.getVM(osc,clients,vmName)
    assert openstack_executor.action_executor_funcs.isActive(vm)
  def test_04_addIPToVM(self):
    """Tests allocating an IP to project and assigning it to a VM
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>add-ip-test04</id>
          <parameters>
            <associate-floating-ip>
              <instance>"""+vmName+"""</instance>
            </associate-floating-ip>
          </parameters>
        </action>  
      </actions>
    """
    
    #TODO: add a way to check that the IP is Added
    openstack_executor.run(xml,options)
  def test_05_releaseIP(self):
    """Tests releasing a floating IP associated with a given VM
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>release-ip-test05</id>
          <parameters>
            <release-floating-ip>
              <instance>"""+vmName+"""</instance>
            </release-floating-ip>
          </parameters>
        </action>  
      </actions>
    """
    
    #TODO: add a way to check that the IP is released
    openstack_executor.run(xml,options)
  def test_06_terminateVM(self):
    
    xml="""
      <actions version="0.0">
        <action>
          <id>vm-terminate-test06</id>
          <parameters>
            <terminate-instance>
              <instance>"""+vmName+"""</instance>
            </terminate-instance>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
    clients={}#seems that queering information such as if a VM is around or
      #not sometimes lags behind, by forcing a re-initalization of clients 
      #it seems to help this
    vm=openstack_executor.action_executor_funcs.getVM(osc,clients,vmName)
    assert vm is None#stupid openstack bug, can't use ==
  def test_07_deleteVolume(self):
    
    xml="""
      <actions version="0.0">
        <action>
          <id>delete-root-volume-test07</id>
          <parameters>
            <delete-volume>
              <volume>"""+vmName+"""-root</volume>
            </delete-volume>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
    clients={}#seems that queering information such as if a VM is around or
      #not sometimes lags behind, by forcing a re-initalization of clients 
      #it seems to help this
    volume=openstack_executor.action_executor_funcs.getVolume(osc,clients,vmName)
    assert volume is None
class TestComputeVMTasks(unittest.TestCase):
  def test_00_createVMFromImage(self):

    """Tests the creation of a VM
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>vm-create-test00</id>
          <parameters>
            <create-instance>
              <name>"""+vmName+"""</name>
              <flavor>"""+flavor+"""</flavor>
              <instance-boot-source>
                <image>"""+imageName+"""</image>
              </instance-boot-source>
              <already-exists>overwrite</already-exists>
            </create-instance>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
    clients={}#seems that queering information such as if a VM is around or
      #not sometimes lags behind, by forcing a re-initalization of clients 
      #it seems to help this
    vm=openstack_executor.action_executor_funcs.getVM(osc,clients,vmName)
    assert openstack_executor.action_executor_funcs.isActive(vm)
  def test_01_createMultipleVMsFromImageRename(self):

    """Tests the creation of a VM
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>vm-create-test01</id>
          <parameters>
            <create-instance>
              <name>"""+vmName+"""</name>
              <instance-count>2</instance-count>
              <flavor>"""+flavor+"""</flavor>
              <instance-boot-source>
                <image>"""+imageName+"""</image>
              </instance-boot-source>
              <already-exists>rename</already-exists>
            </create-instance>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
    clients={}
    vm0=openstack_executor.action_executor_funcs.getVM(osc,clients,vmName+"-0")
    vm1=openstack_executor.action_executor_funcs.getVM(osc,clients,vmName+"-1")
    assert openstack_executor.action_executor_funcs.isActive(vm0)
    assert openstack_executor.action_executor_funcs.isActive(vm1)
  def test_02_terminateAllVMs(self):
    
    xml="""
      <actions version="0.0">
        <action>
          <id>vm-terminate-0-test02</id>
          <parameters>
            <terminate-instance>
              <instance>"""+vmName+"""</instance>
            </terminate-instance>
          </parameters>
        </action>
        <action>
          <id>vm-terminate-1-test02</id>
          <parameters>
            <terminate-instance>
              <instance>"""+vmName+"""-0</instance>
            </terminate-instance>
          </parameters>
        </action>
        <action>
          <id>vm-terminate-2-test02</id>
          <parameters>
            <terminate-instance>
              <instance>"""+vmName+"""-1</instance>
            </terminate-instance>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
    clients={}#seems that queering information such as if a VM is around or
      #not sometimes lags behind, by forcing a re-initalization of clients 
      #it seems to help this
    vm=openstack_executor.action_executor_funcs.getVM(osc,clients,vmName)
    vm0=openstack_executor.action_executor_funcs.getVM(osc,clients,vmName+"-0")
    vm1=openstack_executor.action_executor_funcs.getVM(osc,clients,vmName+"-1")
    assert vm is None
    assert vm0 is None
    assert vm1 is None
class TestCreateVMWithUserData(unittest.TestCase):
  def test_00__createVM(self):
    """Tests the creation of a VM with supplied user data
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>vm-create</id>
          <parameters>
            <create-instance>
              <name>"""+vmName+"""</name>
              <flavor>"""+flavor+"""</flavor>
              <instance-boot-source>
                <image>"""+imageName+"""</image>
              </instance-boot-source>
              <key-name>thekey</key-name>
              <post-creation-script>test_cloud_init.yaml</post-creation-script>
              <already-exists>overwrite</already-exists>
            </create-instance>
          </parameters>
        </action>
      </actions>
    """
    options.path=os.path.dirname(__file__)
    openstack_executor.run(xml,options)
    clients={}#seems that queering information such as if a VM is around or
      #not sometimes lags behind, by forcing a re-initalization of clients 
      #it seems to help this
    #vm=openstack_executor.action_executor_funcs.getVM(osc,clients,vmName)
    #assert openstack_executor.action_executor_funcs.isActive(vm)
if __name__=="__main__":
  unittest.main()