import logging, asyncio
from bleak import BleakClient
from typing import Tuple
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
        
        await asyncio.sleep(1)  # Wait for a second to allow service discovery to complete
        
        # Check if the device is valid.
        services = self.client.services
        
        self.characteristics = CoyoteV2
        logger.debug(f"Got characteristics: {str(self.characteristics)}")
        for i in self.client.services.characteristics.values():
            if i.uuid == self.characteristics.characteristicBattery:
                self.characteristics.characteristicBattery = i
            elif i.uuid == self.characteristics.characteristicEStimPower:
                self.characteristics.characteristicEStimPower = i
            elif i.uuid == self.characteristics.characteristicEStimA:
                self.characteristics.characteristicEStimA = i
            elif i.uuid == self.characteristics.characteristicEStimB:
                self.characteristics.characteristicEStimB = i
        
        service = [service.uuid for service in services]
        logger.debug(f"Got services: {str(service)}")
        if CoyoteV2.serviceBattery in service and CoyoteV2.serviceEStim in service:
            logger.info("Connected to DGLAB v2.0")
        elif CoyoteV3.serviceWrite in service and CoyoteV3.serviceNotify in service:
            raise Exception("DGLAB v3.0 is not supported")
        else:
            raise Exception("Unknown device (你自己看看你连的是什么jb设备)")
        
        self.channelA_wave_set: list[tuple[int, int, int]] = []
        self.channelB_wave_set: list[tuple[int, int, int]] = []
        
        # Initialize self.coyote
        await self.get_batterylevel()
        await self.get_strength()
        
        await self.set_wave_sync(0, 0, 0, 0, 0, 0)
        await self.set_strength(0, 0)
        
        self.wave_tasks = asyncio.gather(self._keep_wave(), self._set_channelA_wave_set(), self._set_channelB_wave_set())
        
        return self


    @classmethod
    async def from_address(cls, address: str) -> 'dglab':
        return cls(address)


    async def get_batterylevel(self) -> int:
        value = await get_batterylevel_(self.client, self.characteristics)
        value = value[0]
        logger.debug(f"Received battery level: {value}")
        self.coyote.Battery = int(value)
        return self.coyote.Battery


    async def get_strength(self) -> Tuple[int, int]:
        value = await get_strength_(self.client, self.characteristics)
        logger.debug(f"Received strength: A: {value[0]}, B: {value[1]}")
        self.coyote.ChannelA.strength = int(value[0])
        self.coyote.ChannelB.strength = int(value[1])
        return self.coyote.ChannelA.strength, self.coyote.ChannelB.strength


    async def set_strength(self, strengthA: int, strengthB: int) -> None:
        self.coyote.ChannelA.strength = strengthA
        self.coyote.ChannelB.strength = strengthB
        r = await set_strength_(self.client, self.coyote, self.characteristics)
        logger.debug(f"Set strength response: {r}")
        return self.coyote.ChannelA.strength, self.coyote.ChannelB.strength


    async def set_wave_set(self, wave_set: list[tuple[int, int, int]], channel: ChannelA | ChannelB) -> None:
        if channel is ChannelA:
            self.channelA_wave_set = wave_set
        elif channel is ChannelB:
            self.channelB_wave_set = wave_set
        return None
        


    async def _set_channelA_wave_set(self) -> None:
        try:
            while True:
                for wave in self.channelA_wave_set:
                    self.coyote.ChannelA.waveX = wave[0]
                    self.coyote.ChannelA.waveY = wave[1]
                    self.coyote.ChannelA.waveZ = wave[2]
                    await asyncio.sleep(0.1)
        except asyncio.exceptions.CancelledError:
            pass


    async def _set_channelB_wave_set(self) -> None:
        try:
            while True:
                for wave in self.channelB_wave_set:
                    self.coyote.ChannelB.waveX = wave[0]
                    self.coyote.ChannelB.waveY = wave[1]
                    self.coyote.ChannelB.waveZ = wave[2]
                    await asyncio.sleep(0.1)
        except asyncio.exceptions.CancelledError:
            pass


    async def set_wave_sync(self, waveX_A: int, waveY_A: int, waveZ_A: int, waveX_B: int, waveY_B: int, waveZ_B: int) -> Tuple[int, int, int, int, int, int]:
        self.channelA_wave_set = [(waveX_A, waveY_A, waveZ_A)]
        self.channelB_wave_set = [(waveX_B, waveY_B, waveZ_B)]
        return (waveX_A, waveY_A, waveZ_A), (waveX_B, waveY_B, waveZ_B)


    async def _set_wave_sync(self, waveX_A: int, waveY_A: int, waveZ_A: int, waveX_B: int, waveY_B: int, waveZ_B: int) -> None:
        self.coyote.ChannelA.waveX = waveX_A
        self.coyote.ChannelA.waveY = waveY_A
        self.coyote.ChannelA.waveZ = waveZ_A
        self.coyote.ChannelB.waveX = waveX_B
        self.coyote.ChannelB.waveY = waveY_B
        self.coyote.ChannelB.waveZ = waveZ_B
        r = await set_wave_sync_(self.client, self.coyote, self.characteristics)
        logger.debug(f"Set wave sync response: {r}")
        return self.coyote.ChannelA, self.coyote.ChannelB


    async def _keep_wave(self) -> None:
        while True:
            r = await set_wave_sync_(self.client, self.coyote, self.characteristics)
            logger.debug(f"Set wave sync response: {r}")
            try:
                await asyncio.sleep(0.1)
            except asyncio.exceptions.CancelledError:
                break
        return None


    async def close(self):
        try:
            self.wave_tasks.cancel()
            await self.wave_tasks
        except asyncio.CancelledError or asyncio.exceptions.InvalidStateError:
            pass
        await self.client.disconnect()
        return None
