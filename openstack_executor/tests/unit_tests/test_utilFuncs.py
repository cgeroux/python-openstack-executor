#!/usr/bin/env python
import unittest
from openstack_executor.utilFuncs import *

class TestUtilFuncs(unittest.TestCase):
  def test_validateHostNameGood(self):
    validateHostName("test")#shouldn't raise an exception
  def test_validateHostNameHyphen(self):
    self.assertRaises(Exception,validateHostName,"-test")
  def test_validateHostNameTooLongLabel(self):
    self.assertRaises(Exception,validateHostName
      ,"asdfhnasdfqwefasdfqwefasdfqsdfasdfasdfhnasdfqwefasd"
      +"fqwefasdfqasdfsdfasdf.a")
  def test_validateHostNameTooShortLabel(self):
    self.assertRaises(Exception,validateHostName,"asdf..asdf")
  def test_validateHostNameBadCharacters(self):
    self.assertRaises(Exception,validateHostName,"as$df.asdf.asdf")
if __name__=="__main__":
  unittest.main()