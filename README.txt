Password manager
================

It allows the user to have a simple encrypted password database in 
a file. User can paste the selected password directly at the password 
prompt - that eliminates the problem of eavesdropping when manually 
selecting password in one window and pasting it to another.

Searches through an OpenPGP-encrypted file consisting of lines of form:

::

    description [description ...] password


Waits for clipboard contents requests until clipboard owner change, 
specified timeout or maximum number of requests is reached.

All specified patterns must be found within description tokens.  If more 
than one line matches, selection menu appears.

Use ``--help`` for details.

Features
--------
    
    * uses GPGME (interface to GnuPG) for decryption,
    * uses PyGTK for clipboard manipulation,
    * clipboard selection (PRIMARY or CLIPBOARD).

Example
-------

::

    $ cat > passwords
    password 1 to batmobile         qwerty
    password 2 to batmobile         123456
    password to the cave            admin1
    $ gpg -e passwords
    $ ./password-manager.py passwords.gpg batmobile 1

.. vi: ft=rst
