# Main Fish Configuration File

# Source system configurations
source /usr/share/cachyos-fish-config/conf.d/done.fish

# Source all .fish files in conf.d directory
for file in ~/.config/fish/conf.d/*.fish
    source $file
end

# Source all functions
for file in ~/.config/fish/functions/*.fish
    source $file
end

# Source personal profile if it exists
if test -f ~/.fish_profile
    source ~/.fish_profile
end

# Set up PATH additions
if test -d ~/.local/bin
    if not contains -- ~/.local/bin $PATH
        set -p PATH ~/.local/bin
    end
end

if test -d ~/Applications/depot_tools
    if not contains -- ~/Applications/depot_tools $PATH
        set -p PATH ~/Applications/depot_tools
    end
end

# Set environment variables
set -x MANROFFOPT "-c"
set -x MANPAGER "sh -c 'col -bx | bat -l man -p'"

# Set universal variables for done plugin
set -U __done_min_cmd_duration 10000
set -U __done_notification_urgency_level low

# Initialize oh-my-posh prompt
#oh-my-posh init fish --config ~/.config/oh-my-posh/themes/amro.omp.json | source

# Initialize starship prompt
#source (/usr/bin/starship init fish --print-full-init | psub)

# bun
set --export BUN_INSTALL "$HOME/.bun"
set --export PATH $BUN_INSTALL/bin $PATH

# pnpm
set -gx PNPM_HOME "/home/vanilla/.local/share/pnpm"
if not string match -q -- $PNPM_HOME $PATH
  set -gx PATH "$PNPM_HOME" $PATH
end

# Set universal paths
set -U fish_user_paths /usr/lib/qt6/bin
set -x ANDROID_SDK_ROOT $HOME/Android/Sdk
set -x PATH $PATH $ANDROID_SDK_ROOT/cmdline-tools/latest/bin
set -x PATH $PATH $ANDROID_SDK_ROOT/platform-tools
