#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VegTrack360 Image Capture Application (version3)

This Flask application connects to a camera and controls the movement of the camera in a grid of horizontal and vertical steps.
Images are captured at each position and saved to a unique folder.

@author: Florian J. Ellsaesser
"""

import subprocess
from flask import Flask, render_template, request
import serial
import time
import cv2
import os

app = Flask(__name__)

#WIFI_SSID = 'My_WiFi_Name'
#WIFI_PASSWORD = 'My_WiFi_Password'

WIFI_INTERFACE = 'wlan0'  # Network interface name

def connect_to_wifi():
    """
    Connects to a predefined WiFi network using the `iw` command.
    """
    subprocess.run(['sudo', 'iw', 'dev', WIFI_INTERFACE, 'connect', WIFI_SSID, 'key', '0:' + WIFI_PASSWORD])


@app.route('/')
def index():
    """
    Renders the index HTML page for the Flask web interface.
    """
    return render_template('index.html')


@app.route('/hello', methods=['POST'])
def hello():
    """
    Handles POST requests from the index page.
    Retrieves user input for horizontal and vertical camera movement, 
    and captures images at each position.
    Stereo mode is also handled if the user enables it.
    """
    # Retrieving data from the request JSON payload
    data = request.json
    horizontal_start = int(data['horizontalStart'])
    horizontal_end = int(data['horizontalEnd'])
    horizontal_step = int(data['horizontalStep'])
    vertical_start = int(data['verticalStart'])
    vertical_end = int(data['verticalEnd'])
    vertical_step = int(data['verticalStep'])
    stereo_mode = bool(data['stereoMode'])  # Stereo mode checkbox

    # Calculate step sizes for movement
    horizontal_step_size = abs((horizontal_end - horizontal_start) / horizontal_step)
    vertical_step_size = abs((vertical_end - vertical_start) / vertical_step)

    # Initialize camera
    camera = cv2.VideoCapture("nvarguscamerasrc ! video/x-raw(memory:NVMM), width=(int)1280, height=(int)720, "
                              "format=(string)NV12, framerate=(fraction)60/1 ! nvvidconv flip-method=2 ! "
                              "video/x-raw, width=(int)640, height=(int)480, format=(string)BGRx ! "
                              "videoconvert ! video/x-raw, format=(string)BGR ! appsink")

    # Define a function to find the next available folder number
    def find_next_folder_number(base_folder, folder_prefix):
        """
        Finds the next available folder number for saving image sets.
        """
        existing_folders = [folder for folder in os.listdir(base_folder) if folder.startswith(folder_prefix)]
        if not existing_folders:
            return 0
        existing_numbers = [int(folder.split('_')[-1]) for folder in existing_folders]
        return max(existing_numbers) + 1

    # Initialize serial port for communication
    port = serial.Serial("/dev/ttyUSB0", 9600)

    # Create a folder to store the images
    base_folder = "/media/vt360/VT360_DRIVE"
    folder_prefix = "Image_set"
    next_folder_number = find_next_folder_number(base_folder, folder_prefix)
    folder_path = os.path.join(base_folder, f"{folder_prefix}_{next_folder_number}")

    # Create folder if it does not exist
    os.makedirs(folder_path, exist_ok=True)
    print(f"Created folder: {folder_path}")

    # Generate steps for horizontal and vertical movement
    circular_steps = [int(horizontal_start + i * horizontal_step_size) for i in range(horizontal_step)] if horizontal_start <= horizontal_end \
        else [int(horizontal_start - i * horizontal_step_size) for i in range(horizontal_step)]
    
    camera_steps = [int(vertical_start + i * vertical_step_size) for i in range(vertical_step)] if vertical_start <= vertical_end \
        else [int(vertical_start - i * vertical_step_size) for i in range(vertical_step)]

    print("Horizontal Steps:", circular_steps)
    print("Vertical Steps:", camera_steps)

    # Initialize camera to start position
    port.write(f"15,90".encode())
    time.sleep(2)

    # Initialize pair number
    pair_number = 1

    # Loop through each position and take a picture (and stereo pair if in stereo mode)
    for i in circular_steps:
        for j in camera_steps:
            # Capture the first image
            result_string = f"{i},{j}"
            print(f"Moving to position: {result_string}")
            port.write(result_string.encode())

            # Allow time for the camera and servo to move and stabilize
            time.sleep(2)  # Increase the delay slightly

            # Capture multiple dummy frames to allow the camera to adjust
            for _ in range(5):  # Capture 5 dummy frames to adjust brightness
                camera.read()

            # Add an extra delay to ensure camera settings stabilize
            time.sleep(0.7)

            # Capture and save the actual image
            control, frame = camera.read()
            if control:
                image_name = f"Image_{next_folder_number}_{pair_number}_r_{i}_c_{j}.jpg"
                cv2.imwrite(os.path.join(folder_path, image_name), frame)
                print(f"Image saved: {image_name}")
            else:
                print(f"Failed to capture image at position: {i}, {j}")

            # Capture the stereo partner if in stereo mode
            if stereo_mode:
                mirrored_i = (i + 180) % 360  # Mirroring the horizontal position
                mirrored_j = (360 - j) % 360  # Mirroring the vertical position (around 0)
                result_string_stereo = f"{mirrored_i},{mirrored_j}"
                print(f"Moving to stereo position: {result_string_stereo}")
                port.write(result_string_stereo.encode())

                # Allow time for the camera and servo to move and stabilize
                time.sleep(2)  # Increase the delay slightly for stereo

                # Capture multiple dummy frames for stereo image
                for _ in range(5):  # Capture 5 dummy frames to adjust brightness
                    camera.read()

                # Extra delay to ensure camera settings stabilize for stereo image
                time.sleep(0.7)

                # Capture and save the stereo image
                control_stereo, frame_stereo = camera.read()
                if control_stereo:
                    stereo_image_name = f"Image_{next_folder_number}_{pair_number}S_r_{mirrored_i}_c_{mirrored_j}.jpg"
                    cv2.imwrite(os.path.join(folder_path, stereo_image_name), frame_stereo)
                    print(f"Stereo image saved: {stereo_image_name}")
                else:
                    print(f"Failed to capture stereo image at position: {mirrored_i}, {mirrored_j}")

            # Increment the pair number
            pair_number += 1

    # Return the camera to the start position
    port.write(f"15,90".encode())
    time.sleep(2)

    # Release the camera
    camera.release()

    return "All images have been taken!"


if __name__ == '__main__':
    connect_to_wifi()  # Connect to WiFi when the script starts
    app.run(debug=True, host='0.0.0.0', port=5000)

