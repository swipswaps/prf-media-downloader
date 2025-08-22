# Royalty-Free Media Bulk Downloader

This is a Python-based application for bulk downloading royalty-free images and videos from multiple sources. It features a command-line interface for scripting and a graphical user interface for interactive use.

Supported Sources:
- **API-based**: Unsplash, Pexels, Pixabay
- **Scraping-based**: Coverr, Mixkit, Videvo

## 1. Install Prerequisites

Before you can run the project, you need to install some essential tools.

<details>
<summary><strong>macOS Installation (using Homebrew)</strong></summary>

Open your Terminal and run the following commands:

```bash
# Install Homebrew if you don't have it already
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python, Git, and the GitHub CLI
brew install python git github
```

</details>

<details>
<summary><strong>Windows Installation (using Chocolatey)</strong></summary>

Open PowerShell as an Administrator and run the following commands:

```powershell
# Install Chocolatey package manager if you don't have it
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Python, Git, and the GitHub CLI
choco install python git gh -y
```

</details>

<details>
<summary><strong>Linux Installation (for Debian/Ubuntu)</strong></summary>

Open your terminal and run the following commands:

```bash
# Update package list and install Python and Git
sudo apt update && sudo apt install python3 python3-pip python3-venv git -y

# Install the GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
&& sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
&& sudo apt update \
&& sudo apt install gh -y
```

</details>

## 2. Set Up the Project

Follow these steps to get the project running on your local machine.

### a. Clone the Repository

Open your terminal and clone this repository:
```bash
gh repo clone swipswaps/prf-media-downloader
cd prf-media-downloader
```

### b. Set Up a Virtual Environment

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

### c. Install Python Dependencies

Install the required Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### d. Configure API Keys

The application requires API keys for Unsplash, Pexels, and Pixabay.

<details>
<summary><strong>Click here for instructions on how to get API keys.</strong></summary>

#### Unsplash
1.  **Create an account**: Go to [unsplash.com/join](https://unsplash.com/join) and create a free account.
2.  **Become a developer**: Visit the [Unsplash Developers](https://unsplash.com/developers) page and accept the terms to register as a developer.
3.  **Create a new application**:
    *   Navigate to your [Applications dashboard](https://unsplash.com/oauth/applications).
    *   Click **New Application**, accept the API usage guidelines, and give your app a name and description.
4.  **Get your key**: Your **Access Key** will be available on your application's dashboard. This is the key you need.

For more details, refer to the [official Unsplash API documentation](https://unsplash.com/documentation).

#### Pexels
1.  **Create an account**: Go to [pexels.com/join](https://www.pexels.com/join/) and create a free account.
2.  **Request an API Key**: Visit the [Pexels API page](https://www.pexels.com/api/) and click the button to request your key. You will need to provide a reason for your request.
3.  **Get your key**: Your API key will be displayed on the same page immediately after your request is approved.

For more details, refer to the [official Pexels API documentation](https://www.pexels.com/api/documentation/).

#### Pixabay
1.  **Create an account**: Go to [pixabay.com/accounts/register/](https://pixabay.com/accounts/register/) and create a free account.
2.  **Find your API key**: After logging in, navigate to the [Pixabay API documentation page](https://pixabay.com/api/docs/).
3.  **Get your key**: Your API key will be displayed directly on this page under the "Search Images" section.

For more details, refer to the [official Pixabay API documentation](https://pixabay.com/api/docs/).

</details>
<br>

1.  Create a file named `.env` in the root of the project directory.
2.  Add your API keys to this file in the following format:

    ```env
    UNSPLASH_KEY="your_unsplash_api_key"
    PEXELS_KEY="your_pexels_api_key"
    PIXABAY_KEY="your_pixabay_api_key"
    ```

The application will automatically load these keys at runtime.

## 3. Usage

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
