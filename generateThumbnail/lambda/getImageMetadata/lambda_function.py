# define Image allowed type as enviroment variable if needed "Allowed_Types" ex: jpg,png 
# and define max file size in kb if needed as Max_Size
import json
import os

def getimageMetadata(event, context):
    imageMetadata = {}
    imageMetadata["bucketName"]= event["detail"]["bucket"]["name"]
    imageMetadata["objectName"]= event["detail"]["object"]["key"]
    imageMetadata["objectSize"]= event["detail"]["object"]["size"]
    
    fileExtension=event["detail"]["object"]["key"]
    fileSize=event["detail"]["object"]["size"]
    fileExtension=fileExtension.split(".")[1]
    EnvAllowedTypes = {}
    
    TmpEnvAllowedTypes = os.environ.get('Allowed_Types')
    
    # Check if Enviroment Variable exists and if yes remove all whitespaces for the string and change to lower and if not intialize empty list
    if TmpEnvAllowedTypes is None:
        TmpEnvAllowedTypes = {}
    else:
        TmpEnvAllowedTypes = TmpEnvAllowedTypes.strip()
    
    # check if the list is empty or not and if not removed in between whitespaces for each item in the list if yes use default values
    if (len(TmpEnvAllowedTypes) > 0):
        EnvAllowedTypes = [x.strip() for x in TmpEnvAllowedTypes.split(',')]
    else:
        EnvAllowedTypes = ["jpeg","png","jpg"]
    
    #Check if Max Size if configured and if not use default value
    MaxSize = os.environ.get('Max_Size')
    if MaxSize is None:
        MaxSize = 700000
    else:
        MaxSize = int(MaxSize)


    # Check if the image extension is in the list and if yes make sure it's less than the needed size
    if fileExtension in EnvAllowedTypes:
        if (fileSize <= MaxSize):
            imageMetadata["isValidImage"] = 1
        else:
            imageMetadata["isValidImage"] = 0
    else:
        imageMetadata["isValidImage"] = 0
        
    
    return imageMetadata,event