from typing import Optional


class ChannelA(object):
    def __init__(self):
        self.strength: Optional[int] = None
        self.wave: Optional[list[int]] = [0, 0, 0, 0]
        self.waveStrenth: Optional[list[int]] = [0, 0, 0, 0]
        self.coefficientStrenth: Optional[int] = None
        self.coefficientFrequency: Optional[int] = None
        self.limit: Optional[int] = None


class ChannelB(object):
    def __init__(self):
        self.strength: Optional[int] = None
        self.wave: Optional[list[int]] = [0, 0, 0, 0]
        self.waveStrenth: Optional[list[int]] = [0, 0, 0, 0]
        self.coefficientStrenth: Optional[int] = None
        self.coefficientFrequency: Optional[int] = None
        self.limit: Optional[int] = None


class Coyote(object):
    def __init__(self):
        self.ChannelA: Optional[ChannelA] = ChannelA()
        self.ChannelB: Optional[ChannelB] = ChannelB()


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
