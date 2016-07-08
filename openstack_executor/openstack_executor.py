from __future__ import print_function

__version__ = "1.0.0"

import optparse as op
from lxml import etree
import os
from .ActionManager import ActionManager

authVersion="2"#default version is 2

class MissingEnvVariable(Exception):
  pass

def addParserOptions(parser):
  """Adds command line options
  """
  
  pass
def parseOptions():
  """Parses command line options
  
  """
  
  parser=op.OptionParser(usage="Usage: %prog [options] SETTINGS.xml"
    ,version="%prog 1.0",description="Creates a backup image of the "
    +"specified OpenStack VM and downloads it to your local machine")
  
  #add options
  addParserOptions(parser)
  
  #parse command line options
  return parser.parse_args()
def main():
  
  #parse command line options
  (options,args)=parseOptions()
  
  #check we got the expected number of arguments
  if (len(args)!=1):
    raise Exception("Expected an xml settings file.")
  
  #load schema to validate against
  schemaFileName=os.path.join(os.path.dirname(__file__),"xmlSchema/actions.xsd")
  schema=etree.XMLSchema(file=schemaFileName)
  
  #parse xml file
  tree=etree.parse(args[0])
  
  #strip out any comments in xml
  comments=tree.xpath('//comment()')
  for c in comments:
    p=c.getparent()
    p.remove(c)
  
  #validate against schema
  schema.assertValid(tree)
  
  #check to see if the environment has the expected variables
  envVars=os.environ.keys()
  requiredVarsV2=["OS_AUTH_URL","OS_USERNAME","OS_PASSWORD","OS_REGION_NAME", "OS_TENANT_NAME"]
  requiredVarsV3=["OS_AUTH_URL","OS_USERNAME","OS_PASSWORD","OS_PROJECT_NAME","OS_USER_DOMAIN_NAME"]
  
  global authVersion
  
  #check for version 2 vars
  try:
    for var in requiredVarsV2:
      
      if( var not in envVars):
        raise MissingEnvVariable(var)
    
    authVersion="2"
  except MissingEnvVariable:
    
    #check for version 3 vars
    for var in requiredVarsV3:
      
      if( var not in envVars):
        raise MissingEnvVariable("Missing environment variables for "
          +"both v2 and v3 authentication methods, did you source your "
          +"*-openrc.sh file?")
    authVersion="3"
  
  #Parse XML Actions
  xmlActions=tree.getroot()
  actionManager=ActionManager(xmlActions)
  
  #perform the actions
  actionManager.performActions()
  