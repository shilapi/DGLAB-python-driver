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
        self.ChannelA: ChannelA = ChannelA()
        self.ChannelB: ChannelB = ChannelB()
        self.Battery: Optional[int] = None


Wave_set = {
    "Going_Faster": [
        (5, 135, 20),
        (5, 125, 20),
        (5, 115, 20),
        (5, 105, 20),
        (5, 95, 20),
        (4, 86, 20),
        (4, 76, 20),
        (4, 66, 20),
        (3, 57, 20),
        (3, 47, 20),
        (3, 37, 20),
        (2, 28, 20),
        (2, 18, 20),
        (1, 14, 20),
        (1, 9, 20),
    ],
}
