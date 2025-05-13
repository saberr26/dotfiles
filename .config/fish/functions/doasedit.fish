function doasedit
    echo "󰗠 Checking current doas.conf syntax..."
    if doas -C /etc/doas.conf >/dev/null 2>&1
        echo "✅ Current config is valid."
    else
        echo "❌ Current config has errors!"
        return 1
    end

    # Create temporary editable copy
    set tmpfile (mktemp /tmp/doas.conf.XXXXXX)
    cp /etc/doas.conf $tmpfile

    echo " Opening config in micro editor..."
    micro $tmpfile

    echo "󰮥 Verifying your edits..."
    if doas -C $tmpfile >/dev/null 2>&1
        echo "✔ Syntax OK. Applying changes..."
        doas cp $tmpfile /etc/doas.conf
        echo "🎉 Changes saved successfully!"
    else
        echo "🚫 Invalid syntax! Changes not applied."
        echo "📁 Your edited file is saved at: $tmpfile"
    end
end
