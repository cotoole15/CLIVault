#!/usr/bin/env python3
import getpass  # For capturing password input.
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import sys
import sqlite3
import curses
from curses import wrapper


def validate_pass(password, retyped_password):
    return password == retyped_password


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
def setup_db():
    input(
        "On the next screen, you will be asked to select the name and location for your new database.\nPlease press enter to continue."
    )
    name = input("Enter a name for your new database:")
    while True:
        password = getpass.getpass("Enter the password for your new database.")
        retyped_password = getpass.getpass("Please enter the same password again:")

        if not (validate_pass(password, retyped_password)):
            print("Passwords don't match, try again.")
        else:
            input("Password set. Press enter.")
            print("Creating database....")
            mkdb(name, password)

            break


def mkdb(name, password):
    salt = os.urandom(16)
    key = generate_key(password, salt)
    # Create fernet object
    fernet = Fernet(key)

    # encrypt the word true, to see if the database has been unlocked
    decrypted = fernet.encrypt("true")
    conn = sqlite3.connect(name)
    cursor = conn.cursor()
    # Create metadata
    cursor.execute(
        """ Create TABLE metadata (
        salt BLOB,
        decrypted TEXT DEFAULT ? 
    );
    """,
        (decrypted,),
    )
    cursor.execute("INSERT INTO metadata (salt) VALUES (?)", (salt,))
    cursor.execute("""CREATE TABLE passwords(
        name TEXT,
        email TEXT,
        username TEXT,
        password BLOB,
        url text
        );
    """)
    try:
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating database: {e}")

    print("Successfully created database")
    conn.close()


def open_db():
    print("executed")


def main(stdscr):
    menu_items = [
        ("Create new database", setup_db),
        ("Open an existing database", open_db),
        ("quit", sys.exit),
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

            # curses.endwin()
            menu_items[index][1]()
            break


if __name__ == "__main__":
    while True:
        wrapper(main)
