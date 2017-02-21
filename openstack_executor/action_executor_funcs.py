from __future__ import print_function
import time
import sys
import novaclient
import threading
import os
from . import utilFuncs 
from . import formats
import urllib

#TODO: 
# - add a function to remove a security group from a VM
# - add a function to create a security group

OSCheckWaitTime=1#time to wait between polling OS to check for action 
  #completion in seconds
OSNumChecks=120#number of times to check for action completion

#assume rate of creation, this is based on a 10GB
#volume with 805MB of data taking 57s to create an image from
gbPers=0.01
waitAnimation="|\\-/"

#helper functions
activeStrings=["ACTIVE","active","available"]
def isList(item):
  if type(item)==type([]) or type(item)==novaclient.base.ListWithMeta:
    return True
  return False
def isActive(osItem):
  """Returns true if the given OpenStack item is active, otherwise false
  """
  if isList(osItem):#if a list ensure all in list are active
    activeCount=0
    for item in osItem:
      if item.status in activeStrings:
        activeCount+=1
    return activeCount==len(osItem)
  else:
    if osItem is not None:#Note != will not work here due to stupid OpenStack bug
      return osItem.status in activeStrings
    else:
      return False
def getVM(osc,clients,hostname):
  """Returns either None if no VM found, a server object if one VM is found,
    or a list of VMs if more than one is found
  """
  
  osc.ensureNovaClient(clients)
  try:
    servers=clients["nova"].servers.findall(name=hostname)
    if len(servers)==0:
      return None
    if len(servers)==1:
      return servers[0]
    elif len(servers)>=1:
      return servers
  except novaclient.exceptions.NotFound:
    return None
def getImage(osc,clients,imageName,project=True):
  """Returns either None if no image found, an image object if one image is found,
    or a list of images if more than one is found
  
  if project is True then search limited to current users project
  """
  
  osc.ensureGlanceClient(clients)
  if project:
    projectID=osc.getProjectID(clients)
    images=clients["glance"].images.list(owner=projectID)
  else:
    images=clients["glance"].images.list()
  matchingImages=[]
  for image in images:

    if image.name==imageName or image.id==imageName:
      matchingImages.append(image)
  if len(matchingImages)==0:
    return None
  elif len(matchingImages)==1:
    return matchingImages[0]
  else:
    return matchingImages
def getVolume(osc,clients,volumeName):
  """Returns either None if no volume found, a volume object if one volume is found,
    or a list of volumes if more than one is found
  """
  
  osc.ensureCinderClient(clients)
  volumes=clients["cinder"].volumes.list()
  matchingVolumes=[]
  for volume in volumes:
    if volume.name==volumeName or volume.id==volumeName:
      matchingVolumes.append(volume)
  if len(matchingVolumes)==0:
    return None
  elif len(matchingVolumes)==1:
    return matchingVolumes[0]
  else:
    return matchingVolumes
def getSecurityGroup(osc,clients,groupName):
  """Returns either None if no group found, a group object if one group is found,
    or a list of groups if more than one is found
  """
  
  securityGroups=clients["nova"].security_groups.list()
  matchingGroups=[]
  for securityGroup in securityGroups:
    if securityGroup.name==groupName or securityGroup.id==groupName:
        matchingGroups.append(securityGroup)
  if len(matchingGroups)==0:
    return None
  elif len(matchingGroups)==1:
    return matchingGroups[0]
  else:
    return matchingGroups
def isAttached(osc,clients,vm,volume):
  """returns True if volume is attached to vm otherwise False
  """
  
 
  if(len(volume.attachments)>0):#if volume has attachments
    osc.ensureNovaClient(clients)
    for attachment in volume.attachments:
      
      instance=clients["nova"].servers.find(id=attachment["server_id"])
      if instance.id==vm.id:
        return True
  
  return False
  
#main action functions
def terminateInstance(parameters,clients,osc,options):
  """Terminate an instance
  """
  
  osc.ensureNovaClient(clients)
  currentMessage="  Terminating instance \""+parameters["instance"]+"\""
  
  #get list of servers
  serverToTerminate=getVM(osc,clients,parameters["instance"])
  if serverToTerminate is not None:#again stupid openstack bug, can't use !=
    if isList(serverToTerminate):
      raise Exception("Found multiple servers matching the given instance \""
        +parameters["instance"]
        +"\" for safety reasons will only delete uniquely identified severs.")
      #Not going to process multiple server terminates as we don't want to 
      #mistakenly delete the wrong one, that could be bad
      #for server in serverToTerminate:
      #  clients["nova"].servers.delete(server)
    else:
      clients["nova"].servers.delete(serverToTerminate)
  else:
    sys.stdout.write("    WARNING: No instance found with name or id \""
      +parameters["instance"]+"\". Nothing to terminate!\n")
    return
  
  #clients={}#re-initialize connection, it seems that if not 
  #re-initializing the terminate check for termination can lag behind on a re-connection.
  #osc.ensureNovaClient(clients)
  
  #wait until action is completed
  serverPresent=True
  iter=0
  while serverPresent and iter<OSNumChecks:
    
    #is the instance still there?
    found=False
    #for safety reasons we aren't going to terminate multiple VMs
    #if isList(serverToTerminate):
    #  for server in serverToTerminate:
    #    vm=getVM(osc,clients,server.id)
    #    if server is not None:
    #      found=True
    #else:
    server=getVM(osc,clients,serverToTerminate.id)
    if server is not None:
      found=True
    
    #if server still there, lets wait
    if found:
      sys.stdout.write(currentMessage+" {0}\r".format(
        waitAnimation[iter%len(waitAnimation)]))
      sys.stdout.flush()
      
      #wait some amount of time before checking again
      time.sleep(OSCheckWaitTime)
    else:
      serverPresent=False
      
      #wait some amount of time before finalizing
      #seems sometimes the above checks are a bit out of sync
      #with later tests, this helps to ensure things are consistent
      #once this function returns
      time.sleep(OSCheckWaitTime)
    
    #increment number of checks
    iter+=1
  
  #check that we haven't timed out
  if iter>=OSNumChecks and serverPresent:
    raise Exception("Timed out waiting for termination to complete.\n")
  
  #notify that termination has completed
  sys.stdout.write("\n    Termination completed.\n")
  return
def createImageFromVolume(parameters,clients,osc,options):
  """Creates an image from a volume
  """
  
  #get the volume to image
  volumeToImage=getVolume(osc,clients,parameters["volume"])
  
  if volumeToImage==None:
    raise Exception("volume with name or id \""+parameters["volume"]
      +"\" not found!")
  
  alreadyExists="fail"
  if "already-exists" in parameters.keys():
    alreadyExists=parameters["already-exists"]
  
  #global over-ride
  if options.alreadyExistsGlobal!=None:
    alreadyExists=options.alreadyExistsGlobal
  
  #check for existence of image
  image=getImage(osc,clients,parameters["image-name"])
  if image is not None:
    if alreadyExists=="skip":
      sys.stdout.write("  An image with the name \""
        +str(parameters["image-name"])
        +"\" already exists, skipping creation.\n")
      sys.stdout.flush()
      return
    elif alreadyExists=="overwrite":
      sys.stdout.write("  An image with the name \""
        +str(parameters["image-name"])
        +"\" already exists, overwriting.\n")
      sys.stdout.flush()
      deleteImage({"image":image.id},clients,osc,options)
    else:
      raise Exception("an image with the name \""
        +str(parameters["image-name"])+"\" already exists.")
  
  currentMessage="  Creating image \""+parameters["image-name"] \
    +"\" from volume \""+parameters["volume"]+"\" "
  
  #create image from volume
  force=True#not sure what this does, a few tests don't indicate a 
    #difference between True of False
  if "format" in parameters.keys():
    diskFormat=parameters["format"]
  else:
    diskFormat="qcow2"
  volumeToImage.upload_to_image(force,parameters["image-name"]
    ,formats.containerFormat,diskFormat)
  
  #check to see if the image has been created
  imageCreated=False
  iter=0
  while not imageCreated and iter<OSNumChecks:
    
    sys.stdout.write(currentMessage+" {0}\r".format(
      waitAnimation[iter%len(waitAnimation)]))
    sys.stdout.flush()
    
    image=getImage(osc,clients,parameters["image-name"])
    if image is not None:
      imageCreated=True
      currentMessage="    Image created, uploading volume data to image"
      sys.stdout.write("\n")
      sys.stdout.flush()
      break
  
  #check that the image has been created
  imageNotActive=True
  iter=0
  
  #estimate how many times we will check based on the size of the volume
  #this should be a significant overestimate
  numChecks=int(float(volumeToImage.size)/gbPers/float(OSCheckWaitTime))
  while imageNotActive and iter<numChecks:
    
    sys.stdout.write(currentMessage+" {0}\r".format(
      waitAnimation[iter%len(waitAnimation)]))
    sys.stdout.flush()
    
    image=getImage(osc,clients,parameters["image-name"])
    if isActive(image):
      imageNotActive=False
      break
    
    #wait some amount of time before checking again
    time.sleep(OSCheckWaitTime)
    iter+=1
      
  if imageNotActive:
    raise Exception("Timed out waiting for image creation to complete.\n")
  
  #notify that image creation has completed
  sys.stdout.write("\n    Image creation completed.\n")
  return
def downloadImage(parameters,clients,osc,options):
  """Downloads an image to the current working directory
  """
  
  osc.ensureGlanceClient(clients)
  
  #check if we have a match-owner option
  matchOwner=True
  if "public-image" in parameters.keys():
    if parameters["public-image"] in ["true",1]:
      matchOwner=False#don't match owner if it is a public
        #image as it won't find it
  
  #get a list of images
  projectID=osc.getProjectID(clients)
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
  
  alreadyExists="fail"
  if "already-exists" in parameters.keys():
    alreadyExists=parameters["already-exists"]
    
  #global over-ride
  if options.alreadyExistsGlobal!=None:
    alreadyExists=options.alreadyExistsGlobal
  
  sys.stdout.write("  Downloading image \""+parameters["image"]
    +"\" to file \""+fileName+"\" \n")
  sys.stdout.flush()
  
  #check to see if the file name already exists
  if os.path.exists(fileName):
    if alreadyExists=="overwrite":
      sys.stdout.write("    file already exists, overwriting.\n")
      sys.stdout.flush()
    elif alreadyExists=="skip":
      sys.stdout.write("    file already exists, skipping download.\n")
      sys.stdout.flush()
      return
    else:
      raise Exception("file with name \""+fileName+"\" already exists!")
      
  #download the image
  imageFile=open(fileName,'wb+')
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
def createInstance(parameters,clients,osc,options):
  """Creates an instance
  """
  
  strReplace=None
  
  #get number of instances to create
  instanceCount=1
  if "instance-count" in parameters.keys():
    instanceCount=int(parameters["instance-count"])
  
  #make sure we aren't creating multiple instances and booting from a volume
  #this is a bit tricky to do, and OpenStack doesn't even do this
  if instanceCount>1:
    if "volume" in parameters["instance-boot-source"].keys():
      raise Exception("Can not create multiple instances when booting "
        +"form a volume!")
  
  osc.ensureNovaClient(clients)
  
  #check that instance name is a valid hostname
  utilFuncs.validateHostName(parameters["name"])
  
  #use lower case host names for consistency as they should be case insensitive
  hostname=parameters["name"].lower()
  
  if instanceCount>1:
    sys.stdout.write("  Creating "+str(instanceCount)+" instances of \""+hostname+"\" ")
    sys.stdout.flush()
  else:
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
      raise Exception("no networks found if there is one available that"
        +" wasn't detected specify it in a \"network\" xml element under the "
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
  
  #check to see if a key pair was specified
  keyName=None
  if "key-name" in parameters.keys():
    keyName=parameters["key-name"]
  
  #check to see if a cloud-init script was specified
  userData=None
  if "post-creation-script" in parameters.keys():
    try:
      #try opening as url
      userData=urllib.request.urlopen(parameters["post-creation-script"]).read()
    except ValueError:
      #try opening as a file
      userData=open(os.path.join(options.path
        ,parameters["post-creation-script"]),'r').read()
  
  #get alreadyExists action to take
  alreadyExists="fail"
  if "already-exists" in parameters.keys():
    alreadyExists=parameters["already-exists"]
  
  #global over-ride
  if options.alreadyExistsGlobal!=None:
    alreadyExists=options.alreadyExistsGlobal
  
  #Quantities used if renaming an instance if it already exists
  #check if name already has a -# on the end
  index=hostname.rfind("-")
  if index==-1:
    baseName=hostname
    count=0
  else:
    try:
      baseName=hostname[:index]
      count=int(hostname[index+1:])
    except ValueError:#e.g. not an integer after "-"
      baseName=hostname
      count=0
  if instanceCount>1:
    hostname=baseName+"-"+str(count)
  
  #check to see if we already have an instance with that name
  if getVM(osc,clients,hostname) is not None:
    if alreadyExists=="skip":
      sys.stdout.write("\n  An instance with the name \""
        +hostname
        +"\" already exists, skipping creation.\n")
      sys.stdout.flush()
      return
    elif alreadyExists=="overwrite":
      sys.stdout.write("  An instance with the name \""+hostname
        +"\" already exists, overwriting.\n")
      sys.stdout.flush()
      terminateInstance({"instance":hostname},clients,osc,options)
    elif alreadyExists=="rename":
      hostnameTry=baseName+"-"+str(count)
      while getVM(osc,clients,hostnameTry):
        count+=1
        hostnameTry=baseName+"-"+str(count)
      sys.stdout.write("\n    An instance with the name \""+hostname
        +"\" already exists, using name \""+hostnameTry+"\" instead.")
      sys.stdout.flush()
      strReplace={hostname:hostnameTry}
      hostname=hostnameTry
    else:
      raise Exception("already an instance present with name \""
        +hostname+"\".")
  
  #create the VM
  hostNamesToCheck=[]
  if "volume" in parameters["instance-boot-source"].keys():#boot from a volume
    
    #get volume id
    osc.ensureCinderClient(clients)
    volumes=clients["cinder"].volumes.list()
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
    currentMessage="    Booting from a volume "
    sys.stdout.write("\n")
    sys.stdout.flush()
    instance=clients["nova"].servers.create(
      name=hostname
      ,block_device_mapping=blockDeviceMapping
      ,flavor=flavor
      ,image=None
      ,nics=nics
      ,key_name=keyName
      ,userdata=userData
      )
    hostNamesToCheck.append(hostname)
  elif "image" in parameters["instance-boot-source"].keys():#boot form an image
    
    #make sure the image is available
    osc.ensureGlanceClient(clients)
    images=clients["glance"].images.list()
  
    bootImage=None
    imageFound=False
    for image in images:
      if(image.name==parameters["instance-boot-source"]["image"]):
        bootImage=image
        imageFound=True
    
    if not imageFound:
      raise Exception("the image \""+parameters["instance-boot-source"]["image"]+"\" not found")
    
    #Create the instance
    if instanceCount>1:
      currentMessage="    Booting "+str(instanceCount)+" instances from an image "
    else:
      currentMessage="    Booting from an image "
    
    sys.stdout.write("\n")
    sys.stdout.flush()
    if instanceCount>1:
      for i in range(instanceCount):
        hostname=baseName+"-"+str(count)
        instance=clients["nova"].servers.create(
          name=hostname
          ,flavor=flavor
          ,image=bootImage
          ,nics=nics
          ,key_name=keyName
          ,userdata=userData
          )
        count+=1
        hostNamesToCheck.append(hostname)
    else:
      instance=clients["nova"].servers.create(
        name=hostname
        ,flavor=flavor
        ,image=bootImage
        ,nics=nics
        ,key_name=keyName
        ,userdata=userData
        )
      hostNamesToCheck.append(hostname)
  else:
    #TODO: implement more methods for creating a VM
    raise NotImplementedError("Haven't yet implemented methods of "
      +"creating an instance other than booting form a volume or image yet.")
  
  #verify the VM was created and is running
  allInstanceNotActive=True
  iter=0
  while allInstanceNotActive and iter<OSNumChecks:
    
    activeCount=0
    for hostname in hostNamesToCheck:
      vm=getVM(osc,clients,hostname)
      if isActive(vm):
        activeCount+=1
      
    if activeCount!=instanceCount:
      sys.stdout.write(currentMessage+" {0}\r".format(
        waitAnimation[iter%len(waitAnimation)]))
      sys.stdout.flush()
      #wait some amount of time before checking again
      time.sleep(OSCheckWaitTime)
    else:
      allInstanceNotActive=False
    iter+=1
  
  #check that instance is now active
  if allInstanceNotActive:
    raise Exception("Timed out while waiting for new instance \""
      +hostname+"\" to become active.")
  
  sys.stdout.write("\n    Creation completed.\n")
  return strReplace
def attachVolume(parameters,clients,osc,options):
  """Attaches a volume to an instance
  """
  
  osc.ensureNovaClient(clients)
  osc.ensureCinderClient(clients)
  
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
  volumes=clients["cinder"].volumes.list()
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
  
  currentMessage="  Attaching \""+parameters["volume"]+"\" to instance \""\
    +parameters["instance"]+"\""
  
  #attach volume to instance
  if "device" in parameters.keys():
    clients["nova"].volumes.create_server_volume(serverToAttachTo.id
      ,volumeToAttach.id,parameters["device"])
  else:
    clients["nova"].volumes.create_server_volume(serverToAttachTo.id
      ,volumeToAttach.id)
  
  #wait until action is completed
  volumeNotAttached=True
  iter=0
  while volumeNotAttached and iter<OSNumChecks:
    
    #is the instance still there?
    volumeCheck=None
    volumes=clients["cinder"].volumes.list()
    for volume in volumes:
      if volume.id==volumeToAttach.id:
        volumeCheck=volume
        break
    
    if volumeCheck is not None:
      for attachment in volumeCheck.attachments:
        instanceAttached=clients["nova"].servers.find(
        id=attachment["server_id"])
        if instanceAttached==serverToAttachTo:
          volumeNotAttached=False
          break
          
    #wait some amount of time before checking again
    sys.stdout.write(currentMessage+" {0}\r".format(
      waitAnimation[iter%len(waitAnimation)]))
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
      
  #check that we haven't timed out
  if iter>=OSNumChecks and volumeNotAttached:
    raise Exception("Timed out waiting for volume attachment to complete.\n")
  
  #notify that termination has completed
  sys.stdout.write("\n    Attachment completed.\n")
  return
def associateFloatingIP(parameters,clients,osc,options):
  """Associates a floating IP with a specific instance
  """
  
  osc.ensureNovaClient(clients)
  
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
  currentMessage="  associating floating ip \""+str(ipToAttach.ip)+"\" with \""\
    +parameters["instance"]+"\""
  
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
  if ipToAttach.instance_id is not None and ipToAttach.instance_id!='':
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
    
    sys.stdout.write(currentMessage+" {0}\r".format(
      waitAnimation[iter%len(waitAnimation)]))
    sys.stdout.flush()
    
    ipCheck=clients["nova"].floating_ips.find(id=ipToAttach.id)
    if ipCheck.instance_id==instanceToAttachTo.id:
      notAttached=False
      break
      
    #wait some amount of time before checking again
    time.sleep(OSCheckWaitTime)
    iter+=1
  
  if notAttached and iter>=OSNumChecks:
    raise Exception("Timed out while waiting for floating ip to associate"
      +" with instance \""+parameters["instance"]+"\".")
  
  sys.stdout.write("\n    Association completed.\n")
  return
def releaseFloatingIP(parameters,clients,osc,options):
  """Releases an IP associated with a given VM back to the IP pool
  """
  
  osc.ensureNovaClient(clients)
  
  currentMessage="  Releasing floating IP associated with instance \""\
    +parameters["instance"]+"\""
  
  #get list of servers
  servers=clients["nova"].servers.list()
  serverToReleaseIPOf=None
  for server in servers:
    if server.name==parameters["instance"] or server.id==parameters["instance"]:
      serverToReleaseIPOf=server
      break
  
  #if no server found
  if serverToReleaseIPOf==None:
    sys.stdout.write("    WARNING: No instance found with name or id \""
      +parameters["instance"]+"\". Not releasing any IP!\n")
    return
  
  #now we should have our server, get the floating IP
  floatingIPAddr=None
  for network in serverToReleaseIPOf.addresses.keys():
    for address in serverToReleaseIPOf.addresses[network]:
      #address['version']=4
      #address['OS-EXT-IPS:type']='fixed'/'floating'
      #address['addr']=192.../206...
      #address['OS-EXT-IPS-MAC:mac_addr']='fa:16:3e:03:a4:7b'
      if address['OS-EXT-IPS:type']=='floating':
        floatingIPAddr=address['addr']
  
  #if no floating IP found
  if floatingIPAddr==None:
    sys.stdout.write("    WARNING: Instance \""+parameters["instance"]
      +"\" does not have a floating IP. nothing to release!\n")
    return
  
  ipList=clients["nova"].floating_ips.list()
  idOfReleasedIP=None
  for ip in ipList:
    if ip.ip==floatingIPAddr:
      idOfReleasedIP=ip.id
      clients["nova"].floating_ips.delete(ip)
  
  #check for the ip to have been released
  #wait until ip is associated
  ipStillAllocated=True
  iter=0
  while ipStillAllocated and iter<OSNumChecks:
    
    sys.stdout.write(currentMessage+" {0}\r".format(
      waitAnimation[iter%len(waitAnimation)]))
    sys.stdout.flush()
    
    ipFound=False
    ipList=clients["nova"].floating_ips.list()
    for ip in ipList:
      if ip.id==idOfReleasedIP:
        ipFound=True
        break
    if not ipFound:
      ipStillAllocated=False
      break
    
    #wait some amount of time before checking again
    time.sleep(OSCheckWaitTime)
    iter+=1
  
  if ipStillAllocated and iter>=OSNumChecks:
    raise Exception("Timed out while waiting for floating ip to be released.")
  
  sys.stdout.write("\n    Release completed.\n")
def deleteImage(parameters,clients,osc,options):
  """Delete an image owned by the current user
  """
    
  osc.ensureGlanceClient(clients)
  
  #Get a list of images owned by the current user
  projectID=osc.getProjectID(clients)
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
  
  currentMessage="  Deleting image \""+parameters["image"]+"\""
  
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
    sys.stdout.write(currentMessage+" {0}\r".format(
      waitAnimation[iter%len(waitAnimation)]))
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
      
  if imageFound:
    raise Exception("Timed out waiting for image deletion to complete.\n")
  
  #notify that image deletion has completed
  sys.stdout.write("\n    Image deletion completed.\n")
  return
def uploadImage(parameters,clients,osc,options):
  """Uploads an image file to OpenStack
  """
  
  osc.ensureGlanceClient(clients)
  
  #check that an image with the given name doesn't already exist
  projectID=osc.getProjectID(clients)
  images=clients["glance"].images.list(owner=projectID)
  
  alreadyExists="fail"
  if "already-exists" in parameters.keys():
    alreadyExists=parameters["already-exists"]
  
  #global over-ride
  if options.alreadyExistsGlobal!=None:
    alreadyExists=options.alreadyExistsGlobal
  
  for image in images:
    if(image.name==parameters["image-name"]):
      
      if alreadyExists=="skip":
        sys.stdout.write("  An image with the name \""
          +parameters["image-name"]
          +"\" already exists, skipping upload.\n")
        sys.stdout.flush()
        return
      elif alreadyExists=="overwrite":
        sys.stdout.write("  An image with the name \""
          +str(parameters["image-name"])
          +"\" already exists, overwriting.\n")
        sys.stdout.flush()
        deleteImage({"image":image.id},clients,osc,options)
      else:
        raise Exception("an image with the name \""+parameters["image-name"]
          +" already exists!")
  
  currentMessage="  Uploading image file \""+parameters["file-name"]\
    +"\" to image \""+parameters["image-name"]+"\" "
  
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
  
  #start uploading data in a separate thread
  updateImageThread=threading.Thread(target=image.update,kwargs={
    "data":open(parameters["file-name"],'rb')
    ,"disk_format":diskFormat
    ,"container_format":formats.containerFormat})
  #image.update(data=open(parameters["file-name"],'rb'),disk_format=diskFormat
  #  ,container_format=formats.containerFormat)
  updateImageThread.start()
  
  #wait for thread to stop, letting user know it is still working
  threadRunning=True
  iter=0
  while threadRunning:
    if not updateImageThread.isAlive():
      threadRunning=False
    
    sys.stdout.write(currentMessage+" {0}\r".format(
      waitAnimation[iter%len(waitAnimation)]))
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
    
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
    sys.stdout.write(currentMessage+" {0}\r".format(
      waitAnimation[iter%len(waitAnimation)]))
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
  
  #check that we haven't timed out
  if iter>=OSNumChecks and imageNotActive:
    updateImageThread
    raise Exception("Timed out waiting for image to upload.\n")
  
  #notify that termination has completed
  sys.stdout.write("\n    Upload completed.\n")
  return
def deleteVolume(parameters,clients,osc,options):
  """Deletes a volume
  """
  
  osc.ensureCinderClient(clients)
  
  #get the volume to delete
  volumeToDelete=None
  projectID=osc.getProjectID(clients)
  volumes=clients["cinder"].volumes.list()
  for volume in volumes:
    if volume.name==parameters["volume"] or volume.id==parameters["volume"]:
      volumeToDelete=volume
      break
  
  if volumeToDelete==None:
    sys.stdout.write("    WARNING: no volume with name or id \""+parameters["volume"]+"\".\n")
    return
  
  currentMessage="  Deleting volume \""+parameters["volume"]+"\""
  
  volumeID=volumeToDelete.id
  #check to see if the volume is attached to a vm
  if volumeToDelete.status=="in-use":
    raise Exception("volume with id \""+volumeID
      +"\" still in use, not able to delete.")
  
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
    sys.stdout.write(currentMessage+" {0}\r".format(
      waitAnimation[iter%len(waitAnimation)]))
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
  
  #check that we haven't timed out
  if iter>=OSNumChecks and volumeExists:
    raise Exception("Timed out after waiting more than "
      +OSCheckWaitTime*OSNumChecks+" s for volume deletion to complete. "
      +"You may wish to check your OS dashboard for problems.\n")
  
  #notify that termination has completed
  sys.stdout.write("\n    Deletion completed.\n")
  return
def createVolume(parameters,clients,osc,options):
  """
  """
  
  osc.ensureCinderClient(clients)
  
  imageID=None
  if "image" in parameters.keys():
    osc.ensureGlanceClient(clients)
  
    #Get a list of images owned by the current user
    #projectID=osc.getProjectID(clients)
    #images=clients["glance"].images.list(owner=projectID)
    #allow all images to be used to create a volume from
    images=clients["glance"].images.list()
    
    #find the image to create volume from
    imageToUse=getImage(osc,clients,parameters["image"],project=False)
    
    #if image not found we have a problem
    if imageToUse==None:
      raise Exception("no image with name or id \""+parameters["image"]
        +"\" was found.\n")
  
    imageID=imageToUse.id
    
  alreadyExists="fail"
  if "already-exists" in parameters.keys():
    alreadyExists=parameters["already-exists"]
  
  #global over-ride
  if options.alreadyExistsGlobal!=None:
    alreadyExists=options.alreadyExistsGlobal
  
  #check if there is a volume with that name already
  volume=getVolume(osc,clients,parameters["volume-name"])
  if volume is not None:
    if alreadyExists=="skip":
      sys.stdout.write("  A volume with the name \""
        +parameters["volume-name"]
        +"\" already exists, skipping creation.\n")
      sys.stdout.flush()
      return
    elif alreadyExists=="overwrite":
      sys.stdout.write("  A volume with the name \""
        +str(parameters["volume-name"])
        +"\" already exists, overwriting.\n")
      sys.stdout.flush()
      deleteVolume({"volume":volume.id},clients,osc,options)
    else:
      raise Exception("a volume with the name \""
        +str(parameters["volume-name"])+"\" already exists.")
  
  #create the volume
  if imageID!=None:
    currentMessage="  Creating volume \""+parameters["volume-name"]\
      +"\" from image \""+parameters["image"]+"\""
  else:
    currentMessage="  Creating an empty volume \""+parameters["volume-name"]+"\""
  
  volume=clients["cinder"].volumes.create(size=parameters["size"]
    ,name=parameters["volume-name"],imageRef=imageID)
  
  volumeID=volume.id
  
  #check that the volume creation has completed
  volumeDoesNotExists=True
  iter=0
  numChecks=int(float(parameters["size"])/gbPers/float(OSCheckWaitTime))
  while volumeDoesNotExists and iter<numChecks:
    
    volume=getVolume(osc,clients,volumeID)
    if isActive(volume):
      volumeDoesNotExists=False
      break
    
    #wait some amount of time before checking again
    sys.stdout.write(currentMessage+" {0}\r".format(
      waitAnimation[iter%len(waitAnimation)]))
    sys.stdout.flush()
    time.sleep(OSCheckWaitTime)
    iter+=1
  
  #check that we haven't timed out
  if iter>=OSNumChecks and volumeDoesNotExists:
    raise Exception("Timed out after waiting "+str(numChecks*OSCheckWaitTime)
      +" s for volume creation to complete.\n")
  
  #notify that creation has completed
  sys.stdout.write("\n    Creation completed.\n")
  return
def addSecurityGroup(parameters,clients,osc,options):
  """Adds a security group to a VM
  """
  
  osc.ensureNovaClient(clients)
  
  #get the requested security group
  securityGroupToAdd=getSecurityGroup(osc,clients,parameters["security-group"])
  
  if securityGroupToAdd==None:
    raise Exception("given security group \""+parameters["security-group"]+"\" not found.")
  if type(securityGroupeToAdd)==type([]):
    raise Exception("multiple security groups found matching \""+parameters["security-group"]+"\".")
  
  #get requested instance
  servers=clients["nova"].servers.list()
  instanceToAttachTo=getVM(osc,clients,parameters["instance"])
  
  #if we don't have the instance report the problem
  if instanceToAttachTo==None:
    raise Exception("given instance \""+parameters["instance"]+"\" not found.")
  if type()==type([]):
    for instance in instanceToAttachTo:
      instance.add_security_group(securityGroupToAdd.name)
  else:
    #add security group
    instanceToAttachTo.add_security_group(securityGroupToAdd.name)
  
  #we are finished, happens really quickly, not going to bother checking 
  #security group added, probably not anything depends on security group 
  #already having been added, at least not on the time frame it takes to add one
  sys.stdout.write("    Security Group Added.\n")
#When creating new action executor functions, add them to this dictionary
#the key will be the XML tag under the <parameters> tag (see actions.xsd 
#scheme for expected xml format).
#One must also add to the parameter-type.xsd to describe the parameters 
#required for that action and add that as a choice under the "parameters-type"
#XML element type. See existing parameter-type.xsd xml type entries, e.g. 
#instance-create.
exeFuncs={
  "create-image-from-volume":createImageFromVolume
  ,"terminate-instance":terminateInstance
  ,"download-image":downloadImage
  ,"create-instance":createInstance
  ,"attach-volume":attachVolume
  ,"associate-floating-ip":associateFloatingIP
  ,"delete-image":deleteImage
  ,"upload-image":uploadImage
  ,"delete-volume":deleteVolume
  ,"create-volume-from-image":createVolume
  ,"create-volume":createVolume
  ,"add-security-group":addSecurityGroup
  ,"release-floating-ip":releaseFloatingIP
  }
