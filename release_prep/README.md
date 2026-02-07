# Jaavis 🤖

**The One-Army Orchestrator.**

Jaavis is a CLI tool designed to help "One-Army" developers manage their knowledge base, build pipelines, and project architectures.

## Features
*   **🧠 Knowledge Base**: Index and search your personal library of skills (`.md` files).
*   **🌾 Harvest**: Quickly capture new skills interactively.
*   **🚀 Pipeline**: Visualize your build protocol in the terminal.
*   **🎭 Persona**: Interactive role selection (Programmer, etc.).

## Installation

1.  Clone this repository:
    ```bash
    git clone https://github.com/YOUR_USERNAME/jaavis.git
    cd jaavis
    ```

2.  Run the installer:
    ```bash
    chmod +x setup_jaavis.sh
    ./setup_jaavis.sh
    ```

3.  Verify:
    ```bash
    jaavis
    ```

## Usage

*   `jaavis` -> Launch the Persona Menu.
*   `jaavis search "auth"` -> Find skills related to auth.
*   `jaavis harvest` -> Add a new skill to your library.
*   `jaavis open "skill-name"` -> Open a skill in VS Code.

## Updating

Since Jaavis is installed via symlink, **updates are instant**.
1.  `git pull`
2.  Your `jaavis` command is automatically updated!

## License
MIT
