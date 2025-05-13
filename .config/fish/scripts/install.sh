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

# Check for fzf
set -g has_fzf 0
if command -v fzf >/dev/null 2>&1
    set -g has_fzf 1
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

# Function to display spinner during operations
function show_spinner
    set -l message $argv[1]
    set -l pid $argv[2]
    set -l spinstr '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    set -l delay 0.1
    
    while ps -p $pid > /dev/null
        for i in (seq (string length $spinstr))
            printf "\r$yellow$message %s$normal" (string sub -s $i -l 1 $spinstr)
            sleep $delay
        end
    end
    printf "\r%-50s\n" " " # Clear the spinner line
end

# Function to get package details
function get_package_details
    set pkg $argv[1]
    set details (pacman -Si $pkg 2>/dev/null)
    if test $status -ne 0
        echo "$red❌ Unable to fetch details for $pkg$normal"
        return 1
    end
    
    # Extract key information
    set name (echo $details | grep -m 1 "Name" | cut -d ":" -f 2 | string trim)
    set version (echo $details | grep -m 1 "Version" | cut -d ":" -f 2 | string trim)
    set description (echo $details | grep -m 1 "Description" | cut -d ":" -f 2 | string trim)
    set url (echo $details | grep -m 1 "URL" | cut -d ":" -f 2 | string trim)
    set licenses (echo $details | grep -m 1 "Licenses" | cut -d ":" -f 2 | string trim)
    set groups (echo $details | grep -m 1 "Groups" | cut -d ":" -f 2 | string trim)
    set provides (echo $details | grep -m 1 "Provides" | cut -d ":" -f 2 | string trim)
    set depends_on (echo $details | grep -m 1 "Depends On" | cut -d ":" -f 2 | string trim)
    set download_size (echo $details | grep -m 1 "Download Size" | cut -d ":" -f 2 | string trim)
    set installed_size (echo $details | grep -m 1 "Installed Size" | cut -d ":" -f 2 | string trim)
    
    # Display package details in a box
    set box_width (math $cols - 4)
    
    echo "$blue┌─"(string repeat -n (math $box_width - 2) "─")"─┐$normal"
    
    echo "$blue│$bold$cyan $name $version$normal"
    echo "$blue│$yellow $description$normal"
    
    if test -n "$url"
        echo "$blue│$green URL:$normal $url"
    end
    
    if test -n "$licenses" && test "$licenses" != "None"
        echo "$blue│$green Licenses:$normal $licenses"
    end
    
    if test -n "$download_size"
        echo "$blue│$green Download Size:$normal $download_size"
    end
    
    if test -n "$installed_size"
        echo "$blue│$green Installed Size:$normal $installed_size"
    end
    
    if test -n "$depends_on" && test "$depends_on" != "None"
        echo "$blue│$green Dependencies:$normal"
        for dep in (echo $depends_on | tr ' ' '\n')
            echo "$blue│  $normal- $dep"
        end
    end
    
    if test -n "$provides" && test "$provides" != "None"
        echo "$blue│$green Provides:$normal $provides"
    end

    echo "$blue└─"(string repeat -n (math $box_width - 2) "─")"─┘$normal"
end

# Function to get pacman version
function get_pacman_version
    command pacman --version | head -n 1 | string match -r 'Pacman v([0-9.]+)' | string sub -s 2
end

# Check if running as root
if test (id -u) -eq 0
    echo "$red❌ This script should not be run as root.$normal"
    echo "It will ask for sudo permissions when needed."
    exit 1
end

# Check if pacman is available
if not command -v pacman >/dev/null
    echo "$red❌ Error: pacman is not installed or not in PATH.$normal"
    echo "This script is designed for Arch Linux and derivatives."
    exit 1
end

# Clear screen
clear

# Print top border
hr "═" $blue

# Display logo
echo
center_text "$magenta█████╗ $green██████╗  $cyan██████╗$blue██╗  ██╗ $yellow█████╗ $red██████╗  $magenta██████╗$green██╗  ██╗"
center_text "$magenta██╔══██╗$green██╔══██╗$cyan██╔════╝$blue██║  ██║$yellow██╔══██╗$red██╔══██╗$magenta██╔════╝$green██║  ██║"
center_text "$magenta███████║$green██████╔╝$cyan██║     $blue███████║$yellow███████║$red██████╔╝$magenta██║     $green███████║"
center_text "$magenta██╔══██║$green██╔══██╗$cyan██║     $blue██╔══██║$yellow██╔══██║$red██╔══██╗$magenta██║     $green██╔══██║"
center_text "$magenta██║  ██║$green██║  ██║$cyan╚██████╗$blue██║  ██║$yellow██║  ██║$red██║  ██║$magenta╚██████╗$green██║  ██║"
center_text "$magenta╚═╝  ╚═╝$green╚═╝  ╚═╝$cyan ╚═════╝$blue╚═╝  ╚═╝$yellow╚═╝  ╚═╝$red╚═╝  ╚═╝$magenta ╚═════╝$green╚═╝  ╚═╝"
echo

# Print bottom border
hr "═" $blue

# Add fzf search function
function fzf_search_packages
    if test $has_fzf -eq 0
        echo "$red❌ fzf is not installed. Please install it first:$normal"
        echo "sudo pacman -S fzf"
        return 1
    end

    # Get list of all packages
    echo "$bold$blue🔍 Searching packages with fzf...$normal"
    
    # Create temporary files
    set tmp_pacman_list "/tmp/arch_pkg_list"
    pacman -Sl | awk '{print $2}' > $tmp_pacman_list
    
    # Run fzf search
    set selected_pkg (cat $tmp_pacman_list | fzf --height 50% --layout=reverse --border --preview "pacman -Si {} | bat --color=always --plain" --preview-window=right:60%)
    
    # Clean up
    rm -f $tmp_pacman_list
    
    if test -n "$selected_pkg"
        return $selected_pkg
    else
        return 1
    end
end

# Add fzf install function
function fzf_install_packages
    if test $has_fzf -eq 0
        echo "$red❌ fzf is not installed. Please install it first:$normal"
        echo "sudo pacman -S fzf"
        return 1
    end

    echo "$bold$blue🔍 Select packages to install with fzf (TAB to select multiple, ENTER to confirm):$normal"
    
    # Get list of all packages
    set tmp_pacman_list "/tmp/arch_pkg_list"
    pacman -Sl | awk '{print $2}' > $tmp_pacman_list
    
    # Run fzf multi-select
    set selected_pkgs (cat $tmp_pacman_list | fzf -m --height 50% --layout=reverse --border --preview "pacman -Si {} | bat --color=always --plain" --preview-window=right:60%)
    
    # Clean up
    rm -f $tmp_pacman_list
    
    if test -n "$selected_pkgs"
        echo "$bold$blue📦 Installing selected packages:$normal"
        echo $selected_pkgs | tr ' ' '\n' | sed 's/^/  - /'
        
        echo "$bold$blue:: $normal Proceed with installation? (y/N)"

        read -P "$bold$green►$normal " confirm
        if string match -qr '^[Yy]$' -- $confirm
            sudo pacman -S $selected_pkgs
        else
            echo "$yellow:: Installation skipped.$normal"
        end
    else
        echo "$yellow⏸ No packages selected.$normal"
    end
end

# Prompt for search method
echo "$bold$blue:: $normal Arch Package Tool - Select an action:"
echo
echo "  $green(S)$normal $bold Search$normal packages by keyword"
echo "  $green(U)$normal $bold Update$normal system packages"
echo "  $green(I)$normal $bold Installed$normal packages search"
echo "  $green(O)$normal $bold Orphaned$normal packages cleanup"
if test $has_fzf -eq 1
    echo "  $green(F)$normal $bold Fuzzy$normal search with fzf"
    echo "  $green(M)$normal $bold Multi-select$normal install with fzf"
end
echo "  $green(Q)$normal $bold Quit$normal"
echo

# Read search method using fish-friendly syntax
read -n 1 -P "$bold$blue:: $normal Enter your choice: " search_method
echo

# Convert to lowercase for case-insensitive matching
set search_method (string lower $search_method)

switch $search_method
    case "q"
        echo "$yellow👋 Goodbye!$normal"
        exit 0
    
    case "m"
        if test $has_fzf -eq 1
            fzf_install_packages
            exit 0
        else
            echo "$red❌ Invalid option. fzf is not installed.$normal"
            exit 1
        end
    
    case "f"
        if test $has_fzf -eq 1
            set pkg (fzf_search_packages)
            
            if test $status -eq 0
                # Show package details
                echo
                echo "$bold$blue:: $normal Getting details for $pkg..."
                echo
                get_package_details $pkg
                
                # Ask user for action
                echo
                echo "$bold$blue:: $normal Package actions for $pkg:"
                echo
                echo "  $green(i)$normal $bold Install/Upgrade$normal package"
                echo "  $red(r)$normal $bold Remove$normal package"
                if pacman -Q $pkg >/dev/null 2>&1
                    echo "  $yellow(d)$normal $bold Dependencies$normal check"
                end
                echo "  $blue(q)$normal $bold Quit$normal"
                echo
                
                read -n 1 -P "$bold$blue:: $normal Enter your choice: " action
                echo
                
                # Convert to lowercase for case-insensitive matching
                set action (string lower $action)
                
                switch $action
                    case "i"
                        echo "$bold$blue:: $normal Installing/Upgrading $pkg..."
                        sudo pacman -S $pkg
                        
                    case "r"
                        if pacman -Q $pkg >/dev/null 2>&1
                            echo "$bold$red:: $normal Removing $pkg..."
                            read -n 1 -P "$yellow:: $normal Remove with dependencies? [y/N] " remove_deps
                            echo
                            
                            if string match -qr '^[Yy]$' -- $remove_deps
                                sudo pacman -Rns $pkg
                            else
                                sudo pacman -R $pkg
                            end
                        else
                            echo "$red:: Package $pkg is not installed.$normal"
                        end
                        
                    case "d"
                        if pacman -Q $pkg >/dev/null 2>&1
                            echo "$bold$blue:: $normal Checking dependencies for $pkg..."
                            echo
                            
                            # Show what depends on this package
                            set rev_deps (pacman -Qi $pkg | grep "Required By" | cut -d ":" -f 2 | string trim)
                            
                            if test "$rev_deps" = "None"
                                echo "$green:: No packages depend on $pkg$normal"
                            else
                                echo "$bold$yellow:: $normal The following packages depend on $pkg:"
                                echo "$rev_deps" | tr ' ' '\n' | sed 's/^/  - /'
                            end
                        else
                            echo "$red:: Package $pkg is not installed.$normal"
                        end
                        
                    case "q"
                        echo "$yellow:: Goodbye!$normal"
                        
                    case '*'
                        echo "$red:: Invalid option. Please try again.$normal"
                        exit 1
                end
            else
                echo "$yellow:: No package selected.$normal"
            end
            
            exit 0
        else
            echo "$red:: fzf is not installed. Please install it first.$normal"
            exit 1
        end
        
    case "o" # List orphaned packages
        echo "$bold$blue:: $normal Checking for orphaned packages..."
        
        # Find orphans
        set orphans (pacman -Qtdq)
        
        if test -z "$orphans"
            echo "$green:: No orphaned packages found!$normal"
            exit 0
        end
        
        # Format orphans list
        set results (echo $orphans | tr ' ' '\n' | nl -w3 -s'. ')
        
        # Count the results
        set result_count (echo $results | wc -l)
        
        echo
        echo "$bold$blue:: $normal Found $result_count orphaned package(s):"
        echo
        
        # Calculate the box width
        set max_len 0
        for line in $results
            set len (string length -- $line)
            if test $len -gt $max_len
                set max_len $len
            end
        end
        
        # Ensure reasonable box width
        set box_width (math "floor(min(max($max_len + 4, 60), $cols - 2))")
        
        # Print top border of the box
        printf "$red┌─"
        for i in (seq (math $box_width - 2))
            printf "─"
        end
        printf "─┐$normal\n"
        
        # Print the results inside the box
        for line in $results
            # Format line
            printf "$red│$normal $line\n"
        end
        
        # Print the bottom border of the box
        printf "$red└─"
        for i in (seq (math $box_width - 2))
            printf "─"
        end
        printf "─┘$normal\n"
        
        # Offer to remove orphans
        echo
        echo "$bold$blue:: $normal Remove all orphaned packages? (Y/n)"

        read -n 1 -P "$bold$blue:: $normal Enter your choice: " remove_orphans
        echo
        
        if string match -qr '^[Nn]$' -- $remove_orphans
            echo "$yellow:: Removal skipped.$normal"
        else
            sudo pacman -Rns $orphans
        end
        
        exit 0
        
    case "i" # Search installed packages
        echo "$bold$blue:: $normal Enter keyword to search installed packages:"

        read -P "$bold$blue:: $normal " inst_keyword
        
        if test -z "$inst_keyword"
            echo "$red❌ No input provided. Aborting.$normal"
            exit 1
        end
        
        # Search installed packages
        set results (pacman -Qs $inst_keyword | grep -E '^local' | nl -w3 -s'. ')
        
        if test -z "$results"
            echo "$red:: No installed packages found matching '$inst_keyword'.$normal"
            exit 1
        end
        
        # Count the results
        set result_count (echo $results | wc -l)
        
        echo
        echo "$bold$blue:: $normal Found $result_count installed package(s) matching '$inst_keyword':"
        echo
        
        # Calculate the box width
        set max_len 0
        for line in $results
            set len (string length -- $line)
            if test $len -gt $max_len
                set max_len $len
            end
        end
        
        # Ensure reasonable box width
        set box_width (math "floor(min(max($max_len + 4, 60), $cols - 2))")
        
        # Print top border of the box
        printf "$green┌─"
        for i in (seq (math $box_width - 2))
            printf "─"
        end
        printf "─┐$normal\n"
        
        # Print the results inside the box
        for line in $results
            set line_num (echo $line | awk '{print $1}')
            set pkg_name (echo $line | awk '{print $2}')
            set pkg_ver (echo $line | awk '{print $3}')
            
            # Format line
            printf "$green│$normal $bold$yellow%s$normal $blue%s$normal $magenta%s$normal\n" $line_num $pkg_name $pkg_ver
        end
        
        # Print the bottom border of the box
        printf "$green└─"
        for i in (seq (math $box_width - 2))
            printf "─"
        end
        printf "─┘$normal\n"
        
    case "u" # List recently updated packages
        echo "$bold$blue:: $normal Fetching recently updated packages..."
        
        # Update package database
        sudo pacman -Sy &>/dev/null &
        set update_pid $last_pid
        show_spinner "Updating package database..." $update_pid
        
        # List recently updated packages
        set results (pacman -Qu 2>/dev/null | nl -w3 -s'. ')
        
        if test -z "$results"
            echo "$green:: All packages are up to date!$normal"
            exit 0
        end
        
        # Count the results
        set result_count (echo $results | wc -l)
        
        echo
        echo "$bold$blue:: $normal $result_count package(s) can be updated:"
        echo
        
        # Calculate the box width
        set max_len 0
        for line in $results
            set len (string length -- $line)
            if test $len -gt $max_len
                set max_len $len
            end
        end
        
        # Ensure reasonable box width
        set box_width (math "floor(min(max($max_len + 4, 60), $cols - 2))")
        
        # Print top border of the box
        printf "$magenta┌─"
        for i in (seq (math $box_width - 2))
            printf "─"
        end
        printf "─┐$normal\n"
        
        # Print the results inside the box
        for line in $results
            set pkg_info (echo $line | awk '{print $2}')
            set line_num (echo $line | awk '{print $1}')
            set old_ver (echo $line | awk '{print $3}')
            set new_ver (echo $line | awk '{print $5}')
            
            # Format line
            printf "$magenta│$normal $bold$yellow%s$normal $blue%s$normal: $red%s$normal → $green%s$normal\n" $line_num $pkg_info $old_ver $new_ver
        end
        
        # Print the bottom border of the box
        printf "$magenta└─"
        for i in (seq (math $box_width - 2))
            printf "─"
        end
        printf "─┘$normal\n"
        
        # Offer to update all packages
        echo
        echo "$bold$blue:: $normal Update all packages? (Y/n)"

        read -n 1 -P "$bold$blue:: $normal Enter your choice: " update_all
        echo
        
        if string match -qr '^[Nn]$' -- $update_all
            echo "$yellow:: Update skipped.$normal"
        else
            sudo pacman -Syu
        end
        
        exit 0
        
    case "s" # Search by keyword
        echo "$bold$blue:: $normal Enter package keyword:"

        read -P "$bold$blue:: $normal " keyword
        
        if test -z "$keyword"
            echo "$red❌ No input provided. Aborting.$normal"
            exit 1
        end
        
        # Create a background process for the search and capture its PID
        pacman -Ss $keyword > /tmp/arch_search_results & 
        set search_pid $last_pid
        
        # Show spinner during search
        show_spinner "Searching packages..." $search_pid
        
        # Process search results
        set results (cat /tmp/arch_search_results | grep -E '^[a-z]' | nl -w3 -s'. ')
        rm -f /tmp/arch_search_results
        
        # Handle no results
        if test -z "$results"
            echo "$red:: No packages found matching '$keyword'.$normal"
            exit 1
        end
        
        # Count the results
        set result_count (echo $results | wc -l)
        
        # Display results header
        echo
        echo "$bold$blue:: $normal Found $result_count package(s) matching '$keyword':"
        echo
        
        # Calculate the box width
        set max_len 0
        for line in $results
            set len (string length -- $line)
            if test $len -gt $max_len
                set max_len $len
            end
        end
        
        # Ensure reasonable box width
        set box_width (math "floor(min(max($max_len + 4, 60), $cols - 2))")
        
        # Print top border of the box
        printf "$cyan┌─"
        for i in (seq (math $box_width - 2))
            printf "─"
        end
        printf "─┐$normal\n"
        
        # Print the results inside the box
        for line in $results
            set pkg_name (echo $line | awk '{print $2}')
            set line_num (echo $line | awk '{print $1}')
            set desc (echo $line | cut -d ' ' -f 3-)
            
            # Check if package is installed
            if pacman -Q $pkg_name >/dev/null 2>&1
                set status_marker "$green✓$normal"
            else
                set status_marker "   "
            end
            
            # Format line
            printf "$cyan│$normal $bold$yellow%s$normal $status_marker $blue%s$normal - $desc\n" $line_num $pkg_name
        end
        
        # Print the bottom border of the box
        printf "$cyan└─"
        for i in (seq (math $box_width - 2))
            printf "─"
        end
        printf "─┘$normal\n"
        
    case '*'
        echo "$red❌ Invalid option. Aborting.$normal"
        exit 1
end

# For search results cases, continue with package selection
echo
echo "$bold$blue:: $normal Enter the number to get details, or 0 to exit:"
read -P "$bold$blue:: $normal " choice

if test "$choice" = "0"
    echo "$yellow:: Goodbye!$normal"
    exit 0
end

# Get the selected package name
set pkg (echo "$results" | grep -E "^ *$choice\. " | awk '{print $2}')

if test -z "$pkg"
    echo "$red:: Invalid selection.$normal"
    exit 1
end

echo
echo "$bold$blue:: $normal Getting details for $pkg..."
echo

# Show package details
get_package_details $pkg

# Ask user for action
echo
echo "$bold$blue:: $normal Package actions for $pkg:"
echo "  $green(i)$normal $bold Install/Upgrade$normal package"
echo "  $red(r)$normal $bold Remove$normal package"
if pacman -Q $pkg >/dev/null 2>&1
    echo "  $yellow(d)$normal $bold Dependencies$normal check"
end
echo "  $blue(q)$normal $bold Quit$normal"
echo

read -n 1 -P "$bold$blue:: $normal Enter your choice: " action
echo

# Convert to lowercase for case-insensitive matching
set action (string lower $action)

switch $action
    case "i"
        echo "$bold$blue:: $normal Installing/Upgrading $pkg..."
        sudo pacman -S $pkg
        
    case "r"
        if pacman -Q $pkg >/dev/null 2>&1
            echo "$bold$red:: $normal Removing $pkg..."
            read -n 1 -P "$yellow:: $normal Remove with dependencies? [y/N] " remove_deps
            echo
            
            if string match -qr '^[Yy]$' -- $remove_deps
                sudo pacman -Rns $pkg
            else
                sudo pacman -R $pkg
            end
        else
            echo "$red:: Package $pkg is not installed.$normal"
        end
        
    case "d"
        if pacman -Q $pkg >/dev/null 2>&1
            echo "$bold$blue:: $normal Checking dependencies for $pkg..."
            echo
            
            # Show what depends on this package
            set rev_deps (pacman -Qi $pkg | grep "Required By" | cut -d ":" -f 2 | string trim)
            
            if test "$rev_deps" = "None"
                echo "$green:: No packages depend on $pkg$normal"
            else
                echo "$bold$yellow:: $normal The following packages depend on $pkg:"
                echo "$rev_deps" | tr ' ' '\n' | sed 's/^/  - /'
            end
        else
            echo "$red:: Package $pkg is not installed.$normal"
        end
        
    case "q"
        echo "$yellow👋 Goodbye!$normal"
        
    case '*'
        echo "$red❌ Invalid option. Aborting.$normal"
end

# Print footer
echo
hr "═" $blue
center_text "$cyan Thanks for using ArchPkgTool • © $(date +%Y) $normal"
hr "═" $blue
