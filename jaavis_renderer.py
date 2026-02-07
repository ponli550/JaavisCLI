import re
import sys
import textwrap

# ANSI Colors
CYAN = '\033[1;36m'
GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
MAGENTA = '\033[1;35m'
BLUE = '\033[1;34m'
WHITE = '\033[1;37m'
RESET = '\033[0m'
GREY = '\033[0;90m'

MAX_WIDTH = 70

def render_sketchy_box(title, items, color=CYAN):
    # Wrap text for items
    wrapped_lines = []
    for item in items:
        # Initial wrap
        lines = textwrap.wrap(item, width=MAX_WIDTH)
        # Add bullet to first line, indent others
        for i, line in enumerate(lines):
            if i == 0:
                wrapped_lines.append(f"• {line}")
            else:
                wrapped_lines.append(f"  {line}")

    # Calculate box width based on title or longest wrapped line
    if wrapped_lines:
        content_width = max([len(line) for line in wrapped_lines] + [len(title)]) + 2
    else:
        content_width = len(title) + 2

    # Ensure min width for aesthetic
    content_width = max(content_width, 40)
    box_width = content_width + 4

    # Sketchy Borders
    print(f"   {GREY}_{'_' * box_width}_{RESET}")
    print(f"  {GREY}/{' ' * box_width}\\{RESET}")
    print(f" {GREY}|{RESET}  {color}{title.center(box_width)}{RESET}  {GREY}|{RESET}")
    print(f" {GREY}|{RESET}  {GREY}{'-' * box_width}{RESET}  {GREY}|{RESET}")

    for line in wrapped_lines:
        # Pad line to match box width
        padding = box_width - len(line) - 2
        print(f" {GREY}|{RESET}  {WHITE}{line}{RESET}{' ' * padding}  {GREY}|{RESET}")

    print(f"  {GREY}\\{'_' * box_width}/{RESET}")
    print(f"          {GREY}|{RESET}")
    print(f"          {GREY}v{RESET}")

def parse_and_render(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    current_phase = None
    items = []

    print(f"\n{MAGENTA}   ( Start ) {RESET}")
    print(f"       {GREY}|{RESET}")
    print(f"       {GREY}v{RESET}")

    # cycling colors for phases
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
             # Clean up the list item
            clean_item = re.sub(r'^\d+\.\s*|-\s*', '', line)
            clean_item = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_item) # Remove bold stars but keep text
            clean_item = re.sub(r'\*(.*?)\*', r'\1', clean_item)     # Remove italic stars but keep text
            if current_phase:
                items.append(clean_item)
        elif current_phase and line[0].isalpha(): # Capture continuation lines/notes if strictly formatted
             pass

    if current_phase:
        render_sketchy_box(current_phase, items, colors[color_idx % len(colors)])

    print(f"\n{GREEN}    ( Done ) {RESET}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 jaavis_renderer.py <md_file>")
        sys.exit(1)
    filepath = sys.argv[1]
    parse_and_render(filepath)
