#!/bin/bash

echo "Stoping $netInterface"
ifconfig wlan0 down
echo "Attempting to stop hostapd"
/etc/init.d/hostapd stop
echo "Attempting to stop dnsmasq"
/etc/init.d/dnsmasq stop
echo "Reconnecting"
wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
echo "Renewing IP Address for $netInterface"
/sbin/dhcpcd
wpa_cli select network 0
