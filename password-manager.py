#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import socket
import signal
import argparse
import textwrap
import re
import copy

import io
import gpgme

import pygtk
pygtk.require('2.0')
import gtk
import glib
import gobject

__version__ = "0.29"

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
    def __init__(self, entries):
        self.entries = list(entries)


class PasswordEntrySelectorTUI(PasswordEntrySelector):
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


class Popup:
    def __init__(self, labeltext, selfdestruct=0, gtkquit=False):
        self.selfdestruct = selfdestruct
        self.gtkquit = gtkquit

        self.window = gtk.Window(gtk.WINDOW_POPUP)
        self.window.set_border_width(10)

        self.window.connect("delete_event", self._delete_event)
        self.window.connect("destroy", self._destroy)

        self.box = gtk.VBox()
        self.window.add(self.box)
        self.box.show()

        label = gtk.Label(labeltext)
        self.box.pack_start(label)
        label.show()

    def show(self):
        screen, x, y, mods = gtk.gdk.display_get_default().get_pointer()
        width, height = self.window.get_size()
        x = max(0, x - width * 2 / 3)
        self.window.move(x, y)
        self.window.set_decorated(False)

        if self.selfdestruct:
            glib.timeout_add_seconds(self.selfdestruct, self._timeout)

        self.window.show()

    def _timeout(self):
        self.window.destroy()
    
    def _delete_event(self, widget, event, data=None):
        return False

    def _destroy(self, widget, data=None):
        if self.gtkquit:
            gtk.main_quit()


class PasswordEntrySelectorGUI(PasswordEntrySelector, Popup):
    def __init__(self, entries):
        PasswordEntrySelector.__init__(self, entries)
        labeltext = "Entries found: {0}.".format(len(self.entries))
        Popup.__init__(self, labeltext, 1 if len(self.entries) == 0 else 0, True)
        self.entry = None

        if(len(self.entries) != 0):
            separator = gtk.HSeparator()
            self.box.pack_start(separator, padding=5)
            separator.show()

        table = gtk.Table()

        for i, entry in enumerate(self.entries):
            button = gtk.Button(entry.description)
            button.connect("clicked", self._clicked, entry)
            button.connect_object("clicked", gtk.Widget.destroy, self.window)
            table.attach(button, 0, 1, i, i+1)
            button.show()

            entry_newline = copy.copy(entry)
            entry_newline.description = "↵"
            entry_newline.password += '\n'

            button = gtk.Button(entry_newline.description)
            button.connect("clicked", self._clicked, entry_newline)
            button.connect_object("clicked", gtk.Widget.destroy, self.window)
            table.attach(button, 1, 2, i, i+1)
            button.show()

        self.box.pack_start(table)
        table.show()
        self.show()

    def select(self):
        print("Select password via GUI.")
        try:
            gtk.main()
        except KeyboardInterrupt:
            pass
        return self.entry

    def _clicked(self, widget, data=None):
        self.entry = data



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

def timeout_quit(usegui):
    print("Timeout.")
    if usegui:
        Popup("Timeout", 1, True).show()
    else:
        gtk.main_quit()

def get_agent():
    agent = os.getenv("GPG_AGENT_INFO")
    if not agent:
        raise ValueError

    # These two lines can also throw ValueError
    sock, pid, v = agent.rsplit(":", 2)
    pid = int(pid)
    return (sock, pid, v)

def clear_passphrases(dialog = True, hup = False):
    try:
        if dialog: clear_passphrases_dialog()
        if hup: clear_passphrases_hup()
    except ValueError, OSError:
        print("Failed to clear passphrases.")
        return False
    print("Probably cleared passphrases.")
    return True

def clear_passphrases_dialog():
    context = gpgme.Context()
    fprs = set()
    for key in context.keylist(None, True):
        fprs |= set((sk.fpr for sk in key.subkeys))
    sockpath, _, _ = get_agent()
    sock = socket.socket(socket.AF_UNIX)
    sock.connect(sockpath)
    f = io.open(sock.fileno())
    if not f.readline().startswith("OK"):
        raise ValueError("No greeting")
    for fpr in fprs:
        print("Clearing passphrase for {0}...".format(fpr))
        sock.send("CLEAR_PASSPHRASE {0}\n".format(fpr))
        if not f.readline().startswith("OK"):
            raise ValueError("Bad response")
    print("Sent request to clear {0} passphrases.".format(len(fprs)))

def clear_passphrases_hup():
    _, pid, _ = get_agent()
    os.kill(pid, signal.SIGHUP)
    print("Sent HUP to GPG agent (pid = {0}).".format(pid))

def parse_arguments():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
            A tool for easy pasting passwords via an X11 clipboard.

            Searches through an OpenPGP-encrypted text file consisting 
            of lines of form:
            description [description ...] password

            Waits for clipboard contents requests until clipboard owner 
            change, specified timeout or maximum number of requests is 
            reached.
            
            All specified search patterns must be found within          
            description tokens. If more than one line matches, selection 
            menu appears. In *tui modes it is a text menu, in *gui modes 
            a graphical menu appears under the cursor.

            Search patterns may be passed as arguments (argtui and 
            arggui modes) or using the PRIMARY clipboard (cliptui and 
            clipgui modes). In clip* modes the manager first waits until 
            you select some text and then treats it as pattern. This is 
            useful for example when you sudo on multiple machines 
            simultaneously - you can select the hostname from a shell 
            prompt.
        """)
    )
    parser.add_argument('--version', action='version', version="%(prog)s {0}".format(__version__))
    parser.add_argument("--mode", "-m", choices=["argtui", "arggui", "cliptui", "clipgui"], default="argtui", help="interaction mode")
    parser.add_argument("--clipboard", "-c", choices=["primary", "clipboard"], default="primary")
    parser.add_argument("--timeout", "-t", type=int, help="application quits after this timeout")
    parser.add_argument("--requests", "-n", type=int, default=-1, help="number of accepted requests before quiting")
    parser.add_argument("--newline", "-l", action="store_true", help="add new line to the password")
    parser.add_argument("--regex", "-r", help="regex to get a search pattern from clipboard text (e.g. hostname)")
    parser.add_argument("--regex-group", "-g", type=int, default=1, help="regex group to use as a search pattern")
    parser.add_argument("--hup", action="store_true", help="HUP GPG agent if flushing cached passphrases")
    parser.add_argument("--flush-now", "-k", action="store_true", help="flush cached passphrases at startup")
    parser.add_argument("--flush", "-f", action="store_true", help="flush cached passphrases at shutdown")
    parser.add_argument("filename", nargs="?", help="filename of encrypted list")
    parser.add_argument("patterns", nargs="*", help="patterns to match against")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()

    if arguments.flush_now:
        exit(clear_passphrases(hup = arguments.hup) == False)

    if not arguments.filename:
        exit("You must specify the encrypted file.")

    usegui = arguments.mode.endswith("gui")
    
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
        if arguments.regex:
            try:
                regex = re.compile(arguments.regex)
            except re.error, e:
                exit("regex error: {}".format(e))
            match = regex.search(cs.text)
            if match:
                patterns = [match.group(arguments.regex_group)]
            else:
                patterns = cs.text.split()
        else:
            patterns = cs.text.split()
    
    d = DecryptedLinesStreamer(arguments.filename)
    s = generate_password_entries(d)
    f = simple_filter(s, patterns)

    if usegui:
        ps = PasswordEntrySelectorGUI(f)
        entry = ps.select()
    else:
        ps = PasswordEntrySelectorTUI(f)
        entry = ps.select()
    
    if entry is not None:
        password = entry.password + "\n" if arguments.newline else entry.password
        c = ClipboardPassword(arguments.clipboard, arguments.requests, password)
        if arguments.timeout is not None:
            glib.timeout_add_seconds(arguments.timeout, timeout_quit, usegui)
        try:
            c.loop()
        except KeyboardInterrupt:
            pass

    if arguments.flush:
        exit(clear_passphrases(hup = arguments.hup) == False)
