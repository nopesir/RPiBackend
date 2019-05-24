#!/bin/bash

echo "Stoping $netInterface"
ifconfig wlan0 down
echo "Stoping wpa_supplicant"
killall wpa_supplicant
echo "Attempting to start hostapd"
/etc/init.d/hostapd start
echo "Attempting to start dnsmasq"
/etc/init.d/dnsmasq start
echo "Setting IP Address for $netInterface"
/sbin/ifconfig $netInterface wlan0 up
