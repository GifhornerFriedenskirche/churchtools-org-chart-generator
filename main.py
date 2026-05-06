"""
main.py
Main execution entry point for the ChurchTools Org-Chart Generator.
Orchestrates generation and uploading.
"""

import os
import time
import logging
from generate_chart import create_organigram
from upload_chart import upload_to_churchtools

# --- Setup Global Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger()

if os.getenv("CT_DEBUG", "false").lower() in ("true", "1", "yes"):
    logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    start_time = time.time()
    logger.info("=== Starting ChurchTools Org-Chart Generator ===")

    # Credentials and Configuration from Environment
    CT_BASE_URL = os.getenv("CT_BASE_URL", "")
    CT_API_TOKEN = os.getenv("CT_API_TOKEN", "")
    CT_WIKI_CATEGORY_ID = os.getenv("CT_WIKI_CATEGORY_ID", "")
    CT_WIKI_PAGE_TITLE = os.getenv("CT_WIKI_PAGE_TITLE", "")

    # Configurable base filename (defaults to "temp_organigram")
    FILE_BASENAME = os.getenv("CT_FILE_NAME", "temp_organigram")

    if not CT_BASE_URL or not CT_API_TOKEN:
        logger.error("❌ Critical Error: CT_BASE_URL or CT_API_TOKEN is missing in environment variables.")
        exit(1)

    # Phase 1: Generate Files
    svg_file_path = f"{FILE_BASENAME}.svg"
    png_file_path = f"{FILE_BASENAME}.png"

    success = create_organigram(CT_BASE_URL, CT_API_TOKEN, svg_file_path)

    # Phase 2: Upload Files (If generation was successful)
    if success:
        if CT_WIKI_CATEGORY_ID and CT_WIKI_PAGE_TITLE:
            try:
                wiki_cat_id = int(CT_WIKI_CATEGORY_ID)

                # Upload SVG
                upload_to_churchtools(svg_file_path, wiki_cat_id, CT_WIKI_PAGE_TITLE, CT_API_TOKEN, CT_BASE_URL)

                # Upload PNG if generated (controlled by CT_GENERATE_PNG in generate_chart)
                if os.path.exists(png_file_path):
                    upload_to_churchtools(png_file_path, wiki_cat_id, CT_WIKI_PAGE_TITLE, CT_API_TOKEN, CT_BASE_URL)

            except ValueError:
                logger.error("❌ CT_WIKI_CATEGORY_ID must be a valid integer.")
        else:
            logger.info("ℹ️ Upload skipped: CT_WIKI_CATEGORY_ID or CT_WIKI_PAGE_TITLE not set.")

    duration = time.time() - start_time
    logger.info(f"=== Process completed successfully in {duration:.2f} seconds ===")
