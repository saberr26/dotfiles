# Custom functions
function backup
    if test (count $argv) -eq 0
        echo "Usage: backup <file_or_dir>"
        return 1
    end

    for target in $argv
        if test -e $target
            cp -r $target $target.bak
            echo "Backed up $target → $target.bak"
        else
            echo "Error: $target does not exist"
        end
    end
end

# Copy DIR1 DIR2
function copy
    set count (count $argv | tr -d \\n)
    if test "$count" = 2; and test -d "$argv[1]"
        set from (echo $argv[1] | trim-right /)
        set to (echo $argv[2])
        command cp -r $from $to
    else
        command cp $argv
    end
end
