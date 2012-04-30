#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import io
import gpgme
import gtk

class DecryptedLinesStreamer:
    def __init__(self, filename):
        self.filename = filename
        self.generator = None

    def __generator(self):
        with io.open(self.filename, mode="rb") as cipher:
            context = gpgme.Context()
            plain = io.BytesIO()
            context.decrypt(cipher, plain)
            for line in plain.getvalue().splitlines():
                yield line.decode("utf-8")

    def next(self):
        return self.generator.next()

    def __next__(self):
        return self.next()

    def __iter__(self):
        self.generator = self.__generator()
        return self

class PasswordEntry:
    def __init__(self, description, password):
        self.description = description
        self.password = password

    def __unicode__(self):
        return u"<PasswordEntry: {0}>".format(self.description)

def generate_password_entries(password_lines):
    for line in password_lines:
        line = line.strip().expandtabs()
        (description, _, password) = line.rpartition(" ")
        description = description.strip()
        yield PasswordEntry(description, password)

def simple_filter(entries, phrase):
    for entry in entries:
        if phrase in entry.description:
            yield entry

class PasswordEntrySelector:
    def __init__(self, entries):
        self.entries = list(entries)

    def select(self):
        found = len(self.entries)
        print("Found {0} password entries.".format(found))
        if found == 0:
            return None
        if found > 1:
            for i in range(0, len(self.entries)):
                print("{0:2d}) {1}".format(i+1, self.entries[i].description))
            try:
                sys.stdout.write("Select an entry: ")
                i = int(sys.stdin.readline().strip())
                entry = self.entries[i-1]
                if len(entry.password) == 0:
                    print("Empty password.")
                    return None
            except (ValueError, IndexError, KeyboardInterrupt):
                return None
        return entry

class Clipboard:
    def get(self, clipboard, selectiondata, info, data):
        print("Password request.")
        selectiondata.set_text(self.password)
    
    def clear(self, clipboard, data):
        print("Clipboard contents changed.")
        gtk.main_quit()

    def __init__(self, password):
        self.password = password
        self.clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_PRIMARY)
        self.clipboard.set_with_data((("UTF8_STRING", 0, 0),), self.get, self.clear, None)
        print("Waiting for requests...")
        try:
            gtk.main()
        except KeyboardInterrupt:
            pass
        print("Done waiting.")


if len(sys.argv) != 3:
    exit("Encrypted password file and search phrase required.")

(filename, phrase) = sys.argv[1:]

d = DecryptedLinesStreamer(filename)
s = generate_password_entries(d)
f = simple_filter(s, phrase)
ps = PasswordEntrySelector(f)
entry = ps.select()

if entry is not None:
    Clipboard(entry.password)
