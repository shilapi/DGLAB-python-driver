import logging
from bleak import BleakClient, BleakScanner
from typing import Tuple, List
from bitstring import BitArray

from pydglab.model import *
from pydglab.uuid import *

logger = logging.getLogger(__name__)


async def scan_():
    devices = await BleakScanner().discover(return_adv=True)
    dglab_v2: List[Tuple] = []
    for i, j in devices.values():
        if j.local_name == CoyoteV2.name and i.address is not None:
            logger.info(f"Found DGLAB v2.0 {i.address}")
            dglab_v2.append((i.address, j.rssi))
    if not dglab_v2:
        logger.error("No DGLAB v2.0 found")
        raise Exception("No DGLAB v2.0 found")
    if len(dglab_v2) > 1:
        logger.warning("Multiple DGLAB v2.0 found, chosing the closest one")
    elif len(dglab_v2) == 0:
        raise Exception("No DGLAB v2.0 found")
    return sorted(dglab_v2, key=lambda device: device[1])[0][0]


async def get_batterylevel_(client: BleakClient, characteristics: CoyoteV2 | CoyoteV3):
    r = await client.read_gatt_char(characteristics.characteristicBattery)
    return r


async def get_strength_(client: BleakClient, characteristics: CoyoteV2 | CoyoteV3):
    r = await client.read_gatt_char(characteristics.characteristicEStimPower)
    r = BitArray(r).bin
    return int(r[-11:], 2), int(r[-22:-11], 2)


async def set_strength_(client: BleakClient, value: Coyote, characteristics: CoyoteV2 | CoyoteV3):
    # Create a byte array with the strength values.
    # The values are multiplied by 7 to convert them to the correct range.
    binArray = '0b00'+'{0:011b}'.format(value.ChannelB.strength * 7)+'{0:011b}'.format(value.ChannelA.strength * 7)
    array = bytearray(BitArray(bin=binArray).tobytes())
    
    r = await client.write_gatt_char(characteristics.characteristicEStimPower, array)
    return r


async def set_wave_(client: BleakClient, value: ChannelA | ChannelB, characteristics: CoyoteV2 | CoyoteV3):
    # Create a byte array with the wave values.
    binArray = '0b0000'+'{0:05b}'.format(value.waveZ)+'{0:010b}'.format(value.waveY)+'{0:05b}'.format(value.waveX)
    array = bytearray(BitArray(bin=binArray).tobytes())

    r = await client.write_gatt_char(characteristics.characteristicEStimA if type(value) is ChannelA else characteristics.characteristicEStimB, array)
    return r


async def set_wave_sync_(client: BleakClient, value: Coyote, characteristics: CoyoteV2 | CoyoteV3):
    # Create a byte array with the wave values.
    binArrayA = '0b0000'+'{0:05b}'.format(value.ChannelA.waveZ)+'{0:010b}'.format(value.ChannelA.waveY)+'{0:05b}'.format(value.ChannelA.waveX)
    arrayA = bytearray(BitArray(bin=binArrayA).tobytes())
    
    binArrayB = '0b0000'+'{0:05b}'.format(value.ChannelB.waveZ)+'{0:010b}'.format(value.ChannelB.waveY)+'{0:05b}'.format(value.ChannelB.waveX)
    arrayB = bytearray(BitArray(bin=binArrayB).tobytes())
    
    r = await client.write_gatt_char(characteristics.characteristicEStimA, arrayA), await client.write_gatt_char(characteristics.characteristicEStimB, arrayB)
    return r
