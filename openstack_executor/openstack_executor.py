from __future__ import print_function

__version__ = "0.0.0"

import optparse as op
from lxml import etree
#from lxml import objectify
#from os import environ as env
#import novaclient.client as nvclient
#nvAPIVersion="2.0"#can't seem to find a good way to get the version number
#import novaclient

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
  
  #parse xml file
  tree=etree.parse(args[0])
  
  #load schema to validate against
  schema=etree.XMLSchema(file="./settings.xsd")
  
  #validate against schema
  schema.assertValid(tree)
  
  #check to see if the environment has the expected variables
  envVars=env.keys()
  requiredVars=["OS_AUTH_URL","OS_USERNAME","OS_PASSWORD","OS_TENANT_NAME"
    ,"OS_REGION_NAME"]
  for var in requiredVars:
    
    if( var not in envVars):
      raise Exception("environment variable \""+var
        +"\" not found, did you source the cloud *-openrc.sh file?")
  
  #Parse XML Actions
  xmlActions=tree.getroot()
  actionManager=ActionManager(xmlActions)
  
  #create the nova client
  #nova=nvclient.Client(nvAPIVersion,auth_url=env['OS_AUTH_URL']
  #  ,username=env['OS_USERNAME'],api_key=env['OS_PASSWORD']
  #  ,project_id=env['OS_TENANT_NAME'],region_name=env['OS_REGION_NAME'])
