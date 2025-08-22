# Use the official n8n Docker image as a base
FROM n8nio/n8n

# Switch to the root user to install system packages
USER root

# Install Python 3, pip, and Git
# We add git in case any Python packages need to pull from a git repo
RUN apk add --no-cache python3 py3-pip git

# Install required Python libraries for scraping
RUN pip3 install beautifulsoup4 requests

# Switch back to the non-root user that n8n runs as
USER node
