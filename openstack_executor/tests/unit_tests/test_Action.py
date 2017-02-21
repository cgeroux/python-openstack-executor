#!/usr/bin/env python
import unittest
from lxml import etree

#this imports the installed version
from openstack_executor.Action import *
def instanceTerminateStub(parameters,clients,osc,options):
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
        <id>backup-test-one-dep</id>
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
    self.actionOneDep.setDependencyAsSatisfied("VM-termination"
      ,{"instance-terminate":instanceTerminateStub},{},None,None)
    
    #check that dependencies are met
    self.assertEqual(self.actionOneDep.allDependenciesMet(),True)
  def test_executedAfterDependenciesMet(self):
    
    #mark dependency as satisfied
    self.actionOneDep.setDependencyAsSatisfied("VM-termination"
      ,{"instance-terminate":instanceTerminateStub},{},None,None)
    
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
    self.actionOneDep.setDependencyAsSatisfied("VM-termination"
      ,{"instance-terminate":instanceTerminateStub},{},None,None)
  def test_setClientInExecFunc(self):
    clients={}
    self.actionOneDep.execute({"instance-terminate":instanceTerminateStub}
      ,clients,None,None)
    self.assertTrue("nova" in clients.keys())
if __name__=="__main__":
  unittest.main()