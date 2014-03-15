#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import textwrap

import io
import gpgme

import pygtk
pygtk.require('2.0')
import gtk
import glib
import gobject


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
                if len(line) == 0:
                    continue
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

def match_phrases(entry, phrases):
    for phrase in phrases:
        if phrase not in entry.description:
            return False
    return True

def simple_filter(entries, phrases):
    for entry in entries:
        if match_phrases(entry, phrases):
            yield entry

class PasswordEntrySelector:
    pass

class PasswordEntrySelectorTUI(PasswordEntrySelector):
    def __init__(self, entries):
        self.entries = list(entries)

    def select(self):
        found = len(self.entries)
        print("Entries found: {0}.".format(found))
        if found == 0:
            return None
        for i in range(0, len(self.entries)):
            print("{0:2d}) {1}".format(i+1, self.entries[i].description))
        if found > 1:
            try:
                sys.stdout.write("Select an entry: ")
                i = int(sys.stdin.readline().strip())
                entry = self.entries[i-1]
            except (ValueError, IndexError, KeyboardInterrupt):
                return None
        else:
            entry = self.entries[0]
        if len(entry.password) == 0:
            print("Empty password.")
            return None
        return entry

class PasswordEntrySelectorGUI(PasswordEntrySelector):
    def __init__(self, entries):
        self.entry = None

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event", self._delete_event)
        self.window.connect("destroy", self._destroy)

        box = gtk.VBox()
        self.window.add(box)
        box.show()

        for entry in entries:
            button = gtk.Button(entry.description)
            button.connect("clicked", self._clicked, entry)
            button.connect_object("clicked", gtk.Widget.destroy, self.window)
            box.pack_start(button)
            button.show()

        screen, x, y, mods = gtk.gdk.display_get_default().get_pointer()
        self.window.move(x, y)
        self.window.set_decorated(False)
        
        self.window.show()

    def select(self):
        gtk.main()
        return self.entry

    def _clicked(self, widget, data=None):
        self.entry = data

    def _delete_event(self, widget, event, data=None):
        return False

    def _destroy(self, widget, data=None):
        gtk.main_quit()



class Clipboard:
    def __init__(self, clipboard_type):
        clipboard_ids = {
            "primary": gtk.gdk.SELECTION_PRIMARY,
            "clipboard": gtk.gdk.SELECTION_CLIPBOARD
        }
        clipboard_type = clipboard_ids[clipboard_type]

        self.clipboard = gtk.clipboard_get(clipboard_type)
        self.clipboard.set_with_data((("UTF8_STRING", 0, 0),), self.get, self.clear, None)

    def loop(self):
        print("Waiting for clipboard events...")
        try:
            gtk.main()
        except KeyboardInterrupt, e:
            print("Done waiting.")
            raise e

class ClipboardPassword(Clipboard):
    def get(self, clipboard, selectiondata, info, data):
        print("Password request.")
        selectiondata.set_text(self.password)
        self.requests -= 1
        if self.requests == 0:
            print("Request count limit reached.")
            gobject.idle_add(gtk.main_quit)
    
    def clear(self, clipboard, data):
        print("Clipboard contents changed.")
        gtk.main_quit()

    def __init__(self, clipboard_type, requests, password):
        Clipboard.__init__(self, clipboard_type)
        self.requests = requests
        self.password = password

class ClipboardSelect(Clipboard):
    def get(self, clipboard, selectiondata, info, data):
        print("Unexpected clipboard contents request.")
        selectiondata.set_text("select a pattern\n")

    def clear(self, clipboard, data):
        print("Clipboard contents changed.")
        self.text = clipboard.wait_for_text()
        gtk.main_quit()

    def __init__(self, clipboard_type = "primary"):
        Clipboard.__init__(self, clipboard_type)

def timeout_quit():
    print("Timeout.")
    gtk.main_quit()

def parse_arguments():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
            Searches through an OpenPGP-encrypted file consisting of lines of form:
            description [description ...] password

            Waits for clipboard contents requests until
            clipboard owner change, specified timeout or
            maximum number of requests is reached.
            
            All specified patterns must be found within description tokens.
            If more than one line matches, selection menu appears.
        """)
    )
    parser.add_argument("--mode", "-m", choices=["argtui", "cliptui", "clipgui"], default="argtui", help="interaction mode")
    parser.add_argument("--clipboard", "-c", choices=["primary", "clipboard"], default="primary")
    parser.add_argument("--timeout", "-t", type=int, help="application quits after this timeout")
    parser.add_argument("--requests", "-n", type=int, default=-1, help="number of accepted requests before quiting")
    parser.add_argument("filename", help="filename of encrypted list")
    parser.add_argument("patterns", nargs="*", help="patterns to match against")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    
    if arguments.mode.startswith("arg"):
        if len(arguments.patterns) == 0:
            exit("You must specify at least one pattern.")
        patterns = arguments.patterns
    else:
        cs = ClipboardSelect()
        try:
            cs.loop()
        except KeyboardInterrupt:
            exit("Nothing to do.")
        patterns = cs.text.split()
    
    d = DecryptedLinesStreamer(arguments.filename)
    s = generate_password_entries(d)
    f = simple_filter(s, patterns)

    if arguments.mode.endswith("tui"):
        ps = PasswordEntrySelectorTUI(f)
        entry = ps.select()
    else:
        ps = PasswordEntrySelectorGUI(f)
        entry = ps.select()
    
    if entry is not None:
        c = ClipboardPassword(arguments.clipboard, arguments.requests, entry.password)
        if arguments.timeout is not None:
            glib.timeout_add_seconds(arguments.timeout, timeout_quit)
        try:
            c.loop()
        except KeyboardInterrupt:
            pass
