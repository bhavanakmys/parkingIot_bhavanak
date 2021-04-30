import datetime
import ibm_boto3
from ibm_botocore.client import Config, ClientError
import cv2

import numpy as np
import sys
import ibmiotf.application
import ibmiotf.device
import random
import time

from cloudant.client import Cloudant
from cloudant.error import CloudantException 
from cloudant.result import Result, ResultByKey
#Provide your IBM Watson Device Credentials
organization = "14lzt6"
deviceType = "parkingiot"
deviceId = "1234"
authMethod = "token"
authToken = "aFYUO38_7(aL&)1s5L"



def myCommandCallback(cmd):
        print("Command received: %s" % cmd.data)
        print(cmd.data['command'])
       
        if(cmd.data['command']=="Parkin"):
                print("car parked in")
                
        if(cmd.data['command']=="Parkout"):
                print("car parked out")
                

        

try:
	deviceOptions = {"org": organization, "type": deviceType, "id": deviceId, "auth-method": authMethod, "auth-token": authToken}
	deviceCli = ibmiotf.device.Client(deviceOptions)
	#..............................................
	
except Exception as e:
	print("Caught exception connecting device: %s" % str(e))
	sys.exit()

# Connect and send a datapoint "hello" with value "world" into the cloud as an event of type "greeting" 10 times
deviceCli.connect()
face_classifier=cv2.CascadeClassifier("haar-face.xml")


#It will read the first frame/image of the video
video=cv2.VideoCapture(0)



COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud" # Current list avaiable at https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints
COS_API_KEY_ID = "BV78DSpY8avIOyG_nfkIL6MyZLWvLJTRyBllwqyo2HKq" # eg "W00YiRnLW4a3fTjMB-oiB-2ySfTrFBIQQWanc--P3byk"
COS_AUTH_ENDPOINT = "https://iam.cloud.ibm.com/identity/token"
COS_RESOURCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/2c8cf62a44f04258af9804a4b2c35c84:c03f5523-5753-41f5-bddd-5e5090e1b486::"


client = Cloudant("apikey-v2-1gplxlnvd4le7qrm439xmfrnl63kh1a86b815vkgqqlq", "a9be84c05f7c3e4c45116e389872de36", url="https://apikey-v2-1gplxlnvd4le7qrm439xmfrnl63kh1a86b815vkgqqlq:a9be84c05f7c3e4c45116e389872de36@9675e673-f840-4422-aef4-c8a35b86a457-bluemix.cloudantnosqldb.appdomain.cloud")
client.connect()
database_name = "datapark"

# Create resource
cos = ibm_boto3.resource("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_RESOURCE_CRN,
    ibm_auth_endpoint=COS_AUTH_ENDPOINT,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)
        
        
def multi_part_upload(bucket_name, item_name, file_path):
    try:
        print("Starting file transfer for {0} to bucket: {1}\n".format(item_name, bucket_name))
        # set 5 MB chunks
        part_size = 1024 * 1024 * 5

        # set threadhold to 15 MB
        file_threshold = 1024 * 1024 * 15

        # set the transfer threshold and chunk size
        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold=file_threshold,
            multipart_chunksize=part_size
        )

        # the upload_fileobj method will automatically execute a multi-part upload
        # in 5 MB chunks for all files over 15 MB
        with open(file_path, "rb") as file_data:
            cos.Object(bucket_name, item_name).upload_fileobj(
                Fileobj=file_data,
                Config=transfer_config
            )

        print("Transfer for {0} Complete!\n".format(item_name))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to complete multi-part upload: {0}".format(e))
        

       
while True:
    #capture the first frame
    check,frame=video.read()
    gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    #detect the faces from the video using detectMultiScale function
    faces=face_classifier.detectMultiScale(gray,1.3,5)
    
    
    #drawing rectangle boundries for the detected face
    for(x,y,w,h) in faces:
        cv2.rectangle(frame, (x,y), (x+w,y+h), (127,0,255), 2)
        cv2.imshow('Face detection', frame)
        picname=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
        picname=picname+".jpg"
        pic=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
        cv2.imwrite(picname,frame)
        vehicle=1
        my_database = client.create_database(database_name)        
        multi_part_upload("cloud-object-storage-wo-cos-standard-c7f",picname,pic+".jpg")      
        if my_database.exists():
            print("'{database_name}' successfully created.")
            json_document = {
                    "_id": pic,
                    "link":COS_ENDPOINT+"/cloud-object-storage-wo-cos-standard-c7f/"+picname
                    }
            new_document = my_database.create_document(json_document)
            if new_document.exists():
                print("Document '{new_document}' successfully created.")
        time.sleep(1)
        freeslot=30
        engslot = 50
        totalslot=80
        data = {'d':{'freeslot' : freeslot, 'engslot': engslot,'totalslot':totalslot }}
        #print data
        def myOnPublishCallback():
            print ("Published data to IBM Watson")

        success = deviceCli.publishEvent("Data", "json", data, qos=0, on_publish=myOnPublishCallback)
        if not success:
            print("Not connected to IoTF")
        time.sleep(1)
        deviceCli.commandCallback = myCommandCallback
        person=0
    #waitKey(1)- for every 1 millisecond new frame will be captured
        Key=cv2.waitKey(1)
        if Key==ord('q'):
        #release the camera
            video.release()
        #destroy all windows
            cv2.destroyAllWindows()
            break
deviceCli.disconnect()
    
