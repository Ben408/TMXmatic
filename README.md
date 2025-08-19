# TMX Processing Tool

A web-based tool for processing TMX (Translation Memory eXchange) and XLIFF files, with a focus on cleaning and managing translation memory data.

## Quick Start (Windows)

- Double-click `start_tmxmatic.bat` in the project root.
- This script will:
  - Check for Python 3; if missing, attempt to install it silently via `winget`.
  - Create and activate a virtual environment at `.venv`.
  - Upgrade `pip` and install dependencies from `other/requirements.txt`; ensure `Flask-CORS` is installed.
  - Launch the app via `launcher.py`, which will:
    - Start the Flask backend at `http://localhost:5000`.
    - Check for Node.js/npm; if missing, download and install Node.js.
    - If the frontend is present at `dist/New_UI`, install Node dependencies, build the UI, and start the dev server (typically on `http://localhost:3000`). Your default browser will open to the running UI.
- Logs are written to a file named like `tmxmatic_YYYYMMDD_HHMMSS.log` in the application directory.

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Node.js 16 or higher (for UI development)
- pip (Python package manager)

### Installation

1. Clone the repository:
bash
git clone [repository-url]
cd tmx-processing-tool

2. Install Python dependencies:
bash
pip install -r requirements.txt

3. Run the Flask development server:
bash
python app.py

The application will be available at `http://localhost:5000`

## Features

### TMX Processing Operations

#### Duplicate Management
The tool offers two distinct approaches to handling duplicates:

1. **True Duplicates** (`find_true_duplicates`)
   - Identifies entries with identical source AND target text
   - Keeps the most recent version based on changedate/creationdate
   - Moves older duplicates to a separate file
   - Use this when you want to remove exact duplicates while keeping the latest version

2. **Non-True Duplicates** (`extract_non_true_duplicates`)
   - Identifies entries with the same source but different target text
   - Moves all variations to a separate file for review
   - Use this to find potentially inconsistent translations
   - Helps maintain translation consistency

#### XLIFF Operations

1. **TMX Leverage** (`xliff_tmx_leverage`)
   - Applies translations from a TMX file to an XLIFF file
   - Only fills empty target segments
   - Provides statistics on:
     - Number of translations found
     - Updates made
     - Remaining empty segments

2. **XLIFF Status Check** (`xliff_check`)
   - Analyzes XLIFF files for completion
   - Reports:
     - Total segments
     - Empty segments
     - Completion rate

### Other Operations

#### TMX File Operations
- **Split TMX by language**
  - `split_by_language(file_path)`: Creates separate TMX files for each target language
  - `split_by_size(file_path, max_tus)`: Splits TMX into smaller files with specified maximum TUs

#### Data Cleaning Operations
- **Remove empty targets**
  - `empty_targets(file_path)`: Removes translation units with empty target segments
  - Creates separate files for valid and empty segments

- **Remove duplicates**
  - `find_true_duplicates(file_path)`: Identifies and separates exact duplicate translations
  - `extract_non_true_duplicates(file_path)`: Identifies similar but non-identical translations
  - `find_sentence_level_segments(file_path)`: Separates complete sentence segments

- **Clean for MT**
  - `clean_tmx_for_mt(file_path)`: Prepares TMX for machine translation training
  - Removes tags, placeholders, and problematic segments
  - Normalizes content for better training results

#### Analysis Tools
- **Date Analysis**
  - `count_creation_dates(file_path)`: Analyzes TU creation date distribution
  - `count_last_usage_dates(file_path)`: Tracks when translations were last modified
  - `find_date_duplicates(file_path, date)`: Finds duplicates around a specific date

- **Content Analysis**
  - `extract_translations(file_path)`: Exports all translations to CSV format
  - Includes metadata like creation dates and change dates

#### Batch Processing
- **Automated Workflows**
  - `batch_process_1_5(file_path)`: Runs steps 1-5 in sequence:
    1. Remove empty targets
    2. Remove true duplicates
    3. Extract non-true duplicates
    4. Remove sentence-level segments
    5. Clean output
  - `batch_process_1_5_9(file_path, cutoff_date)`: Adds date filtering to the workflow

#### File Conversion
- **Format Conversion**
  - `convert_vatv_to_tmx(file_path)`: Converts VATV CSV files to TMX format
  - `convert_termweb_to_tmx(file_path)`: Converts TermWeb Excel files to TMX format

#### File Management
- **Merge Operations**
  - `merge_tmx_files(file_paths)`: Combines multiple TMX files
  - Removes duplicates and keeps most recent versions
  - Maintains consistent source language

#### XLIFF Support
- **XLIFF Operations**
  - `leverage_tmx_into_xliff(tmx_file, xliff_file)`: Applies TMX translations to XLIFF
  - `check_empty_targets(xliff_file)`: Analyzes XLIFF completion status

## Development

### Project Structure
```
tmx-processing-tool/
├── app.py              # Flask application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── scripts/           # Processing scripts
│   ├── __init__.py
│   ├── remove_duplicates.py
│   ├── extract_ntds.py
│   └── xliff_operations.py
└── New_UI/           # React frontend
    └── components/   # UI components
```

### Running in Development Mode

1. Start the Flask backend:
```bash
python app.py
```

2. Start the UI development server (in a separate terminal):
```bash
cd New_UI
npm install
npm run dev
```

### Building for Distribution

1. Build the UI:
```bash
cd New_UI
npm run build
```

2. Build the executable:
```bash
pyinstaller app.spec
```

The executable will be created in the `dist` directory.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Support

For support, please open an issue in the GitHub repository.

