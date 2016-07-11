#!/usr/bin/env python
import unittest
from lxml import etree

#this imports the installed version
from openstack_executor.ActionManager import *

order=0
step0Order=None
step1Order=None
def step0(parameters,clients):
  global step0Order
  global order
  step0Order=order
  order=order+1
def step1(parameters,clients):
  global step1Order
  global order
  step1Order=order
  order=order+1

class TestClassActionManagerMethods(unittest.TestCase):
  #def setUp(self):
  #  #create actions of testing
  #  
  #  xmlActionManagerStr= '''
  #    <actions>
  #      <action>
  #        <id>backup-test-one-dep</id>
  #        <dependencies>
  #          <dependency>VM-termination</dependency>
  #        </dependencies>
  #      </action>
  #      <action>
  #        <id>VM-termination</id>
  #      </action>
  #    </actions>'''
  #  xmlActionManager=etree.fromstring(xmlActionManagerStr)
  #  self.actionManager=ActionManager(xmlActionManager)
  def test_MissingDependencyException(self):
    xmlActionManagerStr= '''
      <actions>
        <action>
          <id>backup-test-one-dep</id>
          <dependencies>
            <dependency>VM-termination</dependency>
          </dependencies>
        </action>
      </actions>'''
    xmlActionManager=etree.fromstring(xmlActionManagerStr)
    self.assertRaises(Exception, ActionManager,xmlActionManager)
  def test_DuplicateActionID(self):
    xmlActionManagerStr= '''
      <actions>
        <action>
          <id>backup-test-one-dep</id>
        </action>
        <action>
          <id>backup-test-one-dep</id>
        </action>
      </actions>'''
    xmlActionManager=etree.fromstring(xmlActionManagerStr)
    self.assertRaises(Exception, ActionManager,xmlActionManager)
  def test_PerformingActionsInOrder(self):
    xmlActionManagerStr= '''
      <actions>
        
        <action>
          <id>step0</id>
          <parameters>
            <step0>
            </step0>
          </parameters>
          <dependencies></dependencies>
        </action>
        
        <action>
          <id>step1</id>
          <parameters>
            <step1>
            </step1>
          </parameters>
          <dependencies>
            <dependency>step0</dependency>
          </dependencies>
        </action>
        
      </actions>'''
    xmlActionManager=etree.fromstring(xmlActionManagerStr)
    actionManager=ActionManager(xmlActionManager)
    Action.exeFuncs={"step0":step0,"step1":step1}#override exeFuncs set in constructor of ActionManager
    actionManager.performActions()
    self.assertEqual(step0Order,0)
    self.assertEqual(step1Order,1)
if __name__=="__main__":
  unittest.main()