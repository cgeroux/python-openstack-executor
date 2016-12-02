import os
import novaclient.client as nvclient
nvAPIVersion="2.0"
import cinderclient.client as ciclient
ciAPIVersion="2"
import glanceclient.client as glclient
glAPIVersion="1"
import keystoneclient.client as kclient
ksAPIVersion="2"

def ensureNovaClient(clients):
  #make sure there is a nova client
  if "nova" not in clients.keys():
    
    #create nova client
    clients["nova"]=createNovaClient(clients)
  if clients["nova"]==None:
    
    #create nova client
    clients["nova"]=createNovaClient(clients)
def ensureCinderClient(clients):
  #make sure there is a cinder client
  if "cinder" not in clients.keys():
    
    #create cinder client
    clients["cinder"]=createCinderClient(clients)
  if clients["cinder"]==None:
    
    #create cinder client
    clients["cinder"]=createCinderClient(clients)
def ensureKeyStoneClient(clients):
  #make sure there is a KeyStone client
  if "keystone" not in clients.keys():
    
    #create keystone client
    clients["keystone"]=createKeyStoneClient()
  if clients["keystone"]==None:
    
    #create keystone client
    clients["keystone"]=createKeyStoneClient()
def ensureGlanceClient(clients):
  
  ensureKeyStoneClient(clients)

  #make sure there is a glance client
  if "glance" not in clients.keys():
    
    #create glance client
    clients["glance"]=createGlanceClient(clients)
  if clients["glance"]==None:
    
    #create glance client
    clients["glance"]=createGlanceClient(clients)
def createNovaClient(clients):
  return nvclient.Client(nvAPIVersion
    ,auth_url=os.environ['OS_AUTH_URL']
    ,username=os.environ['OS_USERNAME']
    ,api_key=os.environ['OS_PASSWORD']
    ,project_id=os.environ['OS_TENANT_NAME']
    ,region_name=os.environ['OS_REGION_NAME'])
def createCinderClient(clients):
  return ciclient.Client(ciAPIVersion
    ,auth_url=os.environ['OS_AUTH_URL']
    ,username=os.environ['OS_USERNAME']
    ,api_key=os.environ['OS_PASSWORD']
    ,project_id=os.environ['OS_TENANT_NAME']
    ,region_name=os.environ['OS_REGION_NAME'])
def createKeyStoneClient():
  ksclient=kclient.Client(ksAPIVersion
    ,username=os.environ['OS_USERNAME']
    ,password=os.environ['OS_PASSWORD']
    ,tenant_name=os.environ['OS_TENANT_NAME']
    ,auth_url=os.environ['OS_AUTH_URL']
    ,region_name=os.environ['OS_REGION_NAME']
  )
  
  ksclient.authenticate()
  return ksclient
def createGlanceClient(clients):
  ensureKeyStoneClient(clients)
  return glclient.Client(glAPIVersion
    ,endpoint=clients["keystone"].service_catalog.url_for(service_type="image"
    ,endpoint_type="publicURL")
    ,token=clients["keystone"].auth_token)
def getProjectID(clients):
  ensureKeyStoneClient(clients)
  return clients["keystone"].tenant_id
def getUserID(clients):
  ensureKeyStoneClient(clients)
  return clients["keystone"].user_id
