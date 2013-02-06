#!/bin/sh

sourcefile=${1:?Source file is required}
sourcetype=${sourcefile##*.}

tempfile=$(mktemp) || exit 1
markfile=$(mktemp) || exit 2

do_remove () {
    [ -x /usr/bin/shred ] && shred -u "$tempfile" || rm -f "$tempfile"
    rm -f "$markfile"
}

do_error () {
    echo "$1" >&2
    do_remove
    exit 3
}

echo "Decrypting $sourcefile of type $sourcetype to $tempfile"
gpg -d < "$sourcefile" > "$tempfile" || do_error "Failed to decrypt sourcefile"
editor "$tempfile"
if [ "$tempfile" -nt "$markfile" ]; then
    echo "Rewriting sourcefile"
    if [ "$sourcetype" = "asc" ]; then
        gpg --default-recipient-self -e -a < "$tempfile" > "$sourcefile"
    else
        gpg --default-recipient-self -e < "$tempfile" > "$sourcefile"
    fi
    [ $? -ne 0 ] && do_error "Failed to reencrypt"
else
    echo "Edit aborted"
fi

do_remove

echo "Finished"
