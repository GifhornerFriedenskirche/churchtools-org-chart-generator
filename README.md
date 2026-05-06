# ChurchTools Org-Chart Generator 📊

An enterprise-grade Python application that automatically fetches organizational structures from the ChurchTools API, generates beautifully formatted SVG and PNG hierarchy charts, and seamlessly uploads them directly to a specified ChurchTools Wiki page.
## ✨ Key Features

* **Smart Canvas Layout Engine:** Automatically calculates compact, overlapping-free hierarchy trees. Safely handles complex multiple-parent groups, isolated nodes, and disconnected subtrees.
* **Intelligent Two-Column Legend:** Dynamically counts and displays unique Group Types and Group Statuses (Active, Draft, Finished, Archived), smartly excluding duplicates from the total counts.
* **Auto-Scaling Protection:** Features dynamic mathematical image resizing. Automatically scales down massive organizational PNG structures to bypass ChurchTools' strict 33-Megapixel API upload restriction.
* **Zero-Clutter Wiki Uploads:** Features a built-in pre-flight cleanup sequence. It locates the target Wiki page by title, identifies existing legacy graphs, performs a hard delete, and uploads the fresh asset-ensuring your Wiki history remains completely uncluttered.
* **Strict Type Safety:** Fully audited with Microsoft Pylance to guarantee enterprise-grade stability and type safety.

## 🏗️ Architecture

The application is cleanly divided into three distinct modules (Separation of Concerns):
1. `main.py`: The orchestrator. Reads environment variables, handles global logging, and links generation with uploading.
2. `generate_chart.py`: The rendering engine. Fetches raw data from the ChurchTools API, builds the mathematical layout, and renders the SVG/PNG files.
3. `upload_chart.py`: The API liaison. Looks up Wiki page identifiers, safely deletes historical charts, and executes multipart file uploads.

## ⚙️ Prerequisites
* Python 3.8+
* CairoSVG Dependencies (Crucial for PNG export):
  * Linux/macOS: Usually works out of the box after `pip install`. You may need `libcairo2-dev`.
  * Windows: CairoSVG requires GTK-3 to be installed and added to your system PATH. Follow the official [GTK for Windows installation guide](https://www.gtk.org/docs/installations/windows/) if PNG generation fails.

## 🚀 Installation
1. Clone the repository:
```bash
  git clone https://github.com/your-org/churchtools-org-chart-generator.git
  cd churchtools-org-chart-generator
```
2. Create and activate a virtual environment:
```bash
  python -m venv venv
  # On Windows:
  .\venv\Scripts\activate
  # On macOS/Linux:
  source venv/bin/activate
```
3. Install required Python packages:
```bash
pip install requests cairosvg
```
## 🛠️ Configuration

The generator is entirely configured via Environment Variables, making it perfect for CI/CD pipelines, Docker, or CRON jobs.

| Environment Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `CT_BASE_URL` | **Yes** | *None* | Your ChurchTools instance URL (e.g., `https://yourchurch.church.tools`). |
| `CT_API_TOKEN` | **Yes** | *None* | A valid ChurchTools Login Token with API access. |
| `CT_WIKI_CATEGORY_ID` | **Yes** | *None* | The integer ID of the target Wiki Category (e.g., `23`). |
| `CT_WIKI_PAGE_TITLE` | **Yes** | *None* | The literal text title of the destination Wiki page (e.g., `Organisation`). |
| `CT_FILE_NAME` | No | `temp_organigram` | The base name for the generated files (without extension). |
| `CT_GENERATE_PNG` | No | `false` | Set to `true` to generate and upload a fallback `.png` image. |
| `CT_SPLIT_DEPTH` | No | `2` | Determines at which hierarchy depth large branches are split into detailed sub-views to keep the main chart readable. |
| `CT_ALLOWED_STATUS_IDS`| No | *All* | Comma-separated list of status IDs to include (e.g., `1,2` for Active and Draft). |
| `CT_DEBUG` | No | `false` | Set to `true` to enable verbose debug logging. |

## 💻 Usage

Once your environment variables are set, simply run the main orchestrator:

```bash
python main.py
```

### Example (Linux/macOS)
```bash
export CT_BASE_URL="[https://mychurch.church.tools](https://mychurch.church.tools)"
export CT_API_TOKEN="your_secure_token_here"
export CT_WIKI_CATEGORY_ID="23"
export CT_WIKI_PAGE_TITLE="Organigramm"
export CT_GENERATE_PNG="true"
export CT_ALLOWED_STATUS_IDS="1,2"

python main.py
```

### Example (Windows PowerShell)
```powershell
$env:CT_BASE_URL="[https://mychurch.church.tools](https://mychurch.church.tools)"
$env:CT_API_TOKEN="your_secure_token_here"
$env:CT_WIKI_CATEGORY_ID="23"
$env:CT_WIKI_PAGE_TITLE="Organigramm"
$env:CT_GENERATE_PNG="true"
$env:CT_ALLOWED_STATUS_IDS="1,2"

python main.py
```

## 🐛 Troubleshooting

* **Error: `PNG generation skipped: 'cairosvg' library is missing.`**
    Ensure `cairosvg` is installed (`pip install cairosvg`). On Windows, ensure you have installed the underlying GTK3 libraries, as Python cannot compile the Cairo graphics engine natively.
* **Upload Skipped / Page Not Found:**
    Double-check your `CT_WIKI_CATEGORY_ID` and ensure the `CT_WIKI_PAGE_TITLE` matches the exact string inside ChurchTools (case-sensitive).
* **PNG looks blurry or upload fails:**
    If the chart exceeds 33 Megapixels, the application will auto-scale the PNG down to ensure the ChurchTools API accepts it. The SVG will remain in infinite resolution.

## 📄 License
This project is licensed under the MIT License.
