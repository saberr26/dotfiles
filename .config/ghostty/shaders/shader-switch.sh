#!/bin/bash

# --- Configuration ---
SHADER_DIR="$HOME/.config/ghostty/shaders"
CONFIG_FILE="$HOME/.config/ghostty/config"
# --- End of Configuration ---

# Use find to get a list of shaders, then pipe it to Rofi
# -dmenu tells Rofi to work as a menu
# -p sets a prompt text
# -i makes the search case-insensitive
SELECTED_SHADER_NAME=$(find "$SHADER_DIR" -type f \( -name "*.glsl" -o -name "*.frag" \) -printf "%f\n" | rofi -dmenu -p "Select Shader" -i)

# Exit if the user cancelled
if [ -z "$SELECTED_SHADER_NAME" ]; then
    echo "No shader selected. Exiting."
    exit 0
fi

# Reconstruct the full path
FULL_SHADER_PATH="$SHADER_DIR/$SELECTED_SHADER_NAME"

# Update the config file
sed -i "s|^custom-shader = .*|custom-shader = $FULL_SHADER_PATH|" "$CONFIG_FILE"

# Signal running Ghostty instances to reload
pkill -SIGHUP ghostty

echo "Ghostty shader set to: $SELECTED_SHADER_NAME"
