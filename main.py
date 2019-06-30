from flask import Flask
from flask import json
from flask import request
from flask import jsonify
import sched
import time
import wifi
import subprocess
import re
import requests
import time
import socket
import getSSID
#from ESP32BLE import ESP32BLE
#from ESP32BLE import ESP32BLEManager
import paho.mqtt.client as mqtt

message = {
    'status': 200,
    'message': 'OK',
    'ip': "127.0.0.1",
    'connected': False
}

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


s = sched.scheduler(time.time, time.sleep)

shadow = {
    'state': {
        'reported': {}
    }
}

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


def internet(host="8.8.8.8", port=53, timeout=3):

    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception as ex:
        return False


def retrieve_ip():
    return ([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                          if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)),
                                                                s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET,
                                                                                                                       socket.SOCK_DGRAM)]][0][1]]) if l][0][0])


app = Flask(__name__)


def check_wifi():
    print(" * Checking wifi...")
    res = False
    try:
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
    ssid = request.args.get('ssid')
    passwd = request.args.get('passwd')

    # Clear all stored messages on MosquittoDB
    subprocess.run("sudo ./clearDB.sh", shell=True, check=True)
    esps = {}

    set_new_network_wpa(ssid=ssid, password=passwd)

    while not check_wifi():
        time.sleep(2)
        pass

    print(" * Master SSID: " + ssid)
    ssids = [x for x in getSSID.main() if "Mongoose_" in x['Name']]
    #print(getSSID.main()['Name']

    data['config']['wifi']['sta']['ssid'] = ssid
    data['config']['wifi']['sta']['pass'] = passwd
    data['config']['mqtt']['server'] = retrieve_ip()

    for x in ssids:
        set_new_network_wpa(ssid=x['Name'], password="Mongoose")
        
        while not check_wifi():
            time.sleep(2)
            pass
        
        print(" * Configuring " + x['Name'] + "...")
        r = requests.post('http://192.168.4.1/rpc/Config.Set', json=data)
        time.sleep(3)
        r2 = requests.post('http://192.168.4.1/rpc/Config.Save', json={'reboot': True})
        
    
    set_new_network_wpa(ssid=ssid, password=passwd)

    while not check_wifi():
        time.sleep(2)
        pass
    print(" * Connected to " + ssid + " and ready!")
    resp = json.dumps(ssids)
    return resp


@app.route("/wificheck", methods=['GET'])
def ret_wifi_status():
    check_wifi()
    return jsonify(wificheck)


def on_connect(mqtt_client, obj, flags, rc):
    mqtt_client.subscribe("+/event/state",1)
    mqtt_client.subscribe("+/event/status",1)
    print(" * MQTT Subscribed!")


def on_message(mqtt_client, obj, msg):
    if(str(msg.topic[-6:]) == "status"):
        if((msg.payload).decode('utf-8') == "online"):
            esps[str(msg.topic[:15])]['online'] = True
        else:
            esps[str(msg.topic[:15])]['online'] = False
        
    else:
        esps[str(msg.topic[:15])] = json.loads(msg.payload)
    
    shadow['state']['reported'] = esps
    mqtt_client.publish("local/things/RaspberryPi/shadow/update", json.dumps(shadow), qos=1)
    print(" * Shadow updated!")


mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1883)


mqtt_client.loop_start()
if __name__ == "__main__":
    app.run(host='127.0.0.1')
