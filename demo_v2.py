# Description: This is a demo script to show how to use the pydglab library to interact with the DGLab device.

import asyncio
import logging

import pydglab
from pydglab import model_v2

logging.basicConfig(
    format="%(module)s [%(levelname)s]: %(message)s", level=logging.INFO
)


async def _():
    await pydglab.scan()
    dglab_instance = pydglab.dglab()
    try:
        await dglab_instance.create()
    except TimeoutError:
        logging.error("Timeout, retrying...")
        await dglab_instance.create()
    await dglab_instance.get_strength()
    await dglab_instance.set_strength_sync(1, 1)
    await dglab_instance.set_wave_sync(0, 0, 0, 0, 0, 0)
    await dglab_instance.set_wave_set(model_v2.Wave_set["Going_Faster"], model_v2.ChannelA)
    await dglab_instance.get_batterylevel()
    await dglab_instance.get_strength()
    await asyncio.sleep(2)
    await dglab_instance.close()


asyncio.run(_())