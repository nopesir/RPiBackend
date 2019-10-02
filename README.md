## PROJECT REPORT: CHRONOTHERMOSTAT


## Introduction

The aim of this project is to build a fully functional chrono-thermostat
system based on Raspberry Pi 3 using Amazon Web Services. For the purpose,
it is built a team of two computer engineers (Luigi Ferrettino and Francesco
Valente) and an electronics engineer (Shabbir Ali) in order to fulfill the spe-
cific requirements. The report will firstly analyze all the functionalities of
the system at an user-level. Then, it will go deeper, exploiting the hardware
architecture and the software architecture with the linked modules. Finally,
all the problems encountered within the development are presented together
with the chosen resolutions.

## Functionalities and use cases

The system is capable of manage multiple rooms at the same time. The
main component is the Raspberry Pi 3, that uses WiFi (instandard mode,
using the home wireless LAN, or alternatively instandalone mode, creating a
LAN network with the built-in antenna as the access point). Moreover, USB
ports can be used to charge smartphones or other devices beacause current
is on, but it has all the data inputs/outputs (USB, Ethernet etc.) disabled 
in order to avoid possible personalizations from the user. At the first boot, it
is necessary an initial setup. Once the user has pushed the ”boot” button of
every ESPs, they will start to blink ad they are ready to receive the configu-
ration. On the GUI, the user has to typeSSIDandPASSWORDof the home
WiFi and automatically the Raspberry will search every ESP and configure
them. Then, the GUI will show every connected device with the possibility
to change the name of the room, the desired temperature, the week schedule
and enable or disable the ”room” manually. Furthermore, for every room
it is showed current temperature, current humidity and perceived temperature. 
Again, informations about the connection are available by clicking on
the top right on the symbol of the WiFi, including the possibility to change
manually standalone/standard mode. If the user wants to add another ESP
(so, another room) later on without repeating the entire setup, it can be
used the smartphone: as the SONOFF system, the ESP when blinking is
discoverable by WiFi; thus the user will connect the smartphone to the SSID
MongooseXXXXXX with the password Mongoose and using the built in
browser (without the nuisanse of installing an app) he will types 192.168.4.
and a form appears. Compiling it with the informations available on the GUI
as described before, the room is automatically added.
The standalone mode can be automatically enabled in case of WiFi fail-
ures and the ESPs know what to do, without lifting a finger they will recon-
nect to the Raspberry in order to preserve the desired settings of the user
even in extreme circumstances.
In addition, the GUI is accessible by any device connected to the network
typing the IP showed into the informations. From the browser, the user can
access to statistics and graphs showing the desired temperature, the measured
temperature and the humidity by day, week, month, year etc. Moreover, it
can be controlled everything that is controllable by the RPi display, but
for security reasons it is prohibited the setup and the manual switch of the
mode. A modified version of the app is accessible from the outside of the
LAN, using as password and username a given ones in order to access to the
public broker. From there the user can enable/disable the rooms, set the
desired temperatures, have informations about the current state and set the
week schedule.


## Hardware architecture

Hardware is composed by the Raspberry Pi 3 with the touchscreen LCD-
case integrated and a variable number of the controlling units (based on the
number of rooms that the user wants to control). A control unit is an ESP
connected with a temperature/humidity sensor DHT22 that has a precision
of±0.5◦C and a double relay used to enable/disable cooling or warming
system based on the desired temperature set by the user.
All of this is packaged up in one small box that will have an AC 220V
input and two AC 220V outputs to be connected to cooling/warming systems.
For demo purposes, the ESP is fed by some batteries and the AC outputs
are simulated by the switch sound; this is only an intermediate testing form,
to be completed with a converter to power up the ESP directly from the AC
220V input.


## Software architecture

Now we analyze all the software modules, frameworks, the communication
protocols and the web services used. In the network LAN all the devices
communicate using WiFi and HTTP/MQTT (on the outside too, but mainly
MQTT). HTTP is used to directly control the RPi WiFi and to retrieve
graphs infos, while MQTT is used to control everything else.
In addition to the AWS account to store logs and configuration, another
AWS account is used to exploit the bridging between the local MQTT broker
and the remote AWS IoT broker throught simple topic re-routing and using
the Device Shadow functionality provided by AWS IoT for ourthing. The
LAN communications are not encrypted because for some security restricted
access modes the RPi automatically reject some requests coming from within
the LAN, while for the bridge and all the outside Internet functionalities TLS
is used.

### RPi 3

On the RPi is used a Mosquitto broker configured to bridge with an AWS IoT
broker on the Internet. This local server exploits persistence on data using
the mosquitto.db file and the MQTT retained mode (in order to preserve
the state of the entire system, aka the configuration); besides, a local sqlite
database stores automatically local logs in order to be subsequently used for
statistics and graphs plotting.
The AWS ping response with the logs upload is implemented creating a
systemd serviceof the Raspbian OS in order to start when connection is
available and always run, even in case of failures.
On the front-end side, an Angular7 app runs on the pre-installed chromium
browser in kiosk and it communicates with the back-end and the other de-
vices throught MQTT and HTTP GET/POST implementing the already
described GUI.
Finally, a Flask server runs in background. It has been used Python
for the high capabilities to manage low level features. The server exposes
endpoints accessible only from the RPi (such as the WiFi connection or the
switch between STA/AP) and endpoints accessible from all the LAN (such

as the logs queries in order to plot the statistics and the week schedule to
automatically manage the rooms). Since this application can view every state
and has access to all the informations, it creates the configuration and send
it to the AWS database using the WEB API every time that it changes.
Furthermore, it is simultaneously a MQTT client that filters all the mes-
sages published and decides what to send or receive through the bridge
from/to AWS IoT. This is done to allow the modified version of the web
app, instantiated in an AWS S3 bucket, to control only with MQTT the
entire system from the outside. In order to enable the outside control, an
AWS EC2 instance with Mosquitto, protected by username and password, is
already bridged with the same AWS IoT, in order to provide a safe interface
without affecting the direct connection to AWS IoT.
RPi is also an AWSthing that has itsshadow(aka the total state up-
dated and persistent, accessible via MQTT or HTTP APIs).

### ESP32 (Mongoose OS)

Mongoose OS is an IoT firmware development framework that aims at de-
crease the development time up to the 90%.

It is recommended by all the lead companies in IoT (e.g. AWS IoT,
Microsoft Azure IoT, Google IoT Core, BM Watson IoT) and in embedded
systems (e.g. TI, STMicroelectronics) and it has a wide range of 
functionalities already implemented with the possibility to use mJS (an embedded
Javascript engine/wrapper for C/C++) as programming language.
The ESPs are capable of save persistent JSON data and multiple 
configurations of WiFi APs and MQTT server infos; it has been implemented a
mechanism for automatically switch between the saved configurations for the
home and the standalone mode in case of failures. In addition, the built-in led
is used for an immediate feedback (when blinking is in AP mode ready to be
configured by smartphone or from the RPi, when on is ready and connected
and when off is disconnected, trying to return online checking configuration
by configuration).
In order to take and save a new configuration, when in AP mode, the
ESP runs a lightweight HTTP Web server, accessible from the IP192.168.4.
and waits for an HTTP POST with the new JSON via a mechanism of RPC
already built in the firmware. When connected and ready, it subscribes to the
defined topics and publish every 20 seconds the current state in JSON. The
desired temperature and the room name, with the enabe/disable command
are set by the user from the app in retained mode in order to preserve the
last desired parameters.
Moreover, a mechanism of online/offline detection is exploited through
the so called last will message:

1. When the ESP connects to the broker, it sends the last will message
    and the topic to send it to.
2. Based on the keepalive timeout, when the broker doesn’t receive the
    ACK within that time, itself will publish the agreed message on that
    topic.

In this case, the last will message is offline (retained), so that when an
ESP for some reason goes offline, it will be reported by the application to
the user, even if the application subscribes after the disconnection.


The DHT22 sensor communicates with the ESP through the I2C protocol
and it is powered by a 3.3V. On the other side, the two relays are powered
by the 5V output and are controlled by 2 PIN initialized as digital out, so
that when warm/cold are on/off is set the corresponding PIN to up (avoiding
warm and cold enabled at the same time).
Internally, the firmware retrieves humidity and temperature and then it
computes the perceived temperature using an approximation formula of the
Heat Index (humiture); finally it refreshes the state and, if online, it publishes
it to the corresponding topic, ready to be shown to the user.

## Amazon Web Services

AWS is the de facto core of this project, the services used are:

- AWS IoT to have a public TLS broker bridged with the local one and
    the thing shadowing implemented and enabled. Moreover, it is used to
    send the logs into Firebird DB and to reply to the ping message from
    the ”PL19” server.
- AWS S3 to store the external Angular7 Web app.
- AWS Firebird DB through the API made available by the teaching
    assistant.
- AWS IAM (Identity and Access Management).
- AWS EC2 to have an external Mosquitto broker publicly available and
    protected with username and password and implements a simple Tele-
    gram Bot to retrieve the current state.


## Final considerations

At present, the entire system works good, despite the fact that it can be
clearly improved. Firstly, an integration with a vocal assistant (such as
Alexa, but Google too) could be very useful into the home to control the
system without using the integrated app or the smartphone. Secondly, the
specifications of the project are fixed atone device for one user. The
system could be generalized to multiple devices for one user. Moreover, for
what concerns the external access through the S3 Angular7 web app, it is
a simple solution that for large scale must be converted to dedicated Flask
server running on the AWS EC2 instance with the Angular7 in it, removing
the S3 bucket.
Mongoose OS is a great success. It was discovered because of the big
amount of time used at the beginning of the project to decide which frame-
works and development environments to use; we learned that it is not a waste
of time at all. In addition, it has allowed us to implement a better SONOFF
(adding the auto switch of the WiFi in case of failures) in a hundred of lines
of JS code.
It has been chosen to bridge the local Mosquitto broker with the re-
mote AWS broker in order not to worry about possible disconnections with
Internet; Mosquitto will take care about it, and the working modes ofstan-
dard/standalone, once set, are reliable.
One of the most challenging parts was the design of the MQTT topic tree
in order to provide an always connected and structured MQTT service with
a smart use of the already implemented Mosquitto local DB for the retained
messages to to save persistently the state of the entire system. Nonetheless,
this project allowed us to discover the great potential of the communication
systems using web services as well as the paradigm of learn-by-doing, the soft
skills in team working and project management.
