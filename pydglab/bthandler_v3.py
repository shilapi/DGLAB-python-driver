import logging
from bleak import BleakClient, BleakScanner
from typing import Tuple, List
from bitstring import BitArray

from pydglab.model_v3 import *
from pydglab.uuid import *

logger = logging.getLogger(__name__)


async def scan():
    """
    Scan for DGLAB v3.0 devices and return a list of tuples with the address and the RSSI of the devices found.

    Returns:
        List[Tuple[str, int]]: (address, RSSI)
    """
    devices = await BleakScanner().discover(return_adv=True)
    dglab_v3: List[Tuple[str, int]] = []
    for i, j in devices.values():
        if j.local_name == CoyoteV3.name and i.address is not None:
            logger.info(f"Found DGLAB v3.0 {i.address}")
            dglab_v3.append((i.address, j.rssi))
    if not dglab_v3:
        logger.error("No DGLAB v3.0 found")
    return dglab_v3


async def scan_():
    dglab_v3 = await scan()
    if not dglab_v3:
        raise Exception("No DGLAB v3.0 found")
    if len(dglab_v3) > 1:
        logger.warning("Multiple DGLAB v3.0 found, chosing the closest one")
    elif len(dglab_v3) == 0:
        raise Exception("No DGLAB v3.0 found")
    return sorted(dglab_v3, key=lambda device: device[1])[0][0]


async def notify_(client: BleakClient, characteristics: CoyoteV3, callback: callable):
    await client.start_notify(characteristics.characteristicNotify, callback)


async def write_strenth_(
    client: BleakClient, value: Coyote, characteristics: CoyoteV3
):
    struct = (
        0xB0,
        0b00010000 + 0b00001111,
        value.ChannelA.strength,
        value.ChannelB.strength,
        value.ChannelA.wave,
        value.ChannelA.waveStrenth,
        value.ChannelB.wave,
        value.ChannelB.waveStrenth,
    )
    bytes_ = bytes(
        tuple(
            item if isinstance(item, int) else subitem
            for item in struct
            for subitem in (tuple(item) if isinstance(item, list) else (item,))
        )
    )
    logger.debug(f"Sending bytes: {bytes_.hex()} , which is {bytes_}")
    await client.write_gatt_char(characteristics.characteristicWrite, bytes_)


async def write_coefficient_(
    client: BleakClient, value: Coyote, characteristics: CoyoteV3
):
    struct = (
        0xBF,
        value.ChannelA.limit,
        value.ChannelB.limit,
        value.ChannelA.coefficientFrequency,
        value.ChannelB.coefficientFrequency,
        value.ChannelA.coefficientStrenth,
        value.ChannelB.coefficientStrenth,
    )
    bytes_ = bytes(
        tuple(
            item if isinstance(item, int) else subitem
            for item in struct
            for subitem in (item if isinstance(item, tuple) else (item,))
        )
    )
    logger.debug(f"Sending bytes: {bytes_.hex()} , which is {bytes_}")
    await client.write_gatt_char(characteristics.characteristicWrite, bytes_)
