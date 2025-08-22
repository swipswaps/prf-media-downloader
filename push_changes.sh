#!/bin/bash

# A simple helper script to stage, commit, and push repository changes.

# ANSI Color Codes
COLOR_RESET='\033[0m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_RED='\033[0;31m'
COLOR_CYAN='\033[0;36m'

# --- Step 1: Check for changes ---
# Refresh the git index to make sure we're looking at the latest state
git update-index -q --refresh

# Check for uncommitted changes
if git diff-index --quiet HEAD --; then
    echo -e "${COLOR_GREEN}✔ No changes detected in the repository. Everything is up to date.${COLOR_RESET}"
    exit 0
fi

# --- Step 2: Show the user what has changed ---
echo -e "${COLOR_YELLOW}Changes detected in your repository:${COLOR_RESET}"
git status -s # -s provides short, easy-to-read output
echo "" # Add a newline for spacing

# --- Step 3: Prompt for a commit message ---
echo -e "${COLOR_CYAN}Please enter a commit message (e.g., 'feat: Add user login page'):${COLOR_RESET}"
read -p "> " COMMIT_MESSAGE

# Check if a commit message was provided
if [ -z "$COMMIT_MESSAGE" ]; then
    echo -e "${COLOR_RED}✖ Commit message cannot be empty. Aborting.${COLOR_RESET}"
    exit 1
fi

# --- Step 4: Stage, Commit, and Push ---
echo -e "\n${COLOR_YELLOW}🚀 Staging all changes, committing, and pushing to remote...${COLOR_RESET}"

git add . && \
git commit -m "$COMMIT_MESSAGE" && \
git push

# --- Step 5: Final Confirmation ---
# Check the exit code of the last command ($?) to see if it was successful
if [ $? -eq 0 ]; then
    echo -e "\n${COLOR_GREEN}✔ Successfully pushed changes to the remote repository!${COLOR_RESET}"
else
    echo -e "\n${COLOR_RED}✖ An error occurred during the push process. Please check the output above.${COLOR_RESET}"
    exit 1
fi
