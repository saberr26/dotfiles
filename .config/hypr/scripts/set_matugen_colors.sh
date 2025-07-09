#!/bin/bash

# This script uses matugen to set Hyprland border colors dynamically.

# Ensure matugen is installed and in your PATH
if ! command -v matugen &> /dev/null
then
    echo "matugen could not be found. Please install it (e.g., pip install matugen)."
    exit 1
fi

# Get the current wallpaper path from swww
WALLPAPER_PATH=$(swww query | grep -oP 'image: \K[^ ]+')

if [ -z "$WALLPAPER_PATH" ]; then
    echo "Could not determine current wallpaper path from swww. Is swww running?"
    exit 1
fi

# Run matugen and parse the output for colors
# We'll use the primary color for active and a slightly desaturated/darker version for inactive

# Example matugen output for primary color:
# primary: #RRGGBB

PRIMARY_COLOR=$(matugen -j -q -i "$WALLPAPER_PATH" | jq -r '.primary')

if [ -z "$PRIMARY_COLOR" ]; then
    echo "Failed to get primary color from matugen. Check matugen installation and wallpaper path."
    exit 1
fi

# Convert hex to rgba for Hyprland (assuming full opacity for now)
# Hyprland expects rgba(RRGGBBAA)
# We'll use the primary color for active border
ACTIVE_BORDER_RGBA="rgba(${PRIMARY_COLOR:1}ff)"

# For inactive, let's try to get a secondary color or derive one.
# Matugen provides a 'secondary' color, let's use that if available, otherwise derive.
SECONDARY_COLOR=$(matugen -j -q -i "$WALLPAPER_PATH" | jq -r '.secondary')

if [ -z "$SECONDARY_COLOR" ]; then
    # Fallback: If no secondary, use a darker version of primary or a default grey
    INACTIVE_BORDER_RGBA="rgba(333333ff)" # A dark grey fallback
else
    INACTIVE_BORDER_RGBA="rgba(${SECONDARY_COLOR:1}ff)"
fi

# Set the colors using hyprctl
hyprctl set \$active_border_color "$ACTIVE_BORDER_RGBA"
hyprctl set \$inactive_border_color "$INACTIVE_BORDER_RGBA"

echo "Hyprland border colors updated using matugen."
