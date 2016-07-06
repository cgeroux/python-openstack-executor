#!/usr/bin/env python
import unittest
from lxml import etree

from openstack_executor.Action import *
def instanceTerminateStub(parameters,clients):
  clients["nova"]=None

class TestClassActionMethods(unittest.TestCase):
  """Note that the function names indicate the function call order.
  
  This is because the functions are called in the order indicated by standard
  string ordering. Thus the test_01 is used to specify it should be run before
  test_02 etc.
  
  Note: it seems that the setup objects are unique for each test and state 
  changes made by one test are not shared between tests. Making ordering much 
  less important.
  """
  
  def setUp(self):
    #create actions of testing
    
    xmlActionStr= '''
      <action>
        <ID>backup-test-one-dep</ID>
        <dependencies>
          <dependency>VM-termination</dependency>
        </dependencies>
        <parameters>
          <instance-terminate>
            <instance-name>test</instance-name>
          </instance-terminate>
        </parameters>
      </action>'''
    xmlAction=etree.fromstring(xmlActionStr)
    self.actionOneDep=Action(xmlAction)
    #print(dir(Action))
    Action.exeFuncs={"instance-terminate":instanceTerminateStub}
  def test_getID(self):
    
    #check we got correct ID
    self.assertEqual(self.actionOneDep.getID(),"backup-test-one-dep")
  def test_getDependencies(self):
    
    #check we got correct Dependencies
    expectedDependencies=["VM-termination"]
    self.assertEqual(self.actionOneDep.getDependencies(),expectedDependencies)
  def test_allDependenciesMetFalse(self):
    
    #check that dependencies not met
    self.assertEqual(self.actionOneDep.allDependenciesMet(),False)
  def test_allDependenciesMetTrue(self):
    
    #mark dependency as satisfied
    self.actionOneDep.setDependencyAsSatisfied("VM-termination")
    
    #check that dependencies are met
    self.assertEqual(self.actionOneDep.allDependenciesMet(),True)
  def test_executedAfterDependenciesMet(self):
    
    #mark dependency as satisfied
    self.actionOneDep.setDependencyAsSatisfied("VM-termination")
    
    #since all dependencies should have been met, did it execute
    self.assertEqual(self.actionOneDep.executed,True)
  def test_signalDependancySatisfied(self):
    
    def signalFunction(dependent,dependency):
      
      #check we have the specified dependent
      self.assertEqual(dependent,"test")
      
      #check we have the correct dependency
      self.assertEqual(dependency,"backup-test-one-dep")
    
    self.actionOneDep.addDependent("test")
    
    self.actionOneDep.setSignalDependencyFunc(signalFunction)
    
    #mark dependency as satisfied, should cause action to execute
    #and signal to dependents it has been completed
    self.actionOneDep.setDependencyAsSatisfied("VM-termination")
  def test_setClientInExecFunc(self):
    self.actionOneDep.execute()
    self.assertTrue("nova" in Action.clients.keys())
if __name__=="__main__":
  unittest.main()