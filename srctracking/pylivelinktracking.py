from __future__ import annotations
from collections import deque
from statistics import mean
from enum import IntEnum
import struct
import datetime
from timecode import Timecode
from uuid import uuid1

class TrackingDataValues(IntEnum):
    MouseX = 1
    MouseY = 2
    Aux1 = 3
    Aux2 = 4
    Aux3 = 5
    Aux4 = 6
    Aux5 = 7
    Aux6 = 8
    Aux7 = 9
    Aux8 = 10
    marker1X = 11
    marker1Y = 12
    marker1Z = 13
    marker2X = 14
    marker2Y = 15
    marker2Z = 16
    marker3X = 17
    marker3Y = 18
    marker3Z = 19


class PyLiveLinkTracking:

    def __init__(self, name: str = "Python_LiveLinkTracking", 
                        uuid: str = str(uuid1()), fps=60, 
                        filter_size: int = 5) -> None:

        # properties
        self.uuid = uuid
        self.name = name
        self.fps = fps
        self._filter_size = filter_size

        self._version = 6
        now = datetime.datetime.now()
        timcode = Timecode(
            self._fps, f'{now.hour}:{now.minute}:{now.second}:{now.microsecond * 0.001}')
        self._frames = timcode.frames
        self._sub_frame = 1056060032                # I don't know how to calculate this
        self._denominator = int(self._fps / 60)     # 1 most of the time
        self._values = [0.000] * 61
        self._old_values = []                 # used for filtering
        for i in range(61):
            self._old_values.append(deque([0.0], maxlen = self._filter_size))

    @property
    def uuid(self) -> str:
        return self._uuid

    @uuid.setter
    def uuid(self, value: str) -> None:
        # uuid needs to start with a $, if it doesn't add it
        if not value.startswith("$"):
            self._uuid = '$' + value
        else:
            self._uuid = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def fps(self) -> int:
        return self._fps

    @fps.setter
    def fps(self, value: int) -> None:
        if value < 1:
            raise ValueError("Only fps values greater than 1 are allowed.")
        self._fps = value

    def encode(self) -> bytes:
        version_packed = struct.pack('<I', self._version)
        uuiid_packed = bytes(self._uuid, 'utf-8')
        name_lenght_packed = struct.pack('!i', len(self._name))
        name_packed = bytes(self._name, 'utf-8')

        now = datetime.datetime.now()
        timcode = Timecode(
            self._fps, f'{now.hour}:{now.minute}:{now.second}:{now.microsecond * 0.001}')
        frames_packed = struct.pack("!II", timcode.frames, self._sub_frame)  
        frame_rate_packed = struct.pack("!II", self._fps, self._denominator)
        data_packed = struct.pack('!B61f', 61, *self._values)
        
        return version_packed + uuiid_packed + name_lenght_packed + name_packed + \
            frames_packed + frame_rate_packed + data_packed

    def get_value(self, index: TrackingDataValues) -> float:
        return self._values[index.value]

    def set_value(self, index: TrackingDataValues, value: float, 
                        no_filter: bool = True) -> None:
        if no_filter:
            self._values[index] = value
        else:
            self._old_values[index].append(value)
            filterd_value = mean(self._old_values[index])
            self._values[index] = filterd_value
