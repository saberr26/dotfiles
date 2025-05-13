# Oh My Posh configuration for Fish shell
# Save this to ~/.config/fish/conf.d/ohmyposh.fish

# Set Oh My Posh theme
set -gx POSH_THEME "$HOME/.config/ohmyposh/pywal-theme.json"

# Initialize Oh My Posh
oh-my-posh init fish --config $POSH_THEME | source

# Function to update Oh My Posh theme with Pywal colors
function update_ohmyposh_theme
    echo "Updating Oh My Posh theme with Pywal colors..."
    bash $HOME/.config/ohmyposh/update-ohmyposh-theme.sh
    
    # Refresh the prompt
    oh-my-posh init fish --config $POSH_THEME | source
    
    echo "Theme updated successfully!"
end

# Set an alias for easy theme updating
alias posh-update="update_ohmyposh_theme"

# If you want to automatically update the theme when starting Fish,
# uncomment the following line:
# update_ohmyposh_theme
