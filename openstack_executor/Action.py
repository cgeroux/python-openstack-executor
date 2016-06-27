class SignalDependencyFunctionNotSet(Exception):
  pass

class Action(object):
  
  def __init__(self,xmlAction=None):
    """Initialize the action
    """
    
    self._XML=xmlAction
    self._dependents=[]
    self._executed=False
    self._setSignalDependencyFunc=None
  def hasXML(self):
    """Indicate if the action has XML set or not
    """
    
    if self._XML==None:
      return False
    else:
      return True
  def setXML(self,xmlAction):
    """Set the XML which defines the action
    """
    
    #save xml settings
    self._XML=xmlAction
  def setSignalDependencyFunc(self,f):
    """Set the function which is used to signal to dependants that a dependency
    has been met.
    
    This function should accept two strings. First string will be the ID of the
    dependant which is being signalled, the second ID will be for the current
    action.
    """
    
    self._signalDependencyFunc=f
  def getID(self):
    """ returns the action ID as specified in the XML
    """
    
    #if we haven't yet parsed out the ID from the do so now
    if not hasattr(self,'_ID'):
      self._ID=self._XML.find("ID").text
    return self._ID
  def getDependencies(self):
    """Returns a list of action IDs which this action is dependent on
    """
    
    if not hasattr(self,"_dependencies"):
      xmlDependencies=self._XML.find("dependencies")
      dependencies={}
      if xmlDependencies!=None:
        for dependency in xmlDependencies:
          dependencies[dependency.text]=False
      self._dependencies=dependencies
    return self._dependencies.keys()
  def setDependencyAsSatisfied(self,dependencyID):
    """Indicates to the action that the dependency named by dependencyID has been satisfied.
    
    If all dependencies have been satisfied will execute the action.
    """
    
    #need to have parsed list of dependencies before hand
    #calling this function will make sure of it
    self.getDependencies()
    
    #make sure we have the specified dependency
    if dependencyID not in self._dependencies.keys():
      raise Exception("dependencyID, \""
        +dependencyID+"\" not in list of dependencies "
        +str(self._dependencies.keys()))
    
    #Set it as satisfied
    self._dependencies[dependencyID]=True
    
    #check to see if all dependencies are satisfied
    if(self.allDependenciesMet()):
      self.execute()
  def allDependenciesMet(self):
    """Returns True if all dependencies have been satisfied.
    """
    
    #need to have parsed list of dependencies before hand
    #calling this function will make sure of it
    self.getDependencies()
    
    #check for an unmet dependency
    for dependency in self._dependencies.values():
      if not dependency:
        return False
    
    #if no unmet dependencies return True
    return True
  def addDependent(self,dependent):
    """Adds an action which is dependent on this action.
    """
    
    self._dependents.append(dependent)
  def executed(self):
    """Returns true if this action has been executed.
    """
    
    return self._executed
  def execute(self):
    """Executes the action, often this will be called from 
    setDependencyAsSatisfied once all dependencies have been flagged as
    satisfied. However, if there are no dependencies this can and should be
    called directly.
    """
    
    if not self._executed:
      
      #TODO: execute the action here
      
      #once finished need to tell dependents we are done
      for dependent in self._dependents:
        if self._signalDependencyFunc==None:
          raise SignalDependencyFunctionNotSet("Dependency Signal function not set for action "+str(self.getID()))
        self._signalDependencyFunc(dependent,self.getID())
    
    self._executed=True
