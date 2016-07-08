from lxml import etree
from .Action import Action

class ActionManager(object):
  """
  """
  
  def __init__(self,xmlActions):
    """Given the top level actions node initializes a dictionary of actions
    """
    
    #set the executor functions to use
    from .action_executor_funcs import exeFuncs
    Action.exeFuncs=exeFuncs
    
    self.actions={}
    self.initialActions=[]
    for xmlAction in xmlActions:
      
      if not (xmlAction.tag is etree.Comment):
      
        #create an action
        action=Action(xmlAction)
        
        #set function to signal dependency complete
        action.setSignalDependencyFunc(self._signalDependencyComplete)
        
        #if action already there, update its XML?
        if action.getID() in self.actions.keys():
          
          #check to see if it has XML already set
          if self.actions[action.getID()].hasXML():
            raise Exception("Action with duplicate ID=\""+str(action.getID())
              +"\" IDs must be unique.")
          
          #some actions are created before their XML is parsed (e.g. actions 
          #mentioned previously as a dependency)
          self.actions[action.getID()].setXML(xmlAction)
        
        else:#new action
          #save the action to the actions dictionary
          self.actions[action.getID()]=action
        
        #Set dependants
        for dependency in action.getDependencies():
          
          #if there is already an action
          if dependency in self.actions.keys():
            
            #add a dependent
            self.actions[dependency].addDependent(action.getID())
          
          #create a new action to be defined later
          else:
            self.actions[dependency]=Action()
        
        #if action has no dependencies it is an initial action
        if len(action.getDependencies())==0:
          self.initialActions.append(action.getID())
    
    #check that all actions are defined (no dependencies that aren't given)
    self._checkAllActionsDefined()
  def _checkAllActionsDefined(self):
    for key,action in self.actions.items():
      
      #if action has not been given XML it is not defined
      if not action.hasXML():
        raise Exception("Action \""+str(key)+"\" given for a dependency but not defined.")
  def _signalDependencyComplete(self,dependent,dependency):
    """signal to the dependent that the dependency has been satisfied
    """
    
    self.actions[dependent].setDependencyAsSatisfied(dependency)
  def performActions(self):
    for action in self.initialActions:
      self.actions[action].execute()
