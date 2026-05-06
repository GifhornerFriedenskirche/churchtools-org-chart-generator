"""
upload_chart.py
Module for handling clean uploads to the ChurchTools Wiki.
Includes automatic lookup of the Page Identifier via Page Title.
"""

import os
import mimetypes
import logging
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)

def _get_page_identifier_by_title(base_url: str, category_id: int, page_title: str, headers: Dict[str, str]) -> Optional[str]:
    """Looks up the technical identifier of a Wiki page based on its title."""
    url = f"{base_url.rstrip('/')}/api/wiki/categories/{category_id}/pages"
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.ok:
            pages = res.json().get("data", [])
            for page in pages:
                if page.get("title") == page_title:
                    return page.get("identifier")
            logger.error(f"❌ Wiki page with title '{page_title}' not found in category {category_id}.")
            return None
        else:
            logger.error(f"❌ Error fetching Wiki pages: HTTP {res.status_code}")
            return None
    except Exception as e:
        logger.error(f"⚠️ API connection error during Wiki lookup: {e}")
        return None

def upload_to_churchtools(file_path: str, wiki_category_id: int, page_title: str, api_token: str, base_url: str) -> bool:
    """Uploads a file to a ChurchTools Wiki page (including cleanup of old versions)."""
    auth_header = api_token if api_token.startswith("Login ") else f"Login {api_token}"

    # Explicitly type the dictionaries to satisfy Pylance
    json_headers: Dict[str, str] = {"Authorization": auth_header, "Accept": "application/json"}

    # 1. Look up the page identifier
    logger.info(f"🔍 Looking up Wiki page '{page_title}'...")
    page_identifier = _get_page_identifier_by_title(base_url, wiki_category_id, page_title, json_headers)

    if not page_identifier:
        return False

    domain_type = f"wiki_{wiki_category_id}"
    domain_identifier = page_identifier
    filename = os.path.basename(file_path)

    # --- PHASE 1: CLEANUP ---
    get_files_url = f"{base_url.rstrip('/')}/api/files/{domain_type}/{domain_identifier}"
    try:
        logger.info(f"🔍 Checking for existing file '{filename}' in Wiki...")
        res_get = requests.get(get_files_url, headers=json_headers, timeout=15)

        if res_get.ok:
            for f in res_get.json().get("data", []):
                if f.get("name") == filename:
                    file_id = f.get("id")
                    logger.info(f"🗑️ Old version found (ID: {file_id}). Deleting...")
                    res_del = requests.delete(f"{base_url.rstrip('/')}/api/files/{file_id}", headers=json_headers, timeout=15)
                    if res_del.ok:
                        logger.info("✅ Old version successfully removed.")
                    else:
                        logger.warning(f"⚠️ Failed to delete old version (HTTP {res_del.status_code}).")
        else:
             logger.debug(f"Could not retrieve file list (HTTP {res_get.status_code}). Skipping cleanup.")

    except Exception as e:
        logger.warning(f"⚠️ Error during cleanup phase: {e}")

    # --- PHASE 2: UPLOAD ---
    upload_url = f"{base_url.rstrip('/')}/api/files/{domain_type}/{domain_identifier}"

    # Explicitly type the upload headers
    upload_headers: Dict[str, str] = {"Authorization": auth_header}

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "image/png" if file_path.lower().endswith(".png") else "image/svg+xml"

    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        logger.info(f"⬆️ Uploading new version of '{filename}' (Size: {file_size_mb:.2f} MB)...")

        with open(file_path, "rb") as f:
            files_payload = {"files[]": (filename, f, mime_type)}
            res = requests.post(upload_url, headers=upload_headers, files=files_payload, timeout=30)

            if not res.ok:
                logger.error(f"❌ Upload failed for {filename}! HTTP {res.status_code}: {res.text}")
                res.raise_for_status()

            logger.info(f"🎉 '{filename}' successfully uploaded.")
            return True

    except Exception as e:
        logger.error(f"⚠️ Error uploading {filename}: {e}")
        return False
