# ChurchTools Org Chart Generator

This project automates the creation of an organizational chart (Org Chart) based on the group structures within a ChurchTools instance. It fetches the live group hierarchy via the ChurchTools REST API, generates a visual SVG chart, and automatically uploads it to a specified ChurchTools Wiki page.

## 🚀 Features

* **Automated Data Retrieval:** Fetches live group data directly from the ChurchTools API.
* **Seamless Wiki Integration:** Automatically resolves the target Wiki page GUID based on the category ID and page title.
* **Stateless API Authentication:** Uses secure Personal Login Tokens (`Authorization: Login <token>`), completely bypassing legacy CSRF and session-cookie issues.
* **Modular Architecture:** Strict Separation of Concerns between orchestration, generation, and uploading for high maintainability.
* **Robust Error Handling:** Comprehensive `try/except` blocks, HTTP status validation, and strict type hinting (Pylance/MyPy compliant).

## 📁 Architecture

The project is split into three main, highly-cohesive modules:

1. `main.py` - **The Orchestrator:** Manages the overall execution flow, triggering the generation and handling the subsequent upload.
2. `generate_chart.py` - **The Engine:** Connects to the `/api/groups` endpoint, fetches the raw hierarchical data, calculates the layout, and renders the `temp_organigram.svg`.
3. `upload_chart.py` - **The Uploader:** Handles API authentication, dynamically resolves the Wiki page identifier via `/api/wiki/categories/{id}/pages`, and safely pushes the SVG into the ChurchTools file system.

## 🛠️ Prerequisites

* **Python 3.9+**
* Python packages: `requests`

Install the required dependencies via pip:
```bash
pip install requests
```
(Note: It is highly recommended to use a virtual environment `venv`.)

## ⚙️ Configuration

The application is configured entirely via Environment Variables to prevent sensitive tokens from being hardcoded into the source code.
Set the following variables before running the script:

Variable,Description,Example
`CT_BASE_URL`,The base URL of your ChurchTools instance.,`https://yourchurch.church.tools`
`CT_API_TOKEN`,Your personal ChurchTools API Login Token.,`abc123def456...`
`CT_WIKI_CATEGORY_ID`,The ID of the Wiki category where the page lives.,`23`
`CT_WIKI_PAGE_TITLE`,The exact title of the target Wiki page.,`Organigramm`
`CT_DEBUG`,(Optional) Set to true or 1 to enable verbose logging.,`true`

Getting your `CT_API_TOKEN`
  1. Log into ChurchTools.
  2. Click on your profile picture (top right) -> Profile Settings.
  3. Go to Security or Login.
  4. Generate a Personal Login Token.

## 🏃‍♂️ Usage
``` Windows (PowerShell)
$env:CT_BASE_URL="[https://yourchurch.church.tools](https://yourchurch.church.tools)"
$env:CT_API_TOKEN="YOUR_TOKEN"
$env:CT_WIKI_CATEGORY_ID="23"
$env:CT_WIKI_PAGE_TITLE="Organigramm"

python main.py
```

``` Linux / macOS (Bash)
export CT_BASE_URL="[https://yourchurch.church.tools](https://yourchurch.church.tools)"
export CT_API_TOKEN="YOUR_TOKEN"
export CT_WIKI_CATEGORY_ID="23"
export CT_WIKI_PAGE_TITLE="Organigramm"

python3 main.py
```

## 📝 Important Notes
* **Temporary Files:** The script generates a `temp_organigram.svg` during execution. Make sure to add `*.svg` to your `.gitignore` to avoid accidentally committing generated charts to version control.

* **Wiki Display:** The file is attached directly to the Wiki page's underlying data object. Depending on your ChurchTools frontend, you might need to embed the file into the Wiki text manually once using the `![Chart](url)` Markdown syntax. Subsequent uploads will automatically overwrite the file and update the image.
