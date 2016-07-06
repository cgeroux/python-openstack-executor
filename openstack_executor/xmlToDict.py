def xmlToDict(xml):
  """Converts an xml tree to a nested python dictionary
  
  Note that it ignores attributes and flattens elements with 
  duplicate tags keeping the value of the last tag parsed.
  It also assumes that there is no mixture between xml elements 
  and text i.e. assumes a form like:
  
  <element0>
    <element-0-0>
      <element-0-0-0>text</element-0-0-0>
    </element-0-0>
    <element-0-1>text</element-0-1>
  </element0>
  
  and not 
  
  <element0>
    <element-0-0>text
      <element-0-0-0>text</element-0-0-0>
    </element-0-0>
    <element-0-1>text</element-0-1>
    text
  </element0>
  """
  
  theXMLDict={}
  
  for element in xml:
    
    if len(element)==0:#no sub elements
      theXMLDict[element.tag]=element.text
    else:#if sub-elements call recursively
      theXMLDict[element.tag]=xmlToDict(element)
  
  return theXMLDict