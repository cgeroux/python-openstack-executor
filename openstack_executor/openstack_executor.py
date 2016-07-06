from __future__ import print_function

__version__ = "0.0.0"

import optparse as op
from lxml import etree
import os
from .ActionManager import ActionManager

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
  
  #validate against schema
  schema.assertValid(tree)
  
  #check to see if the environment has the expected variables
  envVars=os.environ.keys()
  requiredVars=["OS_AUTH_URL","OS_USERNAME","OS_PASSWORD","OS_TENANT_NAME"
    ,"OS_REGION_NAME"]
  for var in requiredVars:
    
    if( var not in envVars):
      
      #check to see if there is a mapping from v3 to v2
        raise Exception("environment variable \""+var
          +"\" not found, did you source the cloud *-openrc.sh "
          +"file and is it version 2 (v2)?")
  
  #Parse XML Actions
  xmlActions=tree.getroot()
  actionManager=ActionManager(xmlActions)
  
  #perform the actions
  actionManager.performActions()
  
  #create the nova client
  #nova=nvclient.Client(nvAPIVersion,auth_url=env['OS_AUTH_URL']
  #  ,username=env['OS_USERNAME'],api_key=env['OS_PASSWORD']
  #  ,project_id=env['OS_TENANT_NAME'],region_name=env['OS_REGION_NAME'])
