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
