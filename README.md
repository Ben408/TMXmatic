# TMXmatic — TMX processing tool

Web-based tooling for processing **TMX** (Translation Memory eXchange), **XLIFF**, and related files, with a focus on cleaning and managing translation memory data. The desktop-style flow uses a **Flask** backend and a **Next.js** UI shipped under `dist/New_UI`.

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

Session logs are written next to the app, named like **`tmxmatic_YYYYMMDD_HHMMSS.log`**.

### UI notes

- **Settings** (gear in the workbench) includes integration options and **Appearance**: **Light**, **Dark**, or **System** theme (persisted via the UI theme provider).

## Prerequisites

- **Python** 3.10 or newer (3.8+ may work; the Windows batch script targets current Python via winget when needed).
- **Node.js** 18+ recommended (**20 LTS** matches typical Next.js 15 / React 19 setups); **`npm`** must be on `PATH` for the batch file’s UI install step.
- **pip** (comes with Python).

## Manual installation (any OS)

1. Clone the repository and enter the project directory.

   ```bash
   git clone <repository-url>
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

### XLIFF

- Leverage TMX into XLIFF and check completion / empty targets (see `scripts/` and API operation names in `app.py`).

## Development

### Project structure (simplified)

```text
TMXmatic/
├── app.py                 # Flask application (API + processing)
├── launcher.py            # Windows-oriented startup: Flask + Next build/dev
├── dependency_manager.py # Node install from dist/New_UI/package.json (also run by the .bat)
├── start_tmxmatic.bat     # Recommended Windows entry point
├── config.py
├── other/
│   └── requirements.txt   # Python dependencies for local / venv install
├── dist/
│   └── New_UI/            # Next.js app (package.json, components, app/)
├── scripts/               # TMX/XLIFF/TBX processing modules
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
