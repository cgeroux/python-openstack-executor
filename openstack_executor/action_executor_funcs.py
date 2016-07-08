from __future__ import print_function
import time
import sys
import novaclient
from . import utilFuncs 
from .openstack_executor import authVersion
from . import formats

OSCheckWaitTime=3#time to wait between polling OS to check for action 
  #completion in seconds
OSNumChecks=20#number of times to check for action completion

#assume rate of creation, this is based on a 10Gb
#volume with 805Mb of data taking 57s to create an image from
gbPers=0.01

if authVersion=="2":
  from .createOSClientsV2 import *
elif authVersion=="3":
  from .createOSClientsV3 import *
else:
  raise Exception("Unexpected authorization version \""+authVersion+"\"")

#TODO: add a parameters["force"] option to items which fail when an 
#image/volume/instance already exists with the specified name which 
#deletes the duplicate before proceeding.

def terminateInstance(parameters,clients):
  """Terminate an instance
  """
  
  ensureNovaClient(clients)
  
  sys.stdout.write("  Terminating instance \""+parameters["instance"]+"\" ")
  sys.stdout.flush()
  
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
def createImageFromVolume(parameters,clients):
  """Creates an image from a volume
  """
  
  ensureCinderClient(clients)
  ensureGlanceClient(clients)
  
  #get the volume to image
  volumeToImage=None
  projectID=getProjectID(clients)
  volumes=clients["cinder"].volumes.list()
  for volume in volumes:
    if volume.name==parameters["volume"] or volume.id==parameters["volume"]:
      volumeToImage=volume
      break
  
  if volumeToImage==None:
    raise Exception("volume with name or id \""+parameters["volume"]
      +"\" not found!")
  
  #check if there is an image with that name already
  #technically there can be multiple images with the same name
  #but that makes things complicated
  images=clients["glance"].images.list(owner=projectID)
  for image in images:
    if(image.name==parameters["image-name"]):
      raise Exception("an image with the name \""+str(parameters["image-name"])
        +"\" already exists.")
  
  sys.stdout.write("  Creating image \""+parameters["image-name"]
    +"\" from volume \""+parameters["volume"]+"\" ")
  sys.stdout.flush()
  
  #create image from volume
  force=True#not sure what this does, a few tests don't indicate a 
    #difference between True of False
  imageName=parameters["image-name"]
  if "format" in parameters.keys():
    diskFormat=parameters["format"]
  else:
    diskFormat="qcow2"
  volumeToImage.upload_to_image(force,imageName,formats.containerFormat,diskFormat)
  
  #check that the image has been created
  imageNotActive=True
  iter=0

  #estimate how many times we will check based on the size of the volume
  #this should be a significant overestimate
  numChecks=int(float(volumeToImage.size)/gbPers/float(OSCheckWaitTime))
  while imageNotActive and iter<numChecks:
    
    images=clients["glance"].images.list(owner=projectID)
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
  
  ensureGlanceClient(clients)
  
  #check if we have a match-owner option
  matchOwner=True
  if "public-image" in parameters.keys():
    if parameters["public-image"] in ["true",1]:
      matchOwner=False#don't match owner if it is a public
        #image as it won't find it
  
  #get a list of images
  projectID=getProjectID(clients)
  if matchOwner:
    images=clients["glance"].images.list(owner=projectID)
  else:
    images=clients["glance"].images.list()
  
  #find the image to download
  imageToDownLoad=None
  for image in images:
    if(image.name==parameters["image"] or image.id==parameters["image"]):
      imageToDownLoad=image
      break
      
  #if image not found
  if imageToDownLoad==None:
    if matchOwner:
      message="no image owned by the current user with name or id \"" \
        +parameters["image"]+"\" was found."
    else:
      message="no image with name or id \""+parameters["image"]+"\" was found."
    raise Exception(message)
  
  #Create a filename to save image to
  fileName=parameters["file-name"]+"."+imageToDownLoad.disk_format
  sys.stdout.write("  Downloading image \""+parameters["image"]
    +"\" to file \""+fileName+"\" \n")
  sys.stdout.flush()
  
  #download the image
  imageFile=open(fileName,'bw+')
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
def createInstance(parameters,clients):
  """Creates an instance
  """
  
  ensureNovaClient(clients)
  
  #check that instance name is a valid hostname
  utilFuncs.validateHostName(parameters["name"])
  
  #use lower case host names for consistency as they should be case insensitive
  hostname=parameters["name"].lower()
  
  sys.stdout.write("  Creating instance \""+hostname+"\" ")
  sys.stdout.flush()
  
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
    sys.stdout.flush()
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
  sys.stdout.flush()
  
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
  sys.stdout.flush()
  
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
def deleteImage(parameters,clients):
  """Delete an image owned by the current user
  """
    
  ensureGlanceClient(clients)
  
  #Get a list of images owned by the current user
  projectID=getProjectID(clients)
  images=clients["glance"].images.list(owner=projectID)
  
  #find the image to delete
  imageToDelete=None
  for image in images:
    if(image.name==parameters["image"] or image.id==parameters["image"]):
      imageToDelete=image
      break
  
  #if image not found warn that nothing is being done
  if imageToDelete==None:
    message="  WARNING: no image owned by the current user with name or id \""\
      +parameters["image"]+"\" was found.\n"
    sys.stdout.write(message)
    return
  
  sys.stdout.write("  Deleting image \""+parameters["image"]+"\" ")
  sys.stdout.flush()
  
  #delete the image
  imageID=imageToDelete.id
  imageToDelete.delete()
  
  #check that it is deleted
  imageFound=True
  iter=0
  while imageFound and iter<OSNumChecks:
    
    #will throw an exception if not found, which one?
    images=clients["glance"].images.list(owner=projectID)
    imageFound=False
    for image in images:
      if(image.id==imageID):
        imageFound=True
        break
    
    #wait some amount of time before checking again
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
      
  if imageFound:
    raise Exception("Timed out waiting for image deletion to complete.\n")
  
  #notify that image deletion has completed
  sys.stdout.write("\n    Image deletion completed.\n")
  return
def uploadImage(parameters,clients):
  """Uploads an image file to OpenStack
  """
  
  ensureGlanceClient(clients)
  
  #check that an image with the given name doesn't already exist
  projectID=getProjectID(clients)
  images=clients["glance"].images.list(owner=projectID)
  imageAlreadyExists=False
  for image in images:
    if(image.name==parameters["image-name"]):
      imageAlreadyExists=True
      break
  if imageAlreadyExists:
    raise Exception("an image with the name \""+parameters["image-name"]
      +" already exists!")
  
  sys.stdout.write("  Uploading image file \""+parameters["file-name"]
    +"\" to image \""+parameters["image-name"]+"\" ")
  sys.stdout.flush()
  
  #guess format from file extension
  diskFormat=None
  for fileType in formats.imageFormats:
    if fileType == parameters["file-name"][-len(fileType):]:
      diskFormat=fileType
  
  #if we couldn't guess image disk format
  if diskFormat==None:
    raise Exception("unable to determine image type from file name \""
      +parameters["file-name"]+"\" expecting an extension of one of "
      +str(formats.imageFormats))
  
  #TODO: the below commands wait for completion to return, would be good to 
  #do it in a separate thread and check for completion so that we can let 
  #the user know that the script is still doing something.
  
  #create an image
  image=clients["glance"].images.create(name=parameters["image-name"])
  imageID=image.id
  image.update(data=open(parameters["file-name"],'rb'),disk_format=diskFormat
    ,container_format=formats.containerFormat)

  #wait for image to be active
  imageNotActive=True
  iter=0
  while imageNotActive and iter<OSNumChecks:
    
    #get image
    images=clients["glance"].images.list(owner=projectID)
    for image in images:
      if(image.id==imageID):
        if(image.status=="active"):
          imageNotActive=False
          break
    #wait some amount of time before checking again
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
  
  #check that we haven't timed out
  if iter>=OSNumChecks and imageNotActive:
    raise Exception("Timed out waiting for image to upload.\n")
  
  #notify that termination has completed
  sys.stdout.write("\n    Upload completed.\n")
  return
def deleteVolume(parameters,clients):
  """Deletes a volume
  """
  
  ensureCinderClient(clients)
  
  #get the volume to image
  volumeToDelete=None
  projectID=getProjectID(clients)
  volumes=clients["cinder"].volumes.list()
  for volume in volumes:
    if volume.name==parameters["volume"] or volume.id==parameters["volume"]:
      volumeToDelete=volume
      break
  
  if volumeToDelete==None:
    raise Exception("volume with name or id \""+parameters["volume"]+"\" not found!")
  
  sys.stdout.write("  Deleting volume \""+parameters["volume"]+"\" ")
  sys.stdout.flush()
  
  volumeID=volumeToDelete.id
  volumeToDelete.delete()
  
  #check that the deletion has completed
  volumeExists=True
  iter=0
  while volumeExists and iter<OSNumChecks:
    
    volumes=clients["cinder"].volumes.list()
    volumeExists=False
    for volume in volumes:
      if volume.id==volumeID:
        volumeExists=True
        break
    
    #wait some amount of time before checking again
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
  
  #check that we haven't timed out
  if iter>=OSNumChecks and volumeExists:
    raise Exception("Timed out waiting for volume deletion to complete.\n")
  
  #notify that termination has completed
  sys.stdout.write("\n    Deletion completed.\n")
  return
def createVolumeFromImage(parameters,clients):
  """
  """
  
  ensureGlanceClient(clients)
  ensureCinderClient(clients)
  
  #Get a list of images owned by the current user
  projectID=getProjectID(clients)
  images=clients["glance"].images.list(owner=projectID)
  
  #find the image to create volume from
  imageToUse=None
  for image in images:
    if(image.name==parameters["image"] or image.id==parameters["image"]):
      imageToUse=image
      break
  
  #if image not found warn that nothing is being done
  if imageToUse==None:
    raise Exception("no image owned by the current user with name or id \""\
      +parameters["image"]+"\" was found.\n")
  
  sys.stdout.write("  Creating volume \""+parameters["volume-name"]
    +"\" from image \""+parameters["image"]+"\" ")
  sys.stdout.flush()
  
  #create the volume
  volume=clients["cinder"].volumes.create(size=parameters["size"]
    ,name=parameters["volume-name"],imageRef=imageToUse.id)
  
  volumeID=volume.id
  
  #check that the volume creation has completed
  volumeDoesNotExists=True
  iter=0
  numChecks=int(float(parameters["size"])/gbPers/float(OSCheckWaitTime))
  while volumeDoesNotExists and iter<numChecks:
    
    volumes=clients["cinder"].volumes.list()
    for volume in volumes:
      if volume.id==volumeID:
        if volume.status=="available":
          volumeDoesNotExists=False
        break
    
    #wait some amount of time before checking again
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
  
  #check that we haven't timed out
  if iter>=OSNumChecks and volumeDoesNotExists:
    raise Exception("Timed out waiting for volume creation to complete.\n")
  
  #notify that creation has completed
  sys.stdout.write("\n    Creation completed.\n")
  return
#When creating new action executor functions, add them to this dictionary
#the key will be the XML tag under the <parameters> tag (see actions.xsd 
#scheme for expected xml format).
#One must also add to the parameter-type.xsd to describe the parameters required
#for that action and add that as a choice under the "parameters-type" XML element
#type. See existing parameter-type.xsd xml type entries, e.g. instance-create.
exeFuncs={
  "terminate-instance":terminateInstance
  ,"create-image-from-volume":createImageFromVolume
  ,"download-image":downloadImage
  ,"create-instance":createInstance
  ,"attach-volume":attachVolume
  ,"associate-floating-ip":associateFloatingIP
  ,"delete-image":deleteImage
  ,"upload-image":uploadImage
  ,"delete-volume":deleteVolume
  ,"create-volume-from-image":createVolumeFromImage
  }
