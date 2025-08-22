# Royalty-Free Media Bulk Downloader (n8n Edition)

This project provides a self-hosted, web-based interface for bulk downloading royalty-free images and videos from multiple sources. It runs on [n8n](https://n8n.io/), a powerful workflow automation tool, and is containerized with Docker for easy setup and management.

## Features

- **Web-Based Interface**: Trigger and manage downloads from a reliable, graphical interface in your browser.
- **Multi-Source**: Fetches from Unsplash, Pexels, and Pixabay via their official APIs.
- **Extensible**: Includes a Python environment for scraping additional sites (e.g., Videvo).
- **Secure**: Manages API keys using n8n's encrypted credential management.
- **Portable**: Runs consistently across any system with Docker.

## Prerequisites

Before you begin, ensure you have the following installed:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (This is included with Docker Desktop on macOS and Windows)

## How It Works

This project uses a `docker-compose.yml` file to launch a pre-configured n8n instance. We provide a `workflow.json` file that you can import into n8n. This workflow is triggered by a simple web request (a "webhook"), processes the API and scraping logic, and downloads the resulting media to a local folder on your machine.

## Setup Instructions

### 1. Clone the Repository

Open your terminal and clone this repository:
```bash
gh repo clone swipswaps/prf-media-downloader
cd prf-media-downloader
```

### 2. Configure Environment

The application uses a `.env` file to manage configuration.

1.  Create a copy of the example file:
    ```bash
    cp .env.example .env
    ```
2.  (Optional) Open the `.env` file and set your local timezone (e.g., `America/New_York`) to ensure scheduled workflow runs are accurate.

### 3. Launch the n8n Instance

Run the following command from the project's root directory. This will build the custom Docker image and start the n8n container in the background.

```bash
docker-compose up --build -d
```
The initial build may take a few minutes.

### 4. First-Time n8n Setup

1.  **Access n8n**: Open your web browser and navigate to [http://localhost:5678](http://localhost:5678).
2.  **Create an Admin Account**: You will be prompted to create an owner account. This is the admin user for your private n8n instance.
3.  **Set Up API Credentials**:
    *   In the n8n sidebar, click **Credentials**, then **Add credential**.
    *   Search for and select **Unsplash API**. Give it a name (e.g., `My Unsplash Key`) and enter your Unsplash Access Key.
    *   Repeat this process for the **Pexels API** and **Pixabay API**. Search for the "Header Auth" credential type for Pexels and provide your key in the `Authorization` header field. For Pixabay, use the "Query Auth" credential type.
4.  **Import the Workflow**:
    *   In the n8n sidebar, click **Workflows**.
    *   Click **Import from File** and select the `workflow.json` file from this project.

### 5. Activate and Use the Workflow

1.  **Activate Workflow**: Open the imported "Royalty-Free Media Downloader" workflow and toggle the **Active** switch in the top-right corner to on.
2.  **Get Webhook URL**:
    *   In the workflow, click on the **Webhook** node.
    *   Copy the **Test URL**.
3.  **Trigger the Workflow**:
    *   You can now send a `POST` request to this URL to trigger a download job. Replace `YOUR_QUERY` with your search term.
    *   The following example uses `curl` from your terminal to search for 10 "office" images. The results will be saved to the `downloads` folder in your project directory.

    ```bash
    curl -X POST \
    -H "Content-Type: application/json" \
    -d '{"query": "office", "items": 10}' \
    http://localhost:5678/webhook-test/d2483582-1215-430b-9366-267484433140
    ```

You now have a fully functional, web-based media downloader!
