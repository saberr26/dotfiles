# Useful aliases
# rust sudo
alias sudo='sudo-rs'
# File operations
alias rm='rm -rf'
alias backup='cp -r'
alias md="mkdir -p"

# git
alias gc='git clone'
alias gp='git pull'

# Directory navigation
alias cd='z'
alias ..='z ..'
alias ...='z ../..'
alias ....='z ../../..'
alias .....='z ../../../..'
alias ......='z ../../../../..'

# Listing files with eza
alias ls='eza -al --color=always --group-directories-first --icons'
alias l="nu -c 'ls -d | sort-by size -r | select name size modified'"
alias la='eza -a --color=always --group-directories-first --icons'  # all files and dirs
alias ll='eza -l --color=always --group-directories-first --icons'  # long format
alias lt='eza -aT --color=always --group-directories-first --icons' # tree listing

# System operations
alias restart-kde='systemctl --user restart plasma-plasmashell.service'
alias grub-update="sudo grub-mkconfig -o /boot/grub/grub.cfg"
alias fixpacman="sudo rm /var/lib/pacman/db.lck"
alias docklean='docker system prune -a --volumes'
alias update='sudo pacman -Syu'
alias mirror="sudo cachyos-rate-mirrors"
alias cleanup='sudo pacman -Rns (pacman -Qtdq)'
alias jctl="journalctl -p 3 -xb"
alias hw='hwinfo --short'
alias big="expac -H M '%m\\t%n' | sort -h | nl"
alias gitpkg='pacman -Q | grep -i "\\-git" | wc -l'
alias rip="expac --timefmt='%Y-%m-%d %T' '%l\\t%n %v' | sort | tail -200 | nl"
alias py='python3'
# Development tools
alias tarnow='tar -acf '
alias untar='tar -zxvf '
alias wget='wget -c '
alias psmem='ps auxf | sort -nr -k 4'
alias psmem10='ps auxf | sort -nr -k 4 | head -10'
alias tb='nc termbin.com 9999'

# Text processing
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'
alias dir='dir --color=auto'
alias vdir='vdir --color=auto'

# Help for new Arch users
alias apt='man pacman'
alias apt-get='man pacman'

# Other tools
alias nmtui='impala'
alias mdcat='glow -ta'
alias edit=ms-edit
alias ff='clear && fastfetch --config ~/.config/fastfetch/fatfetch.jsonc'
