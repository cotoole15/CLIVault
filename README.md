# CliVault a simple password manager
## Video link https://www.dropbox.com/scl/fi/75wnba3x9bimcz6m92kwv/cs50p-project.mp4?rlkey=rnmll76fymmuwt1b2m2sjvzbn&dl=0
## Warning
This project was made to enhance my skills with respect to encryption, database management and other topics. It should not be used in a production environment. 
## Description 
A simple secure password manager with the ability to create, modify and delete entries, using secure encryption from python's fernet module.

## Introduction
Cli Vault is a simple password manager with the ability to manage credentials and store them securely in a database. It supports entry creation, deletion and copying of usernames and passwords. It prompts the user to save or discard their changes on exit, protecting the database from accidental modification.

## Technical details
### Database
The project uses SQLite for data storage. Databases are stored as .db files and are accessed using the python sqlite3 module. Tables are generated automatically by the database creation (mkdb) function.
### Encryption
Encryption and decryption are handled by Fernet, from the cryptography module. This module provides symmetric encryption using AES128 in CBC mode.  It uses HMAC-SHA256 to ensure integrity of the encrypted data.
The generate_key function handles creation of new keys.
Keys are derived using a password and a salt. Keys are treated as two halves internally. The first 16 bytes correspond to the encryption key itself, while the other 16 bytes contain the HMAC signing key which ensures that data has not been tampered with. They are stored in base64 format, so they can be safely represented as a string, but they are converted back into bytes for actual use. The program includes custom encrypt and decrypt functions that convert strings and interface with Fernet to perform encryption and decryption.


## How it works

### Database creation
The user enters a name and password  for their new database. This password must be retyped to prevent mistakes. If passwords match the mkdb function is called. This generates a new key, encrypts the word true for unlock validation and stores the salt in the database. The passwords table is then created (See the next section for details on this).
### Database unlocking
When a user enters their password, the open_db function attempts to decrypt the is_unlocked value in the database. If the unlocked value is true, entries are loaded, otherwise  a handled value error is returned and users are re-prompted for their password.

### Retrieval of password entries
Each password row contains five attributes: name, e-mail, username, password and a URL. When the database is unlocked the build_entries function loops over the rows and creates an instance of the entry class for each of the user’s credentials. The user is then shown a menu with their added credentials and options to add a new entry or quit and lock the database. When a user presses enter on an entry they are presented with   the ability to copy their username and password, or edit the entry. The edit entry menu contains options to modify the entry’s attributes such as username, password, email, etc. If a user sets these attributes and presses save changes the list of entries is modified in memory. The user is then prompted to save or discard changes to the database on exit.


### Storage of entries
When a user chooses to save their changes, the passwords table is wiped and replaced with the entries from memory. This approach is functional but not efficient (see the limitations section for details). The user is then returned to the main menu.

### Clipboard functionality
Pyperclip is used to handle the copying of usernames and passwords.
## Limitations
### Entry storage
When entries are saved back to disk the entire passwords table is wiped and replaced with a copy from memory. This is inefficient as the entire database is rewritten when an entry is changed. This could result in large performance penalties as the database grows. It could also result in data loss, if the user’s machine crashes mid write.

### No search or filtering features
The current implementation does not allow a user to group passwords into categories, add tags or search for an entry.  This could be challenging for a user with hundreds of credentials.

### No GUI
The interface is a command line environment; requiring the use of a keyboard instead of a mouse to operate. This may be difficult for users who prefer to point and click. Typing confirmations such as y or n may feel clunky for some users.
### No autosave
A user must save on exit. Until then their changes will remain in memory. This could result in data loss if the application crashes unexpectedly.

### No clipboard timeout
The clipboard is not automatically cleared which could allow an attacker to access a user’s password. This could also result in the user accidentally pasting confidential information.
### No database auto-lock
The user must manually lock the database. If a user left their computer unattended and forgot to lock the screen an attacker might be able to capture their password via local or remote access.

## References

https://cryptography.io/en/latest/fernet/

