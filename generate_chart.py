"""
generate_chart.py
Holt die Daten aus ChurchTools, berechnet das Layout und erstellt das SVG.
"""

import os
import logging
import requests
from typing import Any

logger = logging.getLogger(__name__)

def fetch_ct_groups() -> list[dict[str, Any]]:
    """
    Holt alle Gruppen aus ChurchTools via API.
    """
    base_url = os.getenv("CT_BASE_URL", "").rstrip("/")
    api_token = os.getenv("CT_API_TOKEN", "")

    if not base_url or not api_token:
        logger.error("Fehlende Variablen CT_BASE_URL oder CT_API_TOKEN für die Gruppenabfrage.")
        return []

    auth_header = api_token if api_token.startswith("Login ") else f"Login {api_token}"
    headers = {
        "Authorization": auth_header,
        "Accept": "application/json"
    }

    url = f"{base_url}/api/groups"

    try:
        logger.info("Lade Gruppen aus ChurchTools herunter...")
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()

        groups = res.json().get("data", [])
        logger.info(f"{len(groups)} Gruppen erfolgreich geladen.")
        return groups

    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Gruppen-API: {e}")
        return []

def create_organigram_svg(output_path: str) -> bool:
    """
    Generiert das Organigramm als SVG-Datei.

    Args:
        output_path (str): Pfad, unter dem das SVG gespeichert werden soll.

    Returns:
        bool: True wenn erfolgreich erstellt, False bei einem Fehler.
    """
    logger.info("Starte Generierung des Organigramms...")

    try:
        # 1. Lade echte Daten aus CT
        groups = fetch_ct_groups()
        if not groups:
            logger.warning("Generierung abgebrochen: Keine Gruppen gefunden.")
            return False

        # 2. TODO: Berechne hier die Baumstruktur anhand von Parent/Child Beziehungen
        # z.B. tree = build_tree(groups)

        # 3. Dummy-SVG (zeigt nun die echte Anzahl der Gruppen an!)
        dummy_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="150">
    <rect width="100%" height="100%" fill="#f0f0f0" rx="10" />
    <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#333">
        Organigramm bereit! ({len(groups)} Gruppen aus ChurchTools geladen)
    </text>
</svg>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(dummy_svg)

        logger.info(f"Organigramm erfolgreich unter '{output_path}' gespeichert.")
        return True

    except Exception as e:
        logger.error(f"Fehler bei der SVG-Generierung: {e}")
        return False

# Lokaler Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    create_organigram_svg("test_organigram.svg")
