from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import json
import datetime 
AllowedActions = ['both', 'publish', 'subscribe']

def replyToPing(sequence):
    pingData = {}

    pingData['sequence'] = sequence
    pingData['message'] = "Ping response."

    message = {}
    message['device_mac'] = "D4:25:8B:D9:E7:2F"
    message['timestamp'] = str(datetime.datetime.now())
    message['event_id'] = 1
    message['event'] = pingData
    messageJson = json.dumps(message)
    myAWSIoTMQTTClient.publishAsync("pl19/event", messageJson, 1)

    print(' * Ping answered!')

# Custom MQTT message callback
def customCallback(client, userdata, message):
    print("* Received ping!")
    messageContent = json.loads(message.payload.decode('utf-8'))
    messageData = messageContent['event']
    if messageContent['event_id'] == 0:
        replyToPing(messageData['sequence'])



host = "a3cezb6rg1vyed-ats.iot.us-west-2.amazonaws.com"
rootCAPath = "root-CA.crt"
certificatePath = "PL-student.cert.pem"
privateKeyPath = "PL-student.private.key"
port = 8883
clientId = "pl19-18"
topic = "pl19/event"



# Configure logging
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)

# Init AWSIoTMQTTClient
myAWSIoTMQTTClient = None
myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
myAWSIoTMQTTClient.configureEndpoint(host, port)
myAWSIoTMQTTClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

myAWSIoTMQTTClient.connect()
myAWSIoTMQTTClient.subscribe("pl19/notification", 1, customCallback)
print(" * Ping subscribed!")

time.sleep(2)
