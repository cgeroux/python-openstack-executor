from .Action import Action

class MissingActionDepedency(Exception):
  pass
class DuplicateActionID(Exception):
  pass
class ActionManager(object):
  def __init__(self,xmlActions):
    """Given the top level actions node initializes a dictionary of actions
    """
    
    self._actions={}
    self._initialActions=[]
    for xmlAction in xmlActions:
      
      #create an action
      action=Action(xmlAction)
      
      #if action already there, update its XML?
      if action.getID() in self._actions.keys():
        
        #check to see if it has XML already set
        if self._actions[action.getID()].hasXML():
          raise DuplicateActionID("Action with duplicate ID=\""+str(action.getID())
            +"\" IDs must be unique.")
        
        #some actions are created before their XML is parsed (e.g. actions 
        #mentioned previously as a dependency)
        self._actions[action.getID()].setXML(xmlAction)
      
      else:#new action
        #save the action to the actions dictionary
        self._actions[action.getID()]=action
      
      #Set dependants
      for dependency in action.getDependencies():
        
        #if there is already an action
        if dependency in self._actions.keys():
          
          #add a dependent
          self._actions[dependency].addDependent(action.getID())
        
        #create a new action to be defined later
        else:
          self._actions[dependency]=Action()
      
      #if action has no dependencies it is an initial action
      if len(action.getDependencies())==0:
        self._initialActions.append(action.getID())
      
    #check that all actions are defined (no dependencies that aren't given)
    self._checkAllActionsDefined()
  def _checkAllActionsDefined(self):
    for key,action in self._actions.items():
      
      #if action has not been given XML it is not defined
      if not action.hasXML():
        raise MissingActionDepedency("Action \""+str(key)+"\" given for a dependency but not defined.")
  def _signalDependencyComplete(self,dependent,dependency):
    """signal to the dependent that the dependency has been satisfied
    """
    
    self._actions[dependent].setDependencyAsSatisfied(dependency)
  def performActions(self):
    for action in self._initialActions:
      self._actions[action].execute()