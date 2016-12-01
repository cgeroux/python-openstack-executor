import string

def validateHostName(hostname):
  """Throws an Exception if the given hostname is not valid
    
    source:
    https://en.wikipedia.org/wiki/Hostname#Restrictions_on_valid_host_names
    
    1) must be under 253 characters
    2) each label (seperated by ".") must be between 1 and 63 characters long
    3) each label must contain only ASCII letters 'a' - 'Z' (case-insensitive)
      , '0' - '9', and '-'
    4) labels must not start or end with a '-'
    5) must be case-insensitive (i.e. will convert upper case to lower case)
  """
  
  allowed=set(string.ascii_lowercase+string.digits+"-"+string.ascii_uppercase)
  
  #1) check for overall length
  if(len(hostname)>252):
    raise Exception("hostname \""+hostname+"\" is longer than 253 characters")
  
  labels=hostname.split(".")
  
  for label in labels:
    
    #2) check for length of label
    if not (len(label) <= 63 and len(label) >= 1):
      raise Exception("hostname label \""+label+"\" is "+str(len(label))
      +" characters long which is not between 1 and 63 characters long")
    
    #3) check for invalid characters
    if not (set(label) <= allowed):
      raise Exception("label \""+label
        +"\" in hostname \""+hostname
        +"\" contains characters which are not allowed, \""
        +str(set(label)-allowed)+"\"")
    
    #4) must not start with a '-'
    if label[0]=='-':
      raise Exception("label \""+label
      +"\" in hostname \""+hostname
      +"\" starts with a '-' which is not allowed")
