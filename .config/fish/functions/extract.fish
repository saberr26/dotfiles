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
end
