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
  flavor="p4-3gb"
else:
  raise Exception("couldn't figure out which cloud you are using based on "
    +"OS_AUTH_URL="+os.environ['OS_AUTH_URL'])

vmName="openstack-executor-integration-test-vm"

class TestVMCreation(unittest.TestCase):
  #TODO: add tests for functions:
  #  downloadImage
  #  attachVolume
  #  uploadImage
  #  createVolume (not from an image)
  #  addSecurityGroup
  #  
  # In addition I could also exercise the various functions under different
  # conditions e.g. overwriting something, skipping etc.
  def test_00_volumeCreateFromImage(self):
    """
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>create-root-volume</id>
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
  def test_01_imageCreateFromVolume(self):
    """
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>create-image-from-volume</id>
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
  def test_02_deleteImage(self):
    """
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>delete-image</id>
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
  def test_03_bootVMFromVolume(self):
    """Tests the creation of a VM
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
                <volume>"""+vmName+"""-root</volume>
              </instance-boot-source>
              <already-exists>overwrite</already-exists>
            </create-instance>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
  def test_04_addIPToVM(self):
    """Tests allocating an IP to project and assigning it to a VM
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>add-ip</id>
          <parameters>
            <associate-floating-ip>
              <instance>"""+vmName+"""</instance>
            </associate-floating-ip>
          </parameters>
        </action>  
      </actions>
    """
    
    openstack_executor.run(xml,options)
  def test_05_releaseIP(self):
    """Tests releasing a floating IP associated with a given VM
    """
    
    xml="""
      <actions version="0.0">
        <action>
          <id>release-ip</id>
          <parameters>
            <release-floating-ip>
              <instance>"""+vmName+"""</instance>
            </release-floating-ip>
          </parameters>
        </action>  
      </actions>
    """
    
    openstack_executor.run(xml,options)
  def test_06_terminateVM(self):
    
    xml="""
      <actions version="0.0">
        <action>
          <id>vm-terminate</id>
          <parameters>
            <terminate-instance>
              <instance>"""+vmName+"""</instance>
            </terminate-instance>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
  def test_07_deleteVolume(self):
    
    xml="""
      <actions version="0.0">
        <action>
          <id>delete-root-volume</id>
          <parameters>
            <delete-volume>
              <volume>"""+vmName+"""-root</volume>
            </delete-volume>
          </parameters>
        </action>
      </actions>
    """
    
    openstack_executor.run(xml,options)
if __name__=="__main__":
  unittest.main()