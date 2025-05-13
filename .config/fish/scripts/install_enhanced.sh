#!/usr/bin/env fish

# Color variables
set -g normal (tput sgr0)
set -g blue (tput setaf 4)
set -g green (tput setaf 2)
set -g yellow (tput setaf 3)
set -g red (tput setaf 1)
set -g magenta (tput setaf 5)
set -g cyan (tput setaf 6)
set -g bold (tput bold)

# Terminal dimensions
set -g cols (tput cols)
set -g rows (tput lines)

# Check for fzf and other tools
set -g has_fzf 0
set -g has_bat 0
set -g has_aur_helper 0
set -g aur_helper ""

if command -v fzf >/dev/null 2>&1
    set -g has_fzf 1
end

if command -v bat >/dev/null 2>&1
    set -g has_bat 1
end

# Check for AUR helpers
for helper in yay paru
    if command -v $helper >/dev/null 2>&1
        set -g has_aur_helper 1
        set -g aur_helper $helper
        break
    end
end

# Function to center text
function center_text
    set text $argv[1]
    set text_len (string length -- $text)
    set offset (math "floor(($cols - $text_len) / 2)")
    printf "%*s%s%s\n" $offset "" "$text" "$normal"
end

# Function for horizontal rule
function hr
    set char $argv[1]
    printf "%s%s%s\n" $argv[2] (string repeat -n $cols $char) $normal
end
