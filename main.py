"""
main.py
Startpunkt der Anwendung. Steuert die Generierung und den anschließenden Upload.
"""

import os
import sys
import logging
from generate_chart import create_organigram_svg
from upload_chart import ChurchToolsWikiUploader

# --- Logging Setup ---
DEBUG_MODE = os.getenv("CT_DEBUG", "false").lower() in ("true", "1", "yes")
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

TEMP_SVG_FILE = "temp_organigram.svg"

def main() -> None:
    logger.info("=== ChurchTools Organigramm Generator gestartet ===")

    # 1. Organigramm generieren
    generation_success = create_organigram_svg(TEMP_SVG_FILE)

    if not generation_success:
        logger.critical("Abbruch: Organigramm konnte nicht generiert werden.")
        sys.exit(1)

    # 2. Upload nach ChurchTools
    try:
        uploader = ChurchToolsWikiUploader()

        identifier = uploader.get_page_identifier()
        if not identifier:
            logger.critical("Abbruch: Zielseite in ChurchTools nicht gefunden.")
            sys.exit(1)

        upload_success = uploader.upload_file(TEMP_SVG_FILE, identifier)

        if not upload_success:
            logger.critical("Abbruch: Fehler beim Hochladen der Datei.")
            sys.exit(1)

    except ValueError as ve:
        logger.critical(f"Konfigurationsfehler: {ve}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unerwarteter Fehler im Upload-Prozess: {e}")
        sys.exit(1)

    logger.info("=== Prozess erfolgreich abgeschlossen ===")

if __name__ == "__main__":
    main()
