# AUTOGENERATED! DO NOT EDIT! File to edit: 01B_pleiades_prep_worker.ipynb (unless otherwise specified).

__all__ = ['process_scene', 'level', 'host', 'q', 'logger']

# Cell
import json
from .pleiades import prep_pleiades

# Cell
def process_scene(json_data):
    loaded_json = json.loads(json_data)
    prep_pleiades(**loaded_json)

# Cell
import os
import logging
import datetime

from .rediswq import RedisWQ

# Cell
level = os.getenv("LOGLEVEL", "INFO").upper()
logging.basicConfig(format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S", level=level)

# Cell
host = os.getenv("REDIS_SERVICE_HOST", "redis-master")
q = RedisWQ(name="jobPL", host=host)

# Cell
logger = logging.getLogger("worker")
logger.info(f"Worker with sessionID: {q.sessionID()}")
logger.info(f"Initial queue state: empty={q.empty()}")

# Cell
while not q.empty():
    item = q.lease(lease_secs=1800, block=True, timeout=600)
    if item is not None:
        itemstr = item.decode("utf=8")
        logger.info(f"Working on {itemstr}")
        start = datetime.datetime.now().replace(microsecond=0)

        process_scene(itemstr)
        q.complete(item)

        end = datetime.datetime.now().replace(microsecond=0)
        logger.info(f"Total processing time {end - start}")
    else:
        logger.info("Waiting for work")

# Cell
logger.info("Queue empty, exiting")