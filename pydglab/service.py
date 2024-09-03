import logging, asyncio, time
from bleak import BleakClient
from typing import Tuple
import pydglab.model_v2 as model_v2
import pydglab.model_v3 as model_v3
from pydglab.uuid import *
import pydglab.bthandler_v2 as v2
import pydglab.bthandler_v3 as v3

logger = logging.getLogger(__name__)


class dglab(object):
    coyote = model_v2.Coyote()

    def __init__(self, address: str = None) -> None:
        self.address = address
        return None

    async def create(self) -> "dglab":
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
            self.address = await v2.scan_()

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
            logger.info("Connected to DGLAB v2.0")

            # Update BleakGATTCharacteristic into characteristics list, to optimize performence.
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

        elif CoyoteV3.serviceWrite in service and CoyoteV3.serviceNotify in service:
            raise Exception("DGLAB v3.0 found, please use dglab_v3 instead")
        else:
            raise Exception(
                "Unknown device (你自己看看你连的是什么jb设备)"
            )  # Sorry for my language.

        self.channelA_wave_set: list[tuple[int, int, int]] = []
        self.channelB_wave_set: list[tuple[int, int, int]] = []

        # Initialize self.coyote
        await self.get_batterylevel()
        await self.get_strength()

        await self.set_wave_sync(0, 0, 0, 0, 0, 0)
        await self.set_strength(0, 0)

        # Start the wave tasks, to keep the device functioning.
        self.wave_tasks = asyncio.gather(
            self._keep_wave(),
        )

        return self

    @classmethod
    async def from_address(cls, address: str) -> "dglab":
        """
        从指定的地址创建一个新的郊狼实例，在需要同时连接多个设备时格外好用。
        Creates a new instance of the 'dglab' class using the specified address.

        Args:
            address (str): The address to connect to.

        Returns:
            dglab: An instance of the 'dglab' class.

        """

        return cls(address)

    async def get_batterylevel(self) -> int:
        """
        读取郊狼设备剩余电量，小心没电导致的寸止哦：）
        Retrieves the battery level from the device.

        Returns:
            int: The battery level as an integer value.
        """

        value = await v2.get_batterylevel_(self.client, self.characteristics)
        value = value[0]
        logger.debug(f"Received battery level: {value}")
        self.coyote.Battery = int(value)
        return self.coyote.Battery

    async def get_strength(self) -> Tuple[int, int]:
        """
        读取郊狼当前强度。
        Retrieves the strength of the device.

        Returns:
            Tuple[int, int]: 通道A强度，通道B强度
        """
        value = await v2.get_strength_(self.client, self.characteristics)
        logger.debug(f"Received strength: A: {value[0]}, B: {value[1]}")
        self.coyote.ChannelA.strength = int(value[0])
        self.coyote.ChannelB.strength = int(value[1])
        return self.coyote.ChannelA.strength, self.coyote.ChannelB.strength

    async def set_strength(self, strength: int, channel: model_v2.ChannelA | model_v2.ChannelB) -> None:
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

        if channel is model_v2.ChannelA:
            self.coyote.ChannelA.strength = strength
        elif channel is model_v2.ChannelB:
            self.coyote.ChannelB.strength = strength
        r = await v2.set_strength_(self.client, self.coyote, self.characteristics)
        logger.debug(f"Set strength response: {r}")
        return (
            self.coyote.ChannelA.strength
            if channel is model_v2.ChannelA
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
        r = await v2.set_strength_(self.client, self.coyote, self.characteristics)
        logger.debug(f"Set strength response: {r}")
        return self.coyote.ChannelA.strength, self.coyote.ChannelB.strength

    """
    How wave set works:
    1. Set the wave set for channel A and channel B.
    2. The wave set will be looped indefinitely by
    wave_set_handler, and change the value in 
    self.coyote.ChannelN.waveN.
    """

    async def set_wave_set(
        self, wave_set: list[tuple[int, int, int]], channel: model_v2.ChannelA | model_v2.ChannelB
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
        if channel is model_v2.ChannelA:
            self.channelA_wave_set = wave_set
        elif channel is model_v2.ChannelB:
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

    """
    How set_wave works:
    Basically, it will generate a wave set with only one wave,
    and changes the value in self.hannelN_wave_set.
    All the wave changes will be applied to the device by wave_set.
    """

    async def set_wave(
        self, waveX: int, waveY: int, waveZ: int, channel: model_v2.ChannelA | model_v2.ChannelB
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
        if channel is model_v2.ChannelA:
            self.channelA_wave_set = [(waveX, waveY, waveZ)]
        elif channel is model_v2.ChannelB:
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
        r = await v2.set_wave_(
            self.client, self.coyote.ChannelA, self.characteristics
        ), await v2.set_wave_(self.client, self.coyote.ChannelB, self.characteristics)
        return (waveX_A, waveY_A, waveZ_A), (waveX_B, waveY_B, waveZ_B)

    def _channelA_wave_set_handler(self):
        """
        Do not use this function directly.

        Yep this is how wave set works :)
        PR if you have a better solution.
        """
        while True:
            for wave in self.channelA_wave_set:
                self.coyote.ChannelA.waveX = wave[0]
                self.coyote.ChannelA.waveY = wave[1]
                self.coyote.ChannelA.waveZ = wave[2]
                yield (None)

    def _channelB_wave_set_handler(self):
        """
        Do not use this function directly.

        Yep this is how wave set works :)
        PR if you have a better solution.
        """
        while True:
            for wave in self.channelB_wave_set:
                self.coyote.ChannelB.waveX = wave[0]
                self.coyote.ChannelB.waveY = wave[1]
                self.coyote.ChannelB.waveZ = wave[2]
                yield (None)

    async def _keep_wave(self) -> None:
        """
        Don't use this function directly.
        """
        last_time = time.time()

        ChannelA_keeping = self._channelA_wave_set_handler()
        ChannelB_keeping = self._channelB_wave_set_handler()

        while True:
            try:
                # logger.debug(f"Time elapsed: {time.time() - last_time}")
                if time.time() - last_time >= 0.1:

                    # Record time for loop
                    last_time = time.time()

                    r = await v2.set_wave_(
                        self.client, self.coyote.ChannelA, self.characteristics
                    ), await v2.set_wave_(
                        self.client, self.coyote.ChannelB, self.characteristics
                    )
                    logger.debug(f"Set wave response: {r}")
                    next(ChannelA_keeping)
                    next(ChannelB_keeping)
            except asyncio.exceptions.CancelledError:
                logger.error("Cancelled error")
                break
        return None

    async def close(self):
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


class dglab_v3(object):
    coyote = model_v3.Coyote()

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
            self.address = await v3.scan_()

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
            raise Exception("DGLAB v2.0 found, please use dglab instead")
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
        await v3.notify_(self.client, self.characteristics, self.notify_callback)

        # Initialize self.coyote
        self.coyote.ChannelA.limit = 200
        self.coyote.ChannelB.limit = 200
        self.coyote.ChannelA.coefficientStrenth = 100
        self.coyote.ChannelB.coefficientStrenth = 100
        self.coyote.ChannelA.coefficientFrequency = 100
        self.coyote.ChannelB.coefficientFrequency = 100

        await self.set_coefficient(200, 100, 100, model_v3.ChannelA)
        await self.set_coefficient(200, 100, 100, model_v3.ChannelB)
        await self.set_wave_sync(0, 0, 0, 0, 0, 0)
        await self.set_strength_sync(0, 0)

        # Start the wave tasks, to keep the device functioning.
        self.wave_tasks = asyncio.gather(
            self._retainer(),
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
            # self.coyote.ChannelA.strength = int(data[2])
            # self.coyote.ChannelB.strength = int(data[3])
            logger.debug(f"Getting bytes(0xB1): {data.hex()} , which is {data}")
        if data[0] == 0xBE:
            # self.coyote.ChannelA.limit = int(data[1])
            # self.coyote.ChannelB.limit = int(data[2])
            # self.coyote.ChannelA.coefficientFrequency = int(data[3])
            # self.coyote.ChannelB.coefficientFrequency = int(data[4])
            # self.coyote.ChannelA.coefficientStrenth = int(data[5])
            # self.coyote.ChannelB.coefficientStrenth = int(data[6])
            logger.debug(f"Getting bytes(0xBE): {data.hex()} , which is {data}")

    async def get_strength(self) -> Tuple[int, int]:
        """
        读取郊狼当前强度。
        Retrieves the strength of the device.

        Returns:
            Tuple[int, int]: 通道A强度，通道B强度
        """
        return self.coyote.ChannelA.strength, self.coyote.ChannelB.strength

    async def set_strength(self, strength: int, channel: model_v3.ChannelA | model_v3.ChannelB) -> None:
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

        if channel is model_v3.ChannelA:
            self.coyote.ChannelA.strength = strength
        elif channel is model_v3.ChannelB:
            self.coyote.ChannelB.strength = strength
        return (
            self.coyote.ChannelA.strength
            if channel is model_v3.ChannelA
            else self.coyote.ChannelB.strength
        )

    async def set_coefficient(
        self,
        strength_limit: int,
        strength_coefficient: int,
        frequency_coefficient: int,
        channel: model_v3.ChannelA | model_v3.ChannelB,
    ) -> None:
        """
        设置强度上线与平衡常数。
        Set the strength limit and coefficient of the device.

        Args:
            strength_limit (int): 电压强度上限
            strength_coefficient (int): 强度平衡常数
            frequency_coefficient (int): 频率平衡常数
            channel (ChannelA | ChannelB): 对手频道

        Returns:
            Tuple[int, int, int]: 电压强度上限，强度平衡常数，频率平衡常数
        """

        if channel is model_v3.ChannelA:
            self.coyote.ChannelA.limit = strength_limit
            self.coyote.ChannelA.coefficientStrenth = strength_coefficient
            self.coyote.ChannelA.coefficientFrequency = frequency_coefficient
        elif channel is model_v3.ChannelB:
            self.coyote.ChannelB.limit = strength_limit
            self.coyote.ChannelB.coefficientStrenth = strength_coefficient
            self.coyote.ChannelB.coefficientFrequency = frequency_coefficient

        await v3.write_coefficient_(self.client, self.coyote, self.characteristics)

        return (
            (
                self.coyote.ChannelA.limit,
                self.coyote.ChannelA.coefficientStrenth,
                self.coyote.ChannelA.coefficientFrequency,
            )
            if channel is model_v3.ChannelA
            else (
                self.coyote.ChannelB.limit,
                self.coyote.ChannelB.coefficientStrenth,
                self.coyote.ChannelB.coefficientFrequency,
            )
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
        self, wave_set: list[tuple[int, int, int]], channel: model_v3.ChannelA | model_v3.ChannelB
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
        if channel is model_v3.ChannelA:
            self.channelA_wave_set = wave_set
        elif channel is model_v3.ChannelB:
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

    """
    How set_wave works:
    Basically, it will generate a wave set with only one wave,
    and changes the value in self.hannelN_wave_set.
    All the wave changes will be applied to the device by wave_set.
    """

    async def set_wave(
        self, waveX: int, waveY: int, waveZ: int, channel: model_v3.ChannelA | model_v3.ChannelB
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
        if channel is model_v3.ChannelA:
            self.channelA_wave_set = [(waveX, waveY, waveZ)]
        elif channel is model_v3.ChannelB:
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

    def _channelA_wave_set_handler(self):
        """
        Do not use this function directly.

        Yep this is how wave set works :)
        PR if you have a better solution.
        """
        try:
            while True:
                for wave in self.channelA_wave_set:
                    wave = self.waveset_converter(wave)
                    self.coyote.ChannelA.wave.insert(0, wave[0])
                    self.coyote.ChannelA.wave.pop()
                    self.coyote.ChannelA.waveStrenth.insert(0, wave[1])
                    self.coyote.ChannelA.waveStrenth.pop()
                    yield (None)
        except asyncio.exceptions.CancelledError:
            pass

    def _channelB_wave_set_handler(self):
        """
        Do not use this function directly.

        Yep this is how wave set works :)
        PR if you have a better solution.
        """
        try:
            while True:
                for wave in self.channelB_wave_set:
                    wave = self.waveset_converter(wave)
                    self.coyote.ChannelB.wave.insert(0, wave[0])
                    self.coyote.ChannelB.wave.pop()
                    self.coyote.ChannelB.waveStrenth.insert(0, wave[1])
                    self.coyote.ChannelB.waveStrenth.pop()
                    yield (None)
        except asyncio.exceptions.CancelledError:
            pass

    async def _retainer(self) -> None:
        """
        Don't use this function directly.
        """
        ChannelA_keeping = self._channelA_wave_set_handler()
        ChannelB_keeping = self._channelB_wave_set_handler()

        last_time = time.time()

        while True:
            if time.time() - last_time >= 0.1:

                # Record time for loop
                last_time = time.time()
                logger.debug(
                    f"Using wave: {self.coyote.ChannelA.wave}, {self.coyote.ChannelA.waveStrenth}, {self.coyote.ChannelB.wave}, {self.coyote.ChannelB.waveStrenth}"
                )
                r = await v3.write_strenth_(
                    self.client, self.coyote, self.characteristics
                )
                logger.debug(f"Retainer response: {r}")
                next(ChannelA_keeping)
                next(ChannelB_keeping)

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
