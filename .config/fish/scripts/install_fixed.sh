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
    set -l elapsed 0
    
    while ps -p $pid > /dev/null
        for i in (seq (string length $spinstr))
            set elapsed (math "$elapsed + $delay")
            printf "\r$yellow$message %s [%.1fs]$normal" (string sub -s $i -l 1 $spinstr) $elapsed
            sleep $delay
        end
    end
    printf "\r%-60s\n" " " # Clear the spinner line
end

# Function to create a progress bar
function progress_bar
    set -l percent $argv[1]
    set -l width $argv[2]
    set -l filled (math "round($width * $percent / 100)")
    set -l empty (math "$width - $filled")
    
    printf "["
    printf "%s" (string repeat -n $filled "█")
    printf "%s" (string repeat -n $empty "░")
    printf "] %d%%\r" $percent
end

# Function to get package details
function get_package_details
    set pkg $argv[1]
    set details (pacman -Si $pkg 2>/dev/null)
    if test $status -ne 0
        echo "$red:: Unable to fetch details for $pkg$normal"
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

# Add fzf search function
function fzf_search_packages
    if test $has_fzf -eq 0
        echo "$red:: fzf is not installed. Please install it first:$normal"
        echo "sudo pacman -S fzf"
        return 1
    end

    # Get list of all packages
    echo "$bold$blue:: $normal Searching packages with fzf..."
    echo "  $yellow•$normal Type to filter packages"
    echo "  $yellow•$normal Press $bold TAB$normal to select/deselect a package"
    echo "  $yellow•$normal Press $bold Shift+TAB$normal to deselect all packages"
    echo "  $yellow•$normal Press $bold ENTER$normal to confirm your selection"
    
    # Create temporary files
    set tmp_pacman_list "/tmp/arch_pkg_list"
    pacman -Sl | awk '{print $2}' > $tmp_pacman_list
    
    # Run fzf multi-select with header
    set selected_pkgs (cat $tmp_pacman_list | fzf -m --height 50% --layout=reverse --border \
        --bind="tab:toggle,shift-tab:deselect-all" \
        --header="TAB: select/deselect | Shift+TAB: deselect all | ENTER: confirm" \
        --preview="pacman -Si {} | bat --color=always --plain" \
        --preview-window=right:60%)
    
    # Clean up
    rm -f $tmp_pacman_list
    
    if test -n "$selected_pkgs"
        echo "$bold$blue:: $normal Installing selected packages:"
        echo $selected_pkgs | tr ' ' '\n' | sed 's/^/  - /'
        
        echo "$bold$blue:: $normal Proceed with installation? (y/N)"
        read -n 1 -P "$bold$blue:: $normal Enter your choice: " confirm
        echo
        
        if string match -qr '^[Yy]$' -- $confirm
            sudo pacman -S $selected_pkgs
            return 0
        else
            echo "$yellow:: Installation skipped.$normal"
            return 1
        end
    else
        echo "$yellow:: No packages selected.$normal"
        return 1
    end
end

# Check if running as root
if test (id -u) -eq 0
    echo "$red:: This script should not be run as root.$normal"
    echo "It will ask for sudo permissions when needed."
    exit 1
end

# Check if pacman is available
if not command -v pacman >/dev/null
    echo "$red:: Error: pacman is not installed or not in PATH.$normal"
    echo "This script is designed for Arch Linux and derivatives."
    exit 1
end

# Clear screen
clear

# Print top border
hr "═" $blue

# Display logo
echo
center_text "   $magenta█████╗ $green██████╗  $cyan██████╗$blue██╗  ██╗ $yellow█████╗ $red██████╗  $magenta██████╗$green██╗  ██╗"
center_text "$magenta██╔══██╗$green██╔══██╗$cyan██╔════╝$blue██║  ██║$yellow██╔══██╗$red██╔══██╗$magenta██╔════╝$green██║  ██║"
center_text "$magenta███████║$green██████╔╝$cyan██║     $blue███████║$yellow███████║$red██████╔╝$magenta██║     $green███████║"
center_text "$magenta██╔══██║$green██╔══██╗$cyan██║     $blue██╔══██║$yellow██╔══██║$red██╔══██╗$magenta██║     $green██╔══██║"
center_text "$magenta██║     ██║$green██║  ██║$cyan╚██████╗$blue██║  ██║$yellow██║  ██║$red██║  ██║$magenta╚██████╗$green██║  ██║"
center_text "$magenta╚═╝     ╚═╝$green╚═╝  ╚═╝$cyan ╚═════╝$blue╚═╝  ╚═╝$yellow╚═╝  ╚═╝$red╚═╝  ╚═╝$magenta ╚═════╝$green╚═╝  ╚═╝"
echo

# Print bottom border
hr "═" $blue

# Prompt for search method
echo "$bold$blue:: $normal Arch Package Tool - Select an action:"
echo
echo "  $green(U)$normal $bold Update$normal system packages"
echo "  $green(I)$normal $bold Installed$normal packages search"
echo "  $green(O)$normal $bold Orphaned$normal packages cleanup"
if test $has_fzf -eq 1
    echo "  $green(F)$normal $bold Fuzzy$normal search and install with fzf"
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
        echo "$yellow:: Goodbye!$normal"
        exit 0
    
    case "f"
        if test $has_fzf -eq 1
            fzf_search_packages
            exit 0
        else
            echo "$red:: fzf is not installed. Please install it first.$normal"
            exit 1
        end
        
    case "o" # List orphaned packages
        echo "$bold$blue:: $normal Checking for orphaned packages..."
        
        # Find orphaned packages
        set orphans (pacman -Qtdq 2>/dev/null)
        
        if test -z "$orphans"
            echo "$green:: No orphaned packages found.$normal"
            exit 0
        end
        
        # Count orphans
        set orphan_count (count $orphans)
        
        echo
        echo "$bold$blue:: $normal Found $orphan_count orphaned package(s):"
        echo
        
        # Format orphans list with numbers
        set counter 1
        set formatted_orphans ""
        set max_len 0
        
        for pkg in $orphans
            # Format the counter to always be 5 digits with padding
            set padded_counter (printf "%05d" $counter)
            set formatted_line "$bold$yellow│$padded_counter│$normal $red$pkg$normal"
            set visible_len (string length -- (string replace -a "\e[" "" "$formatted_line" | string replace -a "m" "" ))
            
            if test $visible_len -gt $max_len
                set max_len $visible_len
            end
            
            set formatted_orphans $formatted_orphans "$formatted_line"
            set counter (math $counter + 1)
        end
        
        # Use full terminal width for box
        set box_width $cols
        
        # Print top border of the box
        printf "$red┌"
        printf "%s" (string repeat -n $box_width "─")
        printf "┐$normal\n"
        
        # Print the orphans inside the box
        for line in $formatted_orphans
            set visible_len (string length -- (string replace -a "\e[" "" "$line" | string replace -a "m" "" ))
            set padding (math "$box_width - $visible_len - 3") # -3 for the left border, space, and right border
            printf "$red│$normal %s" $line
            if test $padding -gt 0
                printf "%s" (string repeat -n $padding " ")
            end
            printf "$red│$normal\r\n"
        end
        
        # Print the bottom border of the box
        printf "$red└"
        printf "%s" (string repeat -n $box_width "─")
        printf "┘$normal\n"
        
        # Offer to remove orphans
        echo
        echo "$bold$blue:: $normal Remove all orphaned packages? (y/N)"
        read -n 1 -P "$bold$blue:: $normal Enter your choice: " remove_orphans
        echo
        
        if string match -qr '^[Yy]$' -- $remove_orphans
            echo "$bold$blue:: $normal Removing orphaned packages..."
            # First ask for sudo password on a separate line
            echo "$bold$blue:: $normal Requesting sudo privileges to remove packages..."
            sudo -v
            sudo pacman -Rns $orphans
        else
            echo "$yellow:: Removal skipped.$normal"
        end
        
        exit 0
        
    case "i" # Search installed packages
        echo "$bold$blue:: $normal Enter package name to search (empty for all):"
        
        read -P "$bold$blue:: $normal " search_term
        
        # Create a background process for the search and capture its PID
        if test -z "$search_term"
            pacman -Q > /tmp/arch_installed_results &
        else
            pacman -Q | grep -i $search_term > /tmp/arch_installed_results &
        end
        set search_pid $last_pid
        
        # Show spinner during search
        show_spinner "Searching installed packages..." $search_pid
        
        # Process search results
        set results (cat /tmp/arch_installed_results)
        rm -f /tmp/arch_installed_results
        
        # Handle no results
        if test -z "$results"
            if test -z "$search_term"
                echo "$red:: No packages installed.$normal"
            else
                echo "$red:: No installed packages found matching '$search_term'.$normal"
            end
            return 1
        end
        
        # Count the results
        set result_count (count $results)
        
        # Display results header
        echo
        if test -z "$search_term"
            echo "$bold$blue:: $normal Found $result_count installed package(s):"
        else
            echo "$bold$blue:: $normal Found $result_count installed package(s) matching '$search_term':"
        end
        echo
        
        # Calculate the box width based on the longest line
        set max_len 0
        set formatted_results ""
        set counter 1
        
        for line in $results
            set line_parts (string split " " -- $line)
            set pkg_name $line_parts[1]
            set pkg_ver $line_parts[2]
            
            # Format line with box-style numbering
            # Format the counter to always be 5 digits with padding
            set padded_counter (printf "%05d" $counter)
            set formatted_line "$bold$yellow│$padded_counter│$normal $blue$pkg_name$normal $magenta$pkg_ver$normal"
            set len (string length -- (string replace -a "\e[" "" "$formatted_line" | string replace -a "m" "" ))
            if test $len -gt $max_len
                set max_len $len
            end
            
            set formatted_results $formatted_results "$formatted_line"
            set counter (math $counter + 1)
        end
        
        # Use full terminal width for box
        set box_width $cols
        
        # Print top border of the box
        printf "$green┌"
        printf "%s" (string repeat -n $box_width "─")
        printf "┐$normal\n"
        
        # Print the results inside the box
        for line in $formatted_results
            set visible_len (string length -- (string replace -a "\e[" "" "$line" | string replace -a "m" "" ))
            set padding (math "$box_width - $visible_len - 3") # -3 for the left border, space, and right border
            printf "$green│$normal %s" $line
            if test $padding -gt 0
                printf "%s" (string repeat -n $padding " ")
            end
            printf "$green│$normal\r\n"
        end
        
        # Print the bottom border of the box
        printf "$green└"
        printf "%s" (string repeat -n $box_width "─")
        printf "┘$normal\n"
        
    case "u" # List recently updated packages
        echo "$bold$blue:: $normal Checking for updates..."
        
        # First ask for sudo password on a separate line
        echo "$bold$blue:: $normal Requesting sudo privileges to synchronize package databases..."
        sudo -v
        
        # Create a background process for the update check and capture its PID
        sudo pacman -Sy > /dev/null 2>&1 &
        set sync_pid $last_pid
        
        # Show spinner during sync
        show_spinner "Synchronizing package databases..." $sync_pid
        
        # Check for updates
        pacman -Qu > /tmp/arch_updates &
        set update_pid $last_pid
        
        # Show spinner during update check
        show_spinner "Checking for updates..." $update_pid
        
        # Process update results
        set results (cat /tmp/arch_updates)
        rm -f /tmp/arch_updates
        
        # Handle no updates
        if test -z "$results"
            echo "$green:: System is up to date.$normal"
            return 0
        end
        
        # Count the updates
        set update_count (count $results)
        
        # Display results header
        echo
        echo "$bold$blue:: $normal Found $update_count package(s) to update:"
        echo
        
        # Calculate the box width based on the longest line
        set max_len 0
        set formatted_results ""
        set counter 1
        
        for line in $results
            set line_parts (string split " " -- $line)
            set pkg_info $line_parts[1]
            set old_ver $line_parts[2]
            set arrow $line_parts[3]
            set new_ver $line_parts[4]
            
            # Format line with box-style numbering
            # Format the counter to always be 5 digits with padding
            set padded_counter (printf "%05d" $counter)
            set formatted_line "$bold$yellow│$padded_counter│$normal $blue$pkg_info$normal: $red$old_ver$normal → $green$new_ver$normal"
            set len (string length -- (string replace -a "\e[" "" "$formatted_line" | string replace -a "m" "" ))
            if test $len -gt $max_len
                set max_len $len
            end
            
            set formatted_results $formatted_results "$formatted_line"
            set counter (math $counter + 1)
        end
        
        # Use full terminal width for box
        set box_width $cols
        
        # Print top border of the box
        printf "$magenta┌"
        printf "%s" (string repeat -n $box_width "─")
        printf "┐$normal\n"
        
        # Print the results inside the box
        for line in $formatted_results
            set visible_len (string length -- (string replace -a "\e[" "" "$line" | string replace -a "m" "" ))
            set padding (math "$box_width - $visible_len - 3") # -3 for the left border, space, and right border
            printf "$magenta│$normal %s" $line
            if test $padding -gt 0
                printf "%s" (string repeat -n $padding " ")
            end
            printf "$magenta│$normal\r\n"
        end
        
        # Print the bottom border of the box
        printf "$magenta└"
        printf "%s" (string repeat -n $box_width "─")
        printf "┘$normal\n"
        
        # Offer to update all packages
        echo
        echo "$bold$blue:: $normal Update all packages? (y/N)"
        read -n 1 -P "$bold$blue:: $normal Enter your choice: " update_all
        echo
        
        if string match -qr '^[Yy]$' -- $update_all
            echo "$bold$blue:: $normal Updating all packages..."
            # First ask for sudo password on a separate line if needed
            sudo -v
            sudo pacman -Su
        else
            echo "$yellow:: Update skipped.$normal"
        end
        
        exit 0
        

        
    case '*'
        echo "$red:: Invalid option.$normal"
        exit 1
end

# For search results cases, continue with package selection
echo
echo "$bold$blue:: $normal Options:"
echo "  $green(#)$normal Enter a $bold number$normal to view package details"
echo "  $green(m)$normal $bold Multi-select$normal packages for installation"
echo "  $green(q)$normal $bold Quit$normal"
echo
read -P "$bold$blue:: $normal " choice

if test "$choice" = "q"
    echo "$yellow:: Goodbye!$normal"
    exit 0
end

if test "$choice" = "m"
    # Multi-select mode
    echo "$bold$blue:: $normal Select packages to install:"
    echo "  $yellow•$normal Press $bold TAB$normal to select/deselect a package"
    echo "  $yellow•$normal Press $bold Shift+TAB$normal to deselect all packages"
    echo "  $yellow•$normal Press $bold ENTER$normal to confirm your selection"
    
    # Create a temporary file with search results
    set tmp_results "/tmp/arch_search_results"
    for line in $results
        set pkg_name (echo $line | awk '{print $2}')
        echo $pkg_name >> $tmp_results
    end
    
    # Run fzf multi-select on the results with custom keybindings
    set selected_pkgs (cat $tmp_results | fzf -m --height 50% --layout=reverse --border \
        --bind="tab:toggle,shift-tab:deselect-all" \
        --header="TAB: select/deselect | Shift+TAB: deselect all | ENTER: confirm" \
        --preview="pacman -Si {} | bat --color=always --plain" \
        --preview-window=right:60%)
    
    # Clean up
    rm -f $tmp_results
    
    if test -n "$selected_pkgs"
        echo "$bold$blue:: $normal Installing selected packages:"
        echo $selected_pkgs | tr ' ' '\n' | sed 's/^/  - /'
        
        echo "$bold$blue:: $normal Proceed with installation? (y/N)"
        read -n 1 -P "$bold$blue:: $normal Enter your choice: " confirm
        echo
        
        if string match -qr '^[Yy]$' -- $confirm
            sudo pacman -S $selected_pkgs
        else
            echo "$yellow:: Installation skipped.$normal"
        end
    else
        echo "$yellow:: No packages selected.$normal"
    end
    
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
            read -n 1 -P "$yellow:: $normal Remove with dependencies? (y/N) " remove_deps
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
        echo "$red:: Invalid option.$normal"
end

# Print footer
echo
hr "═" $blue
center_text "$cyan Thanks for using ArchPkgTool • © $(date +%Y) $normal"
hr "═" $blue
