import os
import novaclient.client as nvclient
nvAPIVersion="2.0"
import cinderclient.client as ciclient
ciAPIVersion="2"
import glanceclient.client as glclient
glAPIVersion="1"
import keystoneclient.client as ksclient
ksAPIVersion="3"

from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient import client

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
  #make sure there is a cinder client
  if "keystone" not in clients.keys():
    
    #create keystone client
    clients["keystone"]=createKeyStoneClient(clients)
  if clients["keystone"]==None:
    
    #create keystone client
    clients["keystone"]=createKeyStoneClient(clients)
def ensureGlanceClient(clients):
  
  ensureKeyStoneClient(clients)

  #make sure there is a glance client
  if "glance" not in clients.keys():
    
    #create glance client
    clients["glance"]=createGlanceClient(clients)
  if clients["glance"]==None:
    
    #create glance client
    clients["glance"]=createGlanceClient(clients)
def ensureSession(clients):
  #make sure there is a cinder client
  if "session" not in clients.keys():
    
    #create keystone client
    clients["session"]=createSession()
  if clients["session"]==None:
    
    #create keystone client
    clients["session"]=createSession()
def createSession():
  auth=v3.Password(auth_url=os.environ['OS_AUTH_URL'],
    username=os.environ['OS_USERNAME'],
    password=os.environ['OS_PASSWORD'],
    project_id=os.environ['OS_PROJECT_ID'],
    user_domain_name=os.environ['OS_USER_DOMAIN_NAME'])
  return session.Session(auth=auth)
def createKeyStoneClient(clients):
  ensureSession(clients)
  return ksclient.Client(ksAPIVersion,session=clients["session"])
def createNovaClient(clients):
  ensureSession(clients)
  return nvclient.Client(nvAPIVersion,session=clients["session"])
def createCinderClient(clients):
  ensureSession(clients)
  return ciclient.Client(ciAPIVersion,session=clients["session"])
def createGlanceClient(clients):
  ensureKeyStoneClient(clients)
  return glclient.Client(glAPIVersion,session=clients["session"])
    #,endpoint=clients["keystone"].service_catalog.url_for(service_type="image"
    #,endpoint_type="publicURL")
    #,token=clients["keystone"].auth_token)
