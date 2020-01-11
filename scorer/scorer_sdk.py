# -*- coding: utf-8 -*-
"""Scorer.py  Main library code of Scorer Cloud Processing for python
"""
# Copyright 2017 Future Standard Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import zmq
import struct
import cv2
import numpy as np
import time
from datetime import datetime
import pickle
import logging

logger = logging.getLogger(__name__)

zeromq_ctx = zmq.Context()


class VideoCapture:
    """VideoCapture class. Class for video captureing from camera.
    """

    def __init__(self, endpoint, blocking=True, timeout=1000, perf_count=False):

        """Initialize the instance
        :param endpoint: ZeroMQ Endpoint
        :param blocking: True if VideoCapture read data as blocking mode
        :param timeout: polling timeout (used only blocking=True).
        """
        # print("sock:" + sock)
        #
        self.img_sock = zeromq_ctx.socket(zmq.PULL)
        # self.img_sock.setsockopt_string(zmq.SUBSCRIBE, '')
        self.img_sock.setsockopt(zmq.RCVHWM, 1)
        self.img_sock.connect(endpoint)
        #
        self.poller = zmq.Poller()
        self.poller.register(self.img_sock, zmq.POLLIN)
        # a
        self.blocking = blocking
        if blocking:
            self.timeout = timeout
        else:
            self.timeout = 0
        self.perf_count = perf_count
        self.perf_counters = []

    def read(self):
        """ Get Frame data from VideoCapture

        :return: Frame data
        """
        if self.perf_count:
            perf_start = time.perf_counter()
        self.events = dict(self.poller.poll(self.timeout))
        if self.perf_count:
            parf_end = time.perf_counter()
            self.perf_counters.append(parf_end - perf_start)

        self.count = 0
        if len(self.events) == 0:
            # No Frame Data
            logger.warning(f"No ZMQ events. (maybe timeout)")
            return (None, None)
        try:
            while True:
                socks = self.events
                if self.img_sock in socks and socks[self.img_sock] == zmq.POLLIN:
                    version, timestamp, frame_type, format_, rows, cols, mat_type, data = self.img_sock.recv_multipart(
                        zmq.NOBLOCK, True, False
                    )
                    self.frame = VideoFrame(
                        version,
                        timestamp,
                        frame_type,
                        format_,
                        rows,
                        cols,
                        mat_type,
                        data,
                    )
                    self.count = 1
                    return (self.frame, self.frame.get_bgr())
        except:
            if self.count == 0:
                logger.exception(f"exception happend self.count==0")
                return (None, None)
        # never reached
        return (None, None)

    def isOpened(self):
        """ Return true if VideoCapture has been ready to read

        :return: True of False
        """
        return not (self.img_sock.closed)

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

    def __init__(
        self, version, timestamp, frame_type, format_, rows, cols, mat_type, data
    ):
        """Initialize the instance

        :param version: version of the protocol
        :param timestamp: timestamp of the frame
        :param frame_type: type of the frame
        :param format_: image format
        :param row: row of the images
        :param col: col of the images
        :param mat_type: mat type of the images
        :param data: image data
        """
        self.version = version.decode("utf-8")
        self.my_time = struct.unpack("!q", timestamp)
        self.frame_type = struct.unpack("!h", frame_type)[0]
        self.my_row = struct.unpack("!i", rows)
        self.my_col = struct.unpack("!i", cols)
        self.my_type = struct.unpack("!i", mat_type)
        self.image_format = format_.decode("utf-8")

        if self.image_format == "I420":
            self.image = np.frombuffer(data, dtype=np.uint8).reshape(
                (self.my_row[0], self.my_col[0])
            )
        elif self.image_format == "BGR":
            self.image = np.frombuffer(data, dtype=np.uint8).reshape(
                (self.my_row[0], self.my_col[0], 3)
            )
        elif self.image_format == "RGB":
            self.image = np.frombuffer(data, dtype=np.uint8).reshape(
                (self.my_row[0], self.my_col[0], 3)
            )
        elif self.image_format == "RGBA":
            self.image = np.frombuffer(data, dtype=np.uint8).reshape(
                (self.my_row[0], self.my_col[0], 4)
            )
        else:
            raise Exception("Invalid format: {0}".format(self.image_format))

        epoch_time = self.my_time[0] / 1000000
        epoch_msec = self.my_time[0] % 1000000

        self.width = self.my_col[0]
        self.height = self.my_row[0]
        self.time = self.my_time[0]
        self.datetime = datetime(*time.localtime(epoch_time)[:6])
        self.msec = epoch_msec

        self.bgr = None
        self.gray = None

    def get_datetime(self):
        return self.datetime

    def get_bgr(self):
        """ Get bgr image data

        :return: bgr image data
        """
        if self.bgr is not None:
            return self.bgr
        if self.image_format == "I420":
            self.bgr = cv2.cvtColor(self.image, cv2.COLOR_YUV2BGR_I420)
        elif self.image_format == "BGR":
            self.bgr = self.image
        elif self.image_format == "RGB":
            self.bgr = cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR)
        elif self.image_format == "RGBA":
            self.bgr = cv2.cvtColor(self.image, cv2.COLOR_RGBA2BGR)
        else:
            raise Exception("Invalid format: {0}".format(self.image_format))
        return self.bgr

    def get_gray(self):
        """Get gray image data

        :return: gray image data
        """
        if self.gray is not None:
            return self.gray
        if self.image_format == "I420":
            self.gray = cv2.cvtColor(self.image, cv2.COLOR_YUV2GRAY_I420)
        elif self.image_format == "BGR":
            self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        elif self.image_format == "RGB":
            self.gray = cv2.cvtColor(self.image, cv2.COLOR_RGB2GRAY)
        elif self.image_format == "RGBA":
            self.gray = cv2.cvtColor(self.image, cv2.COLOR_RGBA2GRAY)
        else:
            raise Exception("Invalid format: {0}".format(self.image_format))
        return self.gray


class VideoWriter:
    def __init__(self, endpoint, first_metadata, perf_count=False):
        self._sock = zeromq_ctx.socket(zmq.PUSH)
        self._sock.setsockopt(zmq.SNDHWM, 1)
        self._sock.bind(endpoint)
        self.first_metadata = first_metadata
        self.perf_count = perf_count
        self.perf_counters = []

    def write(self, image):
        version = "1.0".encode("utf-8")
        timestamp = struct.pack("!q", self.first_metadata.time)
        frame_type = struct.pack("!h", 0)
        rows = struct.pack("!i", image.shape[0])
        cols = struct.pack("!i", image.shape[1])
        mat_type = struct.pack("!i", 0)
        image_format = "BGR".encode("utf-8")
        if self.perf_count:
            perf_start = time.perf_counter()
        self._sock.send_multipart(
            [
                version,
                timestamp,
                frame_type,
                image_format,
                rows,
                cols,
                mat_type,
                image.tobytes(),
            ]
        )
        if self.perf_count:
            perf_end = time.perf_counter()
            self.perf_counters.append(perf_end - perf_start)

    def write_with_metadata(self, meta, image):
        version = meta.version.encode("utf-8")
        timestamp = struct.pack("!q", meta.time)
        frame_type = struct.pack("!h", meta.frame_type)
        rows = struct.pack("!i", meta.height)
        cols = struct.pack("!i", meta.width)
        mat_type = struct.pack("!i", meta.my_type[0])
        image_format = "BGR".encode("utf-8")
        self._sock.send_multipart(
            [
                version,
                timestamp,
                frame_type,
                image_format,
                rows,
                cols,
                mat_type,
                image.tobytes(),
            ]
        )

    def isOpened(self):
        """ Return true if VideoCapture has been ready to read

        :return: True of False
        """
        return not (self._sock.closed)

    def release(self):
        """ Close video captureing connection

        """
        self._sock.close()
