# Language Data Workbench (TMXmatic) - processing tool for TMX, TBX, XLIFF and Excel files.

Web-based tooling for processing **TMX** (Translation Memory eXchange), **XLIFF**, **DOCX**, and related files, with a focus on cleaning and managing translation memory and language data. The desktop-style flow uses a **Flask** backend and a **Next.js** UI shipped under `dist/New_UI`.

**Phase 2** adds **[Okapi Framework](https://okapiframework.org/)** integration: registry-driven convert/merge/QA operations, hybrid Python + Okapi pipelines, and a pipeline builder in the workbench UI.

<img width="1244" height="1080" alt="image" src="https://github.com/user-attachments/assets/4f638ba2-20d0-4c4a-ad77-462af9bdc415" />


## Quick Start (Windows)

1. Install **[Node.js LTS](https://nodejs.org/)** (includes `npm`) and ensure `node` and `npm` are on your `PATH`.
2. Double-click **`start_tmxmatic.bat`** in the project root.

The batch script will, in order:

- Resolve **Python 3** (`py -3` or `python`); if missing, it may attempt a silent install via **winget** (when available).
- Run **`dependency_manager.py`**, which installs all UI packages declared in **`dist/New_UI/package.json`** (uses **`npm ci`** when `package-lock.json` is present, otherwise **`npm install`**). This step **requires** `npm` on `PATH`; the script stops with an error if the install fails.
- Create and activate a virtual environment at **`.venv`**, upgrade **pip**, and install Python packages from **`other/requirements.txt`**, then ensure **Flask-CORS** is available.
- Start **`launcher.py`**, which:
  - Starts the Flask backend at **`http://127.0.0.1:5000`** (and related API routes).
  - If **`dist/New_UI`** exists, ensures Node dependencies again, **builds** the Next.js app, then starts the **dev** server (typically **`http://localhost:3000`**). Your browser may open to the running UI.
  - May still attempt to resolve or configure **Node/npm** from the launcher when the Next.js thread starts (see logs if the UI does not come up).

- A command window will appear, when the Next.js server is up a web-browser tab will open with the UI.

- Drag in assets to process or use the file picker.

- Select operations to run individually or select multiple operations to run as a batch.

For **Okapi** pipelines (e.g. DOCX → XLIFF), complete the [Okapi setup](#okapi-integration-phase-2) below before using the **Pipelines** tab.

Session logs are written next to the app, named like **`tmxmatic_YYYYMMDD_HHMMSS.log`**.

### UI notes

- **Settings** (gear in the workbench) includes integration options and **Appearance**: **Light**, **Dark**, or **System** theme (persisted via the UI theme provider).
- **Okapi / Pipelines** — upload a supported file (e.g. `.docx`), select it in the workspace, then open the **Pipelines** tab to run Okapi operations or saved pipeline templates.

## Prerequisites

- **Windows 10/11** (recommended entry point: `start_tmxmatic.bat`).
- **Python** 3.10 or newer (3.8+ may work; the Windows batch script targets current Python via winget when needed).
- **Node.js** 18+ recommended (**20 LTS** matches typical Next.js 15 / React 19 setups); **`npm`** must be on `PATH` for the batch file’s UI install step.
- **pip** (comes with Python).
- **Docker Desktop** (recommended for Okapi) — required for the default **Docker tikal** backend. No host Java install needed; Okapi runs inside a local container image you build once.

## Okapi integration (Phase 2)

LDW can run Okapi **tikal** operations and multi-step pipelines without installing Java or Rainbow on the host. Operations are defined in `config/okapi_operations.yml` and exposed via the Flask API and the **Pipelines** UI tab.

### Backend options

Configure under **Settings → Integrations → Okapi** (stored in `integration_settings.json`).

| Backend | When to use | What you need |
|--------|-------------|----------------|
| **Docker tikal** (default) | Local pilot and day-to-day use on Windows | [Docker Desktop](https://www.docker.com/products/docker-desktop/) + one-time image build (below) |
| **GitHub Actions** | No local Docker; offload runs to your fork | Fork [ldw-okapi-workflows](https://github.com/Ben408/ldw-okapi-workflows), GitHub PAT, repo name `user/ldw-okapi-workflows` |
| **Hosted Okapi** | Existing Okapi workspace API | API key, URL, workspace ID |
| **Longhorn** | Custom external Okapi API | `longhorn_url` (stock Longhorn is not a drop-in for LDW pipelines) |
| **Local tikal** | Dev-only; not recommended | Path to `tikal.bat` on the host (JRE drift risk) |

### Docker tikal setup (recommended)

The image is **not** published to Docker Hub. After cloning the repo, build it once on your machine:

```powershell
cd <repo-root>
.\scripts\build_okapi_tikal_image.ps1
```

The script downloads the official Okapi **1.48.0** Linux distribution (~40 MB), builds `ldw-okapi-tikal:1.48` from `docker/okapi-tikal/Dockerfile` (Eclipse Temurin 17 JRE inside the container), and runs `tikal -info` as a smoke check.

Verify Docker + convert:

```powershell
.\.venv\Scripts\python.exe scripts\okapi_smoke.py docker
```

Expected: `tikal ready (ldw-okapi-tikal:1.48)` and a successful `convert` smoke test.

In **Settings**, confirm:

- **Backend:** Docker tikal  
- **Docker image:** `ldw-okapi-tikal:1.48`

Backend health is also available at `GET http://127.0.0.1:5000/api/okapi/backends/status` while Flask is running.

### GitHub Actions backend (optional)

Use this when Docker is not available and your organization runs Okapi in **its own GitHub fork** (not on shared TMXmatic Actions).

1. Fork the public template [ldw-okapi-workflows](https://github.com/Ben408/ldw-okapi-workflows) to `your-company/ldw-okapi-workflows` (your fork may be private).
2. In LDW **Settings → Okapi**, choose **GitHub Actions**, enter your fork and a PAT, then **Test GitHub connection**.
3. LDW **rejects** `Ben408/TMXmatic` and the upstream template repo as run targets — you must use a fork you control.

The template repo is **public** so anyone can fork it; security comes from **your PAT** and **your fork**, not from hiding the workflow YAML.

### Using Okapi in the UI

1. Start LDW (`start_tmxmatic.bat` or manual Flask + Next dev server).
2. Upload a file Okapi supports (e.g. `.docx`, `.xlf`, Office formats).
3. Select the file in the workspace (single-file workspaces auto-select).
4. Open **Pipelines** → choose an operation or template → run.
5. Download artifacts when the job completes.

Supported upload types are centralized in `dist/New_UI/lib/workspace-upload-formats.ts` (TMX, DOCX, XLIFF, and other Okapi-friendly formats).

### Troubleshooting

| Symptom | Fix |
|--------|-----|
| `image ldw-okapi-tikal:1.48 not found` | Run `.\scripts\build_okapi_tikal_image.ps1` |
| `docker daemon not running` | Start Docker Desktop |
| Okapi panel empty / API 404 from UI port | Ensure Flask is on `:5000`; Next.js rewrites `/api/*` to Flask (see `dist/New_UI/next.config.js`) |
| GitHub backend unavailable | Set `github_token` + `github_repo` in secrets or env vars |

More detail: `docs/DEVELOPMENT_STATUS.md`, `docs/BUGS_FIXED.md`.

## Manual installation (Windows)

1. Clone the repository and enter the project directory.

   ```powershell
   git clone https://github.com/Ben408/TMXmatic.git
   cd TMXmatic
   ```

2. Create a virtual environment (recommended) and install Python dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   python -m pip install --upgrade pip
   python -m pip install -r other/requirements.txt
   python -m pip install flask-cors
   ```

3. Install the Next.js UI dependencies (single source of truth: `package.json`):

   ```bash
   cd dist/New_UI
   npm ci
   # or: npm install --legacy-peer-deps
   ```

4. Run the backend:

   ```bash
   cd ../..   # back to repo root
   python app.py
   ```

   The API and server-rendered routes are served from the Flask app (default **`http://127.0.0.1:5000`**). For the full workbench UI in development, run the Next app in another terminal (see below).

## Features (overview)

### TMX processing

- **Duplicate management**: true duplicates vs non-true (same source, different targets), with helpers for sentence-level segments and cleanup.
- **Data cleaning**: empty targets, MT-oriented cleaning, context props, date-based workflows.
- **Analysis**: creation/last-change dates, exports, batch pipelines (`batch_process_1_5`, `batch_process_1_5_9`, etc.).
- **Merge / split / conversions**: merge TMX, split by language or size, VATV / TermWeb style conversions where implemented.

### XLIFF and Okapi

- Leverage TMX into XLIFF and check completion / empty targets (see `scripts/` and API operation names in `app.py`).
- **Okapi**: DOCX/Office → XLIFF extraction, merge, QA, terminology, and user-defined hybrid pipelines (see [Okapi integration](#okapi-integration-phase-2)).

## Development

### Project structure (simplified)

```text
TMXmatic/
├── app.py                 # Flask application (API + processing)
├── launcher.py            # Windows-oriented startup: Flask + Next build/dev
├── dependency_manager.py # Node install from dist/New_UI/package.json (also run by the .bat)
├── start_tmxmatic.bat     # Recommended Windows entry point
├── config.py
├── config/
│   └── okapi_operations.yml  # Okapi operation registry
├── docker/
│   └── okapi-tikal/       # Dockerfile + build context for ldw-okapi-tikal image
├── ldw_core/okapi/        # Runners, executor, pipeline integration
├── other/
│   └── requirements.txt   # Python dependencies for local / venv install
├── dist/
│   └── New_UI/            # Next.js app (package.json, components, app/)
├── scripts/               # TMX/XLIFF/TBX processing + okapi_smoke.py, build_okapi_tikal_image.ps1
└── app.spec               # PyInstaller spec (if you build an executable)
```

### Backend only

```bash
python app.py
```

### UI (Next.js) in dev

From the repo root:

```bash
cd dist/New_UI
npm install   # or npm ci
npm run dev
```

Open the URL shown in the terminal (usually **`http://localhost:3000`**). The UI expects the Flask API at **`http://127.0.0.1:5000`** unless you configure otherwise.

### Building the UI for production

```bash
cd dist/New_UI
npm run build
```

### Building a Windows executable

```bash
pyinstaller app.spec
```

Output appears under the **`dist/`** directory (PyInstaller output; not the same folder as **`dist/New_UI`**).

## Node dependency management (`dependency_manager.py`)

- **`DependencyManager.ensure_node_dependencies()`** compares **`dist/New_UI/package.json`** (`dependencies` + `devDependencies`) to top-level folders under **`dist/New_UI/node_modules`**. If anything is missing, it runs one full **`npm ci`** (or **`npm install`** if there is no lockfile, or after a failed `npm ci`).
- You can run the same step manually from the repo root:

  ```bash
  python dependency_manager.py
  ```

## Contributing

1. Fork the repository  
2. Create a feature branch  
3. Commit your changes  
4. Push to the branch  
5. Open a Pull Request  

## License

Licensed under the Apache License, Version 2.0 (the "License");  
you may not use this file except in compliance with the License.  
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software  
distributed under the License is distributed on an "AS IS" BASIS,  
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
See the License for the specific language governing permissions and  
limitations under the License.

## Support

For support, please open an issue in the GitHub repository.

## Contact
email: ben@bencornelius.com
