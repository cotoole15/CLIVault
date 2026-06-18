#!/usr/bin/env python3

import base64
import os
import glob
import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import sys
import sqlite3
import curses
from curses import wrapper
import pyperclip


class Entry:
    def __init__(
        self,
        name=None,
        username=None,
        password=None,
        email=None,
        url=None,
        creating=False,
        changed=False,
    ):
        if not (creating):
            if name is None:
                raise ValueError("No name provided")
            if password is None:
                raise ValueError("NO password provided")
        self.name = name
        self.username = username
        self.password = password
        self.url = url
        self.email = email
        self.changed = changed

    def __str__(self):
        return self.name


def entry_menu(stdscr, entry, entries, changed_entries):
    # The following code was generated with the help of cs50's AI which gave me instructions on creating a tuple for functions with different numbers of arguments
    # The tuple's layout is: label, function, args
    options = (
        ("Copy username", cp_username, (entry,)),
        ("Copy password", cp_pass, (entry,)),
        (
            "Edit entry",
            add_or_update,
            (stdscr, entry, entries, changed_entries),
        ),
    )

    stdscr.keypad(True)

    curses.noecho()
    index = 0
    while True:
        stdscr.clear()

        stdscr.addstr(f"Options menu:\n", curses.A_BOLD)

        for i, (label, function, args) in enumerate(options):
            if i == index:

                stdscr.addstr(f" * {label}\n", curses.A_REVERSE)

            else:
                stdscr.addstr(f"{label}\n")
        stdscr.move(index + 1, 0)

        key = stdscr.getkey()
        if key == "KEY_DOWN":
            if index < len(options) - 1:
                index += 1

        elif key == "KEY_UP":
            if index > 0:
                index -= 1
        elif key == "Key_ENTER" or key == "\n" or key == "\r":
            option = options[index]
            label, function, args = option

            # Execute the function
            function(*args)
            break


def cp_pass(entry):
    if entry is None:
        raise ValueError("No entry provided")
    pyperclip.copy(entry.password)


def cp_username(entry):
    if entry is None:
        raise ValueError("No entry provided")
    pyperclip.copy(entry.username)


def prompt_delete(stdscr, entry, entries, changed_entries):
    stdscr.clear()
    ans = prompt(stdscr, "Delete entry? y/n")
    if ans == "y":
        entries.remove(entry)


def getpass(stdscr, prompt):
    stdscr.clear()
    stdscr.refresh()

    curses.noecho()

    password = ""
    key = ""

    stdscr.addstr(prompt + "\n")

    while key != "\n":

        stdscr.clrtoeol()

        key = stdscr.getkey()
        if key.isalpha():
            password += key
        elif key == "\n":

            curses.echo()

            return password
        elif key == "KEY_BACKSPACE" or key == "\b" or key == "\x7f":
            password = password[:-1]
        stdscr.move(1, 0)

        stdscr.addstr("*" * len(password))


def decrypt_entry(row, key):
    if not (row):
        raise ValueError("No row provided")
    if not (key):
        raise ValueError("NO decryption key provided")

    name = decrypt(key, row[0].encode()) if row[0] else None
    email = decrypt(key, row[1].encode()) if row[1] else None
    username = decrypt(key, row[2].encode()) if row[2] else None
    password = decrypt(key, row[3]) if row[3] else None
    url = decrypt(key, row[4].encode()) if row[4] else None
    dec_entry = Entry(name, username, password, email, url, False, False)
    return dec_entry


def prompt(stdscr, text):

    # Show typed characters
    curses.echo()
    stdscr.keypad(False)

    stdscr.addstr(text)
    typed_text = stdscr.getstr().decode()
    curses.noecho()
    stdscr.keypad(True)
    return typed_text


def encrypt_entries(conn, cursor, key, entries):

    # recursively encrypt the contents of each entry

    for e in entries:
        # encode each variable into bytes and then encrypt and decode it back into a string, accept for the password

        e.name = encrypt(key, e.name)
        e.username = encrypt(key, e.username)
        e.password = encrypt(key, e.password)
        e.email = encrypt(key, e.email)
        e.url = encrypt(key, e.url)
    return entries


def save_entries(conn, cursor, key, entries):
    encrypted_entries = encrypt_entries(conn, cursor, key, entries)
    cursor.execute("DELETE FROM passwords")
    for e in entries:
        cursor.execute(
            "insert into passwords values(?,?,?,?,?)",
            (
                e.name,
                e.email,
                e.username,
                e.password,
                e.url,
            ),
        )


def generate_editing_options(entry):
    # This generates the list of entries and exit options to be used by add_or_update
    options = (
        [
            f"Title: {entry.name if entry.name is not None else 'not set'}",
            set_name,
            entry,
        ],
        [
            f"Username: {entry.username if entry.username is not None else 'Not set'}",
            set_username,
            entry,
        ],
        [
            f"Password: {'*' * len(entry.password) if entry.password is not None else 'not set'}",
            set_password,
            entry,
        ],
        [
            f"e-mail: {entry.email if entry.email is not None else 'Not set'}",
            set_email,
            entry,
        ],
        [f"URL: {entry.url if entry.url is not None else 'Not set'}", set_url, entry],
        ["Cancel", None, None],
        ["Save changes", None, None],
    )
    return options


def prompt_save(stdscr, conn, cursor, key, entries, changed_entries):
    if not (changed_entries):
        # Close without saving anything
        cursor.close()
        conn.close()
    else:
        stdscr.clear()
        stdscr.addstr("You have changed the following entries:\n")
        for name in changed_entries:
            stdscr.addstr(name + "\n")
        ans = prompt(stdscr, "save changes?")
        if "y" in ans:
            save_entries(conn, cursor, key, entries)
            conn.commit()
            cursor.close()
            conn.close()


def save_entry(new_entry, entries, changed_entries):
    if new_entry is None:
        raise ValueError("No entry provided")
    if entries is None:
        raise ValueError("No entries provided")

    found = False
    for i, entry in enumerate(entries):
        if new_entry == entry and new_entry.changed:
            # Reset changed state
            new_entry.changed = False
            changed_entries.append(new_entry.name)

            entries[i] = new_entry

            found = True  # The entry already exists
            break
    if not (found):
        new_entry.changed = False
        changed_entries.append(new_entry.name)

        entries.append(new_entry)


def set_username(stdscr, entry):
    username = prompt(stdscr, "Enter new username")
    if username == "":
        prompt(stdscr, "Username unchanged, press enter to return to entry creation")
    else:
        entry.username = username
        entry.changed = True


def set_password(stdscr, entry):
    while True:
        new_password = getpass(stdscr, "Enter new password")
        retyped = getpass(stdscr, "Retype new password")
        try:
            validate_pass(new_password, retyped)
        except ValueError as e:
            prompt(stdscr, e)
            continue
        break
    entry.password = new_password
    entry.changed = True


def set_name(stdscr, entry):
    name = prompt(stdscr, "Enter a name for this entry:")
    if name == "":
        prompt(stdscr, "Name unchanged, press enter to return to entry creation")
    else:
        entry.name = name
        entry.changed = True


def set_email(stdscr, entry):
    email = prompt(stdscr, "Enter an e-mail address")
    if email == "":
        prompt(stdscr, "email unchanged, press enter to return to entry creation")
    else:
        entry.email = email
        entry.changed = True


def set_url(stdscr, entry):
    url = prompt(stdscr, "Enter URL:")
    if url == "":
        prompt(stdscr, "URL unchanged, press enter to return to entry creation")
    else:
        entry.url = url
        entry.changed = True


def add_or_update(stdscr, entry=None, entries=None, changed_entries=None):
    if entries is None:
        raise ValueError("No entries provided")

    if entry is None:
        entry = Entry(None, None, None, None, None, True)

    curses.noecho()
    stdscr.keypad(True)
    stdscr.clear()
    index = 0
    option = None
    options = generate_editing_options(entry)

    while True:

        stdscr.clear()
        stdscr.refresh()
        stdscr.addstr(
            f"{'Create new entry:\n' if entry is None else 'Edit entry:\n'}",
            curses.A_BOLD,
        )
        for i, (label, functionin, value) in enumerate(options):
            if i == index:
                # Mark the currently selected option as highlighted
                stdscr.addstr(f"* {label}\n", curses.A_REVERSE)

            else:
                stdscr.addstr(f"{label}\n")
        stdscr.move(index + 1, 0)
        stdscr.refresh()

        key = stdscr.getkey()
        if key == "KEY_DOWN":
            if index < len(options) - 1:
                index += 1

        elif key == "KEY_UP":
            if index > 0:
                index -= 1
        if key == "Key_ENTER" or key == "\n" or key == "\r":
            stdscr.clear()

            option = options[index]
            label, function, value = option
            if label == "Cancel":

                return
            elif label == "Save changes":
                try:
                    save_entry(entry, entries, changed_entries)
                except ValueError as e:
                    prompt(stdscr, f"Couldn't save entry: {e}")
                    continue
                return
            else:
                function(stdscr, value)
                options = generate_editing_options(entry)

                curses.initscr()
                continue


def manage_entries(conn, cursor, dec_key, stdscr, entries):
    index = 0
    changed_entries = []
    curses.noecho()
    curses.cbreak()

    stdscr.keypad(True)
    stdscr.clear()

    while True:
        options = []
        for entry in entries:
            options.append(entry)
        options.append("Add entry")
        options.append("quit")

        stdscr.clear()
        stdscr.addstr(f"showing {len(entries)} Passwords:\n", curses.A_BOLD)

        for i, option in enumerate(options):
            if i == index:

                stdscr.addstr(f"* {option}\n", curses.A_REVERSE)

            else:
                stdscr.addstr(f"{option}\n")
        stdscr.move(index + 1, 0)
        stdscr.refresh()

        key = stdscr.getkey()
        if key == "KEY_DOWN":
            if index < len(options) - 1:
                index += 1

        elif key == "KEY_UP":
            if index > 0:
                index -= 1
        elif key == "Key_ENTER" or key == "\n" or key == "\r":

            if index == len(options) - 2:
                add_or_update(stdscr, None, entries, changed_entries)
                continue

            elif index == len(options) - 1:
                prompt_save(stdscr, conn, cursor, dec_key, entries, changed_entries)
                break
            else:
                entry = options[index]
                entry_menu(stdscr, entry, entries, changed_entries)

                continue
        if key == "KEY_DC":
            entry = options[index]
            prompt_delete(stdscr, entry, entries, changed_entries)


def decrypt(key, bytes):
    fernet = Fernet(key)

    try:
        return fernet.decrypt(bytes).decode()
    except (cryptography.exceptions.InvalidSignature, cryptography.fernet.InvalidToken):
        raise ValueError("Wrong password")


def build_entries(cursor, key):

    entries = []
    cursor.execute("SELECT * FROM passwords")
    rows = cursor.fetchall()

    for row in rows:

        dec_entry = decrypt_entry(row, key)

        entries.append(dec_entry)
    return entries


def encrypt(key, s):
    if s is None:
        return None
    fernet = Fernet(key)
    s = s.encode()
    return fernet.encrypt(s).decode()


def quit(stdscr):
    stdscr.clear()
    stdscr.addstr("Goodbye, thanks for trying out my program!")
    prompt(stdscr, "Press enter to exit")
    sys.exit(0)


def open_db_interactive(stdscr):
    # This reuses the curses code that I implemented in main
    options = []
    options.append("Enter path to database")
    databases = glob.glob("*.db")
    options = options + databases

    index = 0
    path = None
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)

    while True:
        stdscr.clear()

        stdscr.addstr("Choose database to open: \n", curses.A_BOLD)

        for i, option in enumerate(options):
            if i == index:
                stdscr.addstr(f"* {option}\n", curses.A_REVERSE)

            else:
                stdscr.addstr(f"{option}\n")
        stdscr.move(index + 1, 0)
        stdscr.refresh()

        key = stdscr.getkey()
        if key == "KEY_DOWN":

            if index + 1 < len(options):
                index += 1
            else:
                index = 0

        elif key == "KEY_UP":
            if index > 0:
                index -= 1
        if key == "Key_ENTER" or key == "\n" or key == "\r":
            curses.nocbreak()
            stdscr.keypad(False)

            stdscr.clear()
            stdscr.refresh()
            curses.endwin()
            if index == 0:
                path = prompt(stdscr, "Enter path:")
                break
            else:
                path = option
                break
    while True:
        password = getpass(stdscr, "Enter password:")
        try:
            conn, cursor, key = open_db(path, password)
        except ValueError as e:
            prompt(stdscr, f" {e}\nPress enter to continue")
            stdscr.clear()
            continue
        except FileNotFoundError:
            stdscr.addstr(f"{e} \n press enter to continue")
            prompt(stdscr, "Press enter to continue")

            continue
        break
    entries = build_entries(cursor, key)
    manage_entries(conn, cursor, key, stdscr, entries)


def validate_pass(password, retyped_password):
    if password != retyped_password:
        raise ValueError("Passwords don't match")
    if password == "":
        raise ValueError("Password must not be empty")


def generate_key(password, salt=None):
    if not (password):
        raise ValueError("No password provided")

    # generate a salt if none is provided (random data to make a key stronger)
    # As this function will also be used to retrieve a key from an existing database, salt can be supplied.
    if salt is None:
        salt = os.urandom(16)
    # Derive the key.
    # source: https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=1_200_000,
    )
    # Cryptography expects a password in bytes, converted below.
    key = kdf.derive(password.encode())
    return base64.b64encode(key)


# An interactive  function to take input and run mkdb, which handles database creation.
def prompt_db(stdscr):
    prompt(
        stdscr,
        "On the next screen, you will be asked to select the name and location for your new database.\nPlease press enter to continue.",
    )
    name = None
    while not (name):
        name = prompt(stdscr, "Enter a name for your new database:")
        if not (name):
            stdscr.clear()
            stdscr.refresh()
            stdscr.addstr("Name cannot be empty")

        else:
            break

    name = name + ".db"
    if os.path.exists(name):

        stdscr.addstr(
            "There is already a database with that name, do you want to overwrite it?"
        )
        answer = prompt(stdscr, "Please type YES in upper case letters to continue")
        if answer != "YES":
            prompt(
                stdscr,
                " Database creation cancelled \nPress enter to return to the menu",
            )
            stdscr.clear()
            wrapper(main)
        else:
            os.remove(name)
            stdscr.addstr("removed " + name)

    while True:
        password = getpass(stdscr, "Enter the password for your new database.")
        retyped_password = getpass(stdscr, "Please enter the same password again:")

        try:
            validate_pass(password, retyped_password)
        except ValueError as e:

            stdscr.addstr(e)
            continue
        else:
            prompt(stdscr, "Password set. Press enter.")

            break
    stdscr.addstr("Creating database....")
    try:
        mkdb(name, password)

    except sqlite3.Error as e:
        stdscr.addstr("Error creating database: \n" + str(e))
        prompt(stdscr, "Press enter to continue")
        prompt_db()
    stdscr.addstr("Successfully created new database")
    prompt(stdscr, "Press enter to continue")


def mkdb(name, password):
    salt = os.urandom(16)
    key = generate_key(password, salt)
    # Create fernet object
    fernet = Fernet(key)

    # encrypt the word true, to see if the database has been unlocked
    s = fernet.encrypt("true".encode())
    conn = sqlite3.connect(name)
    cursor = conn.cursor()
    # Create metadata
    cursor.execute(""" Create TABLE metadata (
        key TEXT,
        value BLOB
    );
    """)
    cursor.execute(
        "INSERT INTO metadata (key,value) VALUES (?,?)",
        (
            "salt",
            salt,
        ),
    )
    cursor.execute(
        "INSERT INTO metadata (key,value) VALUES (?,?)",
        (
            "is_unlocked",
            s,
        ),
    )

    cursor.execute("""create TABLE passwords(
        name TEXT,
        email TEXT,
        username TEXT,
        password BLOB,
        url TEXT
    );""")
    conn.commit()
    conn.close()


def open_db(path, password):
    if not (os.path.exists(path)):
        raise FileNotFoundError(f"The file at {path} does not exist")

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT value FROM metadata WHERE key="salt";
    """)
    salt = cursor.fetchone()[0]

    key = generate_key(password, salt)
    cursor.execute("""
        SELECT value FROM metadata
        WHERE key="is_unlocked";    
    """)
    is_unlocked = cursor.fetchone()[0]
    try:
        is_unlocked = decrypt(key, is_unlocked)
    except (cryptography.exceptions.InvalidSignature, cryptography.fernet.InvalidToken):
        raise ValueError("Wrong password")
    if is_unlocked == "true":
        return (conn, cursor, key)
    else:
        raise ValueError("wrong password")


def main(stdscr):
    menu_items = [
        ("Create new database", prompt_db, stdscr),
        ("Open an existing database", open_db_interactive, stdscr),
        ("quit", quit, stdscr),
    ]
    curses.noecho()
    curses.cbreak()  # Allow for responding to keys without hitting enter.
    stdscr.keypad(True)
    index = 0
    while True:
        stdscr.clear()

        stdscr.addstr("Main menu:\n", curses.A_BOLD)

        for i, option in enumerate(menu_items):
            if i == index:
                stdscr.addstr(f"* {option[0]}\n", curses.A_REVERSE)

            else:
                stdscr.addstr(f"{option[0]}\n")
        stdscr.move(index + 1, 0)
        stdscr.refresh()

        key = stdscr.getkey()
        if key == "KEY_DOWN":
            if index < 2:
                index += 1

        elif key == "KEY_UP":
            if index > 0:
                index -= 1
        if key == "Key_ENTER" or key == "\n" or key == "\r":
            curses.nocbreak()
            stdscr.keypad(False)

            stdscr.clear()
            stdscr.refresh()

            menu_items[index][1](menu_items[index][2])
            return


if __name__ == "__main__":
    while True:
        wrapper(main)
