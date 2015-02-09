Password manager
================

It allows the user to have a simple encrypted password database in 
a text file. User can paste the selected password directly at the 
password prompt - that eliminates the problem of eavesdropping when 
manually selecting password in one window and pasting it to another.

Searches through an OpenPGP-encrypted file consisting of lines of form:

::

    description [description ...] password


Waits for clipboard contents requests until clipboard owner change, 
specified timeout or maximum number of requests is reached.

All specified patterns must be found within description tokens.  If more 
than one line matches, selection menu appears.

Search patterns may be passed as arguments or using the PRIMARY
clipboard. In those modes the manager first waits until you select some 
text and then treats it as pattern. This is useful for example when you 
``sudo`` on multiple machines simultaneously - you can select the 
hostname from a shell prompt.

Use ``--help`` for details.

Features
--------
    
    * uses GPGME (interface to GnuPG) for decryption,
    * can read a search pattern from the PRIMARY clipboard,
    * uses PyGTK for clipboard manipulation,
    * uses PyGTK to display a password selection GUI,
    * clipboard selection (PRIMARY or CLIPBOARD).

Example
-------

.. image:: http://wodny.org/img/screenshots/password-manager.gif

::
    
    # Create a password database
    $ cat > passwords
    password 1 to batmobile         qwerty
    password 2 to batmobile         123456
    password to the cave            admin1

    # Encrypt it
    $ gpg -e passwords

    # Find and paste passwords
    $ ./password-manager.py passwords.gpg batmobile 1
    $ ./password-manager.py -m clipgui -t 10 -n 1 passwords.gpg

    # Select a username@hostname string in your terminal.
    # The password manager will cut just the hostname
    # using a regexp and then search for the right password
    $ ./password-manager.py -m clipgui -r "@([^:]+):?"

.. vi: ft=rst
