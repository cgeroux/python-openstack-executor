from __future__ import print_function
from lxml import etree
import sys
from .xmlToDict import xmlToDict

class Action(object):
  """
  """
  
  def __init__(self,xmlAction=None):
    """Initialize the action
    """
    
    self.XML=xmlAction
    self.dependents=[] 
    self.executed=False
    self.signalDependencyFunc=None
    self.parameters=None
    self.ID=None
    self.dependencies=None
    self.type=None
  def setXML(self,xmlAction):
    """Set the XML which defines the action
    """
    
    self.__init__(xmlAction)#TODO: should this re-initialize the object?
  def replaceInXML(self,strReplace):
    """
    """
    
    if self.hasXML():
      context=etree.iterwalk(self.XML,events=("end",))
      for event,node in context:
        if node.text!=None:
          tmp=node.text
          for key in strReplace:#TODO: is this the way we want to 
            #handle multiple replaces? This could cause unexpected 
            #behaviour depending on the order they are applied.
            tmp=tmp.replace(key,strReplace[key])
          node.text=tmp
  def setSignalDependencyFunc(self,f):
    """Set the function which is used to signal to dependants that a dependency
    has been met.
    
    This function should accept two strings. First string will be the ID of the
    dependant which is being signalled, the second ID will be for the current
    action.
    """
    
    self.signalDependencyFunc=f
  def setDependencyAsSatisfied(self,dependencyID,exeFuncs,clients,osc,options
    ,strReplace=None):
    """Indicates to the action that the dependency named by dependencyID has been satisfied.
    
    If all dependencies have been satisfied will execute the action.
    """
    
    #need to have parsed list of dependencies before hand
    #calling this function will make sure of it
    self.getDependencies()
    
    #make sure we have the specified dependency
    if dependencyID not in self.dependencies.keys():
      raise Exception("dependencyID, \""
        +dependencyID+"\" not in list of dependencies "
        +str(self.dependencies.keys()))
    
    #Set it as satisfied
    self.dependencies[dependencyID]=True
    
    #adjust xml if needed in case of renames of dependencies
    if strReplace!=None:
      sys.stdout.write("  Updating action \""+self.getID()
        +"\" by replacing the following dictionary keys with"
        +" their values in the action's XML:\n    "
        +str(strReplace)+" ...\n")
      sys.stdout.flush()
      self.replaceInXML(strReplace)
    
    #check to see if all dependencies are satisfied
    if(self.allDependenciesMet()):
      self.execute(exeFuncs,clients,osc,options,strReplace=strReplace)
  def getID(self):
    """ returns the action ID as specified in the XML
    """
    
    #if we haven't yet parsed out the ID from the do so now
    if self.ID==None:
      self.ID=self.XML.find("id").text
    return self.ID
  def getParameters(self):
    """
    """
    
    xmlParameters=self.XML.find("parameters")
    xmlParameterSpecific=xmlParameters[0]#get the action specific parameters
    result=xmlToDict(xmlParameterSpecific)
    return result
  def getType(self):
    """Returns the action type
    """
    
    if self.type==None:
      xmlParameters=self.XML.find("parameters")
      for parameter in xmlParameters:
        if not (parameter.tag is etree.Comment):
          self.type=parameter.tag
          break
    
    return self.type
  def getDependencies(self):
    """Returns a list of action IDs which this action is dependent on
    """
    
    if self.dependencies==None:
      xmlDependencies=self.XML.find("dependencies")
      dependencies={}
      if xmlDependencies!=None:
        for dependency in xmlDependencies:
          if not (dependency.tag is etree.Comment):
            dependencies[dependency.text]=False
      self.dependencies=dependencies
    
    return list(self.dependencies.keys())
  def addDependent(self,dependent):
    """Adds an action which is dependent on this action.
    """
    
    self.dependents.append(dependent)
  def execute(self,exeFuncs,clients,osc,options,strReplace=None):
    """Executes the action, often this will be called from 
    setDependencyAsSatisfied once all dependencies have been flagged as
    satisfied. However, if there are no dependencies this can and should be
    called directly.
    
    strReplace propagates any modifications needed in dependent actions.
    """
    
    if not self.executed:
      
      sys.stdout.write("Executing action \""+self.getID()+"\"\n")
      sys.stdout.flush()
      
      tmp=exeFuncs[self.getType()](self.getParameters(),clients,osc,options)
      if tmp!=None: 
        if strReplace!=None:#merge the two dictionaries
          strReplace.update(tmp)
        else:
          strReplace=tmp
      
      #once finished need to tell dependents we are done
      for dependent in self.dependents:
        if self.signalDependencyFunc==None:
          raise Exception("Dependency Signal function not set for action "+str(self.getID()))
        self.signalDependencyFunc(dependent,self.getID(),strReplace=strReplace)
      
      #indicate that action has been executed
      self.executed=True
  def hasXML(self):
    """Indicate if the action has XML set or not
    """
    
    if self.XML==None:
      return False
    else:
      return True
  def allDependenciesMet(self):
    """Returns True if all dependencies have been satisfied.
    """
    
    #need to have parsed list of dependencies before hand
    #calling this function will make sure of it
    self.getDependencies()
    
    #check for an unmet dependency
    for dependency in self.dependencies.values():
      if not dependency:
        return False
    
    #if no unmet dependencies return True
    return True
