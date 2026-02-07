import curses
import os
import shutil
import subprocess
import io
import stat

# Try importing Rich
try:
    from rich.console import Console
    from rich.markdown import Markdown
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Colors (initialized in run)
COLOR_DEFAULT = 1
COLOR_HIGHLIGHT = 2
COLOR_TITLE = 3
COLOR_SUBTITLE = 4

def is_locked(path):
    """Check if file has user immutable flag (uchg) set."""
    try:
        st = os.stat(path)
        return bool(st.st_flags & stat.UF_IMMUTABLE)
    except Exception:
        return False

def toggle_lock(path):
    """Toggle the user immutable flag."""
    locked = is_locked(path)
    flag = 'nouchg' if locked else 'uchg'
    try:
        subprocess.call(['chflags', flag, path])
        return not locked
    except Exception:
        return locked

def get_skills(library_path):
    """Walks the library and returns a list of (name, path, domain) tuples."""
    skills = []
    if not os.path.exists(library_path):
        return skills

    for root, dirs, files in os.walk(library_path):
        for f in files:
            if f.endswith(".md") and f != "TEMPLATE_SKILL.md":
                abs_path = os.path.join(root, f)
                # Domain is the folder name, unless it's the root of library
                domain = os.path.basename(root)
                if root == library_path:
                    domain = "root"

                skills.append({
                    "name": f,
                    "path": abs_path,
                    "domain": domain,
                    "locked": is_locked(abs_path)
                })

    # Sort by domain then name
    skills.sort(key=lambda x: (x['domain'], x['name']))
    return skills

def draw_dual_pane(stdscr, selected_idx, skills, filter_text):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # Define window widths (30% left, 70% right)
    left_w = int(w * 0.3)
    right_w = w - left_w

    # 1. Left Window: The List
    try:
        left_win = stdscr.subwin(h - 2, left_w, 1, 0) # Start at (1,0)
        left_win.box()
        left_win.addstr(0, 2, " SKILLS ", curses.color_pair(COLOR_TITLE))

        # Calculate scroll offset for list
        max_items = h - 4
        start_idx = max(0, selected_idx - max_items + 1)
        end_idx = min(len(skills), start_idx + max_items)

        for i in range(start_idx, end_idx):
            skill = skills[i]
            y = i - start_idx + 1 # Relative to window

            attr = curses.color_pair(COLOR_HIGHLIGHT) if i == selected_idx else curses.A_NORMAL

            # Lock Indicator
            lock_char = "🔒 " if skill.get('locked') else "  "

            # Clip name to fit the narrow pane
            # Available width = Window Width - Border(2) - Lock(2)
            max_name_len = left_w - 4 - 2
            display_name = f"{lock_char}{skill['name'][:max_name_len]}"

            try:
                left_win.addstr(y, 2, display_name, attr)
            except curses.error: pass
    except curses.error:
        pass # Window creation might fail if terminal too small

    # 2. Right Window: The Preview
    try:
        right_win = stdscr.subwin(h - 2, right_w, 1, left_w) # Start at (1, left_w)
        right_win.box()
        right_win.addstr(0, 2, " PREVIEW ", curses.color_pair(COLOR_TITLE))

        if skills and selected_idx < len(skills):
            selected_skill = skills[selected_idx]
            try:
                if HAS_RICH:
                    # Capture Rich output
                    f = io.StringIO()
                    console = Console(file=f, force_terminal=True, color_system=None, width=right_w - 4)

                    with open(selected_skill['path'], 'r') as md_file:
                        content = md_file.read()
                        md = Markdown(content)
                        console.print(md)

                    formatted_content = f.getvalue()
                    lines = formatted_content.splitlines()
                else:
                    # Fallback if Rich import failed
                    with open(selected_skill['path'], 'r') as f:
                        lines = f.readlines()

                for i, line in enumerate(lines):
                    if i >= h - 4: break
                    # Clean the line and clip it to pane width
                    clean_line = line.rstrip()[:right_w - 4]
                    right_win.addstr(i + 1, 2, clean_line)
            except Exception as e:
                right_win.addstr(1, 2, f"Error reading file: {e}")
    except curses.error:
        pass

    # 3. Footer & Filter Info
    footer = f" Filter: /{filter_text} | Nav: UP/DOWN | Act: ENTER | Edit: E | Run: R | Lock: L | Quit: Q "
    try:
        stdscr.addstr(h - 1, 0, footer.center(w)[:w-1], curses.color_pair(COLOR_SUBTITLE))
    except curses.error:
        pass

    stdscr.refresh()

def action_menu(stdscr, skill, library_path):
    """Sub-menu for Edit/Move/Delete"""
    options = ["Edit (VS Code)", "Move", "Delete", "Cancel"]
    selected_idx = 0

    while True:
        h, w = stdscr.getmaxyx()
        # Draw Box for inputs
        box_h, box_w = 10, 50
        try:
            box_y, box_x = (h - box_h) // 2, (w - box_w) // 2
            win = curses.newwin(box_h, box_w, box_y, box_x)
            win.box()
            win.addstr(1, 2, f"Action: {skill['name']}", curses.color_pair(COLOR_TITLE))

            for idx, option in enumerate(options):
                # Check formatting based on lock status
                display_option = option
                is_disabled = False

                if skill.get('locked') and option in ["Move", "Delete"]:
                     display_option = f"{option} (LOCKED)"
                     is_disabled = True

                if idx == selected_idx:
                    attr = curses.color_pair(COLOR_HIGHLIGHT)
                elif is_disabled:
                    attr = curses.color_pair(COLOR_DEFAULT) | curses.A_DIM
                else:
                    attr = curses.color_pair(COLOR_DEFAULT)

                win.addstr(3 + idx, 4, f"> {display_option}" if idx == selected_idx else f"  {display_option}", attr)

            win.refresh()
        except curses.error:
            pass

        key = stdscr.getch()

        if key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1
        elif key == curses.KEY_DOWN and selected_idx < len(options) - 1:
            selected_idx += 1
        elif key in [10, 13]: # Enter
            # BLOCK ACTIONS IF LOCKED
            if skill.get('locked') and selected_idx in [1, 2]: # Move or Delete
                # Flash error or just ignore
                curses.beep()
                continue

            if selected_idx == 0: # Edit
                try:
                    subprocess.call(['code', skill['path']])
                except FileNotFoundError:
                    subprocess.call(['open', skill['path']])
                return # Exit menu after action
            elif selected_idx == 1: # Move
                curses.echo()
                win.addstr(8, 2, "New Domain: ")
                try:
                    new_domain = win.getstr(8, 14).decode('utf-8').strip()
                    curses.noecho()

                    if new_domain:
                        new_dir = os.path.join(library_path, "skills", new_domain)
                        if not os.path.exists(new_dir):
                            os.makedirs(new_dir)
                        new_path = os.path.join(new_dir, skill['name'])
                        shutil.move(skill['path'], new_path)
                        return "refresh" # Signal to refresh list
                except curses.error:
                    pass
            elif selected_idx == 2: # Delete
                win.addstr(8, 2, "Are you sure? (y/N): ", curses.color_pair(COLOR_DEFAULT))
                win.refresh()
                confirm = stdscr.getch()
                if confirm in [ord('y'), ord('Y')]:
                    os.remove(skill['path'])
                    return "refresh"
            elif selected_idx == 3: # Cancel
                return

            return

def run_associated_script(stdscr, skill, library_path):
    """Looks for a script in library/scripts/ corresponding to the skill"""
    script_name = skill['name'].replace('.md', '.sh')
    # Try flat scripts folder first
    script_path = os.path.join(library_path, 'scripts', script_name)

    if not os.path.exists(script_path):
        # Try domain-based folder
        script_path = os.path.join(library_path, 'scripts', skill['domain'], script_name)

    if os.path.exists(script_path) and os.access(script_path, os.X_OK):
        # Found executable script
        curses.def_prog_mode() # Save curses state
        curses.endwin()        # Restore terminal for script output

        print(f"\n[Jaavis] Running script: {script_name}...\n")
        subprocess.call([script_path])
        print(f"\n[Jaavis] Execution finished. Press ENTER to return.")
        input()

        curses.reset_prog_mode() # Restore curses state
        curses.doupdate()
    else:
        pass

def edit_in_terminal(stdscr, path):
    """Launch console editor (nano/vim) for the selected file"""
    editor = os.environ.get('EDITOR', 'nano')

    # Check if editor exists
    if not shutil.which(editor):
        # Fallback
        if shutil.which('vim'): editor = 'vim'
        elif shutil.which('vi'): editor = 'vi'
        else: return # No editor found

    curses.def_prog_mode()
    curses.endwin()

    try:
        subprocess.call([editor, path])
    except Exception as e:
        print(f"Error launching editor: {e}")
        input("Press Enter to continue...")

    curses.reset_prog_mode()
    curses.doupdate()

def main(stdscr, library_path):
    # Setup Colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COLOR_DEFAULT, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_HIGHLIGHT, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(COLOR_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_SUBTITLE, curses.COLOR_YELLOW, -1)

    curses.curs_set(0) # Hide cursor

    filter_text = ""
    current_row = 0

    while True:
        # Get all skills and filter them based on user input
        all_skills = get_skills(library_path)
        skills = [s for s in all_skills if filter_text.lower() in s['name'].lower()]

        # Bound selection
        if skills:
            current_row = max(0, min(current_row, len(skills) - 1))

        # Call the new Dual Pane Drawer
        draw_dual_pane(stdscr, current_row, skills, filter_text)

        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(skills) - 1:
            current_row += 1
        elif key == ord('q') and not filter_text:
            break
        elif key == 27: # ESC
            filter_text = ""
        elif key in [8, 127, curses.KEY_BACKSPACE]:
            filter_text = filter_text[:-1]
        elif key in [ord('E'), ord('e')]:
            if skills:
                 edit_in_terminal(stdscr, skills[current_row]['path'])
        elif 32 <= key <= 126 and key not in [ord('R'), ord('r'), ord('L'), ord('l')]:
            # Reserve R/L for shortcuts
            filter_text += chr(key)
        elif key in [ord('R'), ord('r')]:
            if skills:
                run_associated_script(stdscr, skills[current_row], library_path)
        elif key in [ord('L'), ord('l')]:
            if skills:
                 skill = skills[current_row]
                 toggle_lock(skill['path'])
                 # Status update implicit on next loop refresh
        elif key in [10, 13]: # Enter
            if skills:
                result = action_menu(stdscr, skills[current_row], library_path)
                if result == "refresh":
                    pass

def run(library_path):
    try:
        curses.wrapper(main, library_path)
    except Exception as e:
        print(f"Error in TUI: {e}")

if __name__ == "__main__":
    test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library")
    run(test_path)
