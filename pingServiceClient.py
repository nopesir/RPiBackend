from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import argparse
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

    print('Published topic %s: %s\n' % (topic, messageJson))

# Custom MQTT message callback
def customCallback(client, userdata, message):
    print("Received a new message: ")
    messageContent = json.loads(message.payload.decode('utf-8'))
    messageData = messageContent['event']
    print(messageContent)
    print(messageData['message'])
    print("Sequence ", messageData['sequence'])
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")
    if messageContent['event_id'] == 0:
        replyToPing(messageData['sequence'])


# Read in command-line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--endpoint", action="store", default="a3cezb6rg1vyed-ats.iot.us-west-2.amazonaws.com", dest="host", help="Your AWS IoT custom endpoint")
parser.add_argument("-r", "--rootCA", action="store", default="root-CA.crt", dest="rootCAPath", help="Root CA file path")
parser.add_argument("-c", "--cert", action="store", default="PL-student.cert.pem", dest="certificatePath", help="Certificate file path")
parser.add_argument("-k", "--key", action="store", default="PL-student.private.key", dest="privateKeyPath", help="Private key file path")
parser.add_argument("-p", "--port", action="store", dest="port", type=int, help="Port number override")
parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,
                    help="Use MQTT over WebSocket")
parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="pl19-18",
                    help="Targeted client id")
parser.add_argument("-t", "--topic", action="store", dest="topic", default="pl19/event", help="Event topic")
parser.add_argument("-m", "--mode", action="store", dest="mode", default="both",
                    help="Operation modes: %s"%str(AllowedActions))
parser.add_argument("-M", "--message", action="store", dest="message", default="Hello World!",
                    help="Message to publish")

args = parser.parse_args()
host = args.host
rootCAPath = args.rootCAPath
certificatePath = args.certificatePath
privateKeyPath = args.privateKeyPath
port = args.port
useWebsocket = args.useWebsocket
clientId = args.clientId
topic = args.topic

if args.mode not in AllowedActions:
    parser.error("Unknown --mode option %s. Must be one of %s" % (args.mode, str(AllowedActions)))
    exit(2)

if args.useWebsocket and args.certificatePath and args.privateKeyPath:
    parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
    exit(2)

if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
    parser.error("Missing credentials for authentication.")
    exit(2)

# Port defaults
if args.useWebsocket and not args.port:  # When no port override for WebSocket, default to 443
    port = 443
if not args.useWebsocket and not args.port:  # When no port override for non-WebSocket, default to 8883
    port = 8883

# Configure logging
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)

# Init AWSIoTMQTTClient
myAWSIoTMQTTClient = None
if useWebsocket:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId, useWebsocket=True)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath)
else:
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
if args.mode == 'both' or args.mode == 'subscribe':
    myAWSIoTMQTTClient.subscribe("pl19/notification", 1, customCallback)
    print("subscribed!")

time.sleep(2)
