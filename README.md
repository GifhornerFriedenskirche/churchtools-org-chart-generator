# churchtools-org-chart-generator
Automated workflow to generate a ChurchTools organizational chart (SVG) and upload it to the ChurchTools Wiki via GitHub Actions.
# ChurchTools Org Chart Generator

This repository contains an automated workflow that periodically fetches your church's group structure from the [ChurchTools](https://church.tools/) REST API, generates a visually appealing and interactive organizational chart (SVG), and uploads it directly to a ChurchTools Wiki.

## Architecture & Privacy

*   **Zero-Logging Policy:** No Personally Identifiable Information (PII) is processed, logged, or stored by this script. It only processes group IDs and names.
*   **Stateless Execution:** The workflow runs ephemerally in a GitHub Action (Ubuntu VM). The generated SVG is *not* committed or saved in this repository. It is discarded immediately after the upload to ensure a clean Git history and maximum security.
*   **Dynamic Mapping:** Group types are dynamically resolved via the API. The color-coding is based on the group type names configured in your specific ChurchTools instance.

## Prerequisites

1. A technical API user in ChurchTools.
2. The API user requires read permissions for groups (`view groups`) and group types (`view group types`).
3. The API user requires write permissions (`upload file`) for the target Wiki category.

## Setup (GitHub Actions)

To run this workflow, you need to configure the following **Repository Secrets** in GitHub under `Settings > Secrets and variables > Actions`:

| Secret Name | Description | Example |
| :--- | :--- | :--- |
| `CT_BASE_URL` | The base URL of your ChurchTools instance (without trailing slash). | `https://mychurch.church.tools` |
| `CT_API_TOKEN` | The login token of the technical API user. | `abc123def456...` |
| `CT_WIKI_CATEGORY_ID` | The ID of the Wiki category in ChurchTools where the image should be uploaded. | `42` |

## Local Development & Testing

To run the script locally (e.g., to adjust the Graphviz layout or colors):

1. Clone this repository.
2. Create a virtual environment: `python -m venv venv`
3. Install the required system and Python dependencies:

```bash
   # Linux / Ubuntu
   sudo apt-get install graphviz

   # macOS
   brew install graphviz

   # Install Python requirements
   pip install -r requirements.txt
