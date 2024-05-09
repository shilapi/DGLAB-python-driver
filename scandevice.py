from bleak import BleakScanner
import asyncio
import logging
import sys

import pydglab

logging.basicConfig(format='%(module)s [%(levelname)s]: %(message)s', level=logging.DEBUG)


async def _():
    dglab_instance = pydglab.dglab()
    await dglab_instance.create()
    await dglab_instance.get_batterylevel()
    await dglab_instance.get_strength()
    await dglab_instance.set_wave_sync(5, 95, 2, 5, 95, 2)
    await dglab_instance.set_strength(50, 50)
    await dglab_instance.get_batterylevel()
    await dglab_instance.get_strength()

asyncio.run(_())