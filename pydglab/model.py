from typing import Optional

class ChannelA(object):
    def __init__(self):
        self.strength: Optional[int] = None
        self.wave: Optional[bytearray[int]] = bytearray((0, 0, 0))
        self.waveX: Optional[int] = self.wave[0]
        self.waveY: Optional[int] = self.wave[1]
        self.waveZ: Optional[int] = self.wave[2]

class ChannelB(object):
    def __init__(self):
        self.strength: Optional[int] = None
        self.wave: Optional[bytearray[int]] = bytearray((0, 0, 0))
        self.waveX: Optional[int] = self.wave[0]
        self.waveY: Optional[int] = self.wave[1]
        self.waveZ: Optional[int] = self.wave[2]

class Coyote(object):
    def __init__(self):
        self.ChannelA: Optional[ChannelA] = ChannelA()
        self.ChannelB: Optional[ChannelB] = ChannelB()
        self.Battery: Optional[int] = None