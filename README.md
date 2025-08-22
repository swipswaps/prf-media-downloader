# Royalty-Free Media Bulk Downloader

This is a Python-based application for bulk downloading royalty-free images and videos from multiple sources. It features a command-line interface for scripting and a graphical user interface for interactive use.

Supported Sources:
- **API-based**: Unsplash, Pexels, Pixabay
- **Scraping-based**: Coverr, Mixkit, Videvo

## Prerequisites

Before you begin, ensure you have the following installed:
- [Python 3.8+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- [GitHub CLI](https://cli.github.com/)

## Setup Instructions

Follow these steps to get the project running on your local machine.

### 1. Clone the Repository

Open your terminal and clone this repository:
```bash
gh repo clone swipswaps/prf-media-downloader
cd prf-media-downloader
```

### 2. Set Up a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies and avoid conflicts with other projects.

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it
# On macOS and Linux:
source .venv/bin/activate
# On Windows:
# .\.venv\Scripts\activate
```

### 3. Install Dependencies

Install the required Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 4. Configure API Keys

The application requires API keys for Unsplash, Pexels, and Pixabay.

1.  Create a file named `.env` in the root of the project directory.
2.  Add your API keys to this file in the following format:

    ```env
    UNSPLASH_KEY="your_unsplash_api_key"
    PEXELS_KEY="your_pexels_api_key"
    PIXABAY_KEY="your_pixabay_api_key"
    ```

The application will automatically load these keys at runtime.

## Usage

You can run the application in two modes: via the command line (CLI) or with the graphical user interface (GUI).

### GUI Mode

For an interactive experience, run the application with the `--gui` flag. This will open a settings window where you can configure your search, select sources, and choose an output directory before fetching and previewing the media.

```bash
python3 prf_media_downloader.py --gui
```

### Command-Line (CLI) Mode

The CLI is ideal for scripting and automation. Here is the basic command structure:

```bash
python3 prf_media_downloader.py --query "Your Search Term" --items 10 --outdir ./downloads
```

**Common Arguments:**
- `--query`: The search term for the media you want to find.
- `--items`: The number of items to fetch from each source (default: 10).
- `--outdir`: The directory where media will be saved (default: `./prf_media_downloads`).
- `--sources`: A comma-separated list of sources to use (e.g., `unsplash,pexels`). Defaults to all.
- `--threads`: Number of parallel download threads (default: 8).

**Example:**
To download 15 images and videos about "laptops" from Unsplash and Pexels into a folder named `tech_media`:
```bash
python3 prf_media_downloader.py --query "laptops" --items 15 --sources "unsplash,pexels" --outdir ./tech_media
```

### Automated Setup (For Linux/macOS)

The included `install_and_run.sh` script can automate the setup process, including dependency installation and launching the application. You may need to make it executable first:
```bash
chmod +x install_and_run.sh
./install_and_run.sh
```
