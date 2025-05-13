#!/usr/bin/env python3
import asyncio
import sys
import shutil
import re
import os
import signal
import argparse
from datetime import datetime

# Unicode characters for the animation
PACMAN = "󰑊"
PACMAN_EAT = "󰮯"
GHOST = ""
DOT = "•"

# ANSI color codes
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "blue": "\033[34m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
    "white": "\033[37m",
    "black_bg": "\033[40m",
    "blue_bg": "\033[44m",
}

class ScrollableLogBox:
    """A scrollable log box with navigation controls"""
    def __init__(self, height=10, title="Installation Logs", max_logs=1000):
        self.height = height
        self.title = title
        self.logs = []
        self.max_logs = max_logs
        self.cols = shutil.get_terminal_size().columns
        self.scroll_pos = 0
        self.is_following = True  # Auto-follow new logs
        self._draw_box()
        
    def _draw_box(self):
        # Top border with title
        title_display = f" {self.title} "
        left_border = "┌" + "─" * ((self.cols - len(title_display)) // 2 - 1)
        right_border = "─" * (self.cols - len(left_border) - len(title_display) - 1) + "┐"
        print(f"{left_border}{title_display}{right_border}")
        
        # Empty content area
        for _ in range(self.height):
            print(f"│{' ' * (self.cols - 2)}│")
        
        # Bottom border with controls
        controls = " ↑/↓: Scroll | F: Toggle Follow | ESC: Exit Controls "
        controls_display = f"│ {controls}{' ' * (self.cols - len(controls) - 3)}│"
        print(controls_display)
        print(f"└{'─' * (self.cols - 2)}┘")
        
        # Move cursor back up to the content area start
        print(f"\033[{self.height + 2}A\033[2B", flush=True)
    
    def add_log(self, message, level="INFO"):
        # Format with timestamp and level
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_code = {
            "INFO": COLORS["reset"],
            "WARN": COLORS["yellow"],
            "ERROR": COLORS["red"],
            "SUCCESS": COLORS["green"],
            "SYSTEM": COLORS["blue"],
        }.get(level, COLORS["reset"])
        
        formatted_log = f"[{timestamp}] {color_code}{level}{COLORS['reset']}: {message}"
        
        # Add to logs
        self.logs.append(formatted_log)
        
        # Trim if needed
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
            
        # Update display if following
        if self.is_following:
            self.scroll_pos = max(0, len(self.logs) - self.height)
            self._update_display()
    
    def toggle_follow(self):
        self.is_following = not self.is_following
        if self.is_following:
            self.scroll_pos = max(0, len(self.logs) - self.height)
            self._update_display()
    
    def scroll_up(self):
        if self.scroll_pos > 0:
            self.scroll_pos -= 1
            self.is_following = False
            self._update_display()
    
    def scroll_down(self):
        if self.scroll_pos < len(self.logs) - self.height:
            self.scroll_pos += 1
            self._update_display()
        elif not self.is_following:
            self.toggle_follow()
    
    def _update_display(self):
        # Save cursor position
        print("\033[s", end="", flush=True)
        
        # Move cursor to log area start
        print(f"\033[{self.height + 2}A\033[2B", end="", flush=True)
        
        # Calculate visible logs
        end_pos = min(self.scroll_pos + self.height, len(self.logs))
        visible_logs = self.logs[self.scroll_pos:end_pos]
        
        # Pad if not enough logs
        while len(visible_logs) < self.height:
            visible_logs.append("")
        
        # Display logs
        for log in visible_logs:
            # Trim if too long
            if len(log) > self.cols - 4:
                log = log[:self.cols - 7] + "..."
            
            # Print log with padding
            print(f"\r│ {log}{' ' * (self.cols - len(log) - 3)}│")
        
        # Update status line
        follow_status = "ON " if self.is_following else "OFF"
        status = f" ↑/↓: Scroll | F: Follow ({follow_status}) | {self.scroll_pos+1}-{end_pos}/{len(self.logs)} "
        print(f"\r│ {status}{' ' * (self.cols - len(status) - 3)}│")
        
        # Restore cursor position
        print("\033[u", end="", flush=True)

class PackageManager:
    """Class to handle package operations"""
    def __init__(self, log_box):
        self.log_box = log_box
        
    async def search(self, query):
        """Search for packages"""
        self.log_box.add_log(f"Searching for packages matching '{query}'...", "SYSTEM")
        
        cmd = ["pacman", "-Ss", query]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            self.log_box.add_log(f"Search failed: {stderr.decode().strip()}", "ERROR")
            return []
        
        results = []
        current_pkg = {}
        
        for line in stdout.decode().splitlines():
            if line.startswith("    "):  # Description line
                if current_pkg:
                    current_pkg["description"] = line.strip()
                    results.append(current_pkg)
                    current_pkg = {}
            elif "/" in line:  # Package line
                parts = line.split(" ", 1)
                if len(parts) >= 2:
                    repo_name = parts[0]
                    rest = parts[1]
                    
                    # Extract version from within parentheses
                    name_ver = rest.split(" ", 1)[0]
                    if " " in rest:
                        desc_part = rest.split(" ", 1)[1]
                    else:
                        desc_part = ""
                    
                    current_pkg = {
                        "repo": repo_name.split("/")[0],
                        "name": repo_name.split("/")[1],
                        "version": name_ver,
                        "description": desc_part
                    }
        
        # Add the last package if it exists
        if current_pkg and "description" not in current_pkg:
            current_pkg["description"] = ""
            results.append(current_pkg)
        
        self.log_box.add_log(f"Found {len(results)} packages matching '{query}'", "SUCCESS")
        
        # Display results
        if results:
            self.log_box.add_log("Search Results:", "SYSTEM")
            for i, pkg in enumerate(results[:10], 1):
                self.log_box.add_log(f"{i}. {COLORS['bold']}{pkg['repo']}/{pkg['name']}{COLORS['reset']} {pkg['version']}")
                self.log_box.add_log(f"   {pkg['description']}")
            
            if len(results) > 10:
                self.log_box.add_log(f"...and {len(results) - 10} more results not shown", "INFO")
        
        return results

    async def get_info(self, package):
        """Get detailed info about a package"""
        self.log_box.add_log(f"Getting info for package '{package}'...", "SYSTEM")
        
        cmd = ["pacman", "-Si", package]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            self.log_box.add_log(f"Failed to get info: {stderr.decode().strip()}", "ERROR")
            return None
        
        self.log_box.add_log(f"Package Information for {COLORS['bold']}{package}{COLORS['reset']}:", "SYSTEM")
        for line in stdout.decode().splitlines():
            self.log_box.add_log(line)
        
        return stdout.decode()
        
    async def install(self, packages):
        """Install packages with progress tracking"""
        self.log_box.add_log(f"Installing {len(packages)} package(s): {', '.join(packages)}", "SYSTEM")
        
        # Check if user wants to see what would be installed first
        self.log_box.add_log("Calculating dependencies...", "INFO")
        
        # Get the list of packages that would be installed
        cmd = ["pacman", "-S", "--print", "--noconfirm"] + packages
        process = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            self.log_box.add_log(f"Failed to calculate dependencies: {stderr.decode().strip()}", "ERROR")
            return process.returncode
            
        # Parse the output to get total packages
        to_install = []
        for line in stdout.decode().splitlines():
            if "installing " in line.lower():
                pkg_name = line.split("installing ")[1].strip()
                to_install.append(pkg_name)
        
        self.log_box.add_log(f"Will install {len(to_install)} package(s) (including dependencies)", "INFO")
        
        # Run the actual installation
        cmd = ["sudo", "pacman", "-S", "--noconfirm"] + packages
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        # Track progress
        current_package = None
        progress_tasks = {}
        
        while True:
            line = await process.stdout.readline()
            if not line:
                break
                
            line_str = line.decode('utf-8', errors='replace').rstrip()
            
            # Log everything
            self.log_box.add_log(line_str, "INFO")
            
            # Look for download progress
            dl_match = re.search(r'\[#+(?: +)?\] (\d+)%', line_str)
            if dl_match and current_package:
                progress = int(dl_match.group(1))
                
                # Update progress bar
                if current_package in progress_tasks:
                    progress_tasks[current_package]["progress"] = progress
                else:
                    # Start new progress task
                    progress_tasks[current_package] = {
                        "progress": progress,
                        "task": asyncio.create_task(
                            self._animate_progress(current_package, progress)
                        )
                    }
            
            # Look for package installation start
            pkg_match = re.search(r'installing (.+?)\.\.\.', line_str, re.IGNORECASE)
            if pkg_match:
                current_package = pkg_match.group(1).strip()
                # Start at 0%
                progress_tasks[current_package] = {
                    "progress": 0,
                    "task": asyncio.create_task(
                        self._animate_progress(current_package, 0)
                    )
                }
                
        # Clean up any remaining progress tasks
        for pkg_data in progress_tasks.values():
            if "task" in pkg_data and not pkg_data["task"].done():
                pkg_data["task"].cancel()
                try:
                    await pkg_data["task"]
                except asyncio.CancelledError:
                    pass
        
        # Wait for process to finish
        await process.wait()
        
        if process.returncode == 0:
            self.log_box.add_log("Installation completed successfully!", "SUCCESS")
        else:
            self.log_box.add_log(f"Installation failed (exit code: {process.returncode})", "ERROR")
            
        return process.returncode
    
    async def _animate_progress(self, package, initial_progress=0):
        """Animate a progress bar for a package"""
        cols = shutil.get_terminal_size().columns - 30  # Leave room for name and percentage
        progress = initial_progress
        
        # Trim package name if too long
        if len(package) > 20:
            package = package[:17] + "..."
        
        # Pad package name
        package = f"{package:<20}"
        
        while progress < 100:
            bar_width = cols - 5
            filled_width = int(bar_width * progress / 100)
            
            # Determine pacman position
            pac_pos = min(filled_width, bar_width - 1)
            
            # Build the bar
            bar = DOT * pac_pos
            pac = PACMAN_EAT if progress % 2 == 0 else PACMAN
            bar += pac
            bar += " " * (bar_width - pac_pos - 1)
            
            # Print the progress bar
            print(f"\r{package} [{bar}] {progress:3d}%", end="", flush=True)
            
            try:
                await asyncio.sleep(0.1)
                progress += 1
            except asyncio.CancelledError:
                # Final state
                bar_width = cols - 5
                bar = DOT * bar_width
                print(f"\r{package} [{bar}] 100%", flush=True)
                raise
        
        # Completed state
        bar = DOT * (cols - 5 - 1) + GHOST
        print(f"\r{package} [{bar}] 100%", flush=True)

class KeyboardHandler:
    """Handle keyboard input for scrolling and navigation"""
    def __init__(self, log_box):
        self.log_box = log_box
        self.running = True
        self._setup_terminal()
        
    def _setup_terminal(self):
        # Save terminal settings
        self.original_stty = os.popen('stty -g').read().strip()
        # Set raw mode
        os.system('stty raw -echo')
        
    def _restore_terminal(self):
        # Restore terminal settings
        os.system(f'stty {self.original_stty}')
    
    def stop(self):
        self.running = False
        self._restore_terminal()
    
    async def input_loop(self):
        """Main input loop"""
        try:
            while self.running:
                # Non-blocking read
                if sys.stdin in await asyncio.wait([asyncio.create_task(
                    asyncio.get_event_loop().run_in_executor(None, sys.stdin.buffer.read1, 1)
                )], timeout=0.1)[0]):
                    key = sys.stdin.buffer.read1(1).decode(errors='ignore')
                    
                    # Handle escape sequences
                    if key == '\x1b':  # ESC
                        # Check for arrow keys (ESC [ A/B)
                        if sys.stdin in await asyncio.wait([asyncio.create_task(
                            asyncio.get_event_loop().run_in_executor(None, sys.stdin.buffer.read1, 1)
                        )], timeout=0.05)[0]):
                            next_key = sys.stdin.buffer.read1(1).decode(errors='ignore')
                            
                            if next_key == '[':
                                if sys.stdin in await asyncio.wait([asyncio.create_task(
                                    asyncio.get_event_loop().run_in_executor(None, sys.stdin.buffer.read1, 1)
                                )], timeout=0.05)[0]):
                                    arrow_key = sys.stdin.buffer.read1(1).decode(errors='ignore')
                                    
                                    if arrow_key == 'A':  # Up arrow
                                        self.log_box.scroll_up()
                                    elif arrow_key == 'B':  # Down arrow
                                        self.log_box.scroll_down()
                    elif key in ('f', 'F'):
                        self.log_box.toggle_follow()
                    elif key in ('q', 'Q', '\x03'):  # q, Q or Ctrl+C
                        self.running = False
                        
                await asyncio.sleep(0.1)
        finally:
            self._restore_terminal()

async def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Arch Linux Package Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Install command
    install_parser = subparsers.add_parser("install", help="Install packages")
    install_parser.add_argument("packages", nargs="+", help="Packages to install")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for packages")
    search_parser.add_argument("query", help="Search query")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Get information about a package")
    info_parser.add_argument("package", help="Package name")
    
    # Parse args
    args = parser.parse_args()
    
    # Create the log box
    log_box = ScrollableLogBox(height=15, title="Arch Linux Package Manager")
    
    # Initialize package manager
    pkg_manager = PackageManager(log_box)
    
    # Create keyboard handler
    kb_handler = KeyboardHandler(log_box)
    kb_task = asyncio.create_task(kb_handler.input_loop())
    
    try:
        # Process command
        if args.command == "install":
            log_box.add_log(f"Starting installation of {len(args.packages)} package(s)", "SYSTEM")
            await pkg_manager.install(args.packages)
        elif args.command == "search":
            log_box.add_log(f"Searching for '{args.query}'", "SYSTEM")
            await pkg_manager.search(args.query)
        elif args.command == "info":
            log_box.add_log(f"Getting info for '{args.package}'", "SYSTEM")
            await pkg_manager.get_info(args.package)
        else:
            log_box.add_log("No command specified. Use --help for usage information.", "ERROR")
            kb_handler.stop()
            return 1
        
        # Wait for user to exit
        log_box.add_log("Press 'q' to exit, arrow keys to scroll, 'f' to toggle log following", "SYSTEM")
        await kb_task
        
    except asyncio.CancelledError:
        log_box.add_log("Operation cancelled.", "WARN")
    finally:
        # Cleanup
        kb_handler.stop()
        if not kb_task.done():
            kb_task.cancel()
            try:
                await kb_task
            except asyncio.CancelledError:
                pass
        
        print("\n\nExiting Arch Linux Package Manager")
    
    return 0

if __name__ == "__main__":
    # Handle signals
    def signal_handler(sig, frame):
        print("\nReceived signal, exiting...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(130)
