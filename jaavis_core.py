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
# This ensures Jaavis finds its Brain/Face regardless of where you run it from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Default Library (Programmer)
DEFAULT_LIBRARY_PATH = os.path.join(BASE_DIR, "library")
TEMPLATE_PATH = os.path.join(DEFAULT_LIBRARY_PATH, "templates/skill.md") # Keep template in default for now or make dynamic
LOGO_PATH = os.path.join(BASE_DIR, "logo.md")

# ANSI Colors
CYAN = '\033[1;36m'
GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
MAGENTA = '\033[1;35m'
BLUE = '\033[1;34m'
WHITE = '\033[1;37m'
RED = '\033[1;31m'
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

def interactive_menu(title, options, default_index=0):
    """Render a menu that can be navigated with arrow keys."""
    selected_index = default_index
    num_options = len(options)

    # Initial Print
    print(f"\n{MAGENTA}{title}{RESET}")
    for i in range(num_options):
        print("") # Placeholder lines to overwrite

    while True:
        # Move cursor back up to start of options (num_options lines + extra spacing)
        # Using ANSI escape: \033[A moves up one line.
        for _ in range(num_options):
            sys.stdout.write('\033[A')

        # Re-render options
        for i, option in enumerate(options):
            prefix = f"{CYAN}▶ {RESET}" if i == selected_index else "  "
            color = CYAN if i == selected_index else WHITE
            # Clear current line then print
            sys.stdout.write('\033[K')
            print(f"{prefix}{color}{option}{RESET}")

        # Capture key
        try:
            key = get_key()
        except KeyboardInterrupt:
            print(f"\n{RED}Aborted.{RESET}")
            sys.exit(0)

        if key == '\x1b[A': # Up
            selected_index = (selected_index - 1) % num_options
        elif key == '\x1b[B': # Down
            selected_index = (selected_index + 1) % num_options
        elif key in ['\r', '\n']: # Enter
            return selected_index


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

def select_persona():
    """Interactive Persona Selection & Configuration"""
    load_face()

    config = load_config()
    current = config.get("current_persona", "programmer")

    print(f"{WHITE}Hi I'm Jaavis, your personal assistant.{RESET}\n")

    # 1. Build Options
    menu_options = ["Programmer (One-Army Protocol as a default)"]

    # Ensure defaults exist in config for listing
    if "personas" not in config: config["personas"] = {}
    if "programmer" not in config["personas"]: config["personas"]["programmer"] = {"path": DEFAULT_LIBRARY_PATH}
    if "contractor" not in config["personas"]: config["personas"]["contractor"] = {"path": os.path.join(BASE_DIR, "library_contractor")}
    if "librarian" not in config["personas"]: config["personas"]["librarian"] = {"path": os.path.join(BASE_DIR, "library_librarian")}

    dynamic_personas = sorted([k for k in config["personas"].keys() if k != "programmer"])

    for p in dynamic_personas:
        lock_status = " 🔒" if config["personas"].get(p, {}).get("locked") else ""
        menu_options.append(f"{p.capitalize()}{lock_status}")

    menu_options.append("Manage Personas")

    # 2. Determine Default Index
    persona_keys = ["programmer"] + dynamic_personas
    default_idx = 0
    if current in persona_keys:
        default_idx = persona_keys.index(current)

    # 3. Show Interactive Menu
    prompt_text = f"Who is operating right now? (Current: {current.upper()})"
    choice_idx = interactive_menu(prompt_text, menu_options, default_index=default_idx)

    # 4. Map Choice to Persona
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
    if "contractor" not in config["personas"]: config["personas"]["contractor"] = {"path": os.path.join(BASE_DIR, "library_contractor")}
    if "librarian" not in config["personas"]: config["personas"]["librarian"] = {"path": os.path.join(BASE_DIR, "library_librarian")}

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
    lib_path = os.path.join(BASE_DIR, lib_dir)

    config["personas"][name] = {
        "path": lib_path,
        "created_at": str(datetime.now()),
        "locked": False
    }

    save_config(config)
    print(f"{GREEN}✔ Persona '{name}' added!{RESET}")
    time.sleep(1)

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
    new_path = os.path.join(BASE_DIR, new_lib_dir)

    if old_path == os.path.join(BASE_DIR, f"library_{old_name}"):
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
        config["personas"][new_name] = config["personas"].pop(old_name)
        config["personas"][new_name]["path"] = new_path
    else:
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
        level = root.replace(lib_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        subindent = ' ' * 4 * (level + 1)

        # Print Directory Name
        folder_name = os.path.basename(root)
        if folder_name and folder_name != "skills":
            print(f"{GREY}{indent}📂 {folder_name}/{RESET}")

        for f in files:
            if f.endswith(".md") and f != "TEMPLATE_SKILL.md":
                print(f"{GREEN}{subindent}📜 {f}{RESET}")
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

def harvest_skill(doc_path=None):
    lib_path = get_active_library_path()
    print(f"{MAGENTA}🌾 Jaavis Harvest Protocol ({get_current_persona_name()}){RESET}")
    print("-----------------------------------------------------")

    # Smart Harvest: Pre-fill from doc
    defaults = {}
    if doc_path:
        print(f"[bold cyan]📄 Parsing documentation: {doc_path}...[/bold cyan]")
        parsed = parse_markdown_doc(doc_path)
        if parsed:
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

        domain = input(f"{CYAN}? Domain (e.g. ui, backend, construction): {RESET}").strip().lower()

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

        filename = skill_name.lower().replace(" ", "-") + ".md"
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
        auto_open = input(f"{CYAN}? Open in editor now? (Y/n): {RESET}")
        if auto_open.lower() != 'n':
             import subprocess
             try:
                subprocess.call(['code', target_path])
             except:
                pass

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
        import json
        import yaml # PyYAML required for frontmatter

        console = Console()
        lib_path = get_active_library_path()

        console.print(Panel.fit("[bold magenta]🧬 Jaavis Blueprint Merge[/bold magenta]", border_style="magenta"))
        console.print("[dim]Create a unified project from separate Frontend and Backend skills.[/dim]\n")

        # 0. Ensure Project Init
        if not os.path.exists(os.path.join(os.getcwd(), ".jaavisrc")):
            console.print("[yellow]Project not initialized. Running 'jaavis init' first...[/yellow]")
            init_project()



        # 1. Tech Stack Advisor (Comparison Table)
        console.print("\n[bold cyan]💡 Tech Stack Advisor[/bold cyan]")

        all_skills = {} # name -> metadata
        search_dirs = ["frontend", "ui", "devops", "backend", "qowi"]

        # Scan and Parse
        for d in search_dirs:
            p = os.path.join(lib_path, "skills", d)
            if os.path.exists(p):
                for f in os.listdir(p):
                    if f.endswith(".md"):
                        path = os.path.join(p, f)
                        with open(path, 'r') as file:
                            content = file.read()
                            meta = parse_frontmatter(content)
                            if meta:
                                skill_id = f.replace(".md", "")
                                all_skills[skill_id] = meta
                                all_skills[skill_id]['path'] = path

        # Display Comparison Table
        from rich.table import Table
        table = Table(title="Available Skills", show_header=True, header_style="bold magenta", box=None)
        table.add_column("Skill ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="white")
        table.add_column("Grade", style="yellow")
        table.add_column("Pros", style="blue")
        table.add_column("Cons", style="red")

        # Sort by Grade (Ascending A->B->C or similar logic, simplistic here)
        for skill_id, meta in sorted(all_skills.items(), key=lambda item: item[1].get('grade', 'Z')):
            pros = ", ".join(meta.get('pros', []))
            cons = ", ".join(meta.get('cons', []))
            table.add_row(
                skill_id,
                meta.get('name', skill_id),
                meta.get('description', 'No description'),
                meta.get('grade', '-'),
                pros,
                cons
            )

        console.print(table)
        console.print("\n")

        # 2. Select Frontend
        console.print("\n[bold cyan]1. Select Frontend Skill[/bold cyan]")

        # Filter Frontends
        frontend_options = [sid for sid, m in all_skills.items() if 'frontend' in m.get('tags', [])]

        # Fallback to file search if no metadata tags found
        if not frontend_options:
            search_dirs = ["frontend", "ui"]
            for d in search_dirs:
                p = os.path.join(lib_path, "skills", d)
                if os.path.exists(p):
                    for f in os.listdir(p):
                        if f.endswith(".md"):
                            frontend_options.append(f.replace(".md", ""))

        if not frontend_options:
             console.print("[red]No frontend skills found.[/red]")
             return

        idx = interactive_menu("Choose Frontend", frontend_options)
        frontend_choice = frontend_options[idx]
        console.print(f"[green]✔ Selected:[/green] {frontend_choice}")

        # 3. Select Backend
        console.print("\n[bold cyan]2. Select Backend Skill[/bold cyan]")

        # Filter Backends
        backend_options = [sid for sid, m in all_skills.items() if 'backend' in m.get('tags', [])]

        # Fallback
        if not backend_options:
            search_dirs = ["devops", "backend", "qowi"]
            for d in search_dirs:
                p = os.path.join(lib_path, "skills", d)
                if os.path.exists(p):
                    for f in os.listdir(p):
                        if f.endswith(".md"):
                            backend_options.append(f.replace(".md", ""))

        if not backend_options:
             console.print("[yellow]No backend skills found. Skipping backend merge.[/yellow]")
             backend_choice = None
        else:
            idx = interactive_menu("Choose Backend", backend_options)
            backend_choice = backend_options[idx]
            console.print(f"[green]✔ Selected:[/green] {backend_choice}")

        # 3. Update .jaavisrc (Blueprint Definition)
        config = load_config_local()
        config["type"] = "blueprint"
        config["frontend"] = frontend_choice
        if backend_choice:
            config["backend"] = backend_choice

        # Save
        with open(os.path.join(os.getcwd(), ".jaavisrc"), 'w') as f:
             json.dump(config, f, indent=2)

        console.print("\n[bold green]💾 Blueprint Saved![/bold green]")

        # 4. Validation (Pre-flight)
        console.print("\n[bold]🩺 Verifying Blueprint Integrity...[/bold]")

        # Check if folders exist (Mock implementation of applying the skills)
        # Real implementation would call apply_skill() here targeting specific folders

        missing = []
        if not os.path.exists("apps/web"):
            missing.append("apps/web (Frontend)")

        if backend_choice and not os.path.exists("apps/api"):
             missing.append("apps/api (Backend)")

        if missing:
            console.print("[yellow]⚠️  Blueprint Incomplete. Missing components:[/yellow]")
            for m in missing:
                console.print(f"  - {m}")

            apply_now = Prompt.ask("\nAttempt to apply skills now?", choices=["y", "n"], default="y")
            if apply_now == "y":
                # FRONTEND APPLY
                console.print(f"\n[bold]Applying {frontend_choice} to apps/web...[/bold]")
                apply_skill(frontend_choice, context={"target_dir": "apps/web"})

                # BACKEND APPLY
                if backend_choice:
                    console.print(f"\n[bold]Applying {backend_choice} to apps/api...[/bold]")
                    apply_skill(backend_choice, context={"target_dir": "apps/api"})

                console.print("\n[green]Merge Sequence Completed.[/green]")

                # CLEANUP / POST-INSTALL
                if Prompt.ask("\nRun automated setup (npm install & build)?", choices=["y", "n"], default="y") == "y":
                    console.print("\n[bold yellow]⚙️  Running Setup...[/bold yellow]")

                    # Frontend Setup
                    if os.path.exists("apps/web/package.json"):
                        console.print("  • Frontend: Installing dependencies...")
                        subprocess.run("cd apps/web && npm install", shell=True, executable='/bin/zsh')

                    # Backend/Docker Setup
                    # Rewrite root docker-compose.yml to include the backend service
                    # Rewrite root docker-compose.yml to include the backend service
                    backend_compose_file = None
                    if os.path.exists("apps/api/compose.yaml"):
                        backend_compose_file = "apps/api/compose.yaml"
                    elif os.path.exists("apps/api/docker-compose.yml"):
                        backend_compose_file = "apps/api/docker-compose.yml"

                    if backend_compose_file:
                        console.print(f"  • Docker: Linking backend ({backend_compose_file})...")
                        with open("docker-compose.yml", "w") as f:
                            f.write(f"# One-Army Docker Compose\n# Root Orchestrator\ninclude:\n  - {backend_compose_file}\n")
                    else:
                        console.print("  [yellow]⚠️  Backend compose file not found (checked apps/api/compose.yaml & docker-compose.yml)[/yellow]")

                    if os.path.exists("docker-compose.yml") or os.path.exists("docker-compose.yaml"):
                        console.print("  • Docker: Building containers...")
                        subprocess.run("docker compose build", shell=True, executable='/bin/zsh')

                    console.print("[green]✨ Blueprint Setup Complete![/green]")
        else:
            console.print("[green]✔ Blueprint Validated. Ready to deploy.[/green]")

    except ImportError as e:
        import sys
        print(f"Missing dependency: {e}. Run 'pip install rich PyYAML'")
        print(f"Python Executable: {sys.executable}")

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
        console.print("[bold green]✨ Project Scaffolding Complete.[/bold green]")

    except ImportError:
        print("Rich not installed. Run 'pip install rich'")

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
        console.print("Select Deployment Strategy:")
        for idx, s in enumerate(strategies):
            console.print(f"  {idx+1}. {s['name']}")

        choice_idx = 0
        if len(strategies) > 1:
            choice_str = Prompt.ask("Choose Strategy", default="1")
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
            if grade == "A" and not shutil.which("kubectl"):
                 issues.append("Kubectl not installed")

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
                    ("Running E2E Tests", "npm run test:e2e"),
                    ("Security Audit", "npm audit"),
                    ("Applying K8s Manifests", "kubectl apply -f k8s/"),
                    ("Migrating DB", "npx supabase migration up")
                ]

        elif selected_strategy["type"] == "harvested":
            # Parse the harvested skill file
            with open(selected_strategy["path"], 'r') as f:
                content = f.read()
                # Regex to extract commands from <!-- JAAVIS:EXEC --> blocks
                pattern = r'<!--\s*JAAVIS:EXEC\s*-->\s*```bash\n(.*?)\n```'
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                     lines = match.strip().split('\n')
                     for line in lines:
                        if line.strip() and not line.strip().startswith('#'):
                            # TEMPLATE DEFAULTING for Deploy Command
                            # If running as a strategy, we assume we want to apply it to CURRENT dir
                            cmd = line.strip().replace("{{target_dir}}", ".")
                            steps.append(("Custom Step", cmd))

        elif selected_strategy["type"] == "manual":
            cmd = Prompt.ask("[bold yellow]Enter Command to Run[/bold yellow]")
            steps = [("Manual Execution", cmd)]

        # 5. Glass Box Preview
        if not steps and selected_strategy["type"] != "manual":
             console.print("[yellow]⚠️  No steps defined for this strategy.[/yellow]")
             return

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

        # 7. Execution Loop
        for title, cmd in steps:
            console.print(f"\n[bold yellow]👉 {title}[/bold yellow]...")
            # Split command string into list for subprocess if not shell=True,
            # but to support complex pipes/env vars, shell=True is often needed for 'deploy' scripts.
            # We used shell=False previously with list, but for flexibility we switch to shell=True here for custom commands.
            # Security Note: User is running this on their own machine, so shell=True is acceptable for local CLI tool.

            result = subprocess.call(cmd, shell=True, executable='/bin/zsh')
            if result != 0:
                console.print(f"[bold red]❌ Failed at step: {title}[/bold red]")
                return

        console.print("\n[bold green]✅ Deployment Complete![/bold green]")

    except ImportError:
        print("Rich not installed. Run 'pip install rich'")

def parse_frontmatter(content):
    """Extracts YAML frontmatter from markdown content"""
    import yaml
    content = content.strip()
    if content.startswith("---"):
        try:
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return yaml.safe_load(parts[1])
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

        commands = []
        for match in matches:
            # Split by line, ignore empty or comments
            lines = match.strip().split('\n')
            for line in lines:
                if line.strip() and not line.strip().startswith('#'):
                    commands.append(line.strip())

        if not commands:
            console.print("[yellow]⚠️  Found execution block but no valid commands.[/yellow]")
            return

        # TEMPLATING: Replace placeholders
        if context:
            final_commands = []
            for cmd in commands:
                for key, val in context.items():
                    cmd = cmd.replace(f"{{{{{key}}}}}", val)
                final_commands.append(cmd)
            commands = final_commands

        console.print(f"[bold blue]🚀 Prepared {len(commands)} commands to execute:[/bold blue]")

        # 3. Execution Loop
        for i, cmd in enumerate(commands, 1):
            console.print(f"\n[bold yellow]Step {i}/{len(commands)}:[/bold yellow] [green]{cmd}[/green]")

            if dry_run:
                console.print("[dim](Dry Run: Skipped)[/dim]")
                continue

            # Execute
            while True:
                # Use TTY passthrough for interactive commands (login, init, etc)
                process = subprocess.run(cmd, shell=True, executable='/bin/zsh')

                if process.returncode == 0:
                    console.print(f"  [green]✔ Success[/green]")
                    break # Next command
                else:
                    console.print(f"[bold red]❌ Failed (Exit Code {process.returncode})[/bold red]")
                    # Stderr is not captured with TTY passthrough, it's printed directly.
                    # console.print(Panel(process.stderr, title="Stderr", border_style="red"))

                    # Stop-on-Fail Protocol
                    action = Prompt.ask(
                        "[bold red]⚠️  Error![/bold red] What to do?",
                        choices=["Reset", "Skip", "Abort"],
                        default="Abort"
                    )

                    if action == "Reset": # Retry
                        console.print("[yellow]🔄 Retrying...[/yellow]")
                        continue
                    elif action == "Skip": # Skip
                        console.print("[yellow]⏭️  Skipping step...[/yellow]")
                        break
                    elif action == "Abort": # Abort
                        console.print("[bold red]🛑 Aborted by user.[/bold red]")
                        return

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

    # 1. Check if git repository
    if not os.path.exists(os.path.join(lib_path, ".git")):
        print(f"{YELLOW}Warning: This library is not currently linked to a remote hub.{RESET}")
        try:
            choice = input(f"{CYAN}? Would you like to link a GitHub/Git repository? (y/n): {RESET}").strip().lower()
            if choice == 'y':
                remote_url = input(f"{CYAN}? Remote Git URL: {RESET}").strip()
                if remote_url:
                    if not link_remote_library(lib_path, remote_url):
                        return
                else:
                    print(f"{RED}No URL provided. Aborting.{RESET}")
                    return
            else:
                print(f"{YELLOW}Sync aborted.{RESET}")
                return
        except KeyboardInterrupt:
            print(f"\n{RED}Aborted.{RESET}")
            return

    # 2. Execute Sync
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
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")

    # Reset update flag after a successful sync attempt
    config = load_config()
    if "auto_sync" in config:
        config["auto_sync"]["updates_pending"] = False
        save_config(config)


# Global Update State
SKILL_UPDATES_AVAILABLE = False

def check_for_skill_updates():
    """Background check for skill library updates (throttled to 24h)."""
    global SKILL_UPDATES_AVAILABLE
    config = load_config()
    lib_path = get_active_library_path()

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

        # Update Banner
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
        table.add_row("merge", "", "Create a Blueprint (Frontend + Backend)")
        table.add_row("init", "", "Scaffold new project structure")
        table.add_row("help", "", "Show this help screen")

        console.print(table)
        console.print("\n[grey50]Run 'jaavis <command> -h' for specific arguments.[/grey50]")

    except ImportError:
        print("Rich not installed. Run 'pip install rich'")

# ==========================================
# MAINTAINER
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Jaavis - One-Army Orchestrator", add_help=False)
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Subcommands with Aliases
    subparsers.add_parser("list", aliases=["ls"], help="List all harvested skills")

    harvest_parser = subparsers.add_parser("harvest", aliases=["new"], help="Interactive skill extraction wizard")
    harvest_parser.add_argument("--doc", help="Path to documentation file to auto-harvest from")

    # Search Command
    search_parser = subparsers.add_parser("search", help="Search skills by content")
    search_parser.add_argument("query", help="Keyword to search for")

    # Open Command
    open_parser = subparsers.add_parser("open", help="Open a skill in VS Code")
    open_parser.add_argument("name", help="Name of the skill to open (fuzzy match)")

    # Delete Command
    delete_parser = subparsers.add_parser("delete", aliases=["rm"], help="Delete a skill")
    delete_parser.add_argument("name", help="Name of the skill to delete")

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

    # Help Command
    subparsers.add_parser("help", help="Show help message")

    try:
        # Parse args (handling aliases manually if argparse version < 3.8 issues, but aliases param works in recent python)
        # To catch 'jaavis' with no args, we check sys.argv
        if len(sys.argv) == 1:
            # SMART DEFAULT: Persona Selection -> TUI
            # This enforces the flow: Users see who they are before entering.
            check_for_skill_updates()
            select_persona()
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
            list_skills()
        elif args.command in ["harvest", "new"]:
            harvest_skill(args.doc)
        elif args.command == "search":
            search_skills(args.query)
        elif args.command == "open":
            open_skill(args.name)
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
        elif args.command == "sync":
            sync_skills()
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
