import os
import pytest
from project import *


def test_mkdb():
    try:
        mkdb("hello.db", "1234")

        assert os.path.exists("hello.db")
    finally:
        os.remove("hello.db")


def test_open_db():
    try:
        mkdb("hello.db", "1234")

        conn, cursor, key = open_db("hello.db", "1234")

        assert isinstance(conn, sqlite3.Connection)
        assert isinstance(cursor, sqlite3.Cursor)
        assert len(key) == 44
        decoded_key = base64.b64decode(key)
        assert len(decoded_key) == 32
    finally:
        cursor.close()

        conn.close()
        os.remove("hello.db")


def test_generate_key():
    with pytest.raises(ValueError):
        generate_key(None, None)
    salt = os.urandom(16)
    key = generate_key("password", salt)
    assert len(key) == 44
    decoded_key = base64.b64decode(key)
    assert len(decoded_key) == 32


def test_encrypt():
    password = "1234"
    salt = os.urandom(16)
    key = generate_key(password, salt)
    s = encrypt(key, "Hello world!")
    assert s != "Hello world!"


def test_decrypt():
    password = "1234"
    salt = os.urandom(16)
    key = generate_key(password, salt)
    s = encrypt(key, "Hello world!")
    decrypted_s = decrypt(key, s.encode())
    assert decrypted_s == "Hello world!"
