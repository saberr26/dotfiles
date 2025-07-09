#!/bin/bash
# save as simulate_keys.sh

# Start ydotool daemon if not running
if ! pgrep -x "ydotoold" > /dev/null; then
    sudo ydotoold &
    sleep 1
fi

# Simulate Ctrl+Shift+,
ydotool key ctrl+shift+comma

# Or for multiple key combos
simulate_shortcut() {
    ydotool key "$1"
    sleep 0.1
}

# Usage examples
simulate_shortcut "ctrl+shift+comma"
simulate_shortcut "ctrl+c"
simulate_shortcut "alt+tab"
