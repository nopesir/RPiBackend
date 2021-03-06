#!/bin/bash
# DISABLE wlan0 IN dhcpcd.conf

echo "Stoping $netInterface"
ifconfig wlan0 down
echo "Attempting to stop hostapd"
/etc/init.d/hostapd stop
echo "Attempting to stop dnsmasq"
/etc/init.d/dnsmasq stop
echo "Reconnecting"
wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
echo "Renewing IP Address for $netInterface"
/etc/init.d/dhcpcd stop
/etc/init.d/dhcpcd start
/sbin/dhcpcd
ifconfig wlan0 up
wpa_cli select network 0

