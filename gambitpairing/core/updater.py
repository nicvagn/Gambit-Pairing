import requests
import json
from typing import Optional, Dict, Any, Tuple
from packaging.version import parse as parse_version
import os
import tempfile
import zipfile
import shutil
import logging
import sys
import subprocess
from pathlib import Path
import hashlib

# Fallback update URL if not defined elsewhere
UPDATE_URL = "https://api.github.com/repos/Chickaboo/Gambit-Pairing/releases/latest"

class Updater:
    """Handles checking for and applying application updates from GitHub Releases."""

    def __init__(self, current_version: str):
        self.current_version = current_version
        self.latest_version_info: Optional[Dict[str, Any]] = None
        self.update_zip_path: Optional[str] = None
        self.expected_checksum: Optional[str] = None

    def check_for_updates(self) -> bool:
        logging.info("Checking for updates...")
        try:
            response = requests.get(UPDATE_URL, timeout=10)
            response.raise_for_status()
            self.latest_version_info = response.json()
            latest_version_str = self.latest_version_info.get("tag_name", "0.0.0").lstrip('v')
            is_newer = parse_version(latest_version_str) > parse_version(self.current_version)
            logging.info(f"Latest version: {latest_version_str}, Current version: {self.current_version}, Newer available: {is_newer}")
            return is_newer
        except requests.RequestException as e:
            logging.error(f"Update check failed: Network error - {e}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred during update check: {e}")
            return False

    def get_latest_version(self) -> Optional[str]:
        return self.latest_version_info.get("tag_name", "N/A").lstrip('v') if self.latest_version_info else None

    def get_release_notes(self) -> Optional[str]:
        return self.latest_version_info.get("body", "No description available.") if self.latest_version_info else None

    def _get_asset_urls(self) -> Tuple[Optional[str], Optional[str]]:
        if not self.latest_version_info: return None, None
        assets = self.latest_version_info.get("assets", [])
        zip_url, checksum_url = None, None
        for asset in assets:
            if asset.get("name", "").endswith(".zip"): zip_url = asset.get("browser_download_url")
            if asset.get("name", "").endswith(".sha256"): checksum_url = asset.get("browser_download_url")
        return zip_url, checksum_url

    def download_update(self, progress_callback=None) -> Optional[str]:
        zip_url, checksum_url = self._get_asset_urls()
        if not zip_url: return None

        if checksum_url:
            try:
                checksum_response = requests.get(checksum_url, timeout=10)
                self.expected_checksum = checksum_response.text.split()[0].strip()
                logging.info(f"Expected checksum: {self.expected_checksum}")
            except Exception as e:
                logging.warning(f"Could not download checksum: {e}")

        try:
            response = requests.get(zip_url, stream=True, timeout=60)
            total_size = int(response.headers.get('content-length', 0))
            temp_dir = tempfile.gettempdir()
            self.update_zip_path = os.path.join(temp_dir, "gambit_update.zip")
            bytes_downloaded = 0
            with open(self.update_zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress_callback(int((bytes_downloaded / total_size) * 100))
            return self.update_zip_path
        except requests.RequestException as e:
            logging.error(f"Failed to download update: {e}")
            return None

    def verify_checksum(self, file_path: str) -> bool:
        if not self.expected_checksum: return True
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        calculated_checksum = sha256_hash.hexdigest()
        logging.info(f"Calculated checksum: {calculated_checksum}")
        return calculated_checksum.lower() == self.expected_checksum.lower()

    def extract_update(self) -> Optional[str]:
        if not self.update_zip_path: return None
        extract_dir = Path(tempfile.gettempdir()) / "gambit_update_extracted"
        if extract_dir.exists(): shutil.rmtree(extract_dir)
        try:
            with zipfile.ZipFile(self.update_zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            os.remove(self.update_zip_path)
            
            extracted_items = list(extract_dir.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                final_path = Path(tempfile.gettempdir()) / "gambit_update_final"
                if final_path.exists(): shutil.rmtree(final_path)
                shutil.move(str(extracted_items[0]), str(final_path))
                shutil.rmtree(extract_dir)
                logging.info(f"Update contents moved to {final_path}")
                return str(final_path)
            return str(extract_dir)
        except Exception as e:
            logging.error(f"Failed to extract update: {e}")
            return None

    def get_pending_update_path(self) -> Optional[str]:
        path = Path(tempfile.gettempdir()) / "gambit_update_final"
        return str(path) if path.is_dir() else None

    def cleanup_pending_update(self):
        path = self.get_pending_update_path()
        if path: shutil.rmtree(path, ignore_errors=True)

    def apply_update(self, extracted_path: str) -> None:
        """
        Apply the update by copying files from the extracted update directory to the app directory,
        skipping the running executable. No admin rights or external scripts required.
        """
        if not getattr(sys, 'frozen', False):
            logging.warning("Skipping update: not running from a frozen executable.")
            return

        app_path = Path(sys.executable)
        app_dir = app_path.parent
        extracted_dir = Path(extracted_path)
        errors = []

        def copytree_overwrite(src, dst):
            for item in src.iterdir():
                s = src / item.name
                d = dst / item.name
                if s.is_dir():
                    d.mkdir(exist_ok=True)
                    copytree_overwrite(s, d)
                else:
                    # Skip the running executable
                    if d.resolve() == app_path.resolve():
                        continue
                    try:
                        shutil.copy2(s, d)
                    except Exception as e:
                        errors.append(f"Failed to copy {s} to {d}: {e}")

        try:
            copytree_overwrite(extracted_dir, app_dir)
            logging.info(f"Update files copied from {extracted_dir} to {app_dir}")
            # Optionally, cleanup extracted_dir
            try:
                shutil.rmtree(extracted_dir)
            except Exception as e:
                logging.warning(f"Could not remove temp update dir: {e}")
            if errors:
                logging.error("Some files could not be updated:\n" + "\n".join(errors))
            else:
                logging.info("Update applied successfully. Please restart the application.")
        except Exception as e:
            logging.error(f"Failed to apply update: {e}")
