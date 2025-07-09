# A custom Nushell completer that suggests executables, built-ins, and paths,
# complete with descriptions and styling for a more "native" feel.
#
# This version includes robust error handling and rich completion metadata.

# --- Part 1: The Completer Function ---
# This is the core logic. It takes the partial text you've typed (`line`)
# and returns a list of potential completions.

export def path-and-command-completer [line: string] {
    # --- Find Nushell Built-in Commands ---
    let built_ins = help commands
        | get name
        | each { |it| {
            value: $it,
            description: "Nushell Built-in Command",
            style: { fg: "#449f44" } # Green for built-ins
        }}

    # --- Find Executable Commands (with error handling) ---
    let commands = $env.PATH
        | split row (char esep)
        | each { |dir|
            try {
                ls $"($dir)/*" | where {|item| $item.type == 'file' and $item.is_executable }
            } catch {
                null # Ignore broken paths
            }
        }
        | flatten
        | get name
        | uniq
        | each {|it| {
            value: $it,
            description: "External Command",
            style: { fg: "#56b6c2" } # Cyan for externals
        }}

    # --- Find Local Paths ---
    let paths = ls
        | each { |it|
            if $it.type == 'dir' {
                {
                    value: $"($it.name)/",
                    description: "Directory",
                    style: { fg: "#4e88d7" } # Blue for directories
                }
            } else {
                {
                    value: $it.name,
                    description: "File",
                    style: { fg: "#abb2bf" } # Gray for files
                }
            }
        }

    # --- Combine, Filter, and Format ---
    $built_ins | append $commands | append $paths
        | where {|it| $it.value starts-with $line }
        | uniq-by value # Prevent duplicates based on the 'value' field
        | sort-by value
}


# --- Part 2: Applying the Completer Globally ---
# To make this completer work for any command you type, we assign it
# as the default completer for all "external" commands (any command not
# built into Nushell).
$env.config.completions.external = {
    enable: true,
    # The 'completer' closure is called by Nushell when you press Tab.
    # It receives the text you've typed and passes it to our main function.
    completer: {|spans| path-and-command-completer $spans.0 }
}


# --- HOW TO USE ---
# 1. Save this file as `my-completions.nu` in your Nushell config directory
#    (usually ~/.config/nushell/).
# 2. Add this line to your main `config.nu` file to load it on startup:
#    source ~/.config/nushell/my-completions.nu
# 3. Restart Nushell. The completions should now work automatically and be colored.
#
# --- TROUBLESHOOTING ---
# If completions still don't work after sourcing this file:
# - Check that this is the LAST thing in your `config.nu` that modifies
#   `$env.config.completions`. Another setting could be overwriting it.
# - Restart your shell completely to ensure the changes are loaded.
