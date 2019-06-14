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


def set_new_network_wpa(ssid, password=''):
    with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as f:
        f.write('ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n')
        f.write('update_config=1\n')
        f.write('country=IT\n')
        f.write('\n')
        f.write('network={\n')
        f.write('    ssid="%s"\n' % ssid)
        if not password:
            f.write('    key_mgmt=NONE\n')
        else:
            f.write('    psk="%s"\n' % password)
            f.write('    key_mgmt=WPA-PSK\n')
        f.write('    priority=1\n')
        f.write('}\n')
        f.close()
        bashCommand = "wpa_cli -i wlan0 reconfigure"
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()


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

    set_new_network_wpa(ssid=ssid, password=passwd)

    while not check_wifi():
        pass

    print("WIFI CONNECTED")
    ssids = []
    # sudo iwlist wlan0 scan | grep Mongoose_
    out = subprocess.check_output(["sudo", "iwlist", "wlan0", "scan"])
    out = out.decode('utf-8')
    lines = out.split('\n')
    for line in lines:
        m = re.search('"(.+?)"', line)
        if m:
            ssids.append(m.group(1))


    ssids = [k for k in ssids if 'Mongoose_' in k]
    data['config']['wifi']['sta']['ssid'] = ssid
    data['config']['wifi']['sta']['pass'] = passwd
    data['config']['mqtt']['enable'] = passwd
    data['config']['mqtt']['server'] = wificheck['ip']

    for x in ssids:
        set_new_network_wpa(ssid=x, password="Mongoose")
        while not check_wifi():
            pass
        print("CONNECTED TO " + x)
        r = requests.post('http://192.168.4.1/rpc/Config.Set', json=data)
        time.sleep(3)
        r2 = requests.post('http://192.168.4.1//rpc/Config.Save', json={'reboot': True})
        

    resp = jsonify(message)
    resp.status_code = 200
    return resp


def on_connect(mqtt_client, obj, flags, rc):
    mqtt_client.subscribe("local/rpi/event/+")
    print(" * MQTT Subscribed!")


def on_message(mqtt_client, obj, msg):
    return


mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1882)


mqtt_client.loop_start()
if __name__ == "__main__":
    app.run(host='127.0.0.1')
