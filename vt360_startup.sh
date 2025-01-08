#!/bin/bash

echo "run startup script"
sudo chmod a+rw /dev/ttyUSB0
sudo chmod -R a+rw /media/vt360/VT360_DRIVE
python3 ~/Desktop/FLASK_APP/app.py
