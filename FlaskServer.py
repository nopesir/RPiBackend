from flask import Flask
from flask import json
from flask import request
from flask import jsonify
from flask_cors import CORS
from datetime import date
import datetime
import time
import subprocess
import sqlite3
import re
import requests
import threading
import socket
import getSSID
from os import path
import paho.mqtt.client as mqtt

application = Flask(__name__)
        

# Enable CORS
CORS(application)

# Infos about WiFi
wificheck = {
    'ssid': "ssid",
    'online': False,
    'ip': "127.0.0.1"
}


# Data to be sent to the ESPs with POST
data = {
    'config': {
        'wifi': {
            'sta': {'enable': True, 'ssid': "ssid", 'pass': "pass"},
            'ap': {'enable': False}
        },
        'mqtt': {'enable': True, 'server': "127.0.0.1"}
    }
}

# Shadow AWS to update the state
shadow = {
    'state': {
        'reported': {}
    }
}

# Configuration initial values
config = {
    'ssid': "ssid",
    'password': "pass",
    'ip': "127.0.0.1",
    'apsta': True 
}


# List of enabled/disabled schedules
chronos = []

# Example element in the chronos list
chrono_elem = {
    "id": "Mongoose_XXXXXX",
    "enabled": False,
    "days": {
        "sunday": False,
        "monday": False,
        "tuesday": False,
        "wednesday": False,
        "thursday": False,
        "friday": False,
        "saturday": False
    },
    "temp": 15,
    "start": "00:00",
    "end": "00:00"
}



res = []

# SSIDS retrieved of every Mongoose_XXXXXX
ssids = []

# State of the WiFi: True is STA, False is AP
apsta = True


stop_threads = False

# Clear all stored messages on MosquittoDB
subprocess.run("sudo /home/pi/devs/FlaskServer/clearDB.sh", shell=True, check=True)

time.sleep(5)


esps = dict()

# Modify the WPA_SUPPLICANT file in order to have only one SSID enabled
def set_new_network_wpa(ssid, password):
    with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as f:
        f.write('ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n')
        f.write('update_config=1\n')
        f.write('country=IT\n')
        f.write('\n')
        f.write('network={\n')
        f.write('    ssid="%s"\n' % ssid)
        if password == '':
            f.write('    key_mgmt=NONE\n')
        else:
            f.write('    psk="%s"\n' % password)
            f.write('    key_mgmt=WPA-PSK\n')
        f.write('    priority=1\n')
        f.write('}\n')
        f.close()
        bashCommand = "sudo wpa_cli -i wlan0 reconfigure"
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        subprocess.run("sudo /home/pi/devs/FlaskServer/toSTA.sh", shell=True, check=True)


# ENDPOINT to change from AP to STA mode
@application.route("/tosta", methods=['GET'])
def set_sta(sssssi='', passss=''):
    global apsta
    if (not apsta):
        if("localhost" in str(request.host)):
            with open('/etc/dhcpcd.conf', 'w') as f:
                f.write('hostname\n\n')
                f.write('clientid\n\n')
                f.write('persistent\n\n')
                f.write('option rapid_commit\n\n')
                f.write('option domain_name_servers, domain_name, domain_search, host_name\n\n')
                f.write('option classless_static_routes\n\n')
                f.write('option ntp_servers\n\n')
                f.write('option interface_mtu\n\n')
                f.write('require dhcp_server_identifier\n\n')
                f.write('slaac private\n\n')
                f.write('#interface wlan0\n')
                f.write('#static ip_address=192.168.0.1/24\n')
                f.write('#denyinterfaces wlan0\n')
                f.write('#denyinterfaces eth0\n')
                f.close()
                time.sleep(2.0)
                # For debug
                set_new_network_wpa(sssssi, passss)
                apsta = not apsta
                with open('/home/pi/devs/FlaskServer/save.txt', 'w') as f:
                    f.write(str(apsta))
                    f.close()
                return jsonify({"result": True})
        else:
            return jsonify({"result": False})
    else:
        return jsonify({"result": "Already in STA"})

# Check from the last shutdown if it was AP or STA and restore state
if(path.exists('/home/pi/devs/FlaskServer/save.txt')):
    with open('/home/pi/devs/FlaskServer/save.txt', mode="r") as f:
        for line in f:
            reader = line.split()
            flag = reader[0] == "True"
    if flag:
        apsta = True
        with open('/etc/dhcpcd.conf', 'w') as f:
            f.write('hostname\n\n')
            f.write('clientid\n\n')
            f.write('persistent\n\n')
            f.write('option rapid_commit\n\n')
            f.write('option domain_name_servers, domain_name, domain_search, host_name\n\n')
            f.write('option classless_static_routes\n\n')
            f.write('option ntp_servers\n\n')
            f.write('option interface_mtu\n\n')
            f.write('require dhcp_server_identifier\n\n')
            f.write('slaac private\n\n')
            f.write('#interface wlan0\n')
            f.write('#static ip_address=192.168.0.1/24\n')
            f.write('#denyinterfaces wlan0\n')
            f.write('#denyinterfaces eth0\n')
            f.close()
            time.sleep(1.0)
            bashCommand = "sudo wpa_cli -i wlan0 reconfigure"
            process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
            subprocess.run("sudo /home/pi/devs/FlaskServer/toSTA.sh", shell=True, check=True)
            # For debug
            # set_new_network_wpa("Giggino", "ciaone77")
    else:
        apsta = False
        with open('/etc/dhcpcd.conf', 'w') as f:
            f.write('hostname\n\n')
            f.write('clientid\n\n')
            f.write('persistent\n\n')
            f.write('option rapid_commit\n\n')
            f.write('option domain_name_servers, domain_name, domain_search, host_name\n\n')
            f.write('option classless_static_routes\n\n')
            f.write('option ntp_servers\n\n')
            f.write('option interface_mtu\n\n')
            f.write('require dhcp_server_identifier\n\n')
            f.write('slaac private\n\n')
            f.write('interface wlan0\n')
            f.write('static ip_address=192.168.11.1/24\n')
            f.write('denyinterfaces wlan0\n')
            f.write('denyinterfaces eth0\n')
            f.close()
            time.sleep(1.0)
            subprocess.run("sudo /home/pi/devs/FlaskServer/toAP.sh", shell=True, check=True)


# ENDPOINT to change from AP to STA mode
@application.route("/toap", methods=['GET'])
def set_ap():
    global apsta
    global stop_threads
    if(apsta):
        if("localhost" in str(request.host)):
            stop_threads = True
            with open('/etc/dhcpcd.conf', 'w') as f:
                f.write('hostname\n\n')
                f.write('clientid\n\n')
                f.write('persistent\n\n')
                f.write('option rapid_commit\n\n')
                f.write('option domain_name_servers, domain_name, domain_search, host_name\n\n')
                f.write('option classless_static_routes\n\n')
                f.write('option ntp_servers\n\n')
                f.write('option interface_mtu\n\n')
                f.write('require dhcp_server_identifier\n\n')
                f.write('slaac private\n\n')
                f.write('interface wlan0\n')
                f.write('static ip_address=192.168.11.1/24\n')
                f.write('denyinterfaces wlan0\n')
                f.write('denyinterfaces eth0\n')
                f.close()
                time.sleep(1.0)
                subprocess.run("sudo /home/pi/devs/FlaskServer/toAP.sh", shell=True, check=True)
                apsta = not apsta
                with open('/home/pi/devs/FlaskServer/save.txt', 'w') as f:
                    f.write(str(apsta))
                    f.close()
                return jsonify({"result": True})
        else:
            return jsonify({"result": False})
    else:
        return jsonify({"result": "Already in AP"})


# Take the local IP of the raspberry
# in order to send it to the Mongoose_XXXXXX
# and have it in the configuration
def retrieve_ip():
    return ([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)),s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0])


# Function used to check the WiFi status
def check_wifi():
    global config
    global wificheck
    global apsta
    res = False

    try:
        # run 'sudo iwgetid -r' into the bash
        out2 = subprocess.check_output(["sudo", "iwgetid", "-r"])
        wificheck['online'] = True
        wificheck['ssid'] = re.sub('\\n', '', out2.decode('utf-8'))
        wificheck['ip'] = retrieve_ip()
        wificheck['apsta'] = apsta
        config['ssid'] = wificheck['ssid']
        config['ip'] = wificheck['ip']
        res = True

    except subprocess.CalledProcessError as e:
        wificheck['online'] = False
        wificheck['ssid'] = "none"
        wificheck['ip'] = "127.0.0.1"
        wificheck['apsta'] = apsta
        config['ssid'] = wificheck['ssid']
        config['ip'] = wificheck['ip']
        res = False

    return res


# Once \connect finishes and the device is in STA mode, checks if there are failures and switch automatically to AP mode
def ap_security_switch():
    global apsta
    global wificheck
    global stop_threads
    while True:
        if apsta:
            print(' * Checking WiFi...')
            if not wificheck['online']:
                set_ap_recovery()
                return
        if stop_threads:
            break
        time.sleep(2)

t = threading.Timer(2.0, ap_security_switch)


# ENDPOINT to connect the system, search for Mongoose_XXXXXX and configure them 
@application.route("/connect", methods=['GET'])
def connect():
    global ssids
    global t
    global chronos
    global stop_threads
    if("localhost" in str(request.host)):
        
        stop_threads = True
        
        try:
            t.join()
        except RuntimeError as e:
            print(e)
        
        
        ssid = request.args.get('ssid')
        passwd = request.args.get('passwd')
        chronos = []
        # Delete shadow state on Amazon AWS
        mqtt_client.publish("local/things/RaspberryPi/shadow/delete", qos=1)

        time.sleep(4)

        # Clear all stored messages on MosquittoDB
        subprocess.run("sudo /home/pi/devs/FlaskServer/clearDB.sh", shell=True, check=True)

        time.sleep(4)

        all_ssids = [x for x in getSSID.main()]

        found = [x for x in all_ssids if ssid == x['Name']]

        if not found:
            stop_threads = True
            return jsonify({"result": False, "message": "SSID not found"})


        time.sleep(2)
        # Connect to the network to retrieve the IP
        if(not apsta):
            set_sta_from_ap(ssid, passwd)
        else:
            set_new_network_wpa(ssid=ssid, password=passwd)
        
        time.sleep(5)

        strin = " * Checking wifi..."
        i = 0
        while not check_wifi():
            i += 1
            strin = strin + "."
            time.sleep(2)
            print(strin + "\r")
            if i > 10:
                break
            pass

        if i > 10:
            stop_threads = True
            return jsonify({"result": False, "message": "Invalid password"})

        print(" * Master SSID: " + ssid)

        time.sleep(1)

        ssids = []
        # Search for networks and filter by SSIDs that starts with "Mongoose_"
        ssids = [x for x in all_ssids if "Mongoose_" in x['Name']]

        # Save the data to be sent to the ESPs
        data['config']['wifi']['sta']['ssid'] = ssid
        data['config']['wifi']['sta']['pass'] = passwd
        data['config']['mqtt']['server'] = retrieve_ip()
        
        # For each Mongoose_XXXXXX
        for x in ssids:
            # Connect to it
            set_new_network_wpa(ssid=x['Name'], password="Mongoose")
            strin = " * Checking wifi..."

            time.sleep(7)
            # Wait for the connection
            while not check_wifi():
                strin = strin + "."
                time.sleep(2)
                print(strin + "\r")
                pass

            print(" * Configuring " + x['Name'] + "...")

            # POST the data to Mongoose OS with IP, SSID, PASS
            r = requests.post('http://192.168.4.1/rpc/Config.Set', json=data)

            time.sleep(2)
            # POST the save and reboot command for Mongoose OS
            r2 = requests.post('http://192.168.4.1/rpc/Config.Save', json={'reboot': True})


        if not ssids:
            stop_threads = True
            return jsonify({"result": False, "message": "Connected, no device was found"})
        # At the end, connect to the network
        set_new_network_wpa(ssid=ssid, password=passwd)

        time.sleep(3)

        # Wait for the connection
        while not check_wifi():
            time.sleep(2)
            pass

        print(" * Connected to " + ssid + " and ready!")
        config['ssid'] = ssid
        config['pass'] = passwd
        config['apsta'] = apsta

        #for x in ssids:
        #    temp = chrono_elem.copy()
        #    temp['id'] = x['Name']
        #    chronos.append(temp)


        config['chonos'] = chronos

        upload_config(config)

        stop_threads = False
        # Start standalone mode recovery thread
        t.start()

        print("Connect ended")
        # Return the correctly connected devices as a vector of dict
        return jsonify({"result": True, "message": ssids})
    else:
        return jsonify({"result": False, "message": "Access denied, try from the RPi"})


# Flask ENDPOINT:
# GET to retrieve the status of the WiFi connection
@application.route("/wificheck", methods=['GET'])
def ret_wifi_status():
    global stop_threads
    if not stop_threads:
        check_wifi()
    return jsonify(wificheck)

# Flask ENDPOINT:
# GET to retrieve the Mongoose_XXXXXX correctly initialized bu the /connect
@application.route("/ssids", methods=['GET'])
def take_ssids():
    return json.dumps(ssids)


# ENDPOINT to retrieve graphs data
@application.route("/graphs", methods=['GET'])
def take_graph():
    global res
    conn = sqlite3.connect('/home/pi/local.db')
    c = conn.cursor()
    c.execute("""SELECT * FROM measured""")
    conn.commit()
    resu = c.fetchall()
    conn.close()

    conn = sqlite3.connect('/home/pi/local.db')
    d = conn.cursor()
    d.execute("""SELECT * FROM desired""")
    conn.commit()
    resu_b = d.fetchall()
    conn.close()

    listOfStr = ["id", "timestamp", "measured", "hum"]
    listOfStr_b = ["id", "timestamp", "desired"]



    res = []
    res_b = []

    for x in resu:
        zipbObj = zip(listOfStr, x)
        dictOfWords = dict(zipbObj)
        res.append(dictOfWords)

    for y in resu_b:
        zipbObj_b = zip(listOfStr_b, y)
        dictOfWords_b = dict(zipbObj_b)
        res_b.append(dictOfWords_b)

    res_tot = []
    res_tot.append(res)
    res_tot.append(res_b)

    return jsonify(res_tot)



# Flask ENDPOINT:
# POST to modify the settings for a specific Mongoose_XXXXXX
# GET to retrieve all the settings of all the Mongoose_XXXXXX
@application.route("/chrono", methods=['POST', 'GET'])
def chrono_set():
    global chronos
    global wificheck
    global chrono_elem
    if request.method == 'POST':
        j_post = request.get_json()
        founds = []
        founds = [x for x in chronos if str(x['id']) in str(j_post['id'])]
        print(founds)
        if not founds:
            chronos.append(j_post)
        else:
            x = founds[0]
            for n, i in enumerate(chronos):
                if i['id'] == x['id']:
                    chronos[n]['days'] = j_post['days']
                    chronos[n]['enabled'] = j_post['enabled']
                    chronos[n]['start'] = str(j_post['start'])
                    chronos[n]['end'] = str(j_post['end'])
                    chronos[n]['temp'] = j_post['temp']
                    chronos[n]['id'] = j_post['id']
        
        shadow['state']['reported']['chronos'] = chronos
        
        config['chonos'] = chronos
        if wificheck['online']:
            upload_config(config)
        shadow['state']['reported']['wifi'] = wificheck
        mqtt_client.publish("local/things/RaspberryPi/shadow/update", json.dumps(shadow), qos=1)
        return jsonify({"result": True})
    else:
        return jsonify(chronos)


# MQTT callback after connection, here there are the subscribes
def on_connect(mqtt_client, obj, flags, rc):
    mqtt_client.subscribe("+/event/state", 1)
    mqtt_client.subscribe("+/event/status", 1)
    mqtt_client.subscribe("+/event/setTemp", 1)
    print(" * MQTT Subscribed!")



def on_disconnect(mqtt_client, obj, flags, rc):
    print("client disconnected")
    time.sleep(10)
    mqtt_client.reconnect()
    print("client reconnected")

# MQTT callback for every message published on every subscribed topic
def on_message(mqtt_client, obj, msg):
    global esps
    global ssids
    global shadow
    global config
    if(str(msg.topic[-6:]) == "status"):
        if((msg.payload).decode('utf-8') == "online"):
            esps[str(msg.topic[:15])]['online'] = True
        else:
            esps[str(msg.topic[:15])]['online'] = False
        mqtt_client.publish("local/" + str(msg.topic), (msg.payload).decode('utf-8'), retain=False)
    elif(str(msg.topic[-7:]) == "setTemp"):
        
        mongoose = str(msg.topic[:15])
        value = (msg.payload).decode('utf-8')

        print(mongoose)
        print(value)

        conn = sqlite3.connect('/home/pi/local.db')
        c = conn.cursor()
        c.execute("""INSERT INTO desired (id, value) VALUES ((?), (?))""", (mongoose, value))
        conn.commit()
        conn.close()

    else:
        flag = True
        for x in ssids:
            if(str(x['Name']) == str(msg.topic[:15])):
                flag = False
        
        if flag:
            ssids.append({"Address": "30:AE:A4:75:25:B1", "Channel": "6", "Encryption": "WEP", "Name": str(msg.topic[:15]), "Quality": " 97 %", "Signal": "-42 dBm"})


        for x in ssids:
            if(str(x['Name']) == str(msg.topic[:15])):
                x['state'] = json.loads(msg.payload)

        esps[str(msg.topic[:15])] = json.loads(msg.payload)
        ide = str(msg.topic[:15])
        temp = str(esps[str(msg.topic[:15])]['currTemp'])
        hum = str(esps[str(msg.topic[:15])]['humidity'])
        conn = sqlite3.connect('/home/pi/local.db')
        c = conn.cursor()
        c.execute("""INSERT INTO measured (id, temp, hum) VALUES ((?), (?), (?))""", (ide, temp, hum))
        conn.commit()
        conn.close()
        mqtt_client.publish("local/" + str(msg.topic), (msg.payload).decode('utf-8'), retain=False)
    
    shadow['state']['reported']['esps'] = ssids
    config['esps'] = esps
    if wificheck['online']:
        upload_config(config)
    shadow['state']['reported']['wifi'] = wificheck
    mqtt_client.publish("local/things/RaspberryPi/shadow/update", json.dumps(shadow), qos=1)






# MQTT callbacks and configuration
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.on_disconnect = on_disconnect
mqtt_client.connect("localhost", 1884)
mqtt_client.loop_start()



def on_connect_aws(mqtt_client_aws, obj, flags, rc):
    mqtt_client_aws.subscribe("local/+/event/onoff", 1)
    mqtt_client_aws.subscribe("local/+/event/setTemp", 1)
    mqtt_client_aws.subscribe("local/+/event/setname", 1)
    mqtt_client_aws.subscribe("local/rpi/chrono/set", 1)
    print(" * MQTT from AWS Subscribed!")

def on_disconnect_aws(mqtt_client_aws, obj, flags, rc):
    time.sleep(10)
    mqtt_client_aws.reconnect()


def on_message_aws(mqtt_client_aws, obj, msg):
    global chronos
    global wificheck
    global chrono_elem
    if(str(msg.topic[-5:]) == "onoff"):
        mqtt_client_aws.publish(str(msg.topic[-27:]), (msg.payload).decode('utf-8'), retain=True)
    elif(str(msg.topic[-7:]) == "setTemp"):
        mqtt_client_aws.publish(str(msg.topic[-29:]), (msg.payload).decode('utf-8'), retain=True)
    elif(str(msg.topic[-7:]) == "setname"):
        mqtt_client_aws.publish(str(msg.topic[-29:]), (msg.payload).decode('utf-8'), retain=True)
    elif(str(msg.topic[-3:]) == "set"):

        j_post = json.loads(str((msg.payload).decode('utf-8')).replace("\\", ""))
        print("json loaded from chrono/set")
        founds = []
        founds = [x for x in chronos if str(x['id']) in str(j_post['id'])]
        print(founds)
        if not founds:
            chronos.append(j_post)
        else:
            x = founds[0]
            for n, i in enumerate(chronos):
                if i['id'] == x['id']:
                    chronos[n]['days'] = j_post['days']
                    chronos[n]['enabled'] = j_post['enabled']
                    chronos[n]['start'] = str(j_post['start'])
                    chronos[n]['end'] = str(j_post['end'])
                    chronos[n]['temp'] = j_post['temp']
        
        shadow['state']['reported']['chronos'] = chronos
        
        config['chonos'] = chronos
        if wificheck['online']:
            upload_config(config)
        shadow['state']['reported']['wifi'] = wificheck
    
    mqtt_client.publish("local/things/RaspberryPi/shadow/update", json.dumps(shadow), qos=1)



mqtt_client_aws = mqtt.Client()
mqtt_client_aws.on_connect = on_connect_aws
mqtt_client_aws.on_message = on_message_aws
mqtt_client_aws.on_disconnect = on_disconnect_aws
mqtt_client_aws.connect("localhost", 1882)
mqtt_client_aws.loop_start()


def upload_config(config):
    global apsta
    data = {
        'device_mac': "D4:25:8B:D9:E7:2F", 
        'nickname': "nopesir",
        'configuration': {}
    }
    API_URI = "http://ec2-34-220-162-82.us-west-2.compute.amazonaws.com:5002/"

    if wificheck['online']:
        response = requests.post(API_URI+"auth", data=json.dumps({'username':'PL19-18', 'password':'raspbian'}), headers={'Content-Type': 'application/json'})
    else:
        return None
    
    if not json.loads(response.text)['access_token']:
    	print("Could not obtain the API_TOKEN!")
    	return None
    
    API_TOKEN = json.loads(response.text)['access_token']


    data['configuration'] = config


    response = requests.post(API_URI+"user/PL19-18/devices", data=json.dumps(data), headers={"Authorization": "JWT " + API_TOKEN, 'Content-Type': 'application/json'})

def download_config():
    global wificheck
    API_URI = "http://ec2-34-220-162-82.us-west-2.compute.amazonaws.com:5002/"

    if wificheck['online']:
        response = requests.post(API_URI+"auth", data=json.dumps({'username':'PL19-18', 'password':'raspbian'}), headers={'Content-Type': 'application/json'})
    else:
        return {}

    if not json.loads(response.text)['access_token']:
    	print("Could not obtain the API_TOKEN!")
    	return None
    
    API_TOKEN = json.loads(response.text)['access_token']

    response = requests.get(API_URI+"user/PL19-18/devices", headers={"Authorization": "JWT " + API_TOKEN, 'Content-Type': 'application/json'})

    return response.json()

# Thread that checks if some schedule is set into the 'chronos' object
def runsched():
    # Restart this fuction after 30 seconds
    while True:

    # Take the local hour and transform it as a string
        now = datetime.datetime.now()
        ore = now.hour
        minuti = now.minute

        if (ore < 10 and ore > 0):
            ore = '0' + str(ore)
        
        if (minuti < 10 and minuti > 0):
            minuti = '0' + str(minuti)

        
        clock = str(ore) + ":" + str(minuti)

        print(clock)

        # Fo every Mongoose_XXXXXX saved in the /connect
        for x in chronos:
            if x['enabled'] == False:
                print(" * " + x['id'] + " chrono is disabled")
            else:
                print(" * " + x['id'] + " chrono is enabled")
                if date.today().weekday() == 0:
                    if bool(x['days']['monday']) == True:
                        if str(x['start']) == str(clock):
                            print(" * Time to enable " + x['id'])
                            mqtt_client.publish(str(x['id']) + "/event/onoff", "on", retain=True)
                            mqtt_client.publish(str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                        if str(x['end']) == str(clock):
                            print(" * Time to disable " + x['id'])
                            mqtt_client.publish(x['id'] + "/event/onoff", "off", retain=True)
                if date.today().weekday() == 1:
                    if bool(x['days']['tuesday']) == True:
                        if str(x['start']) == str(clock):
                            print(" * Time to enable " + x['id'])
                            mqtt_client.publish(str(x['id']) + "/event/onoff", "on", retain=True)
                            mqtt_client.publish(str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                        if str(x['end']) == str(clock):
                            print(" * Time to disable " + x['id'])
                            mqtt_client.publish(x['id'] + "/event/onoff", "off", retain=True)
                if date.today().weekday() == 2:
                    if bool(x['days']['wednesday']) == True:
                        if str(x['start']) == str(clock):
                            print(" * Time to enable " + x['id'])
                            mqtt_client.publish(str(x['id']) + "/event/onoff", "on", retain=True)
                            mqtt_client.publish(str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                        if str(x['end']) == str(clock):
                            print(" * Time to disable " + x['id'])
                            mqtt_client.publish(x['id'] + "/event/onoff", "off", retain=True)
                if date.today().weekday() == 3:
                    if bool(x['days']['thursday']) == True:
                        if str(x['start']) == str(clock):
                            print(" * Time to enable " + x['id'])
                            mqtt_client.publish(str(x['id']) + "/event/onoff", "on", retain=True)
                            mqtt_client.publish(str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                        if str(x['end']) == str(clock):
                            print(" * Time to disable " + x['id'])
                            mqtt_client.publish(x['id'] + "/event/onoff", "off", retain=True)
                if date.today().weekday() == 4:
                    if bool(x['days']['friday']) == True:
                        if str(x['start']) == str(clock):
                            print(" * Time to enable " + x['id'])
                            mqtt_client.publish(str(x['id']) + "/event/onoff", "on", retain=True)
                            mqtt_client.publish(str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                        if str(x['end']) == str(clock):
                            print(" * Time to disable " + x['id'])
                            mqtt_client.publish(x['id'] + "/event/onoff", "off", retain=True)
                if date.today().weekday() == 5:
                    if bool(x['days']['saturday']) == True:
                        if str(x['start']) == str(clock):
                            print(" * Time to enable " + x['id'])
                            mqtt_client.publish(str(x['id']) + "/event/onoff", "on", retain=True)
                            mqtt_client.publish(str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                        if str(x['end']) == str(clock):
                            print(" * Time to disable " + x['id'])
                            mqtt_client.publish(x['id'] + "/event/onoff", "off", retain=True)
                if date.today().weekday() == 6:
                    if bool(x['days']['sunday']) == True:
                        if str(x['start']) == str(clock):
                            print(" * Time to enable " + x['id'])
                            mqtt_client.publish(str(x['id']) + "/event/onoff", "on", retain=True)
                            mqtt_client.publish(str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                        if str(x['end']) == str(clock):
                            print(" * Time to disable " + x['id'])
                            mqtt_client.publish(x['id'] + "/event/onoff", "off", retain=True)
        time.sleep(25)

t_sched = threading.Timer(2.0, runsched)
t_sched.start()
def set_ap_recovery():
    global apsta
    if(apsta):
        with open('/etc/dhcpcd.conf', 'w') as f:
            f.write('hostname\n\n')
            f.write('clientid\n\n')
            f.write('persistent\n\n')
            f.write('option rapid_commit\n\n')
            f.write('option domain_name_servers, domain_name, domain_search, host_name\n\n')
            f.write('option classless_static_routes\n\n')
            f.write('option ntp_servers\n\n')
            f.write('option interface_mtu\n\n')
            f.write('require dhcp_server_identifier\n\n')
            f.write('slaac private\n\n')
            f.write('interface wlan0\n')
            f.write('static ip_address=192.168.11.1/24\n')
            f.write('denyinterfaces wlan0\n')
            f.write('denyinterfaces eth0\n')
            f.close()
            time.sleep(1.0)
            subprocess.run("sudo /home/pi/devs/FlaskServer/toAP.sh", shell=True, check=True)
            apsta = not apsta
            with open('/home/pi/devs/FlaskServer/save.txt', 'w') as f:
                f.write(str(apsta))
                f.close()


def set_sta_from_ap(sssssi='', passss=''):
    global apsta
    if (not apsta):
        with open('/etc/dhcpcd.conf', 'w') as f:
            f.write('hostname\n\n')
            f.write('clientid\n\n')
            f.write('persistent\n\n')
            f.write('option rapid_commit\n\n')
            f.write('option domain_name_servers, domain_name, domain_search, host_name\n\n')
            f.write('option classless_static_routes\n\n')
            f.write('option ntp_servers\n\n')
            f.write('option interface_mtu\n\n')
            f.write('require dhcp_server_identifier\n\n')
            f.write('slaac private\n\n')
            f.write('#interface wlan0\n')
            f.write('#static ip_address=192.168.0.1/24\n')
            f.write('#denyinterfaces wlan0\n')
            f.write('#denyinterfaces eth0\n')
            f.close()
            time.sleep(1.0)
            # For debug
            set_new_network_wpa(sssssi, passss)
            apsta = not apsta
            with open('/home/pi/devs/FlaskServer/save.txt', 'w') as f:
                f.write(str(apsta))
                f.close()


if __name__ == "__main__":
    application.run(host='0.0.0.0')
