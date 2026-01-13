from pathlib import Path


class ToolConfig:
    def __init__(self, avb_key_path: str, ota_key_path: str, ota_cert_path: str):
        self.avb_key_path = str(Path(avb_key_path).expanduser().resolve(strict=False))
        self.ota_key_path = str(Path(ota_key_path).expanduser().resolve(strict=False))
        self.ota_cert_path = str(Path(ota_cert_path).expanduser().resolve(strict=False))
