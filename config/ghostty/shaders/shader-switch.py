#!/usr/bin/env python3
import os
import signal
import json
import subprocess
import random
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gio, GLib, Adw, Gdk, GObject

# --- Configuration ---
APP_ID = "com.github.vanilla.GhosttyShaderSwitcher"
CONFIG_DIR = os.path.expanduser("~/.config/ghostty-shader-switcher")
SHADER_DIR = os.path.expanduser("~/.config/ghostty/shaders")
CONFIG_PATH = os.path.expanduser("~/.config/ghostty/config")
FAVORITES_PATH = os.path.join(CONFIG_DIR, "favorites.json")
RECENT_PATH = os.path.join(CONFIG_DIR, "recent.json")
APP_SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")
SHADER_CACHE_PATH = os.path.join(CONFIG_DIR, "shader_cache.json")
GHOSTTY_CONFIG_KEY = "custom-shader"


class ShaderItem(GObject.Object):
    __gtype_name__ = "ShaderItem"
    name = GObject.Property(type=str)
    path = GObject.Property(type=str)
    size_str = GObject.Property(type=str)
    modified_str = GObject.Property(type=str)
    is_favorite = GObject.Property(type=bool, default=False)
    is_active = GObject.Property(type=bool, default=False)
    preview_text = GObject.Property(type=str, default="")

    def __init__(self, name, path):
        super().__init__()
        self.name = name
        self.path = path
        try:
            stat = os.stat(path)
            self.size_str = f"{stat.st_size / 1024:.1f} KB"
            self.modified_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y")
            
            # Cache shader preview
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:5]  # First 5 lines for preview
                    self.preview_text = ''.join(lines).strip()
            except:
                self.preview_text = "Preview unavailable"
        except FileNotFoundError:
            self.size_str = "N/A"
            self.modified_str = "File not found"
            self.preview_text = "File not found"


class ShaderWatcher:
    def __init__(self, callback):
        self.callback = callback
        self.watching = False
        self.last_check = {}
        
    def start_watching(self):
        if self.watching:
            return
        self.watching = True
        threading.Thread(target=self._watch_loop, daemon=True).start()
    
    def stop_watching(self):
        self.watching = False
    
    def _watch_loop(self):
        while self.watching:
            try:
                if os.path.exists(SHADER_DIR):
                    current_files = {}
                    for file_path in Path(SHADER_DIR).glob("*"):
                        if file_path.suffix.lower() in ('.glsl', '.frag', '.vert', '.fs', '.vs'):
                            current_files[str(file_path)] = file_path.stat().st_mtime
                    
                    if current_files != self.last_check:
                        self.last_check = current_files
                        GLib.idle_add(self.callback)
                
                time.sleep(1)  # Check every second
            except Exception:
                pass


class ShaderSwitcher(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.window = None
        self.settings = None
        self.toast_overlay = None
        self.search_revealer = None
        self.shutting_down = False
        self.all_shader_items = []
        self.favorites = set()
        self.recent_shaders = []
        self._active_shader_name = None
        self.all_list_box = Gtk.ListBox()
        self.favorites_list_box = Gtk.ListBox()
        self.recent_list_box = Gtk.ListBox()
        self.all_search_entry = Gtk.SearchEntry()
        self.shader_watcher = ShaderWatcher(self.on_shader_directory_changed)
        self.ghostty_process_cache = {}
        self.last_ghostty_check = 0

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.shutting_down = True
        self.shader_watcher.stop_watching()
        if self.window: self.window.close()
        self.quit()

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.load_app_settings()
        self.load_data_files()
        self.create_actions()
        self.setup_keyboard_shortcuts()
        style_manager = Adw.StyleManager.get_default()
        color_scheme = self.settings.get("color_scheme", 0)
        if color_scheme == 1: style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif color_scheme == 2: style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else: style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def setup_keyboard_shortcuts(self):
        shortcuts = [
            ("app.search", ["<Control>f"]),
            ("app.refresh", ["<Control>r", "F5"]),
            ("app.random", ["<Control><Shift>r"]),
            ("app.escape", ["Escape"]),
            ("app.apply_first", ["Return"]),
            ("app.toggle_favorite", ["<Control>d"]),
            ("app.quick_disable", ["<Control><Shift>d"])
        ]
        
        for action_name, accels in shortcuts:
            if "." not in action_name:
                continue
            action_simple_name = action_name.split(".", 1)[1]
            if action_simple_name == "search":
                action = Gio.SimpleAction.new("search", None)
                action.connect("activate", self.toggle_search)
                self.add_action(action)
            elif action_simple_name == "escape":
                action = Gio.SimpleAction.new("escape", None)
                action.connect("activate", self.close_search)
                self.add_action(action)
            elif action_simple_name == "apply_first":
                action = Gio.SimpleAction.new("apply_first", None)
                action.connect("activate", self.apply_first_shader)
                self.add_action(action)
            elif action_simple_name == "toggle_favorite":
                action = Gio.SimpleAction.new("toggle_favorite", None)
                action.connect("activate", self.toggle_selected_favorite)
                self.add_action(action)
            elif action_simple_name == "quick_disable":
                action = Gio.SimpleAction.new("quick_disable", None)
                action.connect("activate", lambda *args: self.disable_shader_quick())
                self.add_action(action)
            
            self.set_accels_for_action(action_name, accels)

    def do_activate(self):
        if not self.window:
            self.window = Adw.ApplicationWindow(application=self, title="Ghostty Shader Switcher")
            self.window.set_default_size(800, 900)
            self.window.connect("close-request", self.on_window_close)
            self.setup_custom_css()
            
            self.toast_overlay = Adw.ToastOverlay()
            self.window.set_content(self.toast_overlay)
            main_content = self._create_main_ui()
            self.toast_overlay.set_child(main_content)
            
            self._active_shader_name = self.get_current_shader_from_config()
            self.refresh_all_lists()
            self.shader_watcher.start_watching()
            
            if self.settings.get("random_on_startup", False): 
                self.set_random_shader()
                
        self.window.present()

    def setup_custom_css(self):
        css_provider = Gtk.CssProvider()
        css = """
        .active-shader-row { 
            background: alpha(@accent_color, 0.1); 
            border-left: 3px solid @accent_color;
        }
        .random-btn { 
            background: linear-gradient(45deg, @accent_color, @success_color);
            color: white;
        }
        .shader-preview-box {
            background: alpha(@window_bg_color, 0.5);
        }
        """
        css_provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_window_close(self, window):
        self.shutting_down = True
        self.shader_watcher.stop_watching()
        return False

    def on_shader_directory_changed(self):
        if not self.shutting_down:
            self.refresh_all_lists()

    def _create_main_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header_bar = self._create_header_bar()
        main_box.append(header_bar)
        
        # Quick actions bar
        quick_actions = self._create_quick_actions()
        main_box.append(quick_actions)
        
        self.view_stack = Adw.ViewStack()
        view_switcher = Adw.ViewSwitcher(stack=self.view_stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        
        all_page = self._create_shader_page(self.all_list_box, is_main_list=True)
        favorites_page = self._create_shader_page(self.favorites_list_box)
        recent_page = self._create_shader_page(self.recent_list_box)
        settings_page = self._create_settings_page()
        
        self.view_stack.add_titled_with_icon(all_page, "all", "All Shaders", "view-grid-symbolic")
        self.view_stack.add_titled_with_icon(favorites_page, "favorites", "Favorites", "star-symbolic")
        self.view_stack.add_titled_with_icon(recent_page, "recent", "Recent", "document-open-recent-symbolic")
        self.view_stack.add_titled_with_icon(settings_page, "settings", "Settings", "preferences-system-symbolic")
        
        switcher_box = Gtk.Box(halign=Gtk.Align.CENTER, margin_top=8, margin_bottom=8)
        switcher_box.append(view_switcher)
        main_box.append(switcher_box)
        main_box.append(self.view_stack)
        
        self.all_search_entry.connect("search-changed", self.on_search_changed)
        self.all_search_entry.connect("activate", self.on_search_activate)
        return main_box

    def _create_quick_actions(self):
        quick_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, 
                           halign=Gtk.Align.CENTER)
        
        random_btn = Gtk.Button(label="Random", icon_name="media-playlist-shuffle-symbolic", 
                               css_classes=["random-btn"])
        random_btn.connect("clicked", lambda x: self.set_random_shader())
        quick_box.append(random_btn)
        
        disable_btn = Gtk.Button(label="Disable", icon_name="edit-clear-symbolic", 
                                css_classes=["destructive-action"])
        disable_btn.connect("clicked", lambda x: self.disable_shader_quick())
        quick_box.append(disable_btn)
        
        reload_ghostty_btn = Gtk.Button(label="Reload Ghostty", icon_name="view-refresh-symbolic",
                                       css_classes=["suggested-action"])
        reload_ghostty_btn.connect("clicked", lambda x: self.smart_ghostty_reload())
        quick_box.append(reload_ghostty_btn)
        
        return quick_box

    def _create_header_bar(self):
        header_bar = Adw.HeaderBar()
        
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.CENTER)
        self.status_icon = Gtk.Image()
        self.status_label = Gtk.Label(css_classes=["heading"])
        self.shader_stats_label = Gtk.Label()
        
        status_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        status_vbox.append(self.status_label)
        status_vbox.append(self.shader_stats_label)
        
        status_box.append(self.status_icon)
        status_box.append(status_vbox)
        header_bar.set_title_widget(status_box)
        
        search_btn = Gtk.Button(icon_name="system-search-symbolic", tooltip_text="Search (Ctrl+F)")
        search_btn.connect("clicked", self.toggle_search)
        header_bar.pack_start(search_btn)
        
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text="Menu")
        menu = Gio.Menu()
        menu.append("Open Shader Folder", "app.open_folder")
        menu.append("Import Shader...", "app.import")
        menu.append("Create New Shader", "app.create_shader")
        
        advanced_section = Gio.Menu()
        advanced_section.append("Backup Shaders", "app.backup_shaders")
        advanced_section.append("Check Ghostty Status", "app.check_ghostty")
        menu.append_section("Advanced", advanced_section)
        
        menu_btn.set_menu_model(menu)
        header_bar.pack_end(menu_btn)
        
        return header_bar

    def _create_shader_page(self, list_box, is_main_list=False):
        page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        if is_main_list:
            self.search_revealer = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN, 
                                               transition_duration=250)
            search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, 
                               margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
            self.all_search_entry.set_hexpand(True)
            self.all_search_entry.set_placeholder_text("Search shaders...")
            
            close_search_btn = Gtk.Button(icon_name="window-close-symbolic", tooltip_text="Close Search (Esc)")
            close_search_btn.connect("clicked", self.close_search)
            
            search_box.append(self.all_search_entry)
            search_box.append(close_search_btn)
            self.search_revealer.set_child(search_box)
            page_box.append(self.search_revealer)
        
        scrolled_window = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        list_box.connect("row-activated", self.on_row_activated)
        
        status_page = Adw.StatusPage(vexpand=True, icon_name="folder-documents-symbolic", 
                                   title="No Shaders Found", 
                                   description="Add some .glsl, .frag, .vert, .fs, or .vs files to get started.")
        
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, halign=Gtk.Align.CENTER)
        
        open_folder_btn = Gtk.Button(label="Open Shader Folder", css_classes=["suggested-action"])
        open_folder_btn.connect("clicked", self.open_shader_folder)
        
        create_shader_btn = Gtk.Button(label="Create New Shader")
        create_shader_btn.connect("clicked", self.create_new_shader)
        
        button_box.append(open_folder_btn)
        button_box.append(create_shader_btn)
        status_page.set_child(button_box)
        
        list_box.set_placeholder(status_page)
        scrolled_window.set_child(list_box)
        page_box.append(scrolled_window)
        
        return page_box

    def _create_shader_row(self, item):
        adw_row = Adw.ActionRow(title=item.name, 
                                 subtitle=f"Modified: {item.modified_str}  •  Size: {item.size_str}")
        
        fav_btn = Gtk.ToggleButton(active=item.is_favorite, 
                                  valign=Gtk.Align.CENTER, tooltip_text="Toggle Favorite")
        fav_btn.set_icon_name("starred-symbolic" if item.is_favorite else "non-starred-symbolic")
        fav_btn.connect("toggled", self.on_favorite_toggled, item)
        adw_row.add_prefix(fav_btn)
        
        active_icon = Gtk.Image(icon_name="media-playback-start-symbolic", 
                               visible=item.is_active, tooltip_text="Currently Active")
        adw_row.add_prefix(active_icon)
        
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        edit_btn = Gtk.Button(icon_name="document-edit-symbolic", 
                             valign=Gtk.Align.CENTER, tooltip_text="Edit Shader File")
        edit_btn.connect("clicked", self.edit_shader, item)
        
        duplicate_btn = Gtk.Button(icon_name="edit-copy-symbolic", 
                                  valign=Gtk.Align.CENTER, tooltip_text="Duplicate Shader")
        duplicate_btn.connect("clicked", self.duplicate_shader, item)
        
        delete_btn = Gtk.Button(icon_name="user-trash-symbolic", css_classes=["destructive-action"], 
                               valign=Gtk.Align.CENTER, tooltip_text="Delete Shader File")
        delete_btn.connect("clicked", self._on_delete_clicked, item)
        
        apply_btn = Gtk.Button(label="Apply", icon_name="checkmark-symbolic", 
                              valign=Gtk.Align.CENTER, tooltip_text="Apply This Shader")
        apply_btn.connect("clicked", lambda b: self.set_shader(item.name))
        
        button_box.append(edit_btn)
        button_box.append(duplicate_btn)
        button_box.append(delete_btn)
        button_box.append(apply_btn)
        adw_row.add_suffix(button_box)
        
        list_box_row = Gtk.ListBoxRow()
        list_box_row.set_child(adw_row)
        list_box_row.shader_name = item.name
        
        if item.is_active:
            list_box_row.add_css_class("active-shader-row")
            
        return list_box_row

    def _on_delete_clicked(self, button, item):
        dialog = Adw.MessageDialog(transient_for=self.window, modal=True, 
                                  heading=f"Delete {item.name}?", 
                                  body="This action is permanent and cannot be undone.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_delete_response, item)
        dialog.present()

    def _on_delete_response(self, dialog, response, item):
        if response == "delete":
            try:
                os.remove(item.path)
                self.show_toast(f"Deleted {item.name}")
                self.refresh_all_lists()
            except OSError as e:
                self.show_toast(f"Error deleting file: {e}", is_error=True)

    def duplicate_shader(self, button, item):
        try:
            base_name = Path(item.name).stem
            extension = Path(item.name).suffix
            counter = 1
            
            while True:
                new_name = f"{base_name}_copy{counter}{extension}"
                new_path = os.path.join(SHADER_DIR, new_name)
                if not os.path.exists(new_path):
                    break
                counter += 1
            
            shutil.copy2(item.path, new_path)
            self.show_toast(f"Duplicated as {new_name}")
            self.refresh_all_lists()
        except Exception as e:
            self.show_toast(f"Error duplicating shader: {e}", is_error=True)

    def _update_list_box(self, list_box, shader_items):
        child = list_box.get_first_child()
        while child:
            list_box.remove(child)
            child = list_box.get_first_child()
        for item in shader_items:
            row = self._create_shader_row(item)
            list_box.append(row)

    def on_row_activated(self, list_box, row):
        if hasattr(row, 'shader_name'):
            self.set_shader(row.shader_name)

    def _create_settings_page(self):
        page = Adw.PreferencesPage()
        
        general_group = Adw.PreferencesGroup(title="General")
        page.add(general_group)
        
        row_random = Adw.SwitchRow(title="Random Shader on Startup", 
                                  subtitle="Apply a random shader every time you launch the app.", 
                                  active=self.settings.get("random_on_startup", False))
        row_random.connect("notify::active", self._on_setting_changed, "random_on_startup")
        general_group.add(row_random)
        
        row_auto_reload = Adw.SwitchRow(title="Smart Ghostty Reload", 
                                       subtitle="Automatically reload Ghostty safely when switching shaders.",
                                       active=self.settings.get("smart_reload", True))
        row_auto_reload.connect("notify::active", self._on_setting_changed, "smart_reload")
        general_group.add(row_auto_reload)
        
        row_preview = Adw.SwitchRow(title="Show Shader Preview", 
                                   subtitle="Display shader code preview in expandable rows.",
                                   active=self.settings.get("show_shader_preview", True))
        row_preview.connect("notify::active", self._on_setting_changed, "show_shader_preview")
        general_group.add(row_preview)
        
        appearance_group = Adw.PreferencesGroup(title="Appearance")
        page.add(appearance_group)
        
        color_models = Gtk.StringList.new(["System Default", "Light", "Dark"])
        row_color = Adw.ComboRow(title="Color Scheme", subtitle="Choose the application theme.", 
                                model=color_models, selected=self.settings.get("color_scheme", 0))
        row_color.connect("notify::selected", self._on_setting_changed, "color_scheme")
        appearance_group.add(row_color)
        
        advanced_group = Adw.PreferencesGroup(title="Advanced")
        page.add(advanced_group)
        
        editor_row = Adw.EntryRow(title="Preferred Editor", 
                                 text="Command to use for editing shaders (leave empty for system default)")
        editor_row.set_text(self.settings.get("preferred_editor", ""))
        editor_row.connect("changed", self._on_editor_changed)
        advanced_group.add(editor_row)
        
        return page

    def _on_editor_changed(self, entry):
        self.settings["preferred_editor"] = entry.get_text()
        self.save_app_settings()

    def _on_setting_changed(self, widget, _, key):
        if isinstance(widget, Adw.SwitchRow): 
            self.settings[key] = widget.get_active()
        elif isinstance(widget, Adw.ComboRow): 
            self.settings[key] = widget.get_selected()
            
        if key == "color_scheme":
            sm = Adw.StyleManager.get_default()
            s = self.settings[key]
            if s == 1: sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            elif s == 2: sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            else: sm.set_color_scheme(Adw.ColorScheme.DEFAULT)
        elif key == "show_shader_preview":
            self.refresh_all_lists()
            
        self.save_app_settings()

    def apply_first_shader(self, *args):
        first_row = self.all_list_box.get_row_at_index(0)
        if first_row and hasattr(first_row, 'shader_name'):
            self.set_shader(first_row.shader_name)

    def toggle_selected_favorite(self, *args):
        # This would require tracking selected row - simplified for now
        self.show_toast("Use the star button on individual shaders to toggle favorites")

    def toggle_search(self, *args):
        if self.search_revealer:
            is_revealed = self.search_revealer.get_reveal_child()
            self.search_revealer.set_reveal_child(not is_revealed)
            if not is_revealed: 
                GLib.timeout_add(250, lambda: self.all_search_entry.grab_focus())
            else: 
                self.all_search_entry.set_text("")

    def close_search(self, *args):
        if self.search_revealer and self.search_revealer.get_reveal_child():
            self.search_revealer.set_reveal_child(False)
            self.all_search_entry.set_text("")

    def on_search_changed(self, entry):
        search_term = entry.get_text().lower()
        if not search_term:
            filtered_items = self.all_shader_items
        else:
            filtered_items = [item for item in self.all_shader_items 
                            if search_term in item.name.lower() or 
                               search_term in item.preview_text.lower()]
        self._update_list_box(self.all_list_box, filtered_items)

    def on_search_activate(self, entry):
        first_row = self.all_list_box.get_row_at_index(0)
        if first_row and hasattr(first_row, 'shader_name'):
            self.set_shader(first_row.shader_name)

    def load_data_files(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            if os.path.exists(FAVORITES_PATH):
                with open(FAVORITES_PATH, 'r') as f: 
                    self.favorites = set(json.load(f))
        except Exception: 
            self.favorites = set()
            
        try:
            if os.path.exists(RECENT_PATH):
                with open(RECENT_PATH, 'r') as f: 
                    self.recent_shaders = json.load(f)
        except Exception: 
            self.recent_shaders = []

    def load_app_settings(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        defaults = {
            "random_on_startup": False, 
            "color_scheme": 0,
            "smart_reload": True,
            "show_shader_preview": True,
            "preferred_editor": ""
        }
        
        if os.path.exists(APP_SETTINGS_PATH):
            try:
                with open(APP_SETTINGS_PATH, 'r') as f: 
                    self.settings = {**defaults, **json.load(f)}
            except Exception: 
                self.settings = defaults
        else: 
            self.settings = defaults

    def save_app_settings(self):
        try:
            with open(APP_SETTINGS_PATH, 'w') as f: 
                json.dump(self.settings, f, indent=4)
        except IOError as e: 
            self.show_toast(f"Error saving settings: {e}", is_error=True)

    def refresh_all_lists(self, *args):
        if self.shutting_down: 
            return
        try:
            self._active_shader_name = self.get_current_shader_from_config()
            os.makedirs(SHADER_DIR, exist_ok=True)
            valid_exts = (".glsl", ".frag", ".vert", ".fs", ".vs")
            files = sorted([f for f in os.listdir(SHADER_DIR) if f.lower().endswith(valid_exts)], 
                          key=str.lower)
            
            self.all_shader_items = [ShaderItem(name, os.path.join(SHADER_DIR, name)) for name in files]
            
            for item in self.all_shader_items:
                item.is_active = (item.name == self._active_shader_name)
                item.is_favorite = (item.name in self.favorites)
            
            self.on_search_changed(self.all_search_entry)
            
            favs = [s for s in self.all_shader_items if s.is_favorite]
            recents = [s for name in self.recent_shaders[:15] 
                      if (s := next((sh for sh in self.all_shader_items if sh.name == name), None))]
            
            self._update_list_box(self.favorites_list_box, favs)
            self._update_list_box(self.recent_list_box, recents)
            self.update_status_label()
            
        except Exception as e:
            self.show_toast(f"Error reading shaders: {e}", is_error=True)

    def create_actions(self):
        actions = [
            ("random", self.set_random_shader), 
            ("refresh", self.refresh_all_lists), 
            ("open_folder", self.open_shader_folder), 
            ("import", self.import_shader), 
            ("disable", self.disable_shader_with_confirmation),
            ("create_shader", self.create_new_shader),
            ("backup_shaders", self.backup_shaders),
            ("check_ghostty", self.check_ghostty_status)
        ]
        
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def on_favorite_toggled(self, button, item):
        is_active = button.get_active()
        button.set_icon_name("starred-symbolic" if is_active else "non-starred-symbolic")
        
        if is_active:
            self.favorites.add(item.name)
            self.show_toast(f"⭐ Added {item.name} to favorites")
        else:
            self.favorites.discard(item.name)
            self.show_toast(f"Removed {item.name} from favorites")
            
        self.save_favorites()
        self.refresh_all_lists()

    def save_favorites(self):
        try:
            with open(FAVORITES_PATH, 'w') as f: 
                json.dump(list(self.favorites), f, indent=4)
        except IOError as e: 
            self.show_toast(f"Error saving favorites: {e}", is_error=True)

    def is_ghostty_running(self):
        """Check if Ghostty is currently running"""
        try:
            result = subprocess.run(["pgrep", "-x", "ghostty"], 
                                  capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except:
            return False

    def get_ghostty_pids(self):
        """Get all Ghostty process IDs"""
        try:
            result = subprocess.run(["pgrep", "-x", "ghostty"], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip()]
            return []
        except:
            return []

    def smart_ghostty_reload(self):
        """Intelligently reload Ghostty based on current state"""
        if not self.is_ghostty_running():
            self.show_toast("Ghostty is not running", is_error=True)
            return
            
        # Try graceful reload first
        try:
            subprocess.run(["pkill", "-SIGHUP", "ghostty"], check=False, timeout=3)
            self.show_toast("✅ Ghostty reloaded successfully")
        except subprocess.TimeoutExpired:
            # If graceful reload fails, offer to restart
            dialog = Adw.MessageDialog(
                transient_for=self.window, 
                modal=True,
                heading="Reload Failed", 
                body="Graceful reload failed. Would you like to restart Ghostty? This will close all terminals."
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("restart", "Restart Ghostty")
            dialog.set_response_appearance("restart", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.connect("response", self._on_restart_ghostty_response)
            dialog.present()
        except Exception as e:
            self.show_toast(f"Error reloading Ghostty: {e}", is_error=True)

    def _on_restart_ghostty_response(self, dialog, response):
        if response == "restart":
            try:
                subprocess.run(["pkill", "-TERM", "ghostty"], check=False, timeout=3)
                # Wait a moment, then try to start it again
                GLib.timeout_add(1000, self._restart_ghostty_delayed)
                self.show_toast("Restarting Ghostty...")
            except Exception as e:
                self.show_toast(f"Error restarting Ghostty: {e}", is_error=True)

    def _restart_ghostty_delayed(self):
        try:
            subprocess.Popen(["ghostty"], start_new_session=True)
            self.show_toast("Ghostty restarted")
        except Exception as e:
            self.show_toast(f"Could not restart Ghostty: {e}", is_error=True)
        return False

    def _write_shader_to_config_safe(self, shader_path=None):
        """Safely write shader configuration without causing crashes"""
        if not os.path.exists(os.path.dirname(CONFIG_PATH)):
            os.makedirs(os.path.dirname(CONFIG_PATH))

        current_lines = []
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                current_lines = f.readlines()
        
        new_lines = []
        key_found = False
        
        for line in current_lines:
            if line.strip().startswith(GHOSTTY_CONFIG_KEY):
                key_found = True
                if shader_path:
                    new_lines.append(f'{GHOSTTY_CONFIG_KEY} = "{shader_path}"\n')
            else:
                new_lines.append(line)
        
        if not key_found and shader_path:
            new_lines.append(f'\n{GHOSTTY_CONFIG_KEY} = "{shader_path}"\n')
        
        # Write atomically
        tmp_path = CONFIG_PATH + ".tmp"
        with open(tmp_path, 'w') as f:
            f.writelines(new_lines)
        
        os.replace(tmp_path, CONFIG_PATH)

        # Smart reload based on settings
        if self.settings.get("smart_reload", True):
            GLib.timeout_add(100, self._delayed_ghostty_signal)
        else:
            self.show_toast("💡 Manually reload Ghostty to see changes", timeout=3)

    def _delayed_ghostty_signal(self):
        """Send reload signal with delay to prevent crashes"""
        try:
            if self.is_ghostty_running():
                subprocess.run(["pkill", "-SIGHUP", "ghostty"], check=False, timeout=2)
        except:
            pass
        return False

    def set_shader(self, shader_name):
        if self.shutting_down: 
            return
            
        shader_path = os.path.join(SHADER_DIR, shader_name)
        if not os.path.isfile(shader_path):
            self.show_toast(f"Shader not found: {shader_name}", is_error=True)
            self.refresh_all_lists()
            return
        
        self._write_shader_to_config_safe(shader_path)
        
        # Update recent shaders
        if shader_name in self.recent_shaders: 
            self.recent_shaders.remove(shader_name)
        self.recent_shaders.insert(0, shader_name)
        self.recent_shaders = self.recent_shaders[:15]
        
        try:
            with open(RECENT_PATH, 'w') as f: 
                json.dump(self.recent_shaders, f, indent=4)
        except Exception:
            pass
        
        self.show_toast(f"✅ Applied shader: {shader_name}")
        self.refresh_all_lists()

    def edit_shader(self, button, item):
        """Open shader in preferred editor"""
        editor = self.settings.get("preferred_editor", "").strip()
        
        if not editor:
            # Use system default
            uri = GLib.filename_to_uri(item.path, None)
            Gtk.show_uri(self.window, uri, Gdk.CURRENT_TIME)
        else:
            # Use preferred editor
            try:
                env_editor = os.environ.get('EDITOR', editor)
                subprocess.Popen([env_editor, item.path])
                self.show_toast(f"Opening {item.name} in {env_editor}")
            except Exception as e:
                self.show_toast(f"Error opening editor: {e}", is_error=True)
                # Fallback to system default
                uri = GLib.filename_to_uri(item.path, None)
                Gtk.show_uri(self.window, uri, Gdk.CURRENT_TIME)

    def set_random_shader(self, *args):
        if self.all_shader_items:
            item = random.choice(self.all_shader_items)
            self.set_shader(item.name)
            self.show_toast(f"🎲 Random shader: {item.name}")
        else: 
            self.show_toast("No shaders available to choose from.", is_error=True)

    def disable_shader_quick(self):
        """Quick disable without confirmation"""
        if not self.get_current_shader_from_config():
            self.show_toast("No active shader to disable.")
            return
            
        self._write_shader_to_config_safe(None)
        self.show_toast("✅ Shader disabled")
        self.refresh_all_lists()

    def disable_shader_with_confirmation(self, *args):
        if not self.get_current_shader_from_config():
            self.show_toast("No active shader to disable.")
            return
            
        dialog = Adw.MessageDialog(
            transient_for=self.window, 
            modal=True, 
            heading="Disable Shader?", 
            body="This will remove the custom shader from your Ghostty configuration."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("disable", "Disable")
        dialog.set_response_appearance("disable", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_disable_response)
        dialog.present()

    def _on_disable_response(self, dialog, response):
        if response == "disable":
            self.disable_shader_quick()

    def create_new_shader(self, *args):
        """Create a new shader file with template"""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            modal=True,
            heading="Create New Shader",
            body="Enter a name for your new shader:"
        )
        
        entry = Gtk.Entry()
        entry.set_placeholder_text("my_shader.glsl")
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        
        def on_response(dialog, response):
            if response == "create":
                name = entry.get_text().strip()
                if name:
                    self._create_shader_file(name)
            dialog.destroy()
        
        dialog.connect("response", on_response)
        dialog.present()
        entry.grab_focus()

    def _create_shader_file(self, name):
        """Create shader file with basic template"""
        if not name.endswith(('.glsl', '.frag', '.vert', '.fs', '.vs')):
            name += '.glsl'
            
        path = os.path.join(SHADER_DIR, name)
        
        if os.path.exists(path):
            self.show_toast(f"Shader {name} already exists", is_error=True)
            return
            
        template = """// New Ghostty Shader
// Author: 
// Description: 

#version 330 core

uniform float time;
uniform vec2 resolution;
uniform sampler2D texture;

in vec2 uv;
out vec4 fragColor;

void main() {
    vec4 color = texture2D(texture, uv);
    
    // Add your shader effects here
    
    fragColor = color;
}
"""
        
        try:
            os.makedirs(SHADER_DIR, exist_ok=True)
            with open(path, 'w') as f:
                f.write(template)
            
            self.show_toast(f"Created {name}")
            self.refresh_all_lists()
            
            # Open in editor immediately
            GLib.timeout_add(500, lambda: self.edit_shader(None, type('obj', (), {'path': path, 'name': name})()))
            
        except Exception as e:
            self.show_toast(f"Error creating shader: {e}", is_error=True)

    def import_shader(self, *args):
        dialog = Gtk.FileChooserDialog(
            title="Import Shader", 
            transient_for=self.window, 
            action=Gtk.FileChooserAction.OPEN, 
            modal=True
        )
        dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Import", Gtk.ResponseType.OK)
        
        # Add file filters
        filter_shader = Gtk.FileFilter()
        filter_shader.set_name("Shader Files")
        for ext in ["*.glsl", "*.frag", "*.vert", "*.fs", "*.vs"]:
            filter_shader.add_pattern(ext)
        dialog.add_filter(filter_shader)
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All Files")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)
        
        dialog.connect("response", self._on_import_response)
        dialog.present()

    def _on_import_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            file = dialog.get_file()
            try:
                dest_path = os.path.join(SHADER_DIR, file.get_basename())
                
                # Check if file exists and ask for overwrite
                if os.path.exists(dest_path):
                    overwrite_dialog = Adw.MessageDialog(
                        transient_for=self.window,
                        modal=True,
                        heading=f"File {file.get_basename()} exists",
                        body="Do you want to overwrite it?"
                    )
                    overwrite_dialog.add_response("cancel", "Cancel")
                    overwrite_dialog.add_response("overwrite", "Overwrite")
                    overwrite_dialog.set_response_appearance("overwrite", Adw.ResponseAppearance.DESTRUCTIVE)
                    
                    def on_overwrite_response(overwrite_dialog, response):
                        if response == "overwrite":
                            try:
                                shutil.copy2(file.get_path(), dest_path)
                                self.show_toast(f"Imported '{file.get_basename()}'")
                                self.refresh_all_lists()
                            except Exception as e:
                                self.show_toast(f"Failed to import: {e}", is_error=True)
                        overwrite_dialog.destroy()
                    
                    overwrite_dialog.connect("response", on_overwrite_response)
                    overwrite_dialog.present()
                else:
                    shutil.copy2(file.get_path(), dest_path)
                    self.show_toast(f"Imported '{file.get_basename()}'")
                    self.refresh_all_lists()
                    
            except Exception as e:
                self.show_toast(f"Failed to import: {e}", is_error=True)
        dialog.destroy()

    def backup_shaders(self, *args):
        """Create a backup of all shaders"""
        try:
            backup_dir = os.path.join(CONFIG_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"shaders_backup_{timestamp}.tar.gz")
            
            import tarfile
            with tarfile.open(backup_path, "w:gz") as tar:
                if os.path.exists(SHADER_DIR):
                    tar.add(SHADER_DIR, arcname="shaders")
            
            self.show_toast(f"✅ Backup created: {os.path.basename(backup_path)}")
            
        except Exception as e:
            self.show_toast(f"Error creating backup: {e}", is_error=True)

    def check_ghostty_status(self, *args):
        """Check and display Ghostty status"""
        is_running = self.is_ghostty_running()
        pids = self.get_ghostty_pids()
        
        if is_running:
            status = f"✅ Ghostty is running ({len(pids)} process{'es' if len(pids) != 1 else ''})"
        else:
            status = "❌ Ghostty is not running"
        
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            modal=True,
            heading="Ghostty Status",
            body=status
        )
        
        if is_running:
            dialog.add_response("reload", "Reload Ghostty")
            dialog.add_response("ok", "OK")
            dialog.set_response_appearance("reload", Adw.ResponseAppearance.SUGGESTED)
        else:
            dialog.add_response("start", "Start Ghostty")  
            dialog.add_response("ok", "OK")
            dialog.set_response_appearance("start", Adw.ResponseAppearance.SUGGESTED)
        
        def on_status_response(dialog, response):
            if response == "reload":
                self.smart_ghostty_reload()
            elif response == "start":
                try:
                    subprocess.Popen(["ghostty"], start_new_session=True)
                    self.show_toast("Starting Ghostty...")
                except Exception as e:
                    self.show_toast(f"Could not start Ghostty: {e}", is_error=True)
            dialog.destroy()
        
        dialog.connect("response", on_status_response)
        dialog.present()

    def open_shader_folder(self, *args):
        os.makedirs(SHADER_DIR, exist_ok=True)
        uri = GLib.filename_to_uri(SHADER_DIR, None)
        Gtk.show_uri(self.window, uri, Gdk.CURRENT_TIME)

    def get_current_shader_from_config(self, get_path=False):
        if not os.path.exists(CONFIG_PATH): 
            return None
        try:
            with open(CONFIG_PATH, 'r') as f:
                for line in f:
                    if line.strip().startswith(GHOSTTY_CONFIG_KEY):
                        path_part = line.split('=', 1)[1].strip().strip('"')
                        return path_part if get_path else os.path.basename(path_part)
        except Exception: 
            return None
        return None

    def update_status_label(self):
        shader_count = len(self.all_shader_items)
        
        if self._active_shader_name:
            self.status_icon.set_from_icon_name("object-select-symbolic")
            self.status_label.set_text(self._active_shader_name)
        else:
            self.status_icon.set_from_icon_name("edit-clear-symbolic")
            self.status_label.set_text("No Active Shader")
        
        # Update stats
        fav_count = len(self.favorites)
        stats_text = f"{shader_count} shader{'s' if shader_count != 1 else ''}"
        if fav_count > 0:
            stats_text += f" • {fav_count} favorite{'s' if fav_count != 1 else ''}"
        
        self.shader_stats_label.set_text(stats_text)

    def show_toast(self, message, is_error=False, timeout=None):
        toast = Adw.Toast(title=message)
        if timeout:
            toast.set_timeout(timeout)
        if is_error: 
            toast.add_css_class("error")
        self.toast_overlay.add_toast(toast)

    
if __name__ == "__main__":
    app = ShaderSwitcher()
    sys.exit(app.run(sys.argv))
