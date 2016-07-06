from __future__ import print_function
from .createOSClients import *
import time
import sys
import novaclient
import utilFuncs


OSCheckWaitTime=3#time to wait between polling OS to check for action 
  #completion in seconds
OSNumChecks=20#number of times to check for action completion

def instanceTerminate(parameters,clients):
  """Terminate an instance
  """
  
  ensureNovaClient(clients)
  
  sys.stdout.write("  Terminating instance \""+parameters["instance"]+"\" ")
  
  #get list of servers
  servers=clients["nova"].servers.list()
  serverToTerminate=None
  for server in servers:
    if server.name==parameters["instance"] or server.id==parameters["instance"]:
      serverToTerminate=server
      clients["nova"].servers.delete(serverToTerminate)
      break
  
  #if no server found
  if serverToTerminate==None:
    sys.stdout.write("\n    WARNING: No instance found with name or id \""
      +parameters["instance"]+"\". Nothing to terminate!\n")
    return
  
  #wait until action is completed
  serverPresent=True
  iter=0
  while serverPresent and iter<OSNumChecks:
    
    #is the instance still there?
    servers=clients["nova"].servers.list()
    found=False
    for server in servers:
      if server.id==serverToTerminate.id:
        found=True
        break
    
    #if server still there, lets wait
    if found:
      sys.stdout.write(".")
      sys.stdout.flush()
      #wait some amount of time before checking again
      time.sleep(OSCheckWaitTime)
    else:
      serverPresent=False
    
    #increment number of checks
    iter+=1
  
  #check that we haven't timed out
  if iter>=OSNumChecks and serverPresent:
    raise Exception("Timed out waiting for termination to complete.\n")
  
  #notify that termination has completed
  sys.stdout.write("\n    Termination completed.\n")
  return
def volumeCreateImage(parameters,clients):
  """Creates an image from a volume
  """
  
  ensureCinderClient(clients)
  ensureKeyStoneClient(clients)
  ensureGlanceClient(clients)
  
  #get the volume to image
  volumeToImage=None
  volumes=clients["cinder"].volumes.list()
  for volume in volumes:
    if volume.name==parameters["volume"] or volume.id==parameters["volume"]:
      volumeToImage=volume
  
  if volumeToImage==None:
    raise Exception("volume with name or id \""+parameters["volume"]+"\" not found!")
  
  #check if there is an image with that name already
  #technically there can be multiple images with the same name
  #but that makes things complicated
  images=clients["glance"].images.list(owner=clients["keystone"].tenant_id)
  for image in images:
    if(image.name==parameters["image-name"]):
      raise Exception("an image with the name \""+str(parameters["image-name"])
        +"\" already exists.")
  
  sys.stdout.write("  Creating image \""+parameters["image-name"]
    +"\" from volume \""+parameters["volume"]+"\" ")
  
  #create image from volume
  force=True#not sure what this does, a few tests don't indicate a 
    #difference between True of False
  image_name=parameters["image-name"]
  container_format='bare'
  if "format" in parameters.keys():
    disk_format=parameters["format"]
  else:
    disk_format="qcow2"
  volumeToImage.upload_to_image(force,image_name,container_format,disk_format)
  
  #check that the image has been created
  imageNotActive=True
  iter=0

  #assume rate of creation, this is based on a 10Gb
  #volume with 805Mb of data taking 57s to create an image from
  gbPers=0.01
  
  #estimate how many times we will check based on the size of the volume
  #this should be a significant overestimate
  numChecks=int(float(volumeToImage.size)/gbPers/float(OSCheckWaitTime))
  while imageNotActive and iter<numChecks:
    
    images=clients["glance"].images.list(owner=clients["keystone"].tenant_id)
    for image in images:
      if image.name==parameters["image-name"]:
        if image.status=="active":
          imageNotActive=False
          break
    
    #wait some amount of time before checking again
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
      
  if imageNotActive:
    raise Exception("Timed out waiting for image creation to complete.\n")
  
  #notify that image creation has completed
  sys.stdout.write("\n    Image creation completed.\n")
  return
def downloadImage(parameters,clients):
  """Downloads an image to the current working directory
  """
  
  ensureKeyStoneClient(clients)
  ensureGlanceClient(clients)
  
  #check if we have a match-owner option
  matchOwner=True
  if "public-image" in parameters.keys():
    if parameters["public-image"] in ["true",1]:
      matchOwner=False#don't match owner if it is a public image as it won't find it
  
  if matchOwner:
    images=clients["glance"].images.list(owner=clients["keystone"].tenant_id)
  else:
    images=clients["glance"].images.list()
  
  imageToDownLoad=None
  for image in images:
    if(image.name==parameters["image"] or image.id==parameters["image"]):
      imageToDownLoad=image
      break
  
  #download image
  fileName=parameters["file-name"]+"."+imageToDownLoad.disk_format
  sys.stdout.write("  Downloading image \""+parameters["image"]
    +"\" to file \""+fileName+"\" \n")
  sys.stdout.flush()
  
  
  imageFile=open(fileName,'w+')
  chunks=imageToDownLoad.data()
  imageSize=chunks.length
  downloaded=0
  for chunk in chunks:
    downloaded+=len(chunk)
    imageFile.write(chunk)
    percent=float(downloaded)/float(imageSize)*100.0
    sys.stdout.write("    {0:.1f}%\r".format(percent))
    sys.stdout.flush()
      
  #notify that image download has completed
  sys.stdout.write("\n    Image download completed.\n")
  return
def instanceCreate(parameters,clients):
  """Creates an instance
  """
  
  ensureNovaClient(clients)
  
  #check that instance name is a valid hostname
  utilFuncs.validateHostName(parameters["name"])
  
  #use lower case host names for consistency as they should be case insensitive
  hostname=parameters["name"].lower()
  
  sys.stdout.write("  Creating instance \""+hostname+"\" ")
  
  #get a network to attach to
  if "network" in parameters.keys():
    
    #get user supplied network name
    networkName=parameters["network"]
    
    #verify that it is in the list of available networks
    networks=clients["nova"].networks.list()
    networkFound=False
    for network in networks:
      if networkName==network.human_id:
        networkFound=True
        break
    
    if not networkFound:
      raise Exception("the supplied network name \""+networkName
        +"\" not found in available networks, check that it is correct.")
  else:#other wise try to pick one
    
    #get a list of potential networks
    networks=clients["nova"].networks.list()
    networkNames=[]
    for network in networks:
      
      #if suffix of network name is "_network" it is a network of the tenant
      if network.human_id[len(network.human_id)-8:]=="_network":
        networkNames.append(network.human_id)
    
    #too many to choose from
    if len(networkNames)>1:
      raise Exception("multiple networks to choose from "
        +str(networkNames)+" select one by specifying in a \"network\" xml "
        +"element under the \"instance-create\" element.")
        
    #none to choose from
    if len(networkNames)<1:
      raise Exception("no networks found if there is one available that wasn't "
        +"detected specify it in a \"network\" xml element under the "
        +"\"instance-create\" element.")
    
    networkName=networkNames[0]
  net=clients["nova"].networks.find(label=networkName)
  nics=[{'net-id':net.id}]
  
  #ensure flavor is in list of available flavors
  flavors=clients["nova"].flavors.list()
  flavorNames=[]
  for flavor in flavors:
    flavorNames.append(flavor.name)
  if parameters["flavor"] not in flavorNames:
    raise Exception("the specified flavor name \""+parameters["flavor"]
      +"\" not in list of available flavors "+str(flavorNames))
  flavor=clients["nova"].flavors.find(name=parameters["flavor"])
  
  #TODO: allow creating multiple instances
  #parameters["instance-count"]
  
  #TODO: add ability to supply a user data file
  
  #TODO: add ability to specify key-pair
  #print(clients["nova"].servers.create.__doc__)
  
  #boot from a volume
  if "volume" in parameters["instance-boot-source"].keys():
    
    #check to see if we already have an instance with that name
    try:
      clients["nova"].servers.find(name=hostname)
    except novaclient.exceptions.NotFound:
      pass #name not used, this is good
    else:
      raise Exception("already an instance present with name \""+hostname+"\"")
    
    #get volume id
    volumes=clients["nova"].volumes.list()
    volumeFound=False
    for volume in volumes:
      
      #if this is the volume to boot from
      if (volume.name==parameters["instance-boot-source"]["volume"] 
        or parameters["instance-boot-source"]["volume"]==volume.id):
        volumeID=volume.id
        volumeFound=True
    
    #if we didn't find the volume
    if not volumeFound:
      raise Exception("no volume found with name or id \""
        +parameters["instance-boot-source"]["volume"]+"\"")
    
    #Create the instance
    blockDeviceMapping={'vda':volumeID}
    sys.stdout.write("\n    Booting from a volume ")
    instance=clients["nova"].servers.create(
      name=hostname
      ,block_device_mapping=blockDeviceMapping
      ,flavor=flavor
      ,image=None
      ,nics=nics
      )
  else:
    #TODO: implement other methods for creating a VM
    raise NotImplementedError("Haven't implemented any other methods of "
      +"creating an instance other than booting form a volume yet.")
  
  #verify the VM was created and is running
  instanceNotActive=True
  iter=0
  while instanceNotActive and iter<OSNumChecks:
    
    try:
      existingNode=clients["nova"].servers.find(name=hostname)
      if(existingNode.status=="ACTIVE"):
        instanceNotActive=False
        break
    except novaclient.exceptions.NotFound:
      pass#keep waiting for instance to show up
    
    if instanceNotActive:
      sys.stdout.write(".")
      sys.stdout.flush()
      #wait some amount of time before checking again
      time.sleep(OSCheckWaitTime)
    iter+=1
  
  #check that instance is now active
  if instanceNotActive:
    raise Exception("Timed out while waiting for new instance \""
      +hostname+"\" to become active.")
  
  sys.stdout.write("\n    Creation completed.\n")
def attachVolume(parameters,clients):
  """Attaches a volume to an instance
  """
  
  ensureNovaClient(clients)
  
  #get instance
  servers=clients["nova"].servers.list()
  serverToAttachTo=None
  for server in servers:
    if server.name==parameters["instance"] or server.id==parameters["instance"]:
      serverToAttachTo=server
      break
  
  #if no instance found
  if serverToAttachTo==None:
    raise Exception("no instance with id or name \""
      +parameters["instance"]+"\" found")
  
  #get volume
  volumes=clients["nova"].volumes.list()
  volumeToAttach=None
  for volume in volumes:
    if volume.name==parameters["volume"] or volume.id==parameters["volume"]:
      volumeToAttach=volume
  
  #if no volume found
  if volumeToAttach==None:
    raise Exception("no volume with id or name \""
      +parameters["volume"]+"\" found")
  
  #check that volume isn't already attached to something
  if(len(volumeToAttach.attachments)>0):
    instanceAttached=clients["nova"].servers.find(
      id=volumeToAttach.attachments[0]["server_id"])
    if instanceAttached==serverToAttachTo:
      sys.stdout.write("  Volume \""+parameters["volume"]
        +"\" already attached to instance \""+parameters["instance"]
        +"\" nothing to be done.\n")
      return
    else:
      raise Exception("the volume \""+volumeToAttach.name
        +"\" is already attached to \""+instanceAttached.name
        +"\" on device \""+volumeToAttach.attachments[0]["device"])
        
  sys.stdout.write("  Attaching \""+parameters["volume"]+"\" to instance \""+parameters["instance"]+"\" ")
  
  #attach volume to instance
  if "device" in parameters.keys():
    clients["nova"].volumes.create_server_volume(serverToAttachTo.id,volumeToAttach.id,parameters["device"])
  else:
    clients["nova"].volumes.create_server_volume(serverToAttachTo.id,volumeToAttach.id)
  
  #wait until action is completed
  volumeNotAttached=True
  iter=0
  while volumeNotAttached and iter<OSNumChecks:
    
    #is the instance still there?
    volumeCheck=clients["nova"].volumes.find(id=volumeToAttach.id)
    
    for attachment in volumeCheck.attachments:
      instanceAttached=clients["nova"].servers.find(
      id=attachment["server_id"])
      if instanceAttached==serverToAttachTo:
        volumeNotAttached=False
        break
      else:
        sys.stdout.write(".")
        sys.stdout.flush()
        #wait some amount of time before checking again
        time.sleep(OSCheckWaitTime)
        iter+=1
      
  #check that we haven't timed out
  if iter>=OSNumChecks and volumeNotAttached:
    raise Exception("Timed out waiting for volume attachment to complete.\n")
  
  #notify that termination has completed
  sys.stdout.write("\n    Attachment completed.\n")
  return
def associateFloatingIP(parameters,clients):
  """Associates a floating IP with a specific instance
  """
  
  ensureNovaClient(clients)
  
  #check if an ip was specified
  if "ip" in parameters.keys():
    
    #check that specified ip is available
    ipList=clients["nova"].floating_ips.list()
    requestedIPExists=False
    ipToAttach=None
    for ip in ipList:
      
      if ip.ip==parameters["ip"]:
        requestedIPExists=True
        ipToAttach=ip
    
    if not requestedIPExists:
      raise Exception("the requested ip \""+parameters["ip"]
        +"\" is not available. To allocate a new ip do not specify it by "
        +"omitting the \"ip\" xml element.")
  
  #otherwise allocate an ip from a pool
  else:
    
    #get list of ip pools available
    ipPools=clients["nova"].floating_ip_pools.list()
    
    #if an ip pool was specified try to find it
    poolFound=False
    ipPoolToUse=None
    if "pool" in parameters.keys():
      
      for ipPool in ipPools:
        
        if ipPool.name==parameters["pool"]:
          ipPoolToUse=ipPool
          poolFound=True
      
      if not poolFound:
        raise Exception("specified ip pool \""+parameters["pool"]
          +"\" not found")
        
    #otherwise use first pool found
    else:
      
      #make sure we have at least one ip pool
      if len(ipPools)<1:
        raise Exception("no ip pools found to allocate ips from, contact "
          +"your OpenStack administrator about why there are no ip pools.")
          
      ipPoolToUse=ipPools[0]
    
    #should now have an ipPool
    ipToAttach=clients["nova"].floating_ips.create(ipPoolToUse.name)
    
  #at this point should have an ip to attach to an instance
  sys.stdout.write("  associating floating ip \""+str(ipToAttach.ip)+"\" with \""
    +parameters["instance"]+"\" ")
  
  #check that specified instance exists
  servers=clients["nova"].servers.list()
  instanceToAttachTo=None
  for server in servers:
    if (server.name==parameters["instance"] 
      or server.id==parameters["instance"]):
      instanceToAttachTo=server
      break
  
  #if we don't have the instance report the problem
  if instanceToAttachTo==None:
    raise Exception("given instance \""+parameters["instance"]+"\" not found.")
  
  #at this point should have an instance to attach the ip to
  
  #check to see if ip already assigned to an instance
  if ipToAttach.instance_id!=None:
    server=clients["nova"].servers.find(id=ipToAttach.instance_id)
    
    #is it the instance we want to attach to?
    if server==instanceToAttachTo:
      sys.stdout.write("\n    ip \""+str(ipToAttach.ip)
        +"\" already associated with instance \""
        +parameters["instance"]+"\" nothing to do.\n")
      return
    else:
      raise Exception("floating ip \""+str(ipToAttach.ip)
        +"\" already assigned to the instance \""+server.name+"\".")
  
  #Associate ip with instance
  instanceToAttachTo.add_floating_ip(ipToAttach)
  
  #wait until ip is associated
  notAttached=True
  iter=0
  while notAttached and iter<OSNumChecks:
    
    ipCheck=clients["nova"].floating_ips.find(id=ipToAttach.id)
    if ipCheck.instance_id==None:
      sys.stdout.write(".")
      sys.stdout.flush()
      #wait some amount of time before checking again
      time.sleep(OSCheckWaitTime)
      iter+=1
    else:
      notAttached=False
      break
  
  if notAttached and iter>=OSNumChecks:
    raise Exception("Timed out while waiting for floating ip to associate"
      +" with instance \""+parameters["instance"]+"\".")
  
  sys.stdout.write("\n    Association completed.\n")
  return
    
#When creating new action executor functions, add them to this dictionary
#the key will be the XML tag under the <parameters> tag (see actions.xsd 
#scheme for expected xml format).
#One must also add to the parameter-type.xsd to describe the parameters required
#for that action and add that as a choice under the "parameters-type" XML element
#type. See existing parameter-type.xsd xml type entries, e.g. instance-create.
exeFuncs={
  "instance-terminate":instanceTerminate
  ,"volume-create-image":volumeCreateImage
  ,"download-image":downloadImage
  ,"instance-create":instanceCreate
  ,"attach-volume":attachVolume
  ,"associate-floating-ip":associateFloatingIP
  }
