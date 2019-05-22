from flask import Flask
from flask import json
from flask import request
from flask import jsonify
import wifi
import subprocess
import re
import gatt
import time
import socket
from ESP32BLE import ESP32BLE
from ESP32BLE import ESP32BLEManager
import paho.mqtt.client as mqtt

def on_connect(mqtt_client, obj, flags, rc):
    mqtt_client.subscribe("+/event/state")
    print(" * MQTT Subscribed!")

def on_message(mqtt_client, obj, msg):
    print("on_message()")


mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("localhost",1883)
mqtt_client.loop_start()

def set_new_network_wpa(ssid, password=''):
    with open('/etc/wpa_supplicant/wpa_supplicant.conf','w') as f:
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
            #process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
            #output, error = process.communicate()



app = Flask(__name__)

@app.route("/connect", methods=['GET'])
def connect():
    ssid = request.args.get('ssid')
    passwd = request.args.get('passwd')
    
    manager = ESP32BLEManager(adapter_name='hci0')
    manager.start_discovery()
    manager.run()
    manager.stop_discovery()
    macs = manager.hashmac

    set_new_network_wpa(ssid=ssid, password=passwd)
    
    if(not macs):
        message = {
            'status': 200,
            'message': 'OK',
            'ESPs': 'null'
        }
        resp = jsonify(message)
        resp.status_code = 200
        return resp
    
    ip_address = ([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                                if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)),
                                                                      s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET,
                                                                                                                             socket.SOCK_DGRAM)]][0][1]]) if l][0][0])
    
    for key, value in macs.items():
        manager = gatt.DeviceManager(adapter_name='hci0')
        device = ESP32BLE(ssid=ssid, password=passwd, manager=manager,
                          mac_address=key, name=value, ip_address=ip_address)
        device.connect()
        manager.run()
        print("Rebooting %s" % value + '..')
        device.disconnect()
        print("------------------------------")
    
    
    message = {
        'status': 200,
        'message': 'OK',
        'ESPs': macs
    }
    resp = jsonify(message)
    resp.status_code = 200

    

    return resp


if __name__ == "__main__":
    app.run(host='127.0.0.1')
    
