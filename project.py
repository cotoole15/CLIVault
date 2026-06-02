#!/usr/bin/env python3
import getpass  # For capturing password input.
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


class Entry:
    def __init__(self, name, username, password, email=None, url=None):
        self.name = name
        self.username = username
        self.password = password
        self.url = url
        self.email = email


def decrypt(key, bytes):
    fernet = Fernet(key)

    try:
        return fernet.decrypt(bytes).decode()
    except cryptography.exceptions.InvalidSignature:
        raise ValueError("Wrong password")


def build_entries(cursor):
    input(
        "This code does not exist yet. But if you got here, the database was unlocked."
    )


def encrypt(key, s):
    fernet = Fernet(key)
    return fernet.encrypt(s.encode())


def quit(stdscr):
    print("Goodbye, thanks for trying out my program!")
    input("Press enter to exit")
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
            curses.endwin()
            if index == 0:
                path = input("Enter path:")
                break
            else:
                path = option
                break
    while True:
        password = input("Enter password")
        try:
            cursor = open_db(path, password)
        except ValueError as e:
            print(e)
            continue
        except FileNotFoundError:
            print(e)
            continue
        build_entries(cursor)


def validate_pass(password, retyped_password):
    if password != retyped_password:
        raise ValueError("Passwords don't amtch")
    if password == "":
        raise ValueError("Password must not be empty")


def generate_key(password, salt=None):

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
    return base64.urlsafe_b64encode(key)


# An interactive  function to take input and run mkdb, which handles database creation.
def prompt_db(stdscr):
    input(
        "On the next screen, you will be asked to select the name and location for your new database.\nPlease press enter to continue."
    )
    name = None
    while not (name):
        name = input("Enter a name for your new database:")
        if not (name):
            print("Name cannot be empty")
        else:
            break

    name = name + ".db"
    if os.path.exists(name):
        print(
            "There is already a database with that name, do you want to overwrite it?"
        )
        answer = input("Please type YES in upper case letters to continue")
        if answer != "YES":
            print("Database creation cancelled")
            input("Press enter to return to the menu")
            wrapper(main)
        else:
            os.remove(name)
            print("removed " + name)

    while True:
        password = getpass.getpass("Enter the password for your new database.")
        retyped_password = getpass.getpass("Please enter the same password again:")

        try:
            validate_pass(password, retyped_password)
        except ValueError as e:

            print(e)
            continue
        else:
            input("Password set. Press enter.")

            break
    print("Creating database....")
    try:
        mkdb(name, password)

    except sqlite3.Error as e:
        print("Error creating database: \n" + str(e))
        input("Press enter to continue")
        prompt_db()
    print("Successfully created new database")
    input("Press enter to continue")


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
        return cursor
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

            menu_items[index][1](menu_items[index][2])
            return


if __name__ == "__main__":
    while True:
        wrapper(main)
