#!/bin/bash

layouts=(us ara)
current=$(cat /tmp/current_layout)  # store current layout index here

if [[ -z "$current" ]]; then
  current=0
fi

next=$(( (current + 1) % ${#layouts[@]} ))

# switch layout using hyprctl
hyprctl switchxkblayout at-translated-set-2-keyboard $next

# save new layout index
echo $next > /tmp/current_layout

# show OSD message with swayosd
swayosd-client --custom-message="Layout: ${layouts[$next]}" --custom-icon="input-keyboard"
