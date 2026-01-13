import os
import logging
import re
from pathlib import Path

from github import Github

from .PixelOTACrawler import get_all_otas
from .toolconfig import ToolConfig
import subprocess

logger = logging.getLogger(__name__)


def extract_kmi_from_kernel(kernel_path: str) -> str | None:
    if not os.path.exists(kernel_path):
        logger.debug("Kernel file does not exist: %s", kernel_path)
        return None

    try:
        with open(kernel_path, 'rb') as f:
            data = f.read()
    except Exception as e:
        logger.error("Error reading kernel file %s: %s", kernel_path, e)
        return None

    m = re.search(b'Linux version [^\n\r\x00]+', data)
    if m:
        try:
            line = m.group(0).decode('utf-8', errors='replace')
        except Exception:
            line = m.group(0).decode('latin1', errors='replace')

        vm = re.search(r'Linux version\s+([^\s(]+)', line)
        if vm:
            kmim = re.search(r"(\d*\.\d*\.\d*-android\d*)-.*", vm.group(1))
            if kmim:
                return kmim.group(1)
        return line
    return None

def get_kernel_link_from_kmi(kmi: str) -> str | None:
    logger.info("Checking GitHub for latest WildKernels/GKI_KernelSU_SUSFS release...")
    g = Github()
    repo = g.get_repo("WildKernels/GKI_KernelSU_SUSFS")
    # find latest non-testing release
    releases = repo.get_releases()
    release = None
    for r in releases:
        if "testing" in r.name.lower():
            continue
        release = r
        break
    if not release:
        logger.error("No suitable release found in WildKernels/GKI_KernelSU_SUSFS")
        g.close()
        return None
    logger.info("Found! Release: %s created at %s", release.name, str(release.created_at))
    latest_assets = release.get_assets()
    collected = []

    for asset in latest_assets:
        if kmi in asset.name:
            collected.append((asset.name, asset.browser_download_url))
    logger.warning("Choosing Normal-AnyKernel3")
    candidates = [item for item in collected if "Normal-AnyKernel3" in item[0]]
    logger.info("Found! %s at %s", candidates[-1][0], candidates[-1][1])
    g.close()
    return candidates[-1][1] if candidates else None
    # return "https://github.com/WildKernels/GKI_KernelSU_SUSFS/releases/download/v1.5.12-r19/6.1.145-android14-2025-09-Normal-AnyKernel3.zip"

class OTAHelper:
    def __init__(self, avbroot_input: ToolConfig, device_name: str, output_dir: str, temp_dir: str):
        self.toolconfig = avbroot_input
        self.device_name = device_name
        self.known_versions = get_all_otas(device_name)
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        pass

    def newer_version_available(self) -> bool:
        latest_version = self.known_versions[-1]
        for root, dirs, files in os.walk(self.output_dir):
            for file in files:
                if latest_version[1].split("/")[-1] in file:
                    logger.info("Latest version %s already exists in output directory.", latest_version[0])
                    return False

        logger.info("Newer version %s available for device %s.", latest_version[0], self.device_name)
        return True

    def root(self, input_ota: str, output_boot: str):
        logger.info("Rooting boot image...")
        cmd_extract = ["/usr/bin/sh", "-c", f"cd {self.temp_dir} && mkdir -p boot_extract && avbroot ota extract --input {input_ota} --partition boot"]
        cmd_unpack = ["/usr/bin/sh", "-c", f"cd {self.temp_dir} && cd boot_extract && magiskboot unpack ../boot.img"]
        cmd_kernel_extract = ["/usr/bin/sh", "-c", f"cd {self.temp_dir} && unzip new_kernel.zip"]
        cmd_kernel_move = ["/usr/bin/sh", "-c", f"cd {self.temp_dir} && mv -f Image boot_extract/kernel"]
        cmd_repack = ["/usr/bin/sh", "-c",
                      f"cd {self.temp_dir} && cd boot_extract && magiskboot repack ../boot.img {output_boot}"]

        try:
            subprocess.run(cmd_extract, check=True)
            subprocess.run(cmd_unpack, check=True)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to extract/unpack boot image: %s", e)
            return None

        kernel_path = os.path.join(self.temp_dir, 'boot_extract', 'kernel')
        kmi = extract_kmi_from_kernel(kernel_path)
        logger.info("Detected kmi from stock boot image: %s", kmi)

        cmd_download = ["/usr/bin/sh", "-c",
                        f"cd {self.temp_dir} && wget -O new_kernel.zip {get_kernel_link_from_kmi(kmi)}"]
        logger.info("Downloading new kernel...")
        subprocess.run(cmd_download, check=True)
        logger.info("New kernel downloaded.")
        logger.info("Processing new boot image...")
        subprocess.run(cmd_kernel_extract, check=True)
        subprocess.run(cmd_kernel_move, check=True)
        subprocess.run(cmd_repack, check=True)
        logger.info("Boot image rooted and repacked.")
        return None


    def patch(self, input_ota: str, output_ota: str, boot: str, data: ToolConfig) -> bool:
        logger.info("Patching OTA...")
        cmd = (f"avbroot ota patch --input {input_ota} --output {output_ota} --key-ota {data.ota_key_path}"
               f" --key-avb {data.avb_key_path} --cert-ota {data.ota_cert_path} --prepatched {boot}")
        result = subprocess.run(cmd, check=True, shell=True)
        logger.info("Patch complete.")
        return result.returncode == 0

    def handle_custota(self, input_ota: str, output_json: str, data: ToolConfig) -> bool:
        logger.info("Handling custota...")
        cmd1 = ["custota-tool", "gen-csig", "--input", input_ota, "--key", data.ota_key_path, "--cert", data.ota_cert_path]
        subprocess.run(cmd1, check=True)
        cmd2 = ["custota-tool", "gen-update-info", "--file", output_json, "--location", input_ota.split("/")[-1]]
        subprocess.run(cmd2, check=True)
        subprocess.run(cmd2, check=True)
        logger.info("Custota handling complete.")
        return True

    def full_run(self):
        logger.info("Starting full OTA patching run...")
        version = self.known_versions[-1]
        self.download(version)
        file_name = version[1].split("/")[-1]
        pre_patched = str(Path(os.path.join(self.temp_dir, file_name)).expanduser().resolve(strict=False))
        post_patched = str(Path(os.path.join(self.output_dir, file_name)).expanduser().resolve(strict=False))
        patched_boot = str(Path(os.path.join(self.temp_dir, "boot.patched.img")).expanduser().resolve(strict=False))
        output_json = os.path.join(self.output_dir, f"{self.device_name}.json")
        self.root(pre_patched, patched_boot)
        self.patch(pre_patched, post_patched, patched_boot, self.toolconfig)
        self.handle_custota(post_patched, output_json, self.toolconfig)
        logger.info("Full OTA patching run complete! Cleaning up...")
        subprocess.run(["/usr/bin/sh", "-c", f"rm -rf {self.temp_dir}/*"], check=True)


    def download(self, version: tuple[str, str]) -> None:
        logger.info(f"Downloading {version[0]} OTA...")
        file_name = version[1].split("/")[-1]
        temp_path = os.path.join(self.temp_dir, file_name)
        subprocess.run(["wget", "--continue", "-O", temp_path, self.known_versions[-1][1]], check=True, capture_output=True)
        logger.info("Download complete.")