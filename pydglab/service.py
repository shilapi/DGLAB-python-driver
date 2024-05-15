import logging, asyncio
from bleak import BleakClient
from typing import Tuple
from pydglab.model_v3 import *
from pydglab.uuid import *
from pydglab.bthandler_v3 import *

logger = logging.getLogger(__name__)


class dglab_v3(object):
    coyote = Coyote()

    def __init__(self, address: str = None) -> None:
        self.address = address
        return None

    async def create(self) -> "dglab_v3":
        """
        建立郊狼连接并初始化。
        Creates a connection to the DGLAB device and initialize.

        Returns:
            dglab: The initialized DGLAB object.

        Raises:
            Exception: If the device is not supported or if an unknown device is connected.
        """

        if self.address is None:
            # If address is not provided, scan for it.
            self.address = await scan_()

        # Connect to the device.
        logger.debug(f"Connecting to {self.address}")
        self.client = BleakClient(self.address, timeout=20.0)
        await self.client.connect()

        # Wait for a second to allow service discovery to complete
        await asyncio.sleep(1)

        # Check if the device is valid.
        services = self.client.services
        service = [service.uuid for service in services]
        logger.debug(f"Got services: {str(service)}")
        if CoyoteV2.serviceBattery in service and CoyoteV2.serviceEStim in service:
            raise Exception("Use dglab_v2 instead")
        elif CoyoteV3.serviceWrite in service and CoyoteV3.serviceNotify in service:
            logger.info("Connected to DGLAB v3.0")

            # Update BleakGATTCharacteristic into characteristics list, to optimize performence.
            self.characteristics = CoyoteV3
            logger.debug(f"Got characteristics: {str(self.characteristics)}")
            for i in self.client.services.characteristics.values():
                if i.uuid == self.characteristics.characteristicWrite:
                    self.characteristics.characteristicWrite = i
                elif i.uuid == self.characteristics.characteristicNotify:
                    self.characteristics.characteristicNotify = i

        else:
            raise Exception(
                "Unknown device (你自己看看你连的是什么jb设备)"
            )  # Sorry for my language.

        self.channelA_wave_set: list[tuple[int, int, int]] = []
        self.channelB_wave_set: list[tuple[int, int, int]] = []

        # Initialize notify
        await notify_(self.client, self.characteristics, self.notify_callback)

        # Initialize self.coyote
        await self.set_wave_sync(0, 0, 0, 0, 0, 0)
        await self.set_strength(0, 0)

        # Start the wave tasks, to keep the device functioning.
        self.wave_tasks = asyncio.gather(
            self._retainer(),
            self._channelA_wave_set_handler(),
            self._channelB_wave_set_handler(),
        )

        return self

    @classmethod
    async def from_address(cls, address: str) -> "dglab_v3":
        """
        从指定的地址创建一个新的郊狼实例，在需要同时连接多个设备时格外好用。
        Creates a new instance of the 'dglab' class using the specified address.

        Args:
            address (str): The address to connect to.

        Returns:
            dglab: An instance of the 'dglab' class.

        """

        return cls(address)

    async def notify_callback(self, sender: BleakGATTCharacteristic, data: bytearray):
        logger.debug(f"{sender}: {data}")
        if data[0] == 0xB1:
            self.coyote.ChannelA.strength = int(data[2])
            self.coyote.ChannelB.strength = int(data[3])
        if data[0] == 0xBE:
            self.coyote.ChannelA.limit = int(data[1])
            self.coyote.ChannelB.limit = int(data[2])
            self.coyote.ChannelA.coefficientFrequency = int(data[3])
            self.coyote.ChannelB.coefficientFrequency = int(data[4])
            self.coyote.ChannelA.coefficientStrenth = int(data[5])
            self.coyote.ChannelB.coefficientStrenth = int(data[6])

    async def get_strength(self) -> Tuple[int, int]:
        """
        读取郊狼当前强度。
        Retrieves the strength of the device.

        Returns:
            Tuple[int, int]: 通道A强度，通道B强度
        """
        return self.coyote.ChannelA.strength, self.coyote.ChannelB.strength

    async def set_strength(self, strength: int, channel: ChannelA | ChannelB) -> None:
        """
        设置电压强度。
        额外设置这个函数用于单独调整强度只是为了和设置波形的函数保持一致罢了。
        Set the strength of the device.

        Args:
            strength (int): 电压强度
            channel (ChannelA | ChannelB): 对手频道

        Returns:
            int: 电压强度
        """

        if channel is ChannelA:
            self.coyote.ChannelA.strength = strength
        elif channel is ChannelB:
            self.coyote.ChannelB.strength = strength
        return (
            self.coyote.ChannelA.strength
            if channel is ChannelA
            else self.coyote.ChannelB.strength
        )

    async def set_strength_sync(self, strengthA: int, strengthB: int) -> None:
        """
        同步设置电流强度。
        这是正道。
        Set the strength of the device synchronously.

        Args:
            strengthA (int): 通道A电压强度
            strengthB (int): 通道B电压强度

        Returns:
            (int, int): A通道强度，B通道强度
        """
        self.coyote.ChannelA.strength = strengthA
        self.coyote.ChannelB.strength = strengthB
        return self.coyote.ChannelA.strength, self.coyote.ChannelB.strength

    """
    How wave set works:
    1. Set the wave set for channel A and channel B.
    2. The wave set will be looped indefinitely by
    wave_set_handler, and change the value in 
    self.coyote.ChannelN.waveN.
    """

    async def set_wave_set(
        self, wave_set: list[tuple[int, int, int]], channel: ChannelA | ChannelB
    ) -> None:
        """
        设置波形组，也就是所谓“不断变化的波形”。
        Set the wave set for the device.

        Args:
            wave_set (list[tuple[int, int, int]]): 波形组
            channel (ChannelA | ChannelB): 对手通道

        Returns:
            None: None
        """
        if channel is ChannelA:
            self.channelA_wave_set = wave_set
        elif channel is ChannelB:
            self.channelB_wave_set = wave_set
        return None

    async def set_wave_set_sync(
        self,
        wave_setA: list[tuple[int, int, int]],
        wave_setB: list[tuple[int, int, int]],
    ) -> None:
        """
        同步设置波形组。
        Set the wave set for the device synchronously.

        Args:
            wave_setA (list[tuple[int, int, int]]): 通道A波形组
            wave_setB (list[tuple[int, int, int]]): 通道B波形组

        Returns:
            None: None
        """
        self.channelA_wave_set = wave_setA
        self.channelB_wave_set = wave_setB
        return None

    def waveset_converter(
        self, wave_set: list[tuple[int, int, int]]
    ) -> tuple[int, int]:
        """
        Convert the wave set to the correct format.
        """
        freq = int((((wave_set[0] + wave_set[1]) - 10) / 990) * 230 + 10)
        strenth = int(wave_set[2] * 5)

        return freq, strenth

    async def _channelA_wave_set_handler(self) -> None:
        """
        Do not use this function directly.

        Yep this is how wave set works :)
        PR if you have a better solution.
        """
        try:
            while True:
                for wave in self.channelA_wave_set:
                    wave = self.waveset_converter(wave)
                    self.coyote.ChannelA.wave = wave[0]
                    self.coyote.ChannelA.waveStrenth = wave[1]
                    await asyncio.sleep(0.1)
        except asyncio.exceptions.CancelledError:
            pass

    async def _channelB_wave_set_handler(self) -> None:
        """
        Do not use this function directly.

        Yep this is how wave set works :)
        PR if you have a better solution.
        """
        try:
            while True:
                for wave in self.channelB_wave_set:
                    wave = self.waveset_converter(wave)
                    self.coyote.ChannelB.wave = wave[0]
                    self.coyote.ChannelB.waveStrenth = wave[1]
                    await asyncio.sleep(0.1)
        except asyncio.exceptions.CancelledError:
            pass

    """
    How set_wave works:
    Basically, it will generate a wave set with only one wave,
    and changes the value in self.hannelN_wave_set.
    All the wave changes will be applied to the device by wave_set.
    """

    async def set_wave(
        self, waveX: int, waveY: int, waveZ: int, channel: ChannelA | ChannelB
    ) -> Tuple[int, int, int]:
        """
        设置波形。
        枯燥，乏味，感觉不如。。。
        Set the wave for the device.

        Args:
            waveX (int): 连续发出X个脉冲，每个脉冲持续1ms
            waveY (int): 发出脉冲后停止Y个周期，每个周期持续1ms
            waveZ (int): 每个脉冲的宽度为Z*5us
            channel (ChannelA | ChannelB): 对手通道

        Returns:
            Tuple[int, int, int]: 波形
        """
        if channel is ChannelA:
            self.channelA_wave_set = [(waveX, waveY, waveZ)]
        elif channel is ChannelB:
            self.channelB_wave_set = [(waveX, waveY, waveZ)]
        return waveX, waveY, waveZ

    async def set_wave_sync(
        self,
        waveX_A: int,
        waveY_A: int,
        waveZ_A: int,
        waveX_B: int,
        waveY_B: int,
        waveZ_B: int,
    ) -> Tuple[int, int, int, int, int, int]:
        """
        同步设置波形。
        Set the wave for the device synchronously.

        Args:
            waveX_A (int): 通道A，连续发出X个脉冲，每个脉冲持续1ms
            waveY_A (int): 通道A，发出脉冲后停止Y个周期，每个周期持续1ms
            waveZ_A (int): 通道A，每个脉冲的宽度为Z
            waveX_B (int): 通道B，连续发出X个脉冲，每个脉冲持续1ms
            waveY_B (int): 通道B，发出脉冲后停止Y个周期，每个周期持续1ms
            waveZ_B (int): 通道B，每个脉冲的宽度为Z

        Returns:
            Tuple[Tuple[int, int, int], Tuple[int, int, int]]: A通道波形，B通道波形
        """
        self.channelA_wave_set = [(waveX_A, waveY_A, waveZ_A)]
        self.channelB_wave_set = [(waveX_B, waveY_B, waveZ_B)]
        return (waveX_A, waveY_A, waveZ_A), (waveX_B, waveY_B, waveZ_B)

    async def _retainer(self) -> None:
        """
        Don't use this function directly.
        """
        while True:
            r = await write_strenth_(self.client, self.coyote, self.characteristics)
            logger.debug(f"Retainer response: {r}")
            try:
                await asyncio.sleep(0.1)
            except asyncio.exceptions.CancelledError:
                break
        return None

    async def close(self) -> None:
        """
        郊狼虽好，可不要贪杯哦。
        Close the connection to the device.

        Returns:
            None: None
        """
        try:
            self.wave_tasks.cancel()
            await self.wave_tasks
        except asyncio.CancelledError or asyncio.exceptions.InvalidStateError:
            pass
        await self.client.disconnect()
        return None
