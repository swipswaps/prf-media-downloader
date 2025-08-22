#!/bin/bash

# A simple helper script to stage, commit, and push repository changes.
# This script automates the common Git workflow of pushing changes to a remote
# repository, providing interactive prompts and clear feedback to the user.

# --- Configuration: ANSI Color Codes ---
# These variables store ANSI escape codes to add color to the script's output,
# making it easier to read and understand. For example, green for success,
# red for errors, and yellow for warnings.
COLOR_RESET='\033[0m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_RED='\033[0;31m'
COLOR_CYAN='\033[0;36m'

# --- Step 1: Check for Local Changes ---
# This block checks if there are any uncommitted changes in your local repository.
# It first silently updates the Git index to ensure it's aware of all file states.
# It then uses `git diff-index` to compare the current working directory with the
# last commit (HEAD). If there are no differences, the script exits cleanly.
git update-index -q --refresh
if git diff-index --quiet HEAD --; then
    echo -e "${COLOR_GREEN}✔ No changes detected in the repository. Everything is up to date.${COLOR_RESET}"
    exit 0
fi

# --- Step 2: Display Detected Changes ---
# If changes are found, this block informs the user and displays a summary.
# `git status -s` provides a compact, "short" format of the changes, which is
# easy to review quickly.
echo -e "${COLOR_YELLOW}Changes detected in your repository:${COLOR_RESET}"
git status -s
echo ""

# --- Step 3: Confirm Git Identity ---
# This block retrieves the user's name and email from the local Git configuration.
# It's a crucial confirmation step. If the identity is explicitly set, it is
# displayed. If not, the script informs the user that Git will use a default,
# system-generated identity and provides instructions on how to set it explicitly.
USER_NAME=$(git config --get user.name)
USER_EMAIL=$(git config --get user.email)
echo -e "${COLOR_CYAN}Checking Git identity...${COLOR_RESET}"
if [ -n "$USER_NAME" ] && [ -n "$USER_EMAIL" ]; then
    echo -e "  - Committing as: ${COLOR_GREEN}$USER_NAME <$USER_EMAIL>${COLOR_RESET}"
else
    echo -e "  - ${COLOR_YELLOW}Git user.name and user.email are not explicitly set.${COLOR_RESET}"
    echo -e "  - Git will proceed using a system-generated identity."
    echo -e "  - To set your identity permanently, you can use:"
    echo -e "    git config --global user.name \"Your Name\""
    echo -e "    git config --global user.email \"you@example.com\""
fi
echo ""

# --- Step 4: Prompt for a Commit Message ---
# The script prompts the user to enter a descriptive message for their commit.
# A good commit message is essential for maintaining a clean project history.
# The script will exit if the user provides an empty message.
echo -e "${COLOR_CYAN}Please enter a commit message (e.g., 'feat: Add user login page'):${COLOR_RESET}"
read -p "> " COMMIT_MESSAGE
if [ -z "$COMMIT_MESSAGE" ]; then
    echo -e "${COLOR_RED}✖ Commit message cannot be empty. Aborting.${COLOR_RESET}"
    exit 1
fi

# --- Step 5: Stage, Commit, and Push ---
# This is the core execution block. It uses `&&` to chain the commands,
# meaning the next command will only run if the previous one was successful.
# 1. `git add .`: Stages all new, modified, and deleted files.
# 2. `git commit`: Commits the staged files with the user's message.
# 3. `git push`: Pushes the new commit to the remote repository on GitHub.
echo -e "\n${COLOR_YELLOW}🚀 Staging all changes, committing, and pushing to remote...${COLOR_RESET}"
git add . && \
git commit -m "$COMMIT_MESSAGE" && \
git push

# --- Step 6: Final Confirmation and Browser Prompt ---
# This block runs after the push attempt. It checks the exit code (`$?`) of the
# `git push` command. A code of 0 means success.
if [ $? -eq 0 ]; then
    # On success, it retrieves the repository's URL from the 'origin' remote.
    REPO_URL=$(git remote get-url origin)
    echo -e "\n${COLOR_GREEN}✔ Successfully pushed changes!${COLOR_RESET}"
    echo -e "You can view your repository here: ${COLOR_CYAN}${REPO_URL}${COLOR_RESET}"

    # --- Step 7: Offer to Open in Browser (with Fallback) ---
    # This section detects the user's operating system to determine the correct
    # command for opening a URL. It then prompts the user to open the URL.
    OPEN_CMD=""
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OPEN_CMD="xdg-open"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OPEN_CMD="open"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OPEN_CMD="start"
    fi

    # If a command was found, it asks the user for input.
    if [ -n "$OPEN_CMD" ]; then
        echo ""
        read -p "$(echo -e ${COLOR_YELLOW}"Open repository in browser? (y/N) "${COLOR_RESET})" choice
        case "$choice" in
          y|Y )
            echo -e "Opening..."
            # It attempts to open the URL, redirecting any potential errors from the
            # command (like a missing browser) to /dev/null so they aren't shown.
            $OPEN_CMD $REPO_URL 2>/dev/null
            # If the command fails, it provides a graceful fallback message.
            if [ $? -ne 0 ]; then
                echo -e "${COLOR_RED}Could not automatically open a web browser.${COLOR_RESET}"
                echo -e "Please copy the link above and paste it into your browser."
            fi
            ;;
          * )
            # If the user enters anything other than 'y' or 'Y', do nothing.
            ;;
        esac
    fi
else
    # If the `git push` command failed, this displays a final error message.
    echo -e "\n${COLOR_RED}✖ An error occurred during the push process. Please check the output above.${COLOR_RESET}"
    exit 1
fi
