if status is-interactive
    # Commands to run in interactive sessions can go here
fastfetch

end

set -g fish_greeting
set --global fish_color_command blue
set --global fish_color_param yellow
set --global fish_color_autosuggestion cyan
#oh-my-posh init fish --config ~/.config/ohmyposh/pywal-template.json | source
#source ~/.config/fish/conf.d/ohmyposh.fish
#~/.config/ohmyposh/update-ohmyposh-theme.sh>>/dev/null
starship init fish | source

#===============================================#
#           aliases and functions
#===============================================#
source ~/.config/fish/aliases.fish

# pnpm
set -gx PNPM_HOME "/home/ilove2b/.local/share/pnpm"
if not string match -q -- $PNPM_HOME $PATH
  set -gx PATH "$PNPM_HOME" $PATH
end
# pnpm end
alias cp /usr/local/bin/cpg
alias mv /usr/local/bin/mvg
