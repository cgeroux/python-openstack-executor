#!/usr/bin/env python
import unittest
from lxml import etree

from openstack_executor.ActionManager import *

class TestClassActionManagerMethods(unittest.TestCase):
  #def setUp(self):
  #  #create actions of testing
  #  
  #  xmlActionManagerStr= '''
  #    <actions>
  #      <action>
  #        <ID>backup-test-one-dep</ID>
  #        <dependencies>
  #          <dependency>VM-termination</dependency>
  #        </dependencies>
  #      </action>
  #      <action>
  #        <ID>VM-termination</ID>
  #      </action>
  #    </actions>'''
  #  xmlActionManager=etree.fromstring(xmlActionManagerStr)
  #  self.actionManager=ActionManager(xmlActionManager)
  def test_MissingDependencyException(self):
    xmlActionManagerStr= '''
      <actions>
        <action>
          <ID>backup-test-one-dep</ID>
          <dependencies>
            <dependency>VM-termination</dependency>
          </dependencies>
        </action>
      </actions>'''
    xmlActionManager=etree.fromstring(xmlActionManagerStr)
    self.assertRaises(MissingActionDepedency, ActionManager,xmlActionManager)
  def test_DuplicateActionID(self):
    xmlActionManagerStr= '''
      <actions>
        <action>
          <ID>backup-test-one-dep</ID>
        </action>
        <action>
          <ID>backup-test-one-dep</ID>
        </action>
      </actions>'''
    xmlActionManager=etree.fromstring(xmlActionManagerStr)
    self.assertRaises(DuplicateActionID, ActionManager,xmlActionManager)
  def test_PerformingActions(self):
    xmlActionManagerStr= '''
      <actions>
        <action>
          <ID>backup-test-one-dep</ID>
        </action>
      </actions>'''
    xmlActionManager=etree.fromstring(xmlActionManagerStr)
    actionManager=ActionManager(xmlActionManager)
    actionManager.performActions()
if __name__=="__main__":
  unittest.main()