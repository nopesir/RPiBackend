# Brief description
As part of the chrono-thermostat system, this repository contains the backend that runs on the RPi. 
It is the core of the project; using flask it exposes HTTP APIs to the Angular frontend in order to manage WiFi, retireve infos about the connected ESPs and so on.
In addition, it filters all the MQTT messages and decides which of them must be sent to AWS IoT.
