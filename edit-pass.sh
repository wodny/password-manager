#!/bin/sh

sourcefile=${1:?Source file is required}
sourcetype=${sourcefile##*.}

tempsource=$(mktemp) || exit 1
tempdest=$(mktemp) || exit 2
markfile=$(mktemp) || exit 3

do_remove () {
    if [ -x /usr/bin/shred ]; then
        msg "Shreding temporary files"
        shred -u "$tempsource"
        shred -u "$tempdest"
    else
        msg "Removing temporary files"
        rm -f "$tempsource"
        rm -f "$tempdest"
    fi
    rm -f "$markfile"
}

msg() {
  echo ">>>" "$@"
}

do_error () {
    msg "$1" >&2
    do_remove
    exit 3
}

msg "Decrypting $sourcefile of type $sourcetype to $tempsource"
gpg -d < "$sourcefile" > "$tempsource" || do_error "Failed to decrypt sourcefile"
editor "$tempsource"
if [ "$tempsource" -nt "$markfile" ]; then
    msg "Rewriting sourcefile"
    if [ "$sourcetype" = "asc" ]; then
        gpg --default-recipient-self -e -a < "$tempsource" > "$tempdest"
    else
        gpg --default-recipient-self -e < "$tempsource" > "$tempdest"
    fi
    [ $? -ne 0 ] && do_error "Failed to reencrypt"
    msg "Copying temporary encrypted file $tempsource to original source $sourcefile"
    cp "$tempdest" "$sourcefile" || do_error "Failed to copy"
else
    msg "Edit aborted"
fi

do_remove

msg "Finished"
