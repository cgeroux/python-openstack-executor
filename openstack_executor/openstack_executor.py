from __future__ import print_function

__version__ = "1.1.0"

import optparse as op
from lxml import etree
import os
from .ActionManager import ActionManager

authVersion="2"#default version is 2
options=None

class MissingEnvVariable(Exception):
  pass

def addParserOptions(parser):
  """Adds command line options
  """
  
  group=op.OptionGroup(parser,title="Already Exists Behaviour",description="These options force a "
    +"global behaviour when ever an existing resource with the same name of "
    +"the one being created is encountered. For finner grained control use "
    +"the <already-exists> element in an specific action's parameters "
    +"element, (e.g. <create-instance>, <download-image> etc.).")
  
  group.add_option("--overwrite-all",action="store_const"
    ,dest="alreadyExistsGlobal",const="overwrite"
    ,help="Forces global overwrite behaviour, will overwrite existing "
    +"resource when encountered [not default].",default=None)
  group.add_option("--skip-all",action="store_const"
    ,dest="alreadyExistsGlobal",const="skip"
    ,help="Forces global skip behaviour, will skip creating a resource "
    +"when it already exists [not default].",default=None)
  group.add_option("--fail-all",action="store_const"
    ,dest="alreadyExistsGlobal",const="fail"
    ,help="Forces global fail behaviour, will throw an exception when "
    +"creating a resource when it already exists [not default]."
    ,default=None)
  parser.add_option_group(group)
def parseOptions():
  """Parses command line options
  
  """
  
  parser=op.OptionParser(usage="Usage: %prog [options] SETTINGS.xml"
    ,version="%prog "+__version__,description="Performs actions specified in the "
    +"SETTINGS.xml file. These actions could be create a VM, attach "
    +"volumes, associate Floating IP, terminate VM, create an image "
    +"from volume, etc. See example SETTINGS.xml likely located in a "
    +"directory like \"${HOME}/.local/lib/pythonX.Y/site-packages/"
    +"openstack_executor-1.0.0-py3.4.egg/openstack_executor/"
    +"example_action_xml_files\"")
  
  #add options
  addParserOptions(parser)
  
  #parse command line options
  return parser.parse_args()
def main():
  
  global options
  
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
  
  print("Authenticating against \""+os.environ["OS_AUTH_URL"]+"\"")
  
  #Parse XML Actions
  xmlActions=tree.getroot()
  actionManager=ActionManager(xmlActions)
  
  #perform the actions
  actionManager.performActions()
  