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
import paho.mqtt.client as mqtt

app = Flask(__name__)

# To resolve CORS error on Angular
CORS(app)


wificheck = {
    'ssid': "ssid",
    'online': False,
    'ip': "127.0.0.1"
}


data = {
    'config': {
        'wifi': {
            'sta': {'enable': True, 'ssid': "ssid", 'pass': "pass"},
            'ap': {'enable': False}
        },
        'mqtt': {'enable': True, 'server': "127.0.0.1"}
    }
}


shadow = {
    'state': {
        'reported': {}
    }
}


chronos = []


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


ssids = []


esps = dict()


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
        subprocess.run("sudo ./toSTA.sh", shell=True, check=True)


def set_sta():
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
        subprocess.run("./toSTA.sh", shell=True, check=True)


def set_ap():
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
        f.write('static ip_address=192.168.0.1/24\n')
        f.write('denyinterfaces wlan0\n')
        f.write('denyinterfaces eth0\n')
        f.close()
        time.sleep(1.0)
        subprocess.run("./toAP.sh", shell=True, check=True)

# Take the local IP of the raspberry
# in order to send it to the Mongoose_XXXXXX


def retrieve_ip():
    return ([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                          if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)),
                                                                s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET,
                                                                                                                       socket.SOCK_DGRAM)]][0][1]]) if l][0][0])


# Function used to check the WiFi status
def check_wifi():
    res = False
    try:
        # run 'sudo iwgetid -r' into the bash
        out2 = subprocess.check_output(["sudo", "iwgetid", "-r"])
        wificheck['online'] = True
        wificheck['ssid'] = re.sub('\\n', '', out2.decode('utf-8'))
        wificheck['ip'] = retrieve_ip()
        res = True

    except subprocess.CalledProcessError as e:
        wificheck['online'] = False
        wificheck['ssid'] = "none"
        wificheck['ip'] = "none"
        res = False

    return res


@app.route("/connect", methods=['GET'])
def connect():
    global ssids

    ssid = request.args.get('ssid')
    passwd = request.args.get('passwd')

    # Delete shadow state on Amazon AWS
    mqtt_client.publish("local/things/RaspberryPi/shadow/delete", qos=1)

    # Clear all stored messages on MosquittoDB
    subprocess.run("sudo ./clearDB.sh", shell=True, check=True)

    # Reset the object
    esps = {}

    # Connect to the network to retrieve the IP
    set_new_network_wpa(ssid=ssid, password=passwd)
    time.sleep(3)
    strin = " * Checking wifi..."
    while not check_wifi():
        strin = strin + "."
        time.sleep(3)
        print(strin + "\r")
        pass

    print(" * Master SSID: " + ssid)

    # Search for networks and filter by SSIDs that starts with "Mongoose_"
    ssids = [x for x in getSSID.main() if "Mongoose_" in x['Name']]

    # Save the data to be sent to the ESPs
    data['config']['wifi']['sta']['ssid'] = ssid
    data['config']['wifi']['sta']['pass'] = passwd
    data['config']['mqtt']['server'] = retrieve_ip()

    # For each Mongoose_XXXXXX
    for x in ssids:

        # Connect to it
        set_new_network_wpa(ssid=x['Name'], password="Mongoose")
        strin = " * Checking wifi..."

        # Wait for the connection
        while not check_wifi():
            strin = strin + "."
            time.sleep(3)
            print(strin + "\r")
            pass

        print(" * Configuring " + x['Name'] + "...")

        # POST the data to Mongoose OS with IP, SSID, PASS
        r = requests.post('http://192.168.4.1/rpc/Config.Set', json=data)
        time.sleep(5)
        # POST the save and reboot command for Mongoose OS
        r2 = requests.post(
            'http://192.168.4.1/rpc/Config.Save', json={'reboot': True})

    # At the end, connect to the network
    set_new_network_wpa(ssid=ssid, password=passwd)

    time.sleep(3)

    # Wait for the connection
    while not check_wifi():
        time.sleep(2)
        pass

    print(" * Connected to " + ssid + " and ready!")

    # Take the ids of every connected device in order to check for time scheduling
    for x in ssids:
        temp = {}
        temp = chrono_elem.copy()
        temp['id'] = x['Name']
        chronos.append(temp)

    # Transform the JSON into a string
    resp = json.dumps(ssids)

    # Start the scheduling thread
    runsched()

    # Return the correctly connected devices as a vector of dict
    return resp


# Flask ENDPOINT:
# GET to retrieve the status of the WiFi connection
@app.route("/wificheck", methods=['GET'])
def ret_wifi_status():
    check_wifi()
    return jsonify(wificheck)

# Flask ENDPOINT:
# GET to retrieve the Mongoose_XXXXXX correctly initialized bu the /connect
@app.route("/ssids", methods=['GET'])
def take_ssids():
    return json.dumps(ssids)


# Flask ENDPOINT:
# POST to modify the settings for a specific Mongoose_XXXXXX
# GET to retrieve all the settings of all the Mongoose_XXXXXX
@app.route("/chrono", methods=['POST', 'GET'])
def chrono_set():
    if request.method == 'POST':
        print(request.is_json)
        j_post = request.get_json()
        for x in chronos:
            if x['id'] == j_post['id']:
                x['days'] = j_post['days']
                x['enabled'] = j_post['enabled']
                x['start'] = j_post['start']
                x['end'] = j_post['end']
                x['temp'] = j_post['temp']

        shadow['state']['reported']['chronos'] = chronos
        mqtt_client.publish(
            "local/things/RaspberryPi/shadow/update", json.dumps(shadow), qos=1)
        return jsonify({"result": True})
    else:
        return jsonify(chronos)

# MQTT callback after connection, here there are the subscribes


def on_connect(mqtt_client, obj, flags, rc):
    mqtt_client.subscribe("+/event/state", 1)
    mqtt_client.subscribe("+/event/status", 1)
    mqtt_client.subscribe("+/event/setTemp", 1)
    print(" * MQTT Subscribed!")


# MQTT callback for every message published on every subscribed topic
def on_message(mqtt_client, obj, msg):
    if(str(msg.topic[-6:]) == "status"):
        if((msg.payload).decode('utf-8') == "online"):
            esps[str(msg.topic[:15])]['online'] = True
        else:
            esps[str(msg.topic[:15])]['online'] = False

    elif(str(msg.topic[-7:]) == "setTemp"):
        print(str(msg.topic[:15]))
        print(int((msg.payload).decode('utf-8')))
        conn = sqlite3.connect('/home/pi/local.db')
        c = conn.cursor()
        c.execute("""INSERT INTO desired(id, timestamp, value) VALUES((?), CURRENT_TIMESTAMP, (?))""", str(msg.topic[:15]), (msg.payload).decode('utf-8'))
        conn.commit()
    else:
        esps[str(msg.topic[:15])] = json.loads(msg.payload)

    shadow['state']['reported'] = esps
    mqtt_client.publish(
        "local/things/RaspberryPi/shadow/update", json.dumps(shadow), qos=1)


# MQTT callbacks and configuration
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1883)
mqtt_client.loop_start()

# Thread that checks if some schedule is set into the 'chronos' object


def runsched():
    # Restart this fuction after 30 seconds
    threading.Timer(30.0, runsched).start()

    # Take the local hour and transform it as a string
    now = datetime.datetime.now()
    clock = str(now.hour) + ":" + str(now.minute)

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
                        mqtt_client.publish(
                            str(x['id']) + "/event/onoff", "on", retain=True)
                        mqtt_client.publish(
                            str(x['id']) + "/event/setTemp", str(x['temp']))
                    if str(x['end']) == str(clock):
                        print(" * Time to disable " + x['id'])
                        mqtt_client.publish(
                            x['id'] + "/event/onoff", "off", retain=True)
            if date.today().weekday() == 1:
                if bool(x['days']['tuesday']) == True:
                    if str(x['start']) == str(clock):
                        print(" * Time to enable " + x['id'])
                        mqtt_client.publish(
                            str(x['id']) + "/event/onoff", "on", retain=True)
                        mqtt_client.publish(
                            str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                    if str(x['end']) == str(clock):
                        print(" * Time to disable " + x['id'])
                        mqtt_client.publish(
                            x['id'] + "/event/onoff", "off", retain=True)
            if date.today().weekday() == 2:
                if bool(x['days']['wednesday']) == True:
                    if str(x['start']) == str(clock):
                        print(" * Time to enable " + x['id'])
                        mqtt_client.publish(
                            str(x['id']) + "/event/onoff", "on", retain=True)
                        mqtt_client.publish(
                            str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                    if str(x['end']) == str(clock):
                        print(" * Time to disable " + x['id'])
                        mqtt_client.publish(
                            x['id'] + "/event/onoff", "off", retain=True)
            if date.today().weekday() == 3:
                if bool(x['days']['thursday']) == True:
                    if str(x['start']) == str(clock):
                        print(" * Time to enable " + x['id'])
                        mqtt_client.publish(
                            str(x['id']) + "/event/onoff", "on", retain=True)
                        mqtt_client.publish(
                            str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                    if str(x['end']) == str(clock):
                        print(" * Time to disable " + x['id'])
                        mqtt_client.publish(
                            x['id'] + "/event/onoff", "off", retain=True)
            if date.today().weekday() == 4:
                if bool(x['days']['friday']) == True:
                    if str(x['start']) == str(clock):
                        print(" * Time to enable " + x['id'])
                        mqtt_client.publish(
                            str(x['id']) + "/event/onoff", "on", retain=True)
                        mqtt_client.publish(
                            str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                    if str(x['end']) == str(clock):
                        print(" * Time to disable " + x['id'])
                        mqtt_client.publish(
                            x['id'] + "/event/onoff", "off", retain=True)
            if date.today().weekday() == 5:
                if bool(x['days']['saturday']) == True:
                    if str(x['start']) == str(clock):
                        print(" * Time to enable " + x['id'])
                        mqtt_client.publish(
                            str(x['id']) + "/event/onoff", "on", retain=True)
                        mqtt_client.publish(
                            str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                    if str(x['end']) == str(clock):
                        print(" * Time to disable " + x['id'])
                        mqtt_client.publish(
                            x['id'] + "/event/onoff", "off", retain=True)
            if date.today().weekday() == 6:
                if bool(x['days']['sunday']) == True:
                    if str(x['start']) == str(clock):
                        print(" * Time to enable " + x['id'])
                        mqtt_client.publish(
                            str(x['id']) + "/event/onoff", "on", retain=True)
                        mqtt_client.publish(
                            str(x['id']) + "/event/setTemp", str(x['temp']), retain=True)
                    if str(x['end']) == str(clock):
                        print(" * Time to disable " + x['id'])
                        mqtt_client.publish(
                            x['id'] + "/event/onoff", "off", retain=True)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
