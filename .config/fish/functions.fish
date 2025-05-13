#doas
function doasedit
    echo "󰗠 Checking current doas.conf syntax..."
    if doas doas -C /etc/doas.conf >/dev/null 2>&1
        echo "✅ Current config is valid."
    else
        echo "❌ Current config has errors (or permission denied)!"
        return 1
    end

    # Temporary file
    set tmpfile (mktemp /tmp/doas.conf.XXXXXX)

    # Create backup and copy in one command
    doas sh -c "cp /etc/doas.conf $tmpfile && chown $(whoami) $tmpfile"

    # Pick editor
    set editor $EDITOR
    if test -z "$editor"
        set editor micro
    end

    echo " Opening config in $editor..."
    $editor $tmpfile

    # Check if file was modified (compare original and edited file)
    set original_hash (doas sha256sum /etc/doas.conf | awk '{print $1}')
    set modified_hash (sha256sum $tmpfile | awk '{print $1}')

    # Make sure the hash values are not empty before comparison
    if test -z "$original_hash" -o -z "$modified_hash"
        echo "🚫 Error: Could not generate hash values. Permission issue or invalid file."
        return 1
    end

    if test $original_hash = $modified_hash
        echo "🚫 No changes were made to the config file."
    else
        echo "󰮥 Verifying your edits..."
        if doas doas -C $tmpfile >/dev/null 2>&1
            echo "✔ Syntax OK. Applying changes..."
            doas sh -c "cp $tmpfile /etc/doas.conf"
            echo "🎉 Changes saved successfully!"
        else
            echo "🚫 Invalid syntax! Changes not applied."
            echo "📁 Your edited file is saved at: $tmpfile"
        end
    end
end

#extracting
function extract

    if test -z "$argv"
        echo "❌ Please specify the file to extract."
        return 1
    end

    set file $argv[1]

    if not test -e $file
        echo "❌ File '$file' does not exist."
        return 1
    end
    
    echo "󰗠 Extracting '$file'..."

    switch (string split . $file)[-1]
        case "tar"
            echo "Extracting $file with tar..."
            tar -xf $file
        case "gz"
            echo "Extracting $file with tar..."
            tar -xzf $file
        case "bz2"
            echo "Extracting $file with tar..."
            tar -xjf $file
        case "xz"
            echo "Extracting $file with tar..."
            tar -xJf $file
        case "zip"
            echo "Extracting $file with unzip..."
            unzip $file
        case "7z"
            echo "Extracting $file with 7z..."
            7z x $file
        case "rar"
            echo "Extracting $file with unrar..."
            unrar x $file
        case "tar.gz"
            echo "Extracting $file with tar..."
            tar -xzf $file
        case "tar.bz2"
            echo "Extracting $file with tar..."
            tar -xjf $file
        case "*"
            echo "❌ Unsupported file format."
            return 1
    end

    echo "🎉 Extraction of '$file' completed!"
end
