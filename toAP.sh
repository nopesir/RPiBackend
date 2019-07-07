#!/bin/bash

# ENABLE wlan0 IN dhcpcd.conf
echo "Stoping $netInterface"
ifconfig wlan0 down
echo "Stoping wpa_supplicant"
killall wpa_supplicant
echo "Attempting to start hostapd"
/etc/init.d/hostapd restart
echo "Setting IP Address for $netInterface"
/sbin/ifconfig $netInterface wlan0 down
/sbin/ifconfig $netInterface wlan0 up
echo "Attempting to start dnsmasq"
ifconfig wlan0 up
/etc/init.d/dnsmasq restart
