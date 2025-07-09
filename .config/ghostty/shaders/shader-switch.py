#!/usr/bin/env python3
import os
import signal
import json
import subprocess
import random
import shutil
from datetime import datetime
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
GHOSTTY_CONFIG_KEY = "custom-shader"


class ShaderItem(GObject.Object):
    __gtype_name__ = "ShaderItem"
    name = GObject.Property(type=str)
    path = GObject.Property(type=str)
    size_str = GObject.Property(type=str)
    modified_str = GObject.Property(type=str)
    is_favorite = GObject.Property(type=bool, default=False)
    is_active = GObject.Property(type=bool, default=False)

    def __init__(self, name, path):
        super().__init__()
        self.name = name
        self.path = path
        try:
            stat = os.stat(path)
            self.size_str = f"{stat.st_size / 1024:.1f} KB"
            self.modified_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y")
        except FileNotFoundError:
            self.size_str = "N/A"
            self.modified_str = "File not found"

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

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.shutting_down = True
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
        search_action = Gio.SimpleAction.new("search", None)
        search_action.connect("activate", self.toggle_search)
        self.add_action(search_action)
        self.set_accels_for_action("app.search", ["<Control>f"])
        self.set_accels_for_action("app.refresh", ["<Control>r", "F5"])
        self.set_accels_for_action("app.random", ["<Control><Shift>r"])
        escape_action = Gio.SimpleAction.new("escape", None)
        escape_action.connect("activate", self.close_search)
        self.add_action(escape_action)
        self.set_accels_for_action("app.escape", ["Escape"])

    def do_activate(self):
        if not self.window:
            self.window = Adw.ApplicationWindow(application=self, title="Ghostty Shader Switcher")
            self.window.set_default_size(700, 800)
            self.window.add_css_class("main-window")
            self.window.connect("close-request", self.on_window_close)
            self.toast_overlay = Adw.ToastOverlay()
            self.window.set_content(self.toast_overlay)
            main_content = self._create_main_ui()
            self.toast_overlay.set_child(main_content)
            self._active_shader_name = self.get_current_shader_from_config()
            self.refresh_all_lists()
            if self.settings.get("random_on_startup", False): self.set_random_shader()
        self.window.present()

    def on_window_close(self, window):
        self.shutting_down = True
        return False

    def _create_main_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header_bar = self._create_header_bar()
        main_box.append(header_bar)
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

    def _create_header_bar(self):
        header_bar = Adw.HeaderBar(css_classes=["flat"])
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.CENTER)
        self.status_icon = Gtk.Image()
        self.status_label = Gtk.Label(css_classes=["status-label"])
        status_box.append(self.status_icon); status_box.append(self.status_label)
        header_bar.set_title_widget(status_box)
        search_btn = Gtk.Button(icon_name="system-search-symbolic", tooltip_text="Search (Ctrl+F)", css_classes=["flat"])
        search_btn.connect("clicked", self.toggle_search)
        header_bar.pack_start(search_btn)
        quick_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0, css_classes=["linked"])
        random_btn = Gtk.Button(icon_name="media-playlist-shuffle-symbolic", tooltip_text="Random Shader (Ctrl+Shift+R)")
        random_btn.add_css_class("random-btn")
        random_btn.connect("clicked", lambda x: self.set_random_shader())
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh (Ctrl+R)", css_classes=["flat"])
        refresh_btn.connect("clicked", lambda x: self.refresh_all_lists())
        quick_box.append(random_btn); quick_box.append(refresh_btn)
        header_bar.pack_end(quick_box)
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text="Menu", css_classes=["flat"])
        menu = Gio.Menu()
        menu.append("Open Shader Folder", "app.open_folder")
        menu.append("Import Shader...", "app.import")
        disable_section = Gio.Menu()
        disable_section.append("Disable Active Shader", "app.disable")
        menu.append_section(None, disable_section)
        menu_btn.set_menu_model(menu)
        header_bar.pack_end(menu_btn)
        return header_bar

    def _create_shader_page(self, list_box, is_main_list=False):
        page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        if is_main_list:
            self.search_revealer = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN, transition_duration=250)
            search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
            self.all_search_entry.set_hexpand(True)
            close_search_btn = Gtk.Button(icon_name="window-close-symbolic", tooltip_text="Close Search (Esc)", css_classes=["flat"])
            close_search_btn.connect("clicked", self.close_search)
            search_box.append(self.all_search_entry)
            search_box.append(close_search_btn)
            self.search_revealer.set_child(search_box)
            page_box.append(self.search_revealer)
        scrolled_window = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        list_box.add_css_class("shader-list")
        list_box.connect("row-activated", self.on_row_activated)
        status_page = Adw.StatusPage(vexpand=True, icon_name="folder-documents-symbolic", title="No Shaders Found", description="Add some .glsl or .frag files to get started.")
        open_folder_btn = Gtk.Button(label="Open Shader Folder", css_classes=["pill", "suggested-action"])
        open_folder_btn.connect("clicked", self.open_shader_folder)
        status_page.set_child(open_folder_btn)
        list_box.set_placeholder(status_page)
        scrolled_window.set_child(list_box)
        page_box.append(scrolled_window)
        return page_box

    def _create_shader_row(self, item):
        adw_row = Adw.ActionRow(title=item.name, subtitle=f"Modified: {item.modified_str}  •  Size: {item.size_str}")
        adw_row.add_css_class("shader-row-content")
        fav_btn = Gtk.ToggleButton(active=item.is_favorite, css_classes=["flat", "favorite-btn"], valign=Gtk.Align.CENTER, tooltip_text="Toggle Favorite")
        fav_btn.set_icon_name("starred-symbolic" if item.is_favorite else "non-starred-symbolic")
        fav_btn.connect("toggled", self.on_favorite_toggled, item)
        adw_row.add_prefix(fav_btn)
        active_icon = Gtk.Image(icon_name="media-playback-start-symbolic", css_classes=["active-indicator"], visible=item.is_active, tooltip_text="Currently Active")
        adw_row.add_prefix(active_icon)
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        delete_btn = Gtk.Button(icon_name="user-trash-symbolic", css_classes=["destructive-action"], valign=Gtk.Align.CENTER, tooltip_text="Delete Shader File")
        delete_btn.connect("clicked", self._on_delete_clicked, item)
        edit_btn = Gtk.Button(icon_name="document-edit-symbolic", css_classes=["edit-btn"], valign=Gtk.Align.CENTER, tooltip_text="Edit Shader File")
        edit_btn.connect("clicked", self.edit_shader, item)
        apply_btn = Gtk.Button(label="Apply", icon_name="checkmark-symbolic", css_classes=["apply-btn"], valign=Gtk.Align.CENTER, tooltip_text="Apply This Shader")
        apply_btn.connect("clicked", lambda b: self.set_shader(item.name))
        button_box.append(delete_btn)
        button_box.append(edit_btn)
        button_box.append(apply_btn)
        adw_row.add_suffix(button_box)
        list_box_row = Gtk.ListBoxRow()
        list_box_row.set_child(adw_row)
        list_box_row.shader_name = item.name
        if item.is_active:
            list_box_row.add_css_class("active-shader-row")
        return list_box_row

    def _on_delete_clicked(self, button, item):
        dialog = Adw.MessageDialog(transient_for=self.window, modal=True, heading=f"Delete {item.name}?", body="This action is permanent and cannot be undone.")
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
        row_random = Adw.SwitchRow(title="Random Shader on Startup", subtitle="Apply a random shader every time you launch the app.", active=self.settings.get("random_on_startup", False))
        row_random.connect("notify::active", self._on_setting_changed, "random_on_startup")
        general_group.add(row_random)
        appearance_group = Adw.PreferencesGroup(title="Appearance")
        page.add(appearance_group)
        color_models = Gtk.StringList.new(["System Default", "Light", "Dark"])
        row_color = Adw.ComboRow(title="Color Scheme", subtitle="Choose the application theme.", model=color_models, selected=self.settings.get("color_scheme", 0))
        row_color.connect("notify::selected", self._on_setting_changed, "color_scheme")
        appearance_group.add(row_color)
        return page

    def _on_setting_changed(self, widget, _, key):
        if isinstance(widget, Adw.SwitchRow): self.settings[key] = widget.get_active()
        elif isinstance(widget, Adw.ComboRow): self.settings[key] = widget.get_selected()
        if key == "color_scheme":
            sm = Adw.StyleManager.get_default()
            s = self.settings[key]
            if s == 1: sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            elif s == 2: sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            else: sm.set_color_scheme(Adw.ColorScheme.DEFAULT)
        self.save_app_settings()

    def toggle_search(self, *args):
        if self.search_revealer:
            is_revealed = self.search_revealer.get_reveal_child()
            self.search_revealer.set_reveal_child(not is_revealed)
            if not is_revealed: GLib.timeout_add(250, lambda: self.all_search_entry.grab_focus())
            else: self.all_search_entry.set_text("")

    def close_search(self, *args):
        if self.search_revealer and self.search_revealer.get_reveal_child():
            self.search_revealer.set_reveal_child(False)
            self.all_search_entry.set_text("")

    def on_search_changed(self, entry):
        search_term = entry.get_text().lower()
        if not search_term:
            filtered_items = self.all_shader_items
        else:
            filtered_items = [item for item in self.all_shader_items if search_term in item.name.lower()]
        self._update_list_box(self.all_list_box, filtered_items)

    def on_search_activate(self, entry):
        first_row = self.all_list_box.get_row_at_index(0)
        if first_row and hasattr(first_row, 'shader_name'):
            self.set_shader(first_row.shader_name)

    def load_data_files(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            if os.path.exists(FAVORITES_PATH):
                with open(FAVORITES_PATH, 'r') as f: self.favorites = set(json.load(f))
        except Exception: self.favorites = set()
        try:
            if os.path.exists(RECENT_PATH):
                with open(RECENT_PATH, 'r') as f: self.recent_shaders = json.load(f)
        except Exception: self.recent_shaders = []

    def load_app_settings(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        defaults = {"random_on_startup": False, "color_scheme": 0}
        if os.path.exists(APP_SETTINGS_PATH):
            try:
                with open(APP_SETTINGS_PATH, 'r') as f: self.settings = {**defaults, **json.load(f)}
            except Exception: self.settings = defaults
        else: self.settings = defaults

    def save_app_settings(self):
        try:
            with open(APP_SETTINGS_PATH, 'w') as f: json.dump(self.settings, f, indent=4)
        except IOError as e: self.show_toast(f"Error saving settings: {e}", is_error=True)

    def refresh_all_lists(self, *args):
        if self.shutting_down: return
        try:
            self._active_shader_name = self.get_current_shader_from_config()
            os.makedirs(SHADER_DIR, exist_ok=True)
            valid_exts = (".glsl", ".frag", ".vert", ".fs", ".vs")
            files = sorted([f for f in os.listdir(SHADER_DIR) if f.lower().endswith(valid_exts)], key=str.lower)
            self.all_shader_items = [ShaderItem(name, os.path.join(SHADER_DIR, name)) for name in files]
            for item in self.all_shader_items:
                item.is_active = (item.name == self._active_shader_name)
                item.is_favorite = (item.name in self.favorites)
            self.on_search_changed(self.all_search_entry)
            favs = [s for s in self.all_shader_items if s.is_favorite]
            recents = [s for name in self.recent_shaders[:15] if (s := next((sh for sh in self.all_shader_items if sh.name == name), None))]
            self._update_list_box(self.favorites_list_box, favs)
            self._update_list_box(self.recent_list_box, recents)
            self.update_status_label()
        except Exception as e:
            self.show_toast(f"Error reading shaders: {e}", is_error=True)

    def create_actions(self):
        actions = [("random", self.set_random_shader), ("refresh", self.refresh_all_lists), ("open_folder", self.open_shader_folder), ("import", self.import_shader), ("disable", self.disable_shader_with_confirmation)]
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
            with open(FAVORITES_PATH, 'w') as f: json.dump(list(self.favorites), f, indent=4)
        except IOError as e: self.show_toast(f"Error saving favorites: {e}", is_error=True)

    def _write_shader_to_config_safe(self, shader_path=None):
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
        
        tmp_path = CONFIG_PATH + ".tmp"
        with open(tmp_path, 'w') as f:
            f.writelines(new_lines)
        
        os.replace(tmp_path, CONFIG_PATH)

        try:
            subprocess.run(["pkill", "-SIGHUP", "ghostty"], check=False)
        except FileNotFoundError:
            pass

    def set_shader(self, shader_name):
        if self.shutting_down: return
        shader_path = os.path.join(SHADER_DIR, shader_name)
        if not os.path.isfile(shader_path):
            self.show_toast(f"Shader not found: {shader_name}", is_error=True)
            self.refresh_all_lists(); return
        
        self._write_shader_to_config_safe(shader_path)
        
        if shader_name in self.recent_shaders: self.recent_shaders.remove(shader_name)
        self.recent_shaders.insert(0, shader_name)
        self.recent_shaders = self.recent_shaders[:15]
        with open(RECENT_PATH, 'w') as f: json.dump(self.recent_shaders, f, indent=4)
        
        self.show_toast(f"Applied shader: {shader_name}")
        self.refresh_all_lists()

    def edit_shader(self, button, item):
        uri = GLib.filename_to_uri(item.path, None)
        Gtk.show_uri(self.window, uri, Gdk.CURRENT_TIME)

    def set_random_shader(self, *args):
        if self.all_shader_items:
            item = random.choice(self.all_shader_items)
            self.set_shader(item.name)
        else: self.show_toast("No shaders available to choose from.", is_error=True)

    def disable_shader_with_confirmation(self, *args):
        if not self.get_current_shader_from_config():
            self.show_toast("No active shader to disable."); return
        dialog = Adw.MessageDialog(transient_for=self.window, modal=True, heading="Disable Shader?", body="This will remove the custom shader from your Ghostty configuration.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("disable", "Disable")
        dialog.set_response_appearance("disable", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_disable_response)
        dialog.present()

    def _on_disable_response(self, dialog, response):
        if response == "disable":
            self._write_shader_to_config_safe(None)
            self.show_toast("✅ Shader disabled successfully.")
            self.refresh_all_lists()

    def import_shader(self, *args):
        dialog = Gtk.FileChooserDialog(title="Import Shader", transient_for=self.window, action=Gtk.FileChooserAction.OPEN, modal=True)
        dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Open", Gtk.ResponseType.OK)
        dialog.connect("response", lambda d, res: self._on_import_response(d, res))
        dialog.present()

    def _on_import_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            file = dialog.get_file()
            try:
                shutil.copy2(file.get_path(), os.path.join(SHADER_DIR, file.get_basename()))
                self.show_toast(f"Imported '{file.get_basename()}'")
                self.refresh_all_lists()
            except (IOError, shutil.Error) as e:
                self.show_toast(f"Failed to import: {e}", is_error=True)
        dialog.destroy()

    def open_shader_folder(self, *args):
        uri = GLib.filename_to_uri(SHADER_DIR, None)
        Gtk.show_uri(self.window, uri, Gdk.CURRENT_TIME)

    def get_current_shader_from_config(self, get_path=False):
        if not os.path.exists(CONFIG_PATH): return None
        try:
            with open(CONFIG_PATH, 'r') as f:
                for line in f:
                    if line.strip().startswith(GHOSTTY_CONFIG_KEY):
                        path_part = line.split('=', 1)[1].strip().strip('"')
                        return path_part if get_path else os.path.basename(path_part)
        except Exception: return None
        return None

    def update_status_label(self):
        if self._active_shader_name:
            self.status_icon.set_from_icon_name("object-select-symbolic")
            self.status_label.set_text(self._active_shader_name)
        else:
            self.status_icon.set_from_icon_name("edit-clear-symbolic")
            self.status_label.set_text("No Active Shader")

    def show_toast(self, message, is_error=False):
        toast = Adw.Toast(title=message)
        if is_error: toast.add_css_class("error")
        self.toast_overlay.add_toast(toast)

    
if __name__ == "__main__":
    app = ShaderSwitcher()
    sys.exit(app.run(sys.argv))
