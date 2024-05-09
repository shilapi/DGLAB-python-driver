import logging
import asyncio
from bleak import BleakClient
from typing import Tuple, List
from pydglab.model import *
from pydglab.uuid import *
from pydglab.bthandler import *

logger = logging.getLogger(__name__)

class dglab(object):
    coyote = Coyote()

    def __init__(self, address: str = None) -> None:
        self.address = address
        return None


    async def create(self) -> 'dglab':
        if self.address is None: 
            # If address is not provided, scan for it.
            self.address = await scan_()
        
        # Connect to the device.
        logger.debug(f"Connecting to {self.address}")
        self.client = BleakClient(self.address, timeout=20.0)
        await self.client.connect()
        
        # Check if the device is valid.
        services = self.client.services
        service = [service.uuid for service in services]
        logger.debug(f"Got services: {str(service)}")
        if CoyoteV2.serviceBattery in service and CoyoteV2.serviceEStim in service:
            logger.info("Connected to DGLAB v2.0")
        elif CoyoteV3.serviceWrite in service and CoyoteV3.serviceNotify in service:
            raise Exception("DGLAB v3.0 is not supported")
        else:
            raise Exception("Unknown device (你自己看看你连的是什么jb设备)")
        
        # Initialize self.coyote
        await self.get_batterylevel()
        await self.get_strength()
        
        await self.set_wave_sync(0, 0, 0, 0, 0, 0)
        await self.set_strength(0, 0)
        
        return self


    @classmethod
    async def from_address(cls, address: str) -> 'dglab':
        return cls(address)


    async def get_batterylevel(self) -> int:
        value = await get_batterylevel_(self.client)
        value = value[0]
        logger.debug(f"Received battery level: {value}")
        self.coyote.Battery = int(value)
        return self.coyote.Battery


    async def get_strength(self) -> Tuple[int, int]:
        value = await get_strength_(self.client)
        logger.debug(f"Received strength: A: {value[0] / 7}, B: {value[1] / 7}")
        self.coyote.ChannelA.strength = int(value[0] / 7)
        self.coyote.ChannelB.strength = int(value[1] / 7)
        return self.coyote.ChannelA.strength, self.coyote.ChannelB.strength


    async def set_strength(self, strengthA: int, strengthB: int) -> None:
        self.coyote.ChannelA.strength = strengthA
        self.coyote.ChannelB.strength = strengthB
        r = await set_strength_(self.client, self.coyote)
        logger.debug(f"Set strength response: {r}")
        return self.coyote.ChannelA.strength, self.coyote.ChannelB.strength


    async def set_wave(self, waveX: int, waveY: int, waveZ: int, channel: ChannelA | ChannelB) -> None:
        if channel is ChannelA:
            self.coyote.ChannelA.waveX = waveX
            self.coyote.ChannelA.waveY = waveY
            self.coyote.ChannelA.waveZ = waveZ
            channel = self.coyote.ChannelA
        elif channel is ChannelB:
            self.coyote.ChannelB.waveX = waveX
            self.coyote.ChannelB.waveY = waveY
            self.coyote.ChannelB.waveZ = waveZ
            channel = self.coyote.ChannelB
        else:
            raise TypeError("Channel must be ChannelA or ChannelB")
        r = await set_wave_(self.client, channel)
        logger.debug(f"Set wave response: {r}")
        return channel


    async def set_wave_sync(self, waveX_A: int, waveY_A: int, waveZ_A: int, waveX_B: int, waveY_B: int, waveZ_B: int) -> None:
        self.coyote.ChannelA.waveX = waveX_A
        self.coyote.ChannelA.waveY = waveY_A
        self.coyote.ChannelA.waveZ = waveZ_A
        self.coyote.ChannelB.waveX = waveX_B
        self.coyote.ChannelB.waveY = waveY_B
        self.coyote.ChannelB.waveZ = waveZ_B
        r = await set_wave_sync_(self.client, self.coyote)
        logger.debug(f"Set wave sync response: {r}")
        return self.coyote.ChannelA, self.coyote.ChannelB



    async def close(self):
        await self.client.disconnect()
        return None
