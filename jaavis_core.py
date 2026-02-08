#!/usr/bin/env python3
import sys
import os
import re
import argparse
import textwrap
import json
import shutil
import time
import subprocess
import tty
import termios
from datetime import datetime

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
HOME = os.path.expanduser("~")
CONFIG_PATH = os.path.join(HOME, ".jaavis_config.json")
WORKFLOW_PATH = os.path.join(HOME, ".agent/workflows/hei_jaavis.md")

# Determine the absolute directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Homebrew Compatibility: If installed via brew, resources are in ../share/jaavis
if not os.path.exists(os.path.join(BASE_DIR, "logo.md")) and not os.path.exists(os.path.join(BASE_DIR, "jaavis_tui.py")):
    brew_share = os.path.join(BASE_DIR, "..", "share", "jaavis")
    if os.path.exists(os.path.join(brew_share, "logo.md")):
        BASE_DIR = brew_share

# Add BASE_DIR to path for modular imports (jaavis_tui)
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Default Library (Programmer)
# PRIORITIZE EXTERNAL HOME FIRST
JAAVIS_HOME = os.path.join(HOME, ".jaavis")
EXTERNAL_LIB_PATH = os.path.join(JAAVIS_HOME, "library")
BUNDLED_LIB_PATH = os.path.join(BASE_DIR, "library")

def get_default_library_path():
    # 1. Env Var
    if os.environ.get("JAAVIS_LIBRARY_PATH"):
        return os.environ.get("JAAVIS_LIBRARY_PATH")

    # 2. External Home (~/.jaavis/library) - FORCE PERSISTENCE
    # If the external library doesn't exist, we must create it from the bundle
    # This ensures upgrades (which change BUNDLED_LIB_PATH) don't wipe user data.
    if not os.path.exists(EXTERNAL_LIB_PATH):
        if os.path.exists(BUNDLED_LIB_PATH):
             try:
                 print(f"📦 First Run: Migrating bundled library to {EXTERNAL_LIB_PATH}...")
                 shutil.copytree(BUNDLED_LIB_PATH, EXTERNAL_LIB_PATH)
             except Exception as e:
                 print(f"⚠️  Migration Warning: Could not copy bundled library: {e}")
        else:
             # Create empty if bundle missing
             os.makedirs(EXTERNAL_LIB_PATH, exist_ok=True)

    # 3. Always return the external path as the source of truth
    return EXTERNAL_LIB_PATH

DEFAULT_LIBRARY_PATH = get_default_library_path()
TEMPLATE_PATH = os.path.join(DEFAULT_LIBRARY_PATH, "templates/skill.md")
LOGO_PATH = os.path.join(BASE_DIR, "logo.md")

# ANSI Colors
CYAN = '\033[1;36m'
GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
MAGENTA = '\033[1;35m'
BLUE = '\033[1;34m'
WHITE = '\033[1;37m'
RED = '\033[1;31m'
BOLD = '\033[1m'
RESET = '\033[0m'
GREY = '\033[0;90m'

# ==========================================
# CONFIGURATION MANAGEMENT
# ==========================================
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except:
             return {}
    return {}

def save_config(data):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def get_git_status(path):
    """Returns (last_sync_time, pending_count) tuple"""
    if not os.path.exists(os.path.join(path, ".git")):
        return None, 0

    try:
        # Get uncommitted changes count
        pending = subprocess.check_output(f"git -C {path} status --porcelain | wc -l", shell=True).decode().strip()
        pending = int(pending) if pending else 0

        # Get last commit relative time
        last_sync = subprocess.check_output(f"git -C {path} log -1 --format='%cr'", shell=True).decode().strip()

        return last_sync, pending
    except:
        return None, 0

def open_brain_vscode():
    """Opens the entire Jaavis Brain (~/.jaavis) in VS Code"""
    if not os.path.exists(JAAVIS_HOME):
        os.makedirs(JAAVIS_HOME, exist_ok=True)

    print(f"📂 Opening JAAVIS Brain at {JAAVIS_HOME}...")

    # Try VS Code first
    if shutil.which('code'):
        subprocess.call(['code', JAAVIS_HOME])
    elif sys.platform == 'darwin':
        subprocess.call(['open', JAAVIS_HOME])
    else:
        print(f"{RED}VS Code ('code') not found in PATH.{RESET}")

def sync_all_personas():
    """Smart Sync: Pulls updates or Clones missing brains. Interactive & Robust."""
    config = load_config()
    personas = config.get("personas", {})
    if "programmer" not in personas: personas["programmer"] = {"path": DEFAULT_LIBRARY_PATH}

    # 1. Build Menu Options
    persona_keys = ["programmer"] + sorted([k for k in personas.keys() if k != "programmer"])
    menu_options = ["Sync All (Default)"]

    for p in persona_keys:
        p_data = personas.get(p, {})
        path = p_data.get("path")
        remote = p_data.get("remote_url", "No Remote")
        short_remote = remote.replace("https://", "").replace("git@", "")[:25] + "..." if len(remote) > 25 else remote

        last_sync, pending = get_git_status(path)
        status_icon = "✅" if pending == 0 else "⚠️ Dirty"

        menu_options.append(f"{p.capitalize()} [{short_remote}] {status_icon}")

    # 2. Select Target
    print(f"\n{MAGENTA}🔄 Jaavis Sync Protocol{RESET}")
    choice_idx = interactive_menu("Select Target to Sync:", menu_options)

    targets = []
    if choice_idx == 0:
        targets = persona_keys # All
    else:
        targets = [persona_keys[choice_idx - 1]] # Specific

    print(f"\n{MAGENTA}⬇️  Syncing Selected Brains...{RESET}")
    config_changed = False

    for name in targets:
        p_data = personas.get(name, {})
        path = p_data.get("path")
        remote_url = p_data.get("remote_url")

        print(f"  {CYAN}• {name.capitalize()}:{RESET} ", end="", flush=True)

        if os.path.exists(path):
            if os.path.exists(os.path.join(path, ".git")):
                # Check for dirty state
                _, pending = get_git_status(path)

                # Logic: Stash -> Pull (Rebase) -> Pop
                commands = []
                if pending > 0:
                    print(f"{YELLOW} Local changes ({pending}). Stashing...{RESET}", end="")
                    commands.append(["git", "stash"])

                commands.append(["git", "pull", "--rebase"])

                if pending > 0:
                    commands.append(["git", "stash", "pop"])

                # Execute
                success = True
                for cmd in commands:
                    res = subprocess.run(cmd, cwd=path, capture_output=True, text=True)
                    if res.returncode != 0:
                        # Fallback: If pull failed, maybe upstream isn't set?
                        if "pull" in cmd and "no tracking information" in res.stderr:
                             try:
                                 current_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path).decode().strip()
                             except:
                                 current_branch = "main"

                             print(f"{YELLOW} Setting upstream to origin/{current_branch}...{RESET}")
                             subprocess.run(["git", "branch", "--set-upstream-to", f"origin/{current_branch}", current_branch], cwd=path, capture_output=True)
                             # Retry pull
                             res = subprocess.run(cmd, cwd=path, capture_output=True, text=True)

                        if res.returncode != 0:
                            print(f"\n    {RED}❌ Error during '{cmd[1]}':{RESET} {res.stderr.strip()}")
                            success = False
                            break

                if success:
                    print(f"{GREEN}Updated ✔{RESET}")

            else:
                 # Exists but not Git-linked
                 print(f"{YELLOW}Exists but not Git-linked.{RESET}")
                 if input(f"    {CYAN}? Initialize and link to remote? (y/N): {RESET}").strip().lower() == 'y':
                     new_remote = input(f"    {CYAN}? Remote Git URL: {RESET}").strip()
                     if new_remote:
                         try:
                             subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
                             subprocess.run(["git", "branch", "-M", "main"], cwd=path, check=True, capture_output=True)
                             subprocess.run(["git", "remote", "add", "origin", new_remote], cwd=path, check=True, capture_output=True)
                             p_data["remote_url"] = new_remote
                             config_changed = True
                             print(f"    {GREY}Linking...{RESET}")
                             subprocess.run(["git", "pull", "origin", "main"], cwd=path, capture_output=True)
                             print(f"    {GREEN}Linked & Synced ✔{RESET}")
                         except Exception as e:
                             print(f"    {RED}Failed: {e}{RESET}")

        elif remote_url:
            # Clone Recovery
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                res = subprocess.run(["git", "clone", remote_url, path], capture_output=True, text=True)
                if res.returncode == 0:
                    print(f"{GREEN}Recovered (Clone) ☁️ -> 💾{RESET}")
                else:
                    print(f"{RED}Clone Failed: {res.stderr}{RESET}")
            except Exception as e:
                print(f"{RED}Error: {e}{RESET}")
        else:
             # Missing & No Remote
             print(f"{RED}Missing & No Remote.{RESET}")
             if input(f"    {CYAN}? Clone from a URL? (y/N): {RESET}").strip().lower() == 'y':
                 new_remote = input(f"    {CYAN}? Remote Git URL: {RESET}").strip()
                 if new_remote:
                     try:
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        res = subprocess.run(["git", "clone", new_remote, path], capture_output=True, text=True)
                        if res.returncode == 0:
                            print(f"    {GREEN}Recovered (Clone) ☁️ -> 💾{RESET}")
                            p_data["remote_url"] = new_remote
                            config_changed = True
                        else:
                            print(f"    {RED}Clone Failed.{RESET}")
                     except Exception as e:
                        print(f"    {RED}Error: {e}{RESET}")

    if config_changed:
        save_config(config)

    print(f"\n{GREEN}Sync Complete.{RESET}")
    time.sleep(2)


def push_all_personas():
    """Iterates through all personas and pushes changes. Interactive."""
    config = load_config()
    personas = config.get("personas", {})
    if "programmer" not in personas: personas["programmer"] = {"path": DEFAULT_LIBRARY_PATH}

    # 1. Build Menu Options
    persona_keys = ["programmer"] + sorted([k for k in personas.keys() if k != "programmer"])
    menu_options = ["Push All (Default)"]

    for p in persona_keys:
        p_data = personas.get(p, {})
        path = p_data.get("path")
        remote = p_data.get("remote_url", "No Remote")
        short_remote = remote.replace("https://", "").replace("git@", "")[:20] + "..." if len(remote) > 20 else remote

        last_sync, pending = get_git_status(path)
        status = f"[{pending} pending]" if pending > 0 else "Clean"

        menu_options.append(f"{p.capitalize()} [{short_remote}] {status}")

    # 2. Select Target
    print(f"\n{MAGENTA}🚀 Jaavis Push Protocol{RESET}")
    choice_idx = interactive_menu("Select Target to Push:", menu_options)

    targets = []
    if choice_idx == 0:
        targets = persona_keys # All
    else:
        targets = [persona_keys[choice_idx - 1]] # Specific

    print(f"\n{MAGENTA}⬆️  Pushing Selected Brains...{RESET}")
    config_changed = False

    for name in targets:
        p_data = personas.get(name, {})
        path = p_data.get("path")

        if not path or not os.path.exists(path): continue

        print(f"  {CYAN}• {name.capitalize()}:{RESET} ", end="", flush=True)

        # Check for Git
        if not os.path.exists(os.path.join(path, ".git")):
             print(f"{YELLOW} Not a git repo.{RESET}")
             if input(f"    {CYAN}? Initialize Git? (y/N): {RESET}").strip().lower() == 'y':
                 try:
                     subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
                     subprocess.run(["git", "branch", "-M", "main"], cwd=path, check=True, capture_output=True)
                     print(f"    {GREEN}Initialized.{RESET}")
                 except:
                     print(f"    {RED}Failed.{RESET}")
                     continue
             else:
                 continue

        # Check Remote
        has_remote = False
        try:
            res = subprocess.run(["git", "remote"], cwd=path, capture_output=True, text=True)
            if "origin" in res.stdout:
                has_remote = True
        except: pass

        if not has_remote:
            print(f"{YELLOW} No remote configured.{RESET}")
            if input(f"    {CYAN}? Add Remote URL? (y/N): {RESET}").strip().lower() == 'y':
                url = input(f"    {CYAN}? URL: {RESET}").strip()
                if url:
                    try:
                        subprocess.run(["git", "remote", "add", "origin", url], cwd=path, check=True, capture_output=True)
                        print(f"    {GREEN}Remote added.{RESET}")
                        personas[name]["remote_url"] = url
                        config_changed = True
                        has_remote = True
                    except:
                        print(f"    {RED}Failed to add remote.{RESET}")

        if has_remote:
            try:
                # Add
                subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
                # Commit (ignore empty)
                subprocess.run(["git", "commit", "-m", f"Brain Sync: {datetime.now()}"], cwd=path, capture_output=True)
                # Push
                res = subprocess.run(["git", "push", "origin", "main"], cwd=path, capture_output=True, text=True)
                if res.returncode != 0:
                     # Try master fallback
                     res = subprocess.run(["git", "push", "origin", "master"], cwd=path, capture_output=True, text=True)

                if res.returncode == 0:
                    print(f"{GREEN}Synced ✔{RESET}")
                else:
                    print(f"{RED}Push Failed.{RESET}")
            except Exception as e:
                 print(f"{RED}Error: {e}{RESET}")
        else:
             print(f"{GREY} Skipped (No Remote){RESET}")

    if config_changed:
        save_config(config)

    print(f"\n{GREEN}Done.{RESET}")
    time.sleep(2)

# ==========================================
# BRAINSTORMING (AI) LOGIC
# ==========================================

def check_api_keys():
    """Ensures API keys are present in config."""
    config = load_config()
    if 'env' not in config: config['env'] = {}

    providers = ['GEMINI_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY']
    changed = False

    print(f"\n{MAGENTA}🔑 AI Configuration {RESET}")
    for p in providers:
        if p not in config['env'] or not config['env'][p]:
            print(f"{YELLOW}  • {p} not found.{RESET}")
            val = input(f"    Enter key (or leave blank to skip): ").strip()
            if val:
                config['env'][p] = val
                changed = True

    if changed:
        save_config(config)
        print(f"{GREEN}Keys saved securely.{RESET}")
    else:
        print(f"{GREY}Configuration checks out.{RESET}")

def get_brainstorm_prompt(context_type="skill"):
    """Returns the 2026 Fortress Standard Prompt."""
    return """
You are the **Jaavis Architect Bot**. Your goal is to **refactor** the provided code into a 2026 "Fortress" Standard skill.

### Core Constraints:
1.  **Idempotency**: Ensure `mkdir`, `cd`, and `cat` operations don't fail if they've already run.
2.  **Pre-flight Checks**: Add logic to verify dependencies (e.g., `command -v kubectl`) before executing.
3.  **Observability**: Use emojis and clear `echo` statements for every major step.
4.  **Modern Patterns**: Use `[[ ]]` for shell tests and ensure all variables are quoted to handle spaces.
5.  **Harvest-Ready**: Maintain the `<!-- JAAVIS:EXEC -->` anchor and the Markdown structure.

### Output Format:
Return **only** the improved Markdown content. Do not include conversational filler.
"""

def call_llm_api(provider, system_prompt, user_content):
    """Generic LLM Caller (Placeholder for now, supports Local Dump)."""
    # In a real implementation, valid `requests` or `urllib` calls would go here.
    # For now, we simulate the "Local" dump which is the fallback.
    return None

def brainstorm_skill(target_path, provider="local"):
    """Executes the brainstorming session."""

    # 1. Read Target Context
    if not os.path.exists(target_path):
        print(f"{RED}Error: Target {target_path} not found.{RESET}")
        return

    with open(target_path, 'r') as f:
        content = f.read()

    # 2. Prepare Prompt
    system_prompt = get_brainstorm_prompt()
    full_request = f"{system_prompt}\n\n--- TARGET CONTEXT ---\n{content}"

    # 3. Execute
    if provider == "local":
        out_file = target_path + ".prompt.txt"
        with open(out_file, 'w') as f:
            f.write(full_request)
        print(f"\n{GREEN}📝 Brainstorm Context generated:{RESET} {out_file}")
        print(f"{GREY}Copy this content into Gemini/ChatGPT/DeepSeek to get your refactor.{RESET}")

        # Auto-open
        if shutil.which('code'):
            subprocess.call(['code', out_file])
        elif sys.platform == 'darwin':
            subprocess.call(['open', out_file])

    elif provider in ["gemini", "openai", "deepseek"]:
        print(f"{YELLOW}📡 Connecting to {provider.upper()} (Simulation)...{RESET}")
        # Placeholder for actual API call
        print(f"{RED}API Integration not yet fully hydrated. Switching to Local Dump.{RESET}")
        brainstorm_skill(target_path, "local")

def run_brainstorm_wizard():
    """Interactive Wizard for Jaavis Brainstorm."""
    print(f"\n{MAGENTA}🧠 Jaavis Brainstorm (AI Refactor){RESET}")

    # 1. Select Target (Simple: Current Directory's files)
    files = [f for f in os.listdir('.') if f.endswith('.md') or f.endswith('.py') or f.endswith('.sh')]
    if not files:
        print(f"{RED}No suitable files found in current directory.{RESET}")
        return

    print(f"\n{CYAN}Select Target to Refactor:{RESET}")
    menu_options = files + ["Cancel"]
    choice = interactive_menu("Make a choice:", menu_options)

    if choice == len(menu_options) - 1: return
    target_file = files[choice]

    # 2. Select Provider
    print(f"\n{CYAN}Select Intelligence Engine:{RESET}")
    providers = ["Local (Generate Prompt File)", "Gemini", "OpenAI", "DeepSeek"]
    p_choice = interactive_menu("Choose Provider:", providers)

    p_map = {0: "local", 1: "gemini", 2: "openai", 3: "deepseek"}
    selected_provider = p_map[p_choice]

    # 3. Check Keys if Cloud
    if selected_provider != "local":
        check_api_keys()

    # 4. Execute
    brainstorm_skill(target_file, selected_provider)

def get_key():

    """Captures a single keypress, handling arrow key escape sequences."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ch += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    if ch == '\x03': raise KeyboardInterrupt
    return ch

def interactive_menu(prompt, options, default_index=0, return_char=False):
    """Renders an interactive menu handling arrow keys. Supports shortcuts."""
    current_row = default_index

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\n{CYAN}{prompt}{RESET}")
        print("-----------------------------------------------------")

        for idx, option in enumerate(options):
            if idx == current_row:
                print(f"{GREEN}> {option}{RESET}")
            else:
                print(f"  {option}")

        print("-----------------------------------------------------")
        print(f"{GREY}Use UP/DOWN arrows to navigate, ENTER to select.{RESET}")
        if return_char:
             print(f"{GREY}[C] Code | [S] Sync All | [P] Push Brain{RESET}")

        key = get_key()

        if key == '\x1b[A': # UP
            if current_row > 0:
                current_row -= 1
        elif key == '\x1b[B': # DOWN
            if current_row < len(options) - 1:
                current_row += 1
        elif key == '\r': # ENTER
            return (current_row, None) if return_char else current_row

        # Handle Shortcuts
        if return_char and key.lower() in ['c', 'p', 's']:
            return (current_row, key.lower())

def get_active_library_path():
    config = load_config()
    current_persona = config.get("current_persona", "programmer")
    personas = config.get("personas", {})

    if current_persona in personas:
        return personas[current_persona].get("path", DEFAULT_LIBRARY_PATH)

    # Default to Programmer/Default path
    return DEFAULT_LIBRARY_PATH

def get_current_persona_name():
    config = load_config()
    return config.get("current_persona", "programmer").capitalize()

# ==========================================
# PERSONA LOGIC
# ==========================================
def load_face():
    """Loads and displays the Jaavis Face (logo.md)"""
    if os.path.exists(LOGO_PATH):
        print(CYAN)
        with open(LOGO_PATH, 'r') as f:
            print(f.read())
        print(RESET)
    else:
        print(f"{CYAN}🤖 JAAVIS{RESET}")

def show_welcome():
    """Display onboarding message for new users"""
    print(f"\n{MAGENTA}👋 Welcome to Jaavis - Your One-Army Orchestrator{RESET}")
    print(f"{GREY}====================================================={RESET}")
    print(f"I am here to help you build, harvest, and deploy at speed.")
    print(f"\n{BOLD}Quick Start Guide:{RESET}")
    print(f"  1. {CYAN}jaavis list --text{RESET}       → Interactive Knowledge Base (TUI)")
    print(f"  2. {CYAN}jaavis init{RESET}       → Start a new project (One-Army Protocol)")
    print(f"  3. {CYAN}jaavis harvest <doc>{RESET}    → Save your knowledge as reusable skills")
    print(f"  4. {CYAN}jaavis deploy{RESET}     → Ship your project to production")
    print(f"  5. {CYAN}jaavis sync{RESET}       → Update your skill library from critical missions")
    print(f"  6. {CYAN}jaavis help{RESET}       → Show this help message")

def select_persona():
    """Interactive Persona Selection & Configuration"""
    load_face()

    config = load_config()
    current = config.get("current_persona", "programmer")

    print(f"{WHITE}Hi I'm Jaavis, your personal assistant.{RESET}\n")
    print(f"{GREY}Current Brain: {JAAVIS_HOME}{RESET}\n")

    # 1. Build Options with Status
    # Ensure defaults exist in config
    if "personas" not in config: config["personas"] = {}
    if "programmer" not in config["personas"]: config["personas"]["programmer"] = {"path": DEFAULT_LIBRARY_PATH}

    persona_keys = ["programmer"] + sorted([k for k in config["personas"].keys() if k != "programmer"])
    menu_options = []

    for p in persona_keys:
        p_data = config["personas"].get(p, {})
        p_path = p_data.get("path", DEFAULT_LIBRARY_PATH)
        lock_status = " 🔒" if p_data.get("locked") else ""

        # Get Git Status
        last_sync, pending = get_git_status(p_path)

        display_name = p.capitalize()
        if p == "programmer": display_name += " (One-Army Protocol)"

        option_str = f"{display_name}{lock_status}"
        if last_sync:
             status_icon = "✅" if pending == 0 else "🛠️"
             option_str += f"\n    ↳ {GREY}Last Sync: {last_sync} | Pending: {pending} {status_icon}{RESET}"

        menu_options.append(option_str)

    # 2. Add Shortcuts
    menu_options.append("Manage Personas")

    # 3. Determine Default Index
    default_idx = 0
    if current in persona_keys:
        default_idx = persona_keys.index(current)

    # 4. Show Interactive Menu with Shortcuts Handler
    prompt_text = f"Who is operating right now? (Current: {current.upper()})"

    # Custom loop to handle shortcuts 'C' and 'P'
    while True:
        choice_idx, char_code = interactive_menu(prompt_text, menu_options, default_index=default_idx, return_char=True)

        if char_code in ['c', 'C']:
             open_brain_vscode()
             continue # Refresh menu
        elif char_code in ['p', 'P']:
             push_all_personas()
             input("Press Enter to continue...")
             continue # Refresh menu
        else:
             break # Selection made

    # 5. Map Choice to Persona
    manage_index = len(menu_options) - 1

    if choice_idx == manage_index:
        manage_personas_menu()
        return select_persona()

    persona_key = persona_keys[choice_idx]
    lib_path = config["personas"].get(persona_key, {}).get("path", DEFAULT_LIBRARY_PATH)

    # Ensure directory exists
    if not os.path.exists(lib_path):
        try:
            os.makedirs(os.path.join(lib_path, "skills"))
            os.makedirs(os.path.join(lib_path, "scripts"))
            print(f"{GREEN}✔ Created new memory bank for {persona_key}{RESET}")
        except:
            pass

    # Save Config
    config["current_persona"] = persona_key

    # Update personas dict
    if "personas" not in config: config["personas"] = {}

    # Default personas ensure they exist in config
    if "programmer" not in config["personas"]: config["personas"]["programmer"] = {"path": DEFAULT_LIBRARY_PATH}

    # Save the selected one if not exists
    if persona_key not in config["personas"]:
        config["personas"][persona_key] = {"path": lib_path}

    save_config(config)

    print(f"{YELLOW}User identified: {persona_key.upper()}{RESET}")
    # Transition to TUI directly
    import jaavis_tui
    jaavis_tui.run(lib_path)

def manage_personas_menu():
    """Menu to manage (Rename, Lock, Delete) personas"""
    while True:
        options = [
            "➕ Create New Persona",
            "✏️  Rename Persona",
            "🔒 Lock/Unlock Persona",
            "🗑️  Delete Persona",
            "⬅️  Back"
        ]

        choice_idx = interactive_menu("🛠️  Persona Management", options)

        if choice_idx == 0:
            add_persona()
        elif choice_idx == 1:
            rename_persona()
        elif choice_idx == 2:
            lock_persona()
        elif choice_idx == 3:
            delete_persona()
        elif choice_idx == 4:
            break

def add_persona():
    print(f"\n{MAGENTA}➕ Create New Persona{RESET}")
    name = input(f"{CYAN}? Persona Name (give it any name): {RESET}").strip().lower()
    if not name: return

    # Normalize
    name = re.sub(r'[^a-z0-9_]', '', name)

    config = load_config()
    if "personas" not in config: config["personas"] = {}

    if name in config["personas"] or name == "programmer":
        print(f"{RED}Error: Persona '{name}' already exists.{RESET}")
        time.sleep(1)
        return

    lib_dir = f"library_{name}"
    # FIX: Use Persistent Home instead of BASE_DIR
    lib_path = os.path.join(JAAVIS_HOME, lib_dir)

    if not os.path.exists(lib_path):
        os.makedirs(lib_path, exist_ok=True)
        # Create subfolders
        os.makedirs(os.path.join(lib_path, "skills"), exist_ok=True)
        os.makedirs(os.path.join(lib_path, "scripts"), exist_ok=True)

    config["personas"][name] = {
        "path": lib_path,
        "created_at": str(datetime.now()),
        "locked": False
    }

    save_config(config)
    print(f"{GREEN}✔ Persona '{name}' added at {lib_path}!{RESET}")
    time.sleep(1)

def migrate_persona_libraries():
    """Auto-migrates persona libraries from Cellar (volatile) to ~/.jaavis (persistent)"""
    config = load_config()
    if "personas" not in config: return

    migrated = False

    for name, persona in config['personas'].items():
        if name == 'programmer': continue # handled by get_default_library_path

        old_path = persona.get('path', '')

        # Detect if the library is in the dangerous 'Cellar' or 'brew' path
        # Or if it starts with BASE_DIR which might be the cellar
        is_volatile = "Cellar/jaavis" in old_path or (BASE_DIR in old_path and JAAVIS_HOME not in old_path)

        if is_volatile:
            new_path = os.path.join(JAAVIS_HOME, f"library_{name}")

            # If path changed, we need to migrate
            if os.path.abspath(old_path) != os.path.abspath(new_path):
                print(f"{YELLOW}📦 Migrating persona '{name}' to persistent storage...{RESET}")

                if os.path.exists(old_path):
                    if not os.path.exists(new_path):
                        try:
                            shutil.copytree(old_path, new_path)
                            print(f"{GREEN}✔ Data moved to {new_path}{RESET}")
                        except Exception as e:
                            print(f"{RED}Failed to move data: {e}{RESET}")
                            continue # Don't update config if copy failed
                    else:
                         print(f"{GREY}Target {new_path} already exists. Updating config pointer.{RESET}")
                else:
                    print(f"{RED}⚠️  Warning: '{name}' library path was lost/missing. Pointing to new location.{RESET}")
                    if not os.path.exists(new_path):
                        os.makedirs(new_path, exist_ok=True)
                        os.makedirs(os.path.join(new_path, "skills"), exist_ok=True)

                persona['path'] = new_path
                migrated = True

    if migrated:
        save_config(config)
        print(f"{GREEN}✔ Migration complete. All personas secured in {JAAVIS_HOME}{RESET}\n")


def rename_persona():
    config = load_config()
    dynamic_personas = sorted([k for k in config.get("personas", {}).keys() if k != "programmer"])

    if not dynamic_personas:
        print(f"{YELLOW}No dynamic personas to rename.{RESET}")
        time.sleep(1)
        return

    print(f"\n{YELLOW}✏️  Rename Persona{RESET}")

    options = []
    for p in dynamic_personas:
        options.append(p)
    options.append("Cancel")

    choice_idx = interactive_menu("Select Persona to rename", options)

    if choice_idx >= len(dynamic_personas):
        return

    old_name = dynamic_personas[choice_idx]


    if config["personas"][old_name].get("locked"):
        print(f"{RED}Error: Persona '{old_name}' is locked. Unlock it first.{RESET}")
        time.sleep(1)
        return

    new_name = input(f"{CYAN}? New Name for '{old_name}': {RESET}").strip().lower()
    if not new_name: return
    new_name = re.sub(r'[^a-z0-9_]', '', new_name)

    if new_name in config["personas"] or new_name == "programmer":
        print(f"{RED}Error: Name '{new_name}' already exists.{RESET}")
        time.sleep(1)
        return

    # Rename directory if it matches library_{old_name}
    old_path = config["personas"][old_name]["path"]
    new_lib_dir = f"library_{new_name}"
    # FIX: Use Persistent Home
    new_path = os.path.join(JAAVIS_HOME, new_lib_dir)

    # Check if old path was the standard naming convention in either location
    # We check both to be safe during transition
    standard_old_base = os.path.join(BASE_DIR, f"library_{old_name}")
    standard_old_home = os.path.join(JAAVIS_HOME, f"library_{old_name}")

    if old_path == standard_old_base or old_path == standard_old_home:
        if os.path.exists(old_path):
            # If target exists, fail
            if os.path.exists(new_path):
                 print(f"{RED}Error: Target path {new_path} already exists.{RESET}")
                 return

            os.rename(old_path, new_path)

        config["personas"][new_name] = config["personas"].pop(old_name)
        config["personas"][new_name]["path"] = new_path
    else:
        # Custom path? Just rename key, don't move folder
        config["personas"][new_name] = config["personas"].pop(old_name)

    save_config(config)
    print(f"{GREEN}✔ Persona renamed to '{new_name}'!{RESET}")
    time.sleep(1)


def lock_persona():
    config = load_config()
    dynamic_personas = sorted([k for k in config.get("personas", {}).keys() if k != "programmer"])

    if not dynamic_personas:
        print(f"{YELLOW}No dynamic personas to lock/unlock.{RESET}")
        time.sleep(1)
        return

    print(f"\n{CYAN}🔒 Lock/Unlock Persona{RESET}")

    options = []
    for p in dynamic_personas:
        status = "🔒 Locked" if config["personas"][p].get("locked") else "🔓 Unlocked"
        options.append(f"{p} ({status})")
    options.append("Cancel")

    choice_idx = interactive_menu("Select Persona to Lock/Unlock", options)

    if choice_idx >= len(dynamic_personas):
        return

    p_name = dynamic_personas[choice_idx]
    is_locked = config["personas"][p_name].get("locked", False)
    config["personas"][p_name]["locked"] = not is_locked

    save_config(config)
    new_status = "Locked" if not is_locked else "Unlocked"
    print(f"{GREEN}✔ Persona '{p_name}' is now {new_status}.{RESET}")
    time.sleep(1)

def delete_persona():
    config = load_config()
    dynamic_personas = sorted([k for k in config.get("personas", {}).keys() if k != "programmer"])

    if not dynamic_personas:
        print(f"{YELLOW}No dynamic personas to delete.{RESET}")
        time.sleep(1)
        return

    print(f"\n{RED}🗑️  Delete Persona{RESET}")

    options = []
    for p in dynamic_personas:
        lock_status = " 🔒" if config["personas"][p].get("locked") else ""
        options.append(f"{p}{lock_status}")
    options.append("Cancel")

    choice_idx = interactive_menu("Select Persona to DELETE", options)

    if choice_idx >= len(dynamic_personas):
        return

    p_name = dynamic_personas[choice_idx]

    if config["personas"][p_name].get("locked"):
        print(f"{RED}Error: Persona '{p_name}' is locked. Unlock it first.{RESET}")
        time.sleep(1)
        return

    print(f"\n{RED}⚠️  WARNING: You are about to delete '{p_name}'.{RESET}")
    print(f"{RED}This will PERMANENTLY delete all persona data and its library files!{RESET}")
    confirm = input(f"{YELLOW}? Type '{p_name}' to confirm deletion: {RESET}").strip()

    if confirm == p_name:
        lib_path = config["personas"][p_name]["path"]

        # Delete library directory
        if os.path.exists(lib_path):
            shutil.rmtree(lib_path)
            print(f"{YELLOW}✔ Deleted memory bank at {lib_path}{RESET}")

        # Remove from config
        del config["personas"][p_name]
        if config.get("current_persona") == p_name:
            config["current_persona"] = "programmer"

        save_config(config)
        print(f"{GREEN}✔ Persona '{p_name}' deleted successfully.{RESET}")
    else:
        print(f"{YELLOW}Deletion aborted. Confirmation name didn't match.{RESET}")

    time.sleep(1)

# ==========================================
# RENDERER LOGIC (From jaavis_renderer.py)
# ==========================================
def render_sketchy_box(title, items, color=CYAN):
    MAX_WIDTH = 70

    # Wrap text for items
    wrapped_lines = []
    for item in items:
        lines = textwrap.wrap(item, width=MAX_WIDTH)
        for i, line in enumerate(lines):
            if i == 0:
                wrapped_lines.append(f"• {line}")
            else:
                wrapped_lines.append(f"  {line}")

    # Calculate box width
    if wrapped_lines:
        content_width = max([len(line) for line in wrapped_lines] + [len(title)]) + 2
    else:
        content_width = len(title) + 2

    content_width = max(content_width, 40)
    box_width = content_width + 4

    # Render
    print(f"   {GREY}_{'_' * box_width}_{RESET}")
    print(f"  {GREY}/{' ' * box_width}\\{RESET}")
    print(f" {GREY}|{RESET}  {color}{title.center(box_width)}{RESET}  {GREY}|{RESET}")
    print(f" {GREY}|{RESET}  {GREY}{'-' * box_width}{RESET}  {GREY}|{RESET}")

    for line in wrapped_lines:
        padding = box_width - len(line) - 2
        print(f" {GREY}|{RESET}  {WHITE}{line}{RESET}{' ' * padding}  {GREY}|{RESET}")

    print(f"  {GREY}\\{'_' * box_width}/{RESET}")
    print(f"          {GREY}|{RESET}")
    print(f"          {GREY}v{RESET}")

def render_pipeline():
    if not os.path.exists(WORKFLOW_PATH):
        print(f"{RED}Error: Workflow file not found at {WORKFLOW_PATH}{RESET}")
        return

    print(f"\n{BLUE}🚀 Initializing Programmer Mode...{RESET}")
    print("-----------------------------------------------------")

    with open(WORKFLOW_PATH, 'r') as f:
        lines = f.readlines()

    current_phase = None
    items = []

    print(f"\n{MAGENTA}   ( Start ) {RESET}")
    print(f"       {GREY}|{RESET}")
    print(f"       {GREY}v{RESET}")

    colors = [CYAN, BLUE, YELLOW, GREEN]
    color_idx = 0

    for line in lines:
        line = line.strip()
        if not line: continue

        if line.startswith("## Phase"):
            if current_phase:
                render_sketchy_box(current_phase, items, colors[color_idx % len(colors)])
                color_idx += 1
                items = []
            current_phase = line.replace("#", "").strip()
        elif line.startswith("1. ") or line.startswith("- "):
            clean_item = re.sub(r'^\d+\.\s*|-\s*', '', line)
            clean_item = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_item)
            clean_item = re.sub(r'\*(.*?)\*', r'\1', clean_item)
            if current_phase:
                items.append(clean_item)

    if current_phase:
        render_sketchy_box(current_phase, items, colors[color_idx % len(colors)])

    print(f"\n{GREEN}    ( Done ) {RESET}\n")
    print("-----------------------------------------------------")
    print(f"{YELLOW}Protocol Loaded.{RESET} Ready for instructions.")

# ==========================================
# SKILL MANAGEMENT LOGIC
# ==========================================
def list_skills():
    lib_path = get_active_library_path()
    persona = get_current_persona_name()
    print(f"{BLUE}🧠 Jaavis Knowledge Base ({persona}){RESET}")
    print("-----------------------------------------------------")

    if not os.path.exists(lib_path):
        print(f"{YELLOW}No library found at {lib_path}{RESET}")
        return

    skills_count = 0
    for root, dirs, files in os.walk(lib_path):
        # Prune .git and __pycache__ from traversal
        dirs[:] = [d for d in dirs if d not in [".git", "__pycache__"]]

        level = root.replace(lib_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        subindent = ' ' * 4 * (level + 1)

        # Print Directory Name
        folder_name = os.path.basename(root)
        if folder_name and folder_name != "skills":
            print(f"{GREY}{indent}📂 {folder_name}/{RESET}")

        for f in files:
            if f.endswith(".md") and f != "TEMPLATE_SKILL.md":
                path = os.path.join(root, f)
                mtime = os.path.getmtime(path)
                is_recent = (time.time() - mtime) < 86400 # 24 hours
                tag = f" {YELLOW}(RECENT){RESET}" if is_recent else ""

                print(f"{GREEN}{subindent}📜 {f}{tag}{RESET}")
                skills_count += 1

    if skills_count == 0:
        print(f"   {GREY}(No skills harvested yet. Use 'jaavis harvest'){RESET}")
    print("-----------------------------------------------------")

def search_skills(query):
    lib_path = get_active_library_path()
    print(f"{BLUE}🔍 Searching Knowledge Base for '{query}'...{RESET}")
    print("-----------------------------------------------------")

    matches = []

    for root, dirs, files in os.walk(lib_path):
        for f in files:
            if f.endswith(".md"):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r') as file_content:
                        content = file_content.read()
                        if query.lower() in content.lower():
                            matches.append(path)
                except Exception:
                    continue

    if matches:
        for match in matches:
            rel_path = match.replace(lib_path + "/", "")
            # Try to show snippet
            print(f"{GREEN}✅ Found in: {WHITE}{rel_path}{RESET}")
    else:
         print(f"{YELLOW}No matches found.{RESET}")
    print("-----------------------------------------------------")

def open_skill(name_query):
    lib_path = get_active_library_path()

    # Find the skill file by fuzzy name match
    target_file = None

    # Direct match first
    for root, dirs, files in os.walk(lib_path):
        for f in files:
             if f == name_query or f == f"{name_query}.md":
                 target_file = os.path.join(root, f)
                 break
        if target_file: break

    # Fuzzy match if no direct match
    if not target_file:
         for root, dirs, files in os.walk(lib_path):
            for f in files:
                if name_query.lower() in f.lower() and f.endswith(".md"):
                     target_file = os.path.join(root, f)
                     break
            if target_file: break

    if target_file:
        print(f"{GREEN}Opening {target_file}...{RESET}")

        # Determine editor
        editor = os.environ.get('EDITOR', 'open')
        # Check if 'code' is available
        if shutil.which('code'):
            editor = 'code'

        try:
             subprocess.call([editor, target_file])
        except Exception as e:
             print(f"{RED}Failed to open: {e}{RESET}")
             # Fallback
             subprocess.call(['open', target_file])
    else:
        print(f"{RED}Skill '{name_query}' not found.{RESET}")
        print(f"{GREY}Tip: Use 'jaavis search' to find the correct name.{RESET}")

def delete_skill(name_query):
    lib_path = get_active_library_path()

    # Find the skill file by fuzzy name match
    target_file = None

    # Direct match first
    for root, dirs, files in os.walk(lib_path):
        for f in files:
             if f == name_query or f == f"{name_query}.md":
                 target_file = os.path.join(root, f)
                 break
        if target_file: break

    # Fuzzy match if no direct match
    if not target_file:
         for root, dirs, files in os.walk(lib_path):
            for f in files:
                if name_query.lower() in f.lower() and f.endswith(".md"):
                     target_file = os.path.join(root, f)
                     break
            if target_file: break

    if target_file:
        print(f"{RED}WARNING: You are about to DELETE:{RESET}")
        print(f"   {target_file}")
        confirm = input(f"{YELLOW}Are you sure? (type 'delete' to confirm): {RESET}")

        if confirm == 'delete':
            try:
                os.remove(target_file)
                print(f"{GREEN}File deleted.{RESET}")
            except Exception as e:
                print(f"{RED}Error deleting file: {e}{RESET}")
        else:
            print("Aborted.")
    else:
        print(f"{RED}Skill '{name_query}' not found.{RESET}")

def get_skill_metadata(file_path):
    """Extracts title and metadata from a skill file (YAML frontmatter)."""
    if not os.path.exists(file_path): return None
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            # Regex to pull the title from the metadata header (GitHub formatted)
            match = re.search(r'^title:\s*(.*)$', content, re.MULTILINE)
            return match.group(1).strip() if match else None
    except:
        return None

def backup_skill(file_path):
    """Atomic Backup: Moves file to ~/.jaavis/backups/"""
    if not os.path.exists(file_path): return

    backup_dir = os.path.join(JAAVIS_HOME, "backups")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    filename = os.path.basename(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{filename}.{timestamp}.bak")

    shutil.copy2(file_path, backup_path)
    return backup_path

def harvest_skill(doc_path=None):
    lib_path = get_active_library_path()
    print(f"{MAGENTA}🌾 Jaavis Harvest Protocol ({get_current_persona_name()}){RESET}")
    print("-----------------------------------------------------")

    # Smart Harvest: Pre-fill from doc OR Draft Overwrite
    defaults = {}
    draft_mode = False
    existing_skill_path = None

    if doc_path and os.path.exists(doc_path):
        # Check if this is a Jaavis Draft (Metadata check)
        draft_title = get_skill_metadata(doc_path)

        if draft_title:
            print(f"{CYAN}📜 Detected Draft Skill: '{draft_title}'{RESET}")
            # Try to find the ORIGINAL skill to overwrite
            for root, dirs, files in os.walk(lib_path):
                for f in files:
                    # Match by Title via metadata read? Too slow.
                    # Match by filename match (draft is usually name.bs.md or just name.md)
                    # Let's rely on User Confirmation or filename heuristic

                    # Heuristic: If doc_path is "deploy_react.bs.md", look for "deploy_react.md"
                    clean_name = os.path.basename(doc_path).replace(".bs.md", ".md")
                    if f == clean_name:
                        existing_skill_path = os.path.join(root, f)
                        break
                if existing_skill_path: break

            if existing_skill_path:
                print(f"{YELLOW}⚠️  Found existing skill: {existing_skill_path}{RESET}")

                # Show Diff
                print(f"\n{BOLD}Diff Preview:{RESET}")
                try:
                    subprocess.run(["diff", "--color", "-u", existing_skill_path, doc_path])
                except Exception:
                    print(" (diff command failed, showing raw paths)")

                confirm = input(f"\n{RED}Overwrite '{os.path.basename(existing_skill_path)}' with this draft? (y/N): {RESET}").strip().lower()

                if confirm == 'y':
                    # Atomic Swap
                    backup = backup_skill(existing_skill_path)
                    print(f"{GREY}📦 Backup saved to {backup}{RESET}")

                    shutil.copy2(doc_path, existing_skill_path)
                    print(f"{GREEN}✔ Skill updated successfully!{RESET}")

                    # Optional: Delete draft?
                    rm_draft = input(f"{GREY}Delete draft file? (y/N): {RESET}").strip().lower()
                    if rm_draft == 'y':
                        os.remove(doc_path)
                        print(f"{GREY}Draft deleted.{RESET}")
                    return
                else:
                    print("Overwrite cancelled. Proceeding to normal harvest...")

        # If not draft overwrite, parse as doc
        print(f"[bold cyan]📄 Parsing documentation: {doc_path}...[/bold cyan]")
        parsed = parse_markdown_doc(doc_path)
        if parsed and parsed.get("name"):
            defaults = parsed
            print(f"  [green]✔ Found:[/green] {defaults.get('name')} | {defaults.get('description')}")
        else:
             print(f"  [red]✘ Failed to parse doc or file not found.[/red]")

    # Template might still be in default or dynamic?
    # For now assume template is in default
    if not os.path.exists(TEMPLATE_PATH):
        print(f"{RED}Error: TEMPLATE_SKILL.md not found at {TEMPLATE_PATH}!{RESET}")
        return

    # 1. Interactive Inputs
    try:
        def_name = defaults.get("name", "")
        skill_name = input(f"{CYAN}? What is the name of this skill? (e.g., 'glass-card') [{def_name}]: {RESET}").strip() or def_name
        if not skill_name:
            print(f"{RED}Aborted.{RESET}")
            return

        # Auto-detect or ask for Deployment
        is_deploy = False
        if "deploy" in skill_name.lower():
            is_deploy = True
        else:
            is_deploy_in = input(f"{CYAN}? Is this a Deployment Strategy? (y/N): {RESET}").strip().lower()
            if is_deploy_in == 'y': is_deploy = True

        if is_deploy:
            domain = "devops"
            # Auto-prefix naming
            if not skill_name.lower().startswith("deploy"):
                skill_name = f"Deploy {skill_name}"
            print(f"{GREEN}   → Auto-categorized as '{domain}' and prefixed as '{skill_name}'{RESET}")
        else:
            domain = input(f"{CYAN}? Domain (e.g. ui, backend, devops): {RESET}").strip().lower()
            # Default to 'misc' only if empty
            if not domain:
                domain = 'misc'

        def_desc = defaults.get("description", "")
        description = input(f"{CYAN}? Description (short summary) [{def_desc}]: {RESET}").strip() or def_desc
        def_grade = defaults.get("grade", "B")
        grade = input(f"{CYAN}? Grade (A/B/C) [{def_grade}]: {RESET}").strip().upper()
        if not grade: grade = def_grade

        def_pros = defaults.get("pros", "")
        pros_input = input(f"{CYAN}? Pros (comma separated) [{def_pros}]: {RESET}").strip() or def_pros

        def_cons = defaults.get("cons", "")
        cons_input = input(f"{CYAN}? Cons (comma separated) [{def_cons}]: {RESET}").strip() or def_cons

        # Sanitize filename
        safe_name = skill_name.lower().replace(" ", "_") # deploying_react -> deploy_react
        # Ensure deploy prefix uses underscore for filename convention
        if is_deploy and not safe_name.startswith("deploy_"):
            safe_name = safe_name.replace("deploy-", "deploy_").replace("deploy", "deploy_")

        filename = safe_name + ".md"
        # Path adjustment: Skills live in library/skills/[domain]
        target_dir = os.path.join(lib_path, "skills", domain)
        target_path = os.path.join(target_dir, filename)

        # 2. Prepare Directory
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # 3. Create File from Template
        with open(TEMPLATE_PATH, 'r') as t:
            template_content = t.read()

        # Simple replacement of placeholders
        new_content = template_content.replace("[Skill Name]", skill_name)
        new_content = new_content.replace("[e.g. Backend, UI, DevOps]", domain)
        new_content = new_content.replace("[Description]", description)
        new_content = new_content.replace("[Grade]", grade)

        pros_list = "\n".join([f"  - \"{p.strip()}\"" for p in pros_input.split(",") if p.strip()]) if pros_input else "  - \"Standard Solution\""
        cons_list = "\n".join([f"  - \"{c.strip()}\"" for c in cons_input.split(",") if c.strip()]) if cons_input else "  - \"None identified\""

        new_content = new_content.replace("[Pros List]", pros_list)
        new_content = new_content.replace("[Cons List]", cons_list)


        snippet = defaults.get("snippet", "")
        if snippet:
             new_content = new_content.replace("(Paste your code snippet here)", snippet)

        if os.path.exists(target_path):
            overwrite = input(f"{YELLOW}! Skill '{filename}' exists. Overwrite? (y/N): {RESET}")
            if overwrite.lower() != 'y':
                print("Aborted.")
                return

        with open(target_path, 'w') as f:
            f.write(new_content)

        print(f"\n{GREEN}✅ Skill Harvested!{RESET}")
        print(f"   Location: {target_path}")
        print(f"   Action: Open this file and paste your code snippet.")

        # Auto-open
        print(f"\n{CYAN}? Open in editor now?{RESET}")
        print(f"  [1] VS Code (default)")
        print(f"  [2] Nano (terminal)")
        print(f"  [n] No")

        choice = input(f"{CYAN}Select [1]: {RESET}").strip().lower()

        import subprocess
        import shutil
        if choice == '' or choice == '1':
             if shutil.which('code'):
                 subprocess.call(['code', target_path])
             elif sys.platform == 'darwin':
                 # Fallback to 'open' on macOS which usually opens default editor (VS Code)
                 subprocess.call(['open', target_path])
             else:
                 print("VS Code not found in PATH. Trying nano...")
                 subprocess.call(['nano', target_path])
        elif choice == '2' or choice == 'nano':
             subprocess.call(['nano', target_path])

    except KeyboardInterrupt:
        print(f"\n{RED}Operation Cancelled.{RESET}")

# ==========================================
# MERGE LOGIC (Blueprint)
# ==========================================
def merge_skills():
    """Merge two skills (Frontend + Backend) into a unified blueprint"""
    try:
        from rich.console import Console
        from rich.prompt import Prompt
        from rich.panel import Panel
        from rich.table import Table
        import json

        console = Console()
        console = Console()
        console.print(Panel.fit("[bold magenta]🧬 Jaavis Blueprint Merge[/bold magenta]", border_style="magenta"))
        console.print("[dim]Create a unified project from separate Frontend and Backend skills.[/dim]\n")

        # 0.5 Selection of Library Source
        config = load_config()
        current_p = config.get("current_persona", "programmer")
        personas_dict = config.get("personas", {})

        # Build options
        options = [f"Active Persona ({current_p})", "All Combined"]
        for p in sorted(personas_dict.keys()):
            options.append(f"Persona: {p}")

        idx = interactive_menu("Select Library Source for Skills", options)
        choice = options[idx]

        lib_paths = []
        if choice.startswith("Active Persona"):
            p_path = personas_dict.get(current_p, {}).get("path", DEFAULT_LIBRARY_PATH)
            lib_paths.append(p_path)
        elif choice == "All Combined":
            for p in personas_dict:
                p_path = personas_dict[p].get("path")
                if p_path: lib_paths.append(p_path)
        else:
            p_name = choice.replace("Persona: ", "")
            p_path = personas_dict.get(p_name, {}).get("path")
            if p_path: lib_paths.append(p_path)

        if not lib_paths:
            lib_paths = [DEFAULT_LIBRARY_PATH]

        # 0. Ensure Project Init
        if not os.path.exists(os.path.join(os.getcwd(), ".jaavisrc")):
            console.print("[yellow]Project not initialized. Running 'jaavis init' first...[/yellow]")
            init_project()

        # 1. Tech Stack Advisor (Comparison Table)
        console.print("\n[bold cyan]💡 Tech Stack Advisor[/bold cyan]")

        all_skills = {} # name -> metadata

        # Recursive Scan and Parse
        with console.status("[bold cyan]Scanning library for skills...") as status:
            for lib_path in lib_paths:
                if not os.path.exists(lib_path): continue
                for root, dirs, files in os.walk(lib_path):
                    for f in files:
                        if f.endswith(".md") and f != "TEMPLATE_SKILL.md":
                            path = os.path.join(root, f)
                            try:
                                with open(path, 'r') as file:
                                    content = file.read()
                                    meta = parse_frontmatter(content)
                                    if meta:
                                        skill_id = f.replace(".md", "")
                                        # Deduplicate by using first-found in priority or just combining
                                        if skill_id not in all_skills:
                                            all_skills[skill_id] = meta
                                            all_skills[skill_id]['path'] = path
                            except:
                                continue

        if not all_skills:
            console.print("[red]No skills with valid metadata found in library.[/red]")
            return

        # Display Comparison Table
        table = Table(title="Available Skills", show_header=True, header_style="bold magenta", box=None)
        table.add_column("Skill ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="white")
        table.add_column("Grade", style="yellow")
        table.add_column("Pros", style="blue")
        table.add_column("Cons", style="red")

        # Sort by Grade
        for skill_id, meta in sorted(all_skills.items(), key=lambda item: str(item[1].get('grade', 'Z'))):
            # Safe string conversion for all fields
            skill_name = str(meta.get('name', skill_id))
            skill_desc = str(meta.get('description', 'No description'))
            skill_grade = str(meta.get('grade', '-'))
            pros = ", ".join(meta.get('pros', [])) if isinstance(meta.get('pros'), list) else str(meta.get('pros', ''))
            cons = ", ".join(meta.get('cons', [])) if isinstance(meta.get('cons'), list) else str(meta.get('cons', ''))

            table.add_row(
                skill_id,
                skill_name,
                skill_desc,
                skill_grade,
                pros,
                cons
            )

        console.print(table)
        console.print("\n")

        # 2. Select Frontend
        console.print("\n[bold cyan]1. Select Frontend Skill[/bold cyan]")
        frontend_options = [sid for sid, m in all_skills.items() if 'frontend' in [t.lower() for t in m.get('tags', [])] or 'ui' in [t.lower() for t in m.get('tags', [])]]

        if not frontend_options:
            frontend_options = sorted(all_skills.keys())

        idx = interactive_menu("Choose Frontend", frontend_options)
        frontend_choice = frontend_options[idx]
        console.print(f"[green]✔ Selected:[/green] {frontend_choice}")

        # 3. Select Backend
        console.print("\n[bold cyan]2. Select Backend Skill[/bold cyan]")
        backend_options = [sid for sid, m in all_skills.items() if 'backend' in [t.lower() for t in m.get('tags', [])] or 'api' in [t.lower() for t in m.get('tags', [])]]

        if not backend_options:
            backend_options = sorted(all_skills.keys())
        backend_options.append("None (Frontend Only)")

        idx = interactive_menu("Choose Backend", backend_options)
        if idx == len(backend_options) - 1:
            backend_choice = None
            console.print("[dim]Backend skipped.[/dim]")
        else:
            backend_choice = backend_options[idx]
            console.print(f"[green]✔ Selected:[/green] {backend_choice}")

        # 4. Update .jaavisrc (Blueprint Definition)
        config = load_config_local()
        config["type"] = "blueprint"
        config["frontend"] = frontend_choice
        if backend_choice:
            config["backend"] = backend_choice

        with open(".jaavisrc", "w") as f:
            json.dump(config, f, indent=2)

        # 5. Merge Execution (Apply Skills)
        console.print(f"\n[bold magenta]🚀 Merging Blueprint...[/bold magenta]")

        # Apply Frontend
        console.print(f"\n[cyan]Applying Frontend: {frontend_choice}[/cyan]")
        apply_skill(frontend_choice, context={"target_dir": "apps/web"})

        # Apply Backend
        if backend_choice:
            console.print(f"\n[cyan]Applying Backend: {backend_choice}[/cyan]")
            apply_skill(backend_choice, context={"target_dir": "apps/api"})

        console.print("\n[green]Merge Sequence Completed.[/green]")

        # 6. Setup / Post-Install
        if Prompt.ask("\nRun automated setup (npm install & build)?", choices=["y", "n"], default="y") == "y":
            console.print("\n[bold yellow]⚙️  Running Setup...[/bold yellow]")

            # Frontend Setup
            if os.path.exists("apps/web/package.json"):
                console.print("  • Frontend: Installing dependencies...")
                # Run with live output instead of silent blocking
                subprocess.run("cd apps/web && npm install", shell=True, executable='/bin/zsh')

            # Backend/Docker Setup
            backend_compose_file = None
            if os.path.exists("apps/api/compose.yaml"):
                backend_compose_file = "apps/api/compose.yaml"
            elif os.path.exists("apps/api/docker-compose.yml"):
                backend_compose_file = "apps/api/docker-compose.yml"

            if backend_compose_file:
                console.print(f"  • Docker: Linking backend ({backend_compose_file})...")
                with open("docker-compose.yml", "w") as f:
                    f.write(f"# One-Army Docker Compose\n# Root Orchestrator\ninclude:\n  - {backend_compose_file}\n")

            if os.path.exists("docker-compose.yml") or os.path.exists("docker-compose.yaml"):
                console.print("  • Docker: Building containers...")
                subprocess.run("docker compose build", shell=True, executable='/bin/zsh')

            console.print("[green]✨ Blueprint Setup Complete![/green]")

    except Exception as e:
        print(f"{RED}Error during merge: {e}{RESET}")

# ==========================================
# CLI HELPERS
# ==========================================
def init_project():
    """Scaffold One-Army Directory Structure & Config"""
    try:
        from rich.console import Console
        from rich.prompt import Prompt
        import json

        console = Console()

        structure = [
            "apps/web",
            "apps/mobile",
            "packages/ui",
            "packages/config",
            "docker"
        ]

        console.print("[bold cyan]🚀 Initializing One-Army Protocol...[/bold cyan]")

        # 1. Directory Structure
        for p in structure:
            path = os.path.join(os.getcwd(), p)
            if not os.path.exists(path):
                os.makedirs(path)
                console.print(f"  [green]✔ Created:[/green] {p}")
            else:
                console.print(f"  [yellow]• Exists:[/yellow]  {p}")



        # 2. Docker Compose
        docker_path = os.path.join(os.getcwd(), "docker-compose.yml")
        if not os.path.exists(docker_path):
            with open(docker_path, 'w') as f:
                f.write("# One-Army Docker Compose\n# services:\n#   (services will be added here)\n")
            console.print("  [green]✔ Created:[/green] docker-compose.yml")

        # 3. Package.json (One-Army Scripts)
        pkg_path = os.path.join(os.getcwd(), "package.json")
        if not os.path.exists(pkg_path):
            pkg_data = {
                "name": os.path.basename(os.getcwd()),
                "version": "1.0.0",
                "scripts": {
                    "start": "echo 'Run start script'",
                    "build": "echo 'Run build script'",
                    "dev": "echo 'Run dev script'",
                    "test": "echo 'Tests Passed'",
                    "test:e2e": "echo 'E2E Tests Passed'",
                    "audit": "echo 'Security Audit Passed'"
                },
                "dependencies": {},
                "devDependencies": {}
            }
            with open(pkg_path, 'w') as f:
                json.dump(pkg_data, f, indent=2)
            console.print("  [green]✔ Created:[/green] package.json (with default scripts)")
        else:
            console.print("  [yellow]• Exists:[/yellow]  package.json")

        console.print("\n[bold yellow]📋 Project Configuration[/bold yellow]")

        # 3. Grade Selection
        console.print("Select Project Grade (affects deployment strictness):")
        console.print("  [bold green]C (Skirmish)[/bold green]: Speed > Quality (Hackathons)")
        console.print("  [bold blue]B (Campaign)[/bold blue]: Balanced (Standard SaaS) [dim][Default][/dim]")
        console.print("  [bold red]A (Fortress)[/bold red]: Quality > Speed (Enterprise/Fintech)")

        grade_choice = Prompt.ask("Choose Grade", choices=["A", "B", "C", "a", "b", "c"]).upper()

        config = {
            "grade": grade_choice,
            "project_name": os.path.basename(os.getcwd()),
            "created_at": str(datetime.now())
        }

        # 4. Save .jaavisrc
        config_path = os.path.join(os.getcwd(), ".jaavisrc")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        console.print(f"  [green]✔ Saved:[/green] .jaavisrc (Grade {grade_choice})")

        # 5. Documentation Scaffolding (Grade Aware)
        console.print("\n[bold cyan]📚 Scaffolding Documentation...[/bold cyan]")

        # Base Structure (Grades B & C)
        docs_structure = {
            "docs": ["00-start-here.md"],
            "docs/architecture": ["overview.md"],
            "docs/architecture/decisions": ["001-init.md"],
            "docs/guides": ["deployment.md", "debugging.md"],
            "docs/reference": ["api.md", "database.md"]
        }

        # Grade A Extensions (The Full Suite)
        if grade_choice == "A":
             docs_structure["docs/architecture"].extend([
                 "requirements.md", "permissions.md", "navigation.md"
             ])
             docs_structure["docs/guides"].extend([
                 "environment-config.md", "data-seeding.md", "ui-design-system.md",
                 "error-handling.md", "integration-guide.md", "security-guidelines.md",
                 "accessibility.md"
             ])
             docs_structure["docs/reference"].extend([
                 "components.md", "file-changes.md", "testing.md", "hooks-utilities.md",
                 "glossary.md"
             ])

        for folder, files in docs_structure.items():
            path = os.path.join(os.getcwd(), folder)
            if not os.path.exists(path):
                os.makedirs(path)

            for f in files:
                filepath = os.path.join(path, f)
                if not os.path.exists(filepath):
                    with open(filepath, 'w') as doc:
                        doc.write(f"# {f.replace('.md', '').capitalize()}\n\n*Generated by Jaavis One-Army Protocol*")
        console.print("[bold green]✨ Project Scaffolding Complete.[/bold green]")

    except ImportError:
        print("Rich not installed. Run 'pip install rich'")

def check_k8s_connection():
    """Checks if kubectl can connect to a running cluster"""
    try:
        # Silently check if the cluster is reachable (timeout to avoid hanging)
        subprocess.check_output(["kubectl", "cluster-info"], stderr=subprocess.STDOUT, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

def check_system(full_scan=True):
    """Performs system health checks. Returns a dict of results."""
    results = {
        "tools": {},
        "config": {},
        "integrations": {},
        "installation": {},
        "all_passed": True
    }

    # 0. Check Installation (Homebrew)
    results["installation"]["Homebrew Managed"] = False
    if shutil.which("brew"):
        try:
            # Check if jaavis is in brew list
            res = subprocess.run(["brew", "list", "--formula"], capture_output=True, text=True)
            if "jaavis" in res.stdout:
                results["installation"]["Homebrew Managed"] = True
        except:
            pass

    # Path of executable
    results["installation"]["Binary Path"] = sys.argv[0]

    # 1. Check Tools
    tools = ["git", "node", "npm"]
    for tool in tools:
        if shutil.which(tool):
            results["tools"][tool] = True
        else:
            results["tools"][tool] = False
            results["all_passed"] = False

    # 2. Check Config
    cwd = os.getcwd()
    results["config"][".jaavisrc"] = os.path.exists(os.path.join(cwd, ".jaavisrc"))
    results["config"][".env"] = os.path.exists(os.path.join(cwd, ".env"))

    if not results["config"][".jaavisrc"]: results["all_passed"] = False

    # 3. Check Integrations (Links)
    results["integrations"]["Vercel Linked"] = os.path.exists(os.path.join(cwd, ".vercel"))
    results["integrations"]["Supabase Linked"] = os.path.exists(os.path.join(cwd, "supabase", "config.toml")) or os.path.exists(os.path.join(cwd, "supabase", "config.json")) # basic check

    # 4. Check Blueprint (Merge)
    config_data = load_config_local() # Need to load local .jaavisrc
    if config_data.get("type") == "blueprint":
        if "frontend" in config_data:
            fe_path = os.path.join(cwd, "apps/web")
            if not os.path.exists(fe_path):
                results["integrations"]["Frontend (Blueprint)"] = False
                results["all_passed"] = False
            else:
                 results["integrations"]["Frontend (Blueprint)"] = True

        if "backend" in config_data:
             be_path = os.path.join(cwd, "apps/api")
             if not os.path.exists(be_path):
                 results["integrations"]["Backend (Blueprint)"] = False
                 results["all_passed"] = False
             else:
                 results["integrations"]["Backend (Blueprint)"] = True

    return results

def load_config_local():
    """Load local .jaavisrc project config"""
    config_path = os.path.join(os.getcwd(), ".jaavisrc")
    if os.path.exists(config_path):
        try:
             with open(config_path, 'r') as f:
                 return json.load(f)
        except:
             return {}
    return {}

def run_doctor():
    """CLI Command: Check system health"""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        console = Console()

        console.print("[bold cyan]🩺 Jaavis Doctor[/bold cyan]")
        results = check_system()

        # Installation Table
        table = Table(show_header=False, box=None)
        table.add_column("Item")
        table.add_column("Status")

        console.print("\n[bold]📦 Installation[/bold]")
        is_brew = results["installation"]["Homebrew Managed"]
        brew_status = "[green]Yes (Brew)[/green]" if is_brew else "[yellow]Manual Symlink[/yellow]"
        table.add_row("  Managed", brew_status)
        table.add_row("  Binary", f"[dim]{results['installation']['Binary Path']}[/dim]")
        console.print(table)

        # Tools Table
        table = Table(show_header=False, box=None)
        table.add_column("Item")
        table.add_column("Status")

        console.print("\n[bold]🛠  Tools[/bold]")
        for tool, passed in results["tools"].items():
            icon = "[green]✔[/green]" if passed else "[red]✘[/red]"
            msg = f"[dim]Found[/dim]" if passed else "[red]Missing[/red]"
            table.add_row(f"  {tool}", f"{icon}  {msg}")
        console.print(table)

        # Config Table
        table = Table(show_header=False, box=None)
        table.add_column("Item")
        table.add_column("Status")

        console.print("\n[bold]📂 Configuration[/bold]")
        for conf, passed in results["config"].items():
            icon = "[green]✔[/green]" if passed else "[yellow]![/yellow]"
            msg = f"[dim]Present[/dim]" if passed else "[yellow]Missing[/yellow]"
            table.add_row(f"  {conf}", f"{icon}  {msg}")
        console.print(table)

        # Integrations
        table = Table(show_header=False, box=None)
        table.add_column("Item")
        table.add_column("Status")

        console.print("\n[bold]🔗 Integrations[/bold]")
        for integ, passed in results["integrations"].items():
            icon = "[green]✔[/green]" if passed else "[yellow]![/yellow]"
            msg = f"[dim]Linked[/dim]" if passed else "[yellow]Not Linked[/yellow]"
            table.add_row(f"  {integ}", f"{icon}  {msg}")
        console.print(table)

        # Personas Integrity Check
        console.print("\n[bold]🧠 Persona Integrity[/bold]")
        p_table = Table(show_header=True, header_style="bold magenta", box=None)
        p_table.add_column("Persona", style="cyan")
        p_table.add_column("Path", style="dim white")
        p_table.add_column("Status", style="bold")

        config = load_config()
        personas = config.get("personas", {})
        if "programmer" not in personas:
             personas["programmer"] = {"path": DEFAULT_LIBRARY_PATH}

        for name, p_data in personas.items():
            path = p_data.get("path", "")
            exists = os.path.exists(path)

            if exists:
                status = "[green]Active[/green]"
            else:
                status = "[red]Missing[/red]"
                results["all_passed"] = False # Fail doctor if brain is missing

            p_table.add_row(name, path, status)

        console.print(p_table)

        # Recovery Hint for Missing Personas
        for name, p_data in personas.items():
            path = p_data.get("path", "")
            if not os.path.exists(path):
                 console.print(f"\n[red]⚠️  Critical: Persona '{name}' is missing its library at {path}[/red]")
                 console.print(f"   [yellow]→ If you have a backup/remote, run:[/yellow] git clone <url> {path}")
                 console.print(f"   [yellow]→ Or run:[/yellow] jaavis sync (if remote was configured)")

        if not results["all_passed"]:
             console.print("\n[yellow]⚠️  Issues detected. Run 'jaavis init' or install missing tools.[/yellow]")
        else:
             console.print("\n[green]✨ System Healthy. Ready to deploy.[/green]")

    except ImportError:
        print("Rich not installed.")

def deploy_project():
    """Execute Deployment Pipeline based on Grade (Glass Box & Harvestable)"""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.prompt import Prompt
        import json
        import subprocess

        console = Console()
        lib_path = get_active_library_path()

        # 1. Read Config
        config_path = os.path.join(os.getcwd(), ".jaavisrc")
        if not os.path.exists(config_path):
            console.print("[bold red]❌ Error:[/bold red] .jaavisrc not found. Run 'jaavis init' first.")
            return

        with open(config_path, 'r') as f:
            config = json.load(f)

        grade = config.get("grade", "B")
        project_name = config.get("project_name", "Unknown")

        # 2. Identify Available Strategies
        strategies = []

        # Standard Strategy
        infra_name = "Local"
        if grade == "B": infra_name = "Docker"
        if grade == "A": infra_name = "Kubernetes"

        strategies.append({
            "name": f"{infra_name} (Grade {grade})",
            "type": "standard",
            "grade": grade
        })

        # Harvested Strategies (Scan library/skills/devops for deploy_*.md)
        devops_path = os.path.join(lib_path, "skills", "devops")
        if os.path.exists(devops_path):
            for f in os.listdir(devops_path):
                if f.startswith("deploy_") and f.endswith(".md"):
                    strategies.append({
                        "name": f.replace("deploy_", "").replace(".md", "").replace("_", " ").title() + " (New)",
                        "type": "harvested",
                        "path": os.path.join(devops_path, f)
                    })

        # Custom/Manual Strategy
        strategies.append({"name": "Custom", "type": "manual"})

        # 3. Strategy Selection
        console.print(f"\n[bold cyan]🚀 Deploying {project_name}[/bold cyan]")

        table = Table(title="Available Deployment Strategies", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=4)
        table.add_column("Strategy", style="green")
        table.add_column("Grade", style="yellow")
        table.add_column("Type", style="dim")

        for idx, s in enumerate(strategies):
            grade_display = s.get("grade", "-")
            type_display = s.get("type", "Standard").title()
            table.add_row(str(idx+1), s["name"], grade_display, type_display)

        console.print(table)

        choice_idx = 0
        if len(strategies) > 1:
            choice_str = Prompt.ask("Choose Strategy ID", default="1")
            try:
                choice_idx = int(choice_str) - 1
            except:
                choice_idx = 0

        selected_strategy = strategies[choice_idx] if 0 <= choice_idx < len(strategies) else strategies[0]

        steps = []

        # 4. Resolve Steps based on Strategy
        if selected_strategy["type"] == "standard":
            grade = selected_strategy["grade"]

            # --- PRE-FLIGHT CHECKS ---
            console.print("\n[bold]🩺 Running Pre-Flight Checks...[/bold]")
            health = check_system()
            issues = []

            # Grade B requires Docker
            if grade == "B" and not shutil.which("docker"):
                 issues.append("Docker not installed")

            # Grade A requires Kubectl
            if grade == "A":
                if not shutil.which("kubectl"):
                     issues.append("Kubectl not installed")
                elif not check_k8s_connection():
                     issues.append("Kubernetes Cluster Unreachable (Check Docker Desktop / Minikube)")

            # Common Checks
            if not health["tools"]["npm"]: issues.append("NPM not installed")

            # Supabase Check (B and A)
            if grade in ["B", "A"] and not health["integrations"]["Supabase Linked"]:
                issues.append("Supabase Project probably not linked (check supabase/config)")

            if issues:
                console.print("[yellow]⚠️  Pre-Flight Warnings:[/yellow]")
                for issue in issues:
                    console.print(f"  - {issue}")

                if not Prompt.ask("\n[bold yellow]Continue anyway?[/bold yellow]", choices=["y", "n"], default="n") == "y":
                    console.print("[red]Aborted.[/red]")
                    return
            else:
                 console.print("[green]✔ Checks Passed[/green]")
            # -------------------------

            if grade == "C": # Skirmish (Local execution, keep running)
                # Use screen to detach, or nohup. Screen is standard on Mac/Linux.
                steps = [
                    ("Building Project", "npm run build"),
                    ("Launching Background Service", f"screen -dmS {project_name} npm run start"),
                    ("Start Dev Server", "npm run dev")
                ]
            elif grade == "B": # Campaign (Dockerized)
                steps = [
                    ("Running Unit Tests", "npm test"),
                    ("Building Containers", "docker compose build"),
                    ("Deploying Services", "docker compose up -d"),
                    ("Pushing DB Schema", "npx supabase db push")
                ]
            elif grade == "A": # Fortress (K8s + Audits)
                steps = [
                    ("Running E2E Tests", "npm run test:e2e")
                ]

                # ---------------------------------------------------------
                # DYNAMIC PACKAGE MANAGER DETECTION FOR AUDIT
                # ---------------------------------------------------------
                cwd = os.getcwd()
                audit_cmd = None

                # 1. Check for PNPM
                if os.path.exists(os.path.join(cwd, "pnpm-lock.yaml")):
                    audit_cmd = "pnpm audit"
                # 2. Check for Bun
                elif os.path.exists(os.path.join(cwd, "bun.lockb")):
                    # Bun doesn't have a native audit yet (as of v1.0).
                    # If package-lock.json also exists, fall back to npm.
                    if os.path.exists(os.path.join(cwd, "package-lock.json")):
                        audit_cmd = "npm audit"
                    else:
                        console.print("[yellow]⚠️  Bun detected but no 'bun audit' available. Skipping audit step.[/yellow]")
                        audit_cmd = None
                # 3. Check for Yarn
                elif os.path.exists(os.path.join(cwd, "yarn.lock")):
                    audit_cmd = "yarn audit"
                # 4. Default to NPM (Standard)
                else:
                    # Grade A requires a lockfile. If missing, generate it.
                    if not os.path.exists(os.path.join(cwd, "package-lock.json")):
                         steps.append(("Generating Lockfile (Required for Audit)", "npm i --package-lock-only"))
                    audit_cmd = "npm audit"

                if audit_cmd:
                    steps.append(("Security Audit", audit_cmd))

                # ---------------------------------------------------------

                steps.extend([
                    ("Applying K8s Manifests", "kubectl apply -f k8s/"),
                    ("Migrating DB", "npx supabase migration up")
                ])

        if selected_strategy["type"] == "harvested":
            console.print(f"[bold green]🚀 Launching Harvested Strategy: {selected_strategy['name']}[/bold green]")
            # Use apply_skill for robust execution (handles complex scripts, TTY, etc.)
            # We pass the full path so apply_skill can skip searching.
            # Note: apply_skill currently expects a name, so we pass the name and ensure it finds it.
            # Or we can just read and execute here using the NEW logic from apply_skill.
            # Let's reuse apply_skill logic by calling it directly if possible, or replicating the robust execution.

            # Replicating robust execution for the specific file:
            with open(selected_strategy["path"], 'r') as f:
                content = f.read()

            # Extract blocks
            pattern = r'<!--\s*JAAVIS:EXEC\s*-->\s*```bash\n(.*?)\n```'
            matches = re.findall(pattern, content, re.DOTALL)

            if not matches:
                console.print("[yellow]⚠️  No execution blocks found in skill file.[/yellow]")
                return

            for i, match in enumerate(matches):
                cmd_block = match.strip()
                if not cmd_block: continue

                # Allow {{target_dir}} templating
                cmd_block = cmd_block.replace("{{target_dir}}", ".")

                console.print(f"\n[bold yellow]👉 Executing Block {i+1}/{len(matches)}...[/bold yellow]")

                # Execute as script file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tmp:
                    tmp.write(f"#!/bin/zsh\nset -e\n{cmd_block}")
                    tmp_path = tmp.name

                os.chmod(tmp_path, 0o755)

                try:
                    # Run with TTY support
                    result = subprocess.run(tmp_path, shell=True, executable='/bin/zsh')
                    if result.returncode != 0:
                         console.print(f"[bold red]❌ Block {i+1} Failed (Exit Code {result.returncode})[/bold red]")
                         if not Prompt.ask("Continue anyway?", choices=["y", "n"], default="n") == "y":
                             return
                finally:
                    os.remove(tmp_path)

            console.print("\n[bold green]✅ Deployment Complete![/bold green]")
            return

        elif selected_strategy["type"] == "manual":
            cmd = Prompt.ask("[bold yellow]Enter Command to Run[/bold yellow]")
            steps = [("Manual Execution", cmd)]

        # 5. Glass Box Preview (Standard Only)
        if not steps and selected_strategy["type"] == "standard":
             console.print("[yellow]⚠️  No steps defined for this strategy.[/yellow]")
             return

        if selected_strategy["type"] == "standard":
            table = Table(title="Preview", show_header=True, header_style="bold magenta")
            table.add_column("Step", style="cyan")
            table.add_column("Command", style="green")

            for title, cmd in steps:
                table.add_row(title, cmd)

            console.print(table)

            # 6. Execute / Harvest Prompt
            action = Prompt.ask(
                "\n[bold yellow]? Ready to execute?[/bold yellow]",
                choices=["Yes", "No", "Harvest"],
                default="Yes"
            )

            if action == "No":
                console.print("[red]Aborted.[/red]")
                return

            if action == "Harvest":
                harvest_name = Prompt.ask("[cyan]Name this strategy (e.g. 'fast-deploy')[/cyan]")
                save_harvested_deploy(harvest_name, steps, lib_path)
                console.print(f"[green]✔ Saved as '{harvest_name}'. Continuing execution...[/green]")

            # 7. Execution Loop (Standard)
            for title, cmd in steps:
                console.print(f"\n[bold yellow]👉 {title}[/bold yellow]...")
                result = subprocess.call(cmd, shell=True, executable='/bin/zsh')
                if result != 0:
                    console.print(f"[bold red]❌ Failed at step: {title}[/bold red]")
                    return

            console.print("\n[bold green]✅ Deployment Complete![/bold green]")

    except ImportError:
        print("Rich not installed. Run 'pip install rich'")

def parse_frontmatter(content):
    """Extracts YAML frontmatter from markdown content with native fallback if PyYAML is missing"""
    content = content.strip()
    if not content.startswith("---"):
        return None

    try:
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        yaml_content = parts[1].strip()

        # Try PyYAML if available
        try:
            import yaml
            return yaml.safe_load(yaml_content)
        except ImportError:
            # Native Fallback (Simple YAML subset: key: value)
            meta = {}
            for line in yaml_content.split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    # Handle basic lists [a, b] or simple strings
                    if val.startswith("[") and val.endswith("]"):
                        val = [i.strip().strip("'").strip('"') for i in val[1:-1].split(",")]
                    else:
                        val = val.strip("'").strip('"')
                    meta[key] = val
            return meta
    except Exception as e:
        return None
    return None

def parse_markdown_doc(doc_path):
    """Extract skill details from a markdown documentation file"""
    if not os.path.exists(doc_path):
        return None

    with open(doc_path, 'r') as f:
        content = f.read()

    meta = {
        "name": "",
        "description": "",
        "snippet": "",
        "grade": "B",
        "pros": "",
        "cons": ""
    }

    lines = content.split('\n')

    # 1. Title (H1)
    for line in lines:
        if line.strip().startswith("# "):
            meta["name"] = line.strip().replace("# ", "").strip()
            break

    # 2. Description (First paragraph after title)
    # Simple heuristic: look for first non-empty, non-header line
    for line in lines:
        l = line.strip()
        if l and not l.startswith("#") and not l.startswith("```"):
            meta["description"] = l
            break

    # 3. Code Snippet (First code block)
    if "```" in content:
        try:
            start = content.find("```") + 3
            # Skip language identifier if present
            end_line = content.find("\n", start)
            if end_line != -1:
                start = end_line + 1

            end = content.find("```", start)
            if end != -1:
                meta["snippet"] = content[start:end].strip()
        except:
            pass

    return meta

def save_harvested_deploy(name, steps, lib_path):
    """Saves a deployment strategy as an executable skill"""
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', name).lower()
    filename = f"deploy_{safe_name}.md"
    devops_dir = os.path.join(lib_path, "skills", "devops")

    if not os.path.exists(devops_dir):
        os.makedirs(devops_dir)

    path = os.path.join(devops_dir, filename)

    commands = "\n".join([step[1] for step in steps])

    content = f"""# Deployment: {name}
> Harvested on {datetime.now()}

## Execution Plan
<!-- JAAVIS:EXEC -->
```bash
{commands}
```
"""
    with open(path, 'w') as f:
        f.write(content)


def apply_skill(skill_name, dry_run=False, context=None):
    """Parses and executes bash blocks from a Skill File (Executable Knowledge)"""
    try:
        from rich.console import Console
        from rich.prompt import Prompt
        from rich.panel import Panel
        from rich.syntax import Syntax
        import subprocess
        import re

        console = Console()
        lib_path = get_active_library_path()

        # 1. Find the Skill File (Reuse logic from open_skill)
        target_file = None
        # Direct/Fuzzy Search
        for root, dirs, files in os.walk(lib_path):
            for f in files:
                if f == skill_name or f == f"{skill_name}.md":
                    target_file = os.path.join(root, f)
                    break
                if skill_name.lower() in f.lower() and f.endswith(".md"):
                     target_file = os.path.join(root, f)
                     break
            if target_file: break

        if not target_file:
            console.print(f"[bold red]❌ Error:[/bold red] Skill '{skill_name}' not found.")
            return

        console.print(f"[bold cyan]🔍 Found Skill:[/bold cyan] {target_file}")

        # 2. Parse Executable Blocks
        with open(target_file, 'r') as f:
            content = f.read()

        # Regex to find <!-- JAAVIS:EXEC --> followed by ```bash ... ```
        # Handles multiline content inside the code block
        pattern = r'<!--\s*JAAVIS:EXEC\s*-->\s*```bash\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)

        if not matches:
            console.print("[yellow]⚠️  No key '<!-- JAAVIS:EXEC -->' executable blocks found in this skill.[/yellow]")
            return

        console.print(f"[bold blue]🚀 Found {len(matches)} execution blocks.[/bold blue]")

        # 3. Execution Loop
        for i, match in enumerate(matches, 1):
            cmd_block = match.strip()

            # TEMPLATING: Replace placeholders
            if context:
                for key, val in context.items():
                    cmd_block = cmd_block.replace(f"{{{{{key}}}}}", val)

            console.print(f"\n[bold yellow]Block {i}/{len(matches)}:[/bold yellow]")
            console.print(Panel(cmd_block, title="Script Content", border_style="blue"))

            if dry_run:
                console.print("[dim](Dry Run: Skipped)[/dim]")
                continue

            # Execute as a single script to preserve context (variables, if/else)
            if Prompt.ask("Execute this block?", choices=["y", "n"], default="y") == "y":
                # Create a temporary script file to handle complex syntax
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tmp:
                    tmp.write(f"#!/bin/zsh\nset -e\n{cmd_block}")
                    tmp_path = tmp.name

                # Make executable
                os.chmod(tmp_path, 0o755)

                try:
                    # Run it
                    process = subprocess.run(tmp_path, shell=True, executable='/bin/zsh')

                    if process.returncode == 0:
                        console.print(f"  [green]✔ Block {i} Success[/green]")
                    else:
                        console.print(f"[bold red]❌ Block {i} Failed (Exit Code {process.returncode})[/bold red]")
                        if Prompt.ask("Continue anyway?", choices=["y", "n"], default="n") == "n":
                            break
                finally:
                    # Cleanup
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            else:
                console.print("[dim]Skipped by user.[/dim]")

        console.print("\n[bold green]✅ Skill Applied Successfully![/bold green]")

    except ImportError:
        print("Rich not installed. Run 'pip install rich'")


def link_remote_library(lib_path, remote_url):
    """Initializes git in the library folder and sets up the remote."""
    try:
        # Check if already a git repo
        if not os.path.exists(os.path.join(lib_path, ".git")):
            print(f"{CYAN}Initializing Git repository in {lib_path}...{RESET}")
            subprocess.run(["git", "init"], cwd=lib_path, check=True, capture_output=True)

        # Add remote
        result = subprocess.run(["git", "remote", "get-url", "origin"], cwd=lib_path, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{YELLOW}Updating existing remote 'origin' to {remote_url}...{RESET}")
            subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=lib_path, check=True)
        else:
            print(f"{GREEN}Adding remote 'origin' {remote_url}...{RESET}")
            subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=lib_path, check=True)

        print(f"{GREEN}✔ Library linked to central hub.{RESET}")
        return True
    except Exception as e:
        print(f"{RED}Error linking remote: {e}{RESET}")
        return False

def sync_skills():
    """CLI Command: Execute Git pull to sync skills."""
    lib_path = get_active_library_path()
    persona = get_current_persona_name()

    print(f"\n{MAGENTA}🔄 Syncing Skills for {persona}{RESET}")
    print(f"{GREY}Path: {lib_path}{RESET}")

    # 1. Check if library exists (Split Architecture Support)
    if not os.path.exists(lib_path):
        print(f"{YELLOW}⚠️  No Skill Library found at {lib_path}{RESET}")
        print(f"{CYAN}Initializing your Knowledge Base (Brain)...{RESET}")

        try:
            print(f"{CYAN}? Choose Source:{RESET}")
            print(f"  [1] Official Jaavis Library (Recommended)")
            print(f"  [2] Custom Git Repository")

            choice = input(f"{CYAN}Select [1]: {RESET}").strip().lower()

            remote_url = ""
            if choice == '' or choice == '1':
                remote_url = "https://github.com/ponli550/JaavisCLI.git"
            elif choice == '2':
                remote_url = input(f"{CYAN}? Remote Git URL: {RESET}").strip()
            else:
                print("Aborted.")
                return

            if remote_url:
                parent_dir = os.path.dirname(lib_path)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)

                print(f"{CYAN}Cloning from {remote_url}...{RESET}")
                subprocess.run(["git", "clone", remote_url, lib_path], check=True)
                print(f"{GREEN}✔ Library initialized successfully!{RESET}")
                return
            else:
                 print("No URL provided.")
                 return
        except Exception as e:
             print(f"{RED}Error initializing library: {e}{RESET}")
             return

    # 2. Check if git repository (Existing Library)
    if not os.path.exists(os.path.join(lib_path, ".git")):
        print(f"{YELLOW}Warning: This library is not linked to a remote hub.{RESET}")
        try:
            print(f"{CYAN}? Choose Sync Source:{RESET}")
            print(f"  [1] Official Jaavis Library (Recommended)")
            print(f"  [2] Custom GitHub/Git Repository ( If you want to sync your own library)")
            print(f"  [n] Cancel")

            choice = input(f"{CYAN}Select [1]: {RESET}").strip().lower()

            remote_url = ""
            if choice == '' or choice == '1':
                remote_url = "https://github.com/ponli550/JaavisCLI.git"
            elif choice == '2':
                remote_url = input(f"{CYAN}? Remote Git URL: {RESET}").strip()
            else:
                print(f"{YELLOW}Sync aborted.{RESET}")
                return

            if remote_url:
                if not link_remote_library(lib_path, remote_url):
                    return
            else:
                print(f"{RED}No URL provided. Aborting.{RESET}")
                return
        except KeyboardInterrupt:
            print(f"\n{RED}Aborted.{RESET}")
            return

            print(f"\n{RED}Aborted.{RESET}")
            return

    # 2. Pre-Sync Safety Check (Dirty State)
    needs_pop = False
    status_output = ""
    try:
        # Check for uncommitted changes
        status_output = subprocess.run(["git", "status", "--porcelain"], cwd=lib_path, capture_output=True, text=True).stdout.strip()
    except:
        pass

    if status_output:
        print(f"\n{YELLOW}⚠️  Uncommitted changes detected in library:{RESET}")
        # Show brief status
        print(subprocess.run(["git", "status", "-s"], cwd=lib_path, capture_output=True, text=True).stdout)

        print(f"{CYAN}? How do you want to proceed?{RESET}")
        options = [
            "Stash changes, Sync, then Pop stash (Recommended)",
            "Commit changes, then Sync (Merge)",
            "Abort (I will fix it manually)"
        ]
        choice = interactive_menu("Select Action", options)

        if choice == 0: # Stash
            print(f"{YELLOW}Stashing changes...{RESET}")
            subprocess.run(["git", "stash"], cwd=lib_path, check=True)
            needs_pop = True
        elif choice == 1: # Commit
            msg = input(f"{CYAN}? Commit Message: {RESET}").strip()
            if not msg: msg = "Auto-save before sync"
            subprocess.run(["git", "add", "."], cwd=lib_path, check=True)
            subprocess.run(["git", "commit", "-m", msg], cwd=lib_path, check=True)
            needs_pop = False
        else:
            print("Aborted.")
            return

    # 3. Execute Sync
    try:
        print(f"{CYAN}Pulling latest updates...{RESET}")
        subprocess.run(["git", "fetch", "origin"], cwd=lib_path, check=True, capture_output=True)

        status = subprocess.run(["git", "status", "-uno"], cwd=lib_path, capture_output=True, text=True).stdout
        if "Your branch is up to date" in status:
            print(f"{GREEN}✔ Skills are already up to date.{RESET}")
            return

        result = subprocess.run(["git", "pull", "origin", "main"], cwd=lib_path, capture_output=True, text=True)
        if result.returncode != 0:
            result = subprocess.run(["git", "pull", "origin", "master"], cwd=lib_path, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"{GREEN}✔ Sync complete!{RESET}")
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "|" in line or "insertions" in line:
                         if line.strip(): print(f"  {line.strip()}")
        else:
            print(f"{RED}Error during sync: {result.stderr.strip()}{RESET}")

        if result.returncode == 0 and needs_pop:
             print(f"{YELLOW}Restoring stashed changes...{RESET}")
             subprocess.run(["git", "stash", "pop"], cwd=lib_path)

    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")


    # Reset update flag after a successful sync attempt
    config = load_config()
    if "auto_sync" in config:
        config["auto_sync"]["updates_pending"] = False
        save_config(config)

def push_library():
    """CLI Command: Push local library changes to remote (Auto-Init & Smart Sync)."""
    lib_path = get_active_library_path()
    persona = get_current_persona_name()

    print(f"\n{MAGENTA}⬆️  Pushing Skills for {persona}{RESET}")
    print(f"{GREY}Path: {lib_path}{RESET}")

    # 1. Auto-Initialize Git
    if not os.path.exists(os.path.join(lib_path, ".git")):
        print(f"{YELLOW}⚠️  Library is not a git repository. Initializing...{RESET}")
        try:
            subprocess.run(["git", "init"], cwd=lib_path, check=True)
            subprocess.run(["git", "branch", "-M", "main"], cwd=lib_path, check=True)
            print(f"{GREEN}✔ Git initialized.{RESET}")
        except Exception as e:
            print(f"{RED}Failed to init git: {e}{RESET}")
            return

    # 2. Check Remote Configuration
    try:
        remote_check = subprocess.run(["git", "remote", "-v"], cwd=lib_path, capture_output=True, text=True)
        if "origin" not in remote_check.stdout:
            print(f"{YELLOW}⚠️  No remote 'origin' configured.{RESET}")
            print(f"{GREY}To back up your skills, create a blank repo on GitHub/GitLab.{RESET}")
            url = input(f"{CYAN}? Paste Remote Repository URL: {RESET}").strip()
            if url:
                subprocess.run(["git", "remote", "add", "origin", url], cwd=lib_path, check=True)
                print(f"{GREEN}✔ Remote 'origin' added.{RESET}")
            else:
                print("Skipping remote configuration (local only).")
    except Exception as e:
        print(f"{RED}Git Remote Error: {e}{RESET}")
        return

    # 3. Smart Sync (Pull befores Push)
    # Only pull if we have a remote and commits exist
    has_remote = "origin" in subprocess.run(["git", "remote"], cwd=lib_path, capture_output=True, text=True).stdout
    if has_remote:
        print(f"{CYAN}🔄 Syncing with remote (Pulling)...{RESET}")
        # We allow this to fail (e.g. empty remote) without stopping
        subprocess.run(["git", "pull", "origin", "main", "--rebase"], cwd=lib_path, capture_output=True)

    # 4. Check Status & Commit
    status_output = subprocess.run(["git", "status", "--porcelain"], cwd=lib_path, capture_output=True, text=True).stdout.strip()

    if status_output:
        print(f"\n{YELLOW}📝 Uncommitted changes detected:{RESET}")
        print(subprocess.run(["git", "status", "-s"], cwd=lib_path, capture_output=True, text=True).stdout)

        if input(f"{CYAN}? Commit and Push? (Y/n): {RESET}").strip().lower() != 'n':
            msg = input(f"{CYAN}? Commit Message: {RESET}").strip()
            if not msg: msg = f"Update skills ({datetime.now().strftime('%Y-%m-%d %H:%M')})"

            subprocess.run(["git", "add", "."], cwd=lib_path, check=True)
            subprocess.run(["git", "commit", "-m", msg], cwd=lib_path, check=True)
        else:
            print("Aborted.")
            return
    else:
        print(f"{GREEN}✔ Working directory clean.{RESET}")

    # 5. Push to Remote
    if has_remote:
        print(f"{CYAN}⬆️  Pushing to origin...{RESET}")
        try:
            # Try main then master
            result = subprocess.run(["git", "push", "origin", "main"], cwd=lib_path, capture_output=True, text=True)
            if result.returncode != 0:
                 result = subprocess.run(["git", "push", "origin", "master"], cwd=lib_path, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"{GREEN}✔ Successfully backed up skills to remote!{RESET}")
            else:
                print(f"{RED}Push failed: {result.stderr.strip()}{RESET}")
                print(f"{GREY}Tip: Check your internet or remote permissions.{RESET}")

        except Exception as e:
            print(f"{RED}Error pushing: {e}{RESET}")
    else:
        print(f"{YELLOW}⚠️  Changes committed locally, but not pushed (No remote).{RESET}")


# Global Update State
SKILL_UPDATES_AVAILABLE = False
APP_UPDATE_AVAILABLE = None # Stores latest version string if available

def check_for_app_updates():
    """Checks GitHub for the latest CLI Release Tag"""
    global APP_UPDATE_AVAILABLE
    config = load_config()

    # Throttling (check app update once every 24h)
    last_app_check = config.get("auto_sync", {}).get("last_app_check")
    if last_app_check:
        try:
            last_check_dt = datetime.fromisoformat(last_app_check)
            if (datetime.now() - last_check_dt).total_seconds() < 86400:
                return
        except:
            pass

    try:
        import urllib.request
        import json

        url = "https://api.github.com/repos/ponli550/JaavisCLI/tags"
        req = urllib.request.Request(url, headers={'User-Agent': 'JaavisCLI'})

        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            if data and isinstance(data, list) and len(data) > 0:
                latest_tag = data[0].get("name", "").replace("v", "")

                # Simple SemVer compare (assuming simple X.Y.Z)
                # If latest != current, assume update (naive but effective for now)
                if latest_tag != VERSION:
                    APP_UPDATE_AVAILABLE = latest_tag
    except:
        pass

    # Save Check Time
    if "auto_sync" not in config: config["auto_sync"] = {}
    config["auto_sync"]["last_app_check"] = datetime.now().isoformat()
    save_config(config)

def check_for_skill_updates():
    """Background check for skill library updates (throttled to 24h)."""
    global SKILL_UPDATES_AVAILABLE
    config = load_config()

    # Run App Update Check in parallel logic (sequential execution here for simplicity)
    check_for_app_updates()

    # Check updates for CORE library (Programmer) only
    lib_path = DEFAULT_LIBRARY_PATH

    # 1. Throttling Check
    last_check_str = config.get("auto_sync", {}).get("last_check")
    if last_check_str:
        try:
            last_check = datetime.fromisoformat(last_check_str)
            if (datetime.now() - last_check).total_seconds() < 86400: # 24 Hours
                # If we already knew there were updates, keep that state
                SKILL_UPDATES_AVAILABLE = config.get("auto_sync", {}).get("updates_pending", False)
                return
        except:
            pass

    # 2. Check for Git Remote
    if not os.path.exists(os.path.join(lib_path, ".git")):
        return

    try:
        # Check if origin remote exists
        result = subprocess.run(["git", "remote"], cwd=lib_path, capture_output=True, text=True)
        if "origin" not in result.stdout:
             return

        # Perform Fetch in background-ish (silent)
        subprocess.run(["git", "fetch", "origin"], cwd=lib_path, capture_output=True, timeout=5)

        # Compare HEAD with origin/main or origin/master
        status = subprocess.run(["git", "status", "-uno"], cwd=lib_path, capture_output=True, text=True).stdout

        if "Your branch is behind" in status:
            SKILL_UPDATES_AVAILABLE = True
        else:
            SKILL_UPDATES_AVAILABLE = False

        # 3. Update Config
        if "auto_sync" not in config: config["auto_sync"] = {}
        config["auto_sync"]["last_check"] = datetime.now().isoformat()
        config["auto_sync"]["updates_pending"] = SKILL_UPDATES_AVAILABLE
        save_config(config)

    except Exception:
        # Silently fail for background checks (no internet, git lock, etc)
        pass

def print_help():
    """Render Rich Help Menu"""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        console = Console()

        # Update Banner (App)
        if APP_UPDATE_AVAILABLE:
            console.print(f"\n[bold green]🚀 Jaavis Update Available: v{APP_UPDATE_AVAILABLE}[/bold green]")
            console.print(f"[dim]Run 'brew upgrade jaavis' to update from v{VERSION}[/dim]")

        # Update Banner (Skills)
        if SKILL_UPDATES_AVAILABLE:
            console.print("\n[bold yellow]🌟 New skill updates available! Run 'jaavis sync' to upgrade your knowledge.[/bold yellow]")

        # Header
        console.print(Panel.fit("[bold cyan]🤖 JAAVIS CLI[/bold cyan] - One-Army Orchestrator", border_style="blue"))
        console.print(f"[dim]Active Persona: {get_current_persona_name()}[/dim]")

        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Command", style="cyan", width=12)
        table.add_column("Alias", style="yellow", width=8)
        table.add_column("Description", style="white")

        table.add_row("manage", "tui", "Interactive Command Center [bold](Default)[/bold]")
        table.add_row("harvest", "new", "Wizard to extract new skills")
        table.add_row("list", "ls", "List all knowledge base skills")
        table.add_row("apply", "", "Inject Skill (Executable Knowledge)")
        table.add_row("deploy", "", "Deploy pipeline (Grade-Aware)")
        table.add_row("search", "", "Fuzzy search by content")
        table.add_row("open", "", "Open skill in VS Code")
        table.add_row("delete", "rm", "Delete a skill")
        table.add_row("doctor", "chk", "Check system health")
        table.add_row("persona", "p", "Switch Persona")
        table.add_row("sync", "", "Update Skill Library (Git Sync)")
        table.add_row("push", "", "Upload Local Changes (Git Push)")
        table.add_row("brainstorm", "bs", "AI Refactor & Optimization")
        table.add_row("merge", "", "Create a Blueprint (Frontend + Backend)")
        table.add_row("init", "", "Scaffold new project structure")
        table.add_row("help", "", "Show this help screen")

        console.print(table)
        console.print("\n[grey50]Run 'jaavis <command> -h' for specific arguments.[/grey50]")

    except ImportError:
        print("Rich not installed. Run 'pip install rich'")

VERSION = "1.1.6"

# ==========================================
# MAINTAINER
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="# Jaavis Core - The One-Army Orchestrator\n# Version: 1.0.0", add_help=False)
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Subcommands with Aliases
    subparsers.add_parser("list", aliases=["ls"], help="List all harvested skills")

    harvest_parser = subparsers.add_parser("harvest", aliases=["new"], help="Interactive skill extraction wizard")
    harvest_parser.add_argument("--doc", help="Path to documentation file to auto-harvest from")
    harvest_parser.add_argument("doc_flag", nargs='?', help="Positional path to doc (optional)")

    # Search Command
    search_parser = subparsers.add_parser("search", help="Search skills by content")
    search_parser.add_argument("query", help="Keyword to search for")

    # Open Command
    open_parser = subparsers.add_parser("open", help="Open a skill in VS Code")
    open_parser.add_argument("name", help="Name of the skill to open (fuzzy match)")

    # Delete Command
    delete_parser = subparsers.add_parser("delete", aliases=["rm"], help="Delete a skill")
    delete_parser.add_argument("name", help="Name of the skill to delete")

    # Code Command (New)
    subparsers.add_parser("code", help="Open Jaavis Brain in VS Code")

    # Manage Command (TUI)
    subparsers.add_parser("manage", aliases=["tui"], help="Interactive TUI Manager")

    # Persona Command
    subparsers.add_parser("persona", aliases=["p"], help="Switch Persona")

    # Init Command
    subparsers.add_parser("init", help="Scaffold One-Army Project")

    # Deploy Command
    subparsers.add_parser("deploy", help="Deploy Project")

    # Merge Command
    subparsers.add_parser("merge", help="Merge Skills into Blueprint")

    # Apply Command
    apply_parser = subparsers.add_parser("apply", help="Apply Skill (Executable Knowledge)")
    apply_parser.add_argument("name", help="Name of the skill to apply")
    apply_parser.add_argument("--dry-run", action="store_true", help="Preview commands without running")

    # Doctor Command
    subparsers.add_parser("doctor", aliases=["chk"], help="Check system health")

    # Sync Command
    subparsers.add_parser("sync", help="Sync skills with remote library")

    # Push Command
    subparsers.add_parser("push", help="Push skills to remote library")

    # Brainstorm Command
    subparsers.add_parser("brainstorm", aliases=["bs"], help="AI Refactor & Optimization")

    # Help Command
    subparsers.add_parser("help", help="Show help message")

    try:
        # Parse args (handling aliases manually if argparse version < 3.8 issues, but aliases param works in recent python)
        # To catch 'jaavis' with no args, we check sys.argv
        if len(sys.argv) == 1:
            # SMART DEFAULT: Persona Selection -> TUI

            # Show Welcome if Config Missing (New User)
            config_path = os.path.join(os.getcwd(), ".jaavisrc")
            global_config = os.path.expanduser("~/.jaavisrc")
            if not os.path.exists(config_path) and not os.path.exists(global_config):
                show_welcome()

            # This enforces the flow: Users see who they are before entering.
            check_for_skill_updates()
            migrate_persona_libraries() # Ensure legacy paths are fixed
            select_persona()
            return

        # Handle custom version flag
        if "--version" in sys.argv or "-v" in sys.argv:
            print(f"Jaavis v{VERSION}")
            return

        # Handle custom help flag to use our Rich help
        if "-h" in sys.argv or "--help" in sys.argv:
            check_for_skill_updates()
            print_help()
            return

        try:
            args = parser.parse_args()
        except argparse.ArgumentError:
            print_help()
            return

        # Command Router
        if args.command in ["list", "ls"]:
            if getattr(args, 'text', False):
                 list_skills()
            else:
                 # Upgrade: 'list' now launches the Interactive TUI
                 import jaavis_tui
                 jaavis_tui.run(get_active_library_path())
        elif args.command in ["harvest", "new"]:
            # Support both positional and flag
            doc_arg = args.doc if args.doc else getattr(args, 'doc_flag', None)
            harvest_skill(doc_arg)
        elif args.command == "search":
            search_skills(args.query)
        elif args.command == "open":
            open_skill(args.name)
        elif args.command == "code":
            open_brain_vscode()
        elif args.command in ["delete", "rm"]:
            delete_skill(args.name)
        elif args.command in ["manage", "tui"]:
            import jaavis_tui
            # Use active library path from config
            jaavis_tui.run(get_active_library_path())
        elif args.command in ["persona", "p"]:
            select_persona()
        elif args.command == "init":
            init_project()
        elif args.command == "merge":
            merge_skills()
        elif args.command == "deploy":
            deploy_project()
        elif args.command in ["doctor", "chk"]:
            run_doctor()
        elif args.command in ["brainstorm", "bs"]:
            run_brainstorm_wizard()
        elif args.command == "sync":
            sync_all_personas()
        elif args.command == "push":
            push_all_personas()
        elif args.command == "apply":
            apply_skill(args.name, args.dry_run)
        elif args.command == "help":
            check_for_skill_updates()
            print_help()
        else:
            # Fallback for unrecognized commands that parse_args didn't catch (rare with argparse)
            print_help()
    except KeyboardInterrupt:
        print(f"\n{RED}Aborted by user.{RESET}")
        sys.exit(0)
    except EOFError:
        print(f"\n{RED}Aborted by user.{RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()
