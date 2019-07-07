#!/bin/bash

# ENABLE wlan0 IN dhcpcd.conf
echo "Stoping $netInterface"
sudo ifconfig wlan0 down
echo "Stoping wpa_supplicant"
sudo killall wpa_supplicant
echo "Attempting to start hostapd"
sudo /etc/init.d/hostapd stop
sudo /etc/init.d/hostapd start
echo "Setting IP Address for $netInterface"
sudo /sbin/ifconfig $netInterface wlan0 down
sudo /sbin/ifconfig $netInterface wlan0 up
echo "Attempting to start dnsmasq"
sudo /etc/init.d/dnsmasq restart
