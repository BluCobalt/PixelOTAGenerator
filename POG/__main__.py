import logging
import sys
import json
import time
import os

from POG import OTAHelper
from POG.toolconfig import ToolConfig

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")

def load_config(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error("Failed to load config file %s: %s. Make sure to use an absolute path.", path, e)
        return {}

def process_device(device, toolcfg):
    logging.info("Processing device %s", device)
    helper = OTAHelper(toolcfg, device, "/app/output", "/app/temp")

    try:
        if helper.newer_version_available():
            logging.info("Newer version available for %s", device)
            helper.full_run()
        else:
            logging.info("No newer version for %s", device)
    except Exception as e:
        logging.exception("Error while processing device %s: %s", device, e)


def main():
    toolconfig = ToolConfig(
        "/app/avbroot-input/avb.key",
        "/app/avbroot-input/ota.key",
        "/app/avbroot-input/ota.crt"
    )

    pdevices = os.environ.get("POG_DEVICES")
    phours = os.environ.get("POG_INTERVAL_HOURS")
    if not pdevices or not phours:
        logging.error("Environment variables POG_DEVICES and POG_INTERVAL_HOURS must be set.")
        sys.exit(1)

    devices = pdevices.split(",")
    hours = int(phours)
    if len(devices) == 0:
        logging.error("No devices specified in POG_DEVICES.")
        sys.exit(1)

    logging.info("Starting device monitor for %d devices; checking every %s hours",
                 len(devices), hours)

    while True:
        for device in devices:
            try:
                process_device(device, toolconfig)
            except Exception:
                logging.exception("Unhandled error processing device: %s", device)
        logging.info("Cycle complete; sleeping for %.0f seconds (~%.2f hours)", hours * 3600, hours)
        time.sleep(hours * 3600)


if __name__ == "__main__":
    main()
