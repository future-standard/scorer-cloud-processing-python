# -*- coding: utf-8 -*-
"""Scorer.py  Main library code of Scorer Cloud Processing for python
"""
#Copyright 2017 Future Standard Co., Ltd.
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import sys
import os
import zmq
import struct
import cv2
import numpy as np
import time
from datetime import datetime
import pickle
import traceback

ZMQ_FRAME_GRABBER_ENDPOINT = os.getenv("ZMQ_FRAME_GRABBER_ENDPOINT", 'CLUSTER_BUFFER')
INACTIVITY_TIMEOUT= os.getenv("INACTIVITY_TIMEOUT", 'INACTIVITY_TIMEOUT')

# For ZMQ connetion
ctx = zmq.Context()

class VideoCapture:
    """VideoCapture class. Class for video captureing from camera.
    """
    def __init__(self, sock, blocking=True):

        """Initialize the instance
        :param blocking: True if VideoCapture read data as blocking mode

        """
        print("sock:" + sock)
        #
        self.img_sock = ctx.socket(zmq.PULL)
        #self.img_sock.setsockopt_string(zmq.SUBSCRIBE, '')
        #self.img_sock.setsockopt(zmq.RCVHWM, 1)
        self.img_sock.connect(sock)
        #
        self.poller = zmq.Poller()
        self.poller.register(self.img_sock, zmq.POLLIN)
        #a
        self.blocking=blocking
        if(blocking == True):
            self.timeout = 1000
        else:
            self.timeout = 0

    def read(self):
        """ Get Frame data from VideoCapture

        :return: Frame data
        """
        self.events =  dict(self.poller.poll(self.timeout))
        self.count = 0
        try:
            while True:
                socks = self.events
                if self.img_sock in socks and socks[self.img_sock] == zmq.POLLIN:
                    #topic, id, timestamp, my_type, format, rows, cols, mat_type, data = \
                    id, timestamp, my_type, format, rows, cols, mat_type, data = \
                                             self.img_sock.recv_multipart(zmq.NOBLOCK, True, False)
                    self.frame = VideoFrame(timestamp, format, rows, cols, mat_type, data)
                    self.count = 1
        except:
            traceback.print_exc()
            if self.count == 0:
                return (None)
        return (self.frame)


    def isOpend(self):
        """ Return true if VideoCapture has been ready to read

        :return: True of False
        """
        return not(self.img_sock.closed)

    def release(self):
        """ Close video captureing connection

        """
        self.img_sock.close()

class VideoFrame:
    """VideoFrame class. This class handles frame and date data.

    Attributes:
        width        width of the frame
        height       width of the frame
        time         time of the frame
        datetime     datetime of the frame
        msec         msec of the frame
    """
    def __init__(self, timestamp, format, rows, cols, mat_type, data):
        """Initialize the instance

        :param timestamp: timestamp of the frame
        :param format: image format
        :param row: row of the images
        :param col: col of the images
        :param mat_type: mat type of the images
        :param data: image data
        """
        self.my_time = struct.unpack('!q', timestamp)
        self.my_row = struct.unpack('!i', rows)
        self.my_col = struct.unpack('!i', cols)
        self.my_type = struct.unpack('!i', mat_type)
        self.image = np.frombuffer(data, dtype=np.uint8).reshape((self.my_row[0],self.my_col[0]));
        self.image_format=format.decode('utf-8')

        epoch_time = self.my_time[0]/1000000
        epoch_msec = self.my_time[0]%1000000

        self.width = self.my_col[0]
        self.height = self.my_row[0]
        self.time = self.my_time[0]
        self.datetime= datetime(*time.localtime(epoch_time)[:6])
        self.msec= epoch_msec

    def get_datetime(self):
        return self.datetime

    def get_bgr(self):
        """ Get bgr image data

        :return: bgr image data
        """
        if self.image_format == "I420":
            bgr = cv2.cvtColor(self.image, cv2.COLOR_YUV2BGR_I420)
        elif self.image_format == "BGR":
            bgr = self.image
        elif self.image_format == "RGBA":
            bgr = cv2.cvtColor(self.image, cv2.COLOR_RGBA2BGR)
        else:
            raise Exception("format is incorrect")
        return bgr

    def get_gray(self):
        """Get gray image data

        :return: gray image data
        """
        if self.image_format == "I420":
            gray = cv2.cvtColor(self.image, cv2.COLOR_YUV2GRAY_I420)
        elif self.image_format == "BGR":
            gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        elif self.image_format == "RGBA":
            gray = cv2.cvtColor(self.image, cv2.COLOR_RGBA2BGR)
        else:
            raise Exception("format is incorrect")
        return gray
