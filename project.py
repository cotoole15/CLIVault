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
def prompt_db():
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

            print("e")
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
        salt BLOB,
        is_unlocked TEXT  
    );
    """)
    cursor.execute("INSERT INTO metadata (salt) VALUES (?)", (salt,))
    cursor.execute("INSERT INTO metadata (is_unlocked) VALUES (?)", (s,))

    cursor.execute("""create TABLE passwords(
        name TEXT,
        email TEXT,
        username TEXT,
        password BLOB,
        url TEXT
    );""")
    conn.commit()
    conn.close()


def open_db():
    print("executed")


def main(stdscr):
    menu_items = [
        ("Create new database", prompt_db),
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

            menu_items[index][1]()
            return


if __name__ == "__main__":
    while True:
        wrapper(main)
