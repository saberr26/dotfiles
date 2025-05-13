source ~/.config/fish/functions.fish

alias cat='bat --style header --style snip --style changes --style header'  # cat


alias grub="grub-mkconfig -o /boot/grub/grub.cfg"    # opensuse
alias fedbup="sudo grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg" # fedora
alias ..='cd ..'    # go back
alias ...='cd ../..'    # go back 2 steps
alias .='cd /'  # go to root dir
alias syu='~/.config/fish/scripts/arch.sh && sudo pacman -Syu && printf '─%.0s' $(seq 1 $(tput cols))' 
alias install ='~/.config/fish/scripts/arch.sh && sudo pacman -S  && printf '─%.0s' $(seq 1 $(tput cols))' 

# other
alias src='clear && source ~/.config/fish/config.fish'
alias clr='clear'   #clear
alias cls='clear'
alias clar='clear'
alias c='clear'
alias q='exit'

# disk spaces and RAM usage
alias du='du -sh'
alias mem='fn_resources __memory'
alias disk='dysk'

# change your default USER shell
alias tobash="sudo chsh $USER -s /bin/bash && echo 'Log out and log back in for change to take effect.'"
alias tozsh="sudo chsh $USER -s /bin/zsh && echo 'Log out and log back in for change to take effect.'"
alias tofish="sudo chsh $USER -s /bin/fish && echo 'Log out and log back in for change to take effect.'"

#fzf
alias find='nvim $(fzf --preview="bat --color=always {}")'

#nvim
alias nv='nvim'
alias nvm='nvim .'
alias open='nvim .'
alias snv='sudo -E nvim -d'
alias vi='nvim'
alias vim='nvim'
alias svi='sudo nvim'
alias vis='nvim "+set si"'
alias vi='vim'
alias svi='sudo vim'
alias vis='vim "+set si"'

# check updates
alias cu='fn_check_updates'

# updates
alias dup='sudo zypper dup -y' # distro update for opensuse
alias update='fn_update'

# install and remove package
alias install='fn_install'
alias remove='fn_uninstall'

# compiling c++ file using gcc
alias cpp='fn_compile_cpp'

# git alias
alias add='git add .'
alias clone='git clone'
alias cloned='git clone --depth=1'
alias branch='git branch -M main'
alias commit='git commit -m'
alias push='git push'
alias pushm='git push -u origin main'
alias pusho='git push origin' # and add your branch name 
alias pull='git pull'
alias info='git_info'
# alias status='git status'

# others
alias nc='clr && neofetch'
alias ff='clr && fastfetch'
alias sys='btop'
alias clock='tty-clock -c -t -D -s'

alias mkdir='mkdir -pv'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

alias fzf='fzf --preview "bat --style=numbers --color=always --line-range :500 {}"'
alias ipexternal="curl -s ifconfig.me && echo"
alias ipexternal="wget -qO- ifconfig.me && echo"
alias exe='chmod +x'
alias root='sudo chmod 777'
alias pyenv='source ~/fabric-dev/fabric/bin/activate.fish'

# List Directory
alias l='eza -lh  --icons=auto' # long list
alias ls='eza -1   --icons=auto' # short list
alias ll='eza -lha --icons=auto --sort=name --group-directories-first' # long list all
alias ld='eza -lhD --icons=auto' # long list dirs
alias lt='eza --icons=auto --tree' # list folder as tree
alias vs='vscodium'
alias e='micro'
