"""
upload_chart.py
Klasse für den sicheren Upload von Dateien an eine ChurchTools Wiki-Seite.
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class ChurchToolsWikiUploader:
    def __init__(self) -> None:
        self.base_url = os.getenv("CT_BASE_URL", "").rstrip("/")
        self.api_token = os.getenv("CT_API_TOKEN", "")
        self.category_id = os.getenv("CT_WIKI_CATEGORY_ID", "")
        self.page_title = os.getenv("CT_WIKI_PAGE_TITLE", "Organigramm")

        self._validate_env_vars()

        auth_header = self.api_token if self.api_token.startswith("Login ") else f"Login {self.api_token}"

        # Statische Header statt Session, um Session-Cookies und CSRF-Probleme zu vermeiden
        self.headers = {
            "Authorization": auth_header,
            "Accept": "application/json"
        }

    def _validate_env_vars(self) -> None:
        """Prüft, ob alle benötigten Umgebungsvariablen vorhanden sind."""
        missing: list[str] = []

        if not self.base_url: missing.append("CT_BASE_URL")
        if not self.api_token: missing.append("CT_API_TOKEN")
        if not self.category_id: missing.append("CT_WIKI_CATEGORY_ID")

        if missing:
            raise ValueError(f"Fehlende Umgebungsvariablen: {', '.join(missing)}")

    def get_page_identifier(self) -> Optional[str]:
        """Holt die GUID der Wiki-Seite anhand des Titels."""
        url = f"{self.base_url}/api/wiki/categories/{self.category_id}/pages"
        logger.debug(f"Hole Wiki-Seiten von: {url}")

        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            res.raise_for_status()

            for page in res.json().get("data", []):
                if page.get("title") == self.page_title:
                    return page.get("identifier")

            logger.error(f"Seite '{self.page_title}' in Kategorie {self.category_id} nicht gefunden.")
            return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Wiki-Seiten: {e}")
            return None

    def upload_file(self, file_path: str, identifier: str) -> bool:
        """Lädt die Datei hoch."""
        if not os.path.exists(file_path):
            logger.error(f"Datei nicht gefunden: {file_path}")
            return False

        domain_type = f"wiki_{self.category_id}"
        upload_url = f"{self.base_url}/api/files/{domain_type}/{identifier}"

        try:
            with open(file_path, "rb") as f:
                files = {"files[]": (os.path.basename(file_path), f, "image/svg+xml")}
                logger.info(f"Lade '{file_path}' in ChurchTools hoch...")

                res = requests.post(upload_url, headers=self.headers, files=files, timeout=30)
                res.raise_for_status()

                logger.info("🎉 Upload erfolgreich!")
                return True
        except Exception as e:
            logger.error(f"Upload fehlgeschlagen: {e}")
            return False
