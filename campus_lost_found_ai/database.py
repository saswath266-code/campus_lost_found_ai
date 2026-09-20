import os
import re

import mysql.connector
from mysql.connector import Error

from dotenv import load_dotenv


# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------
# MYSQL CONFIGURATION
# ---------------------------------------------------------

MYSQL_HOST = os.getenv(
    "MYSQL_HOST",
    "localhost"
)

MYSQL_PORT = int(
    os.getenv(
        "MYSQL_PORT",
        "3306"
    )
)

MYSQL_DATABASE = os.getenv(
    "MYSQL_DATABASE",
    "campus_lost_found"
)

MYSQL_USER = os.getenv(
    "MYSQL_USER",
    "root"
)

MYSQL_PASSWORD = os.getenv(
    "MYSQL_PASSWORD",
    ""
)


# ---------------------------------------------------------
# VALIDATE DATABASE NAME
# ---------------------------------------------------------

if not re.match(
    r"^[A-Za-z0-9_]+$",
    MYSQL_DATABASE
):

    raise ValueError(
        "Invalid MYSQL_DATABASE name."
    )


# ---------------------------------------------------------
# CONNECT TO MYSQL SERVER
# ---------------------------------------------------------

def connect_server():

    return mysql.connector.connect(

        host=MYSQL_HOST,

        port=MYSQL_PORT,

        user=MYSQL_USER,

        password=MYSQL_PASSWORD
    )


# ---------------------------------------------------------
# CONNECT TO APPLICATION DATABASE
# ---------------------------------------------------------

def connect():

    return mysql.connector.connect(

        host=MYSQL_HOST,

        port=MYSQL_PORT,

        user=MYSQL_USER,

        password=MYSQL_PASSWORD,

        database=MYSQL_DATABASE
    )


# ---------------------------------------------------------
# INITIALIZE DATABASE
# ---------------------------------------------------------

def init_db():

    server_connection = None
    connection = None

    try:

        # ---------------------------------------------
        # Create database if it doesn't exist
        # ---------------------------------------------

        server_connection = connect_server()

        cursor = server_connection.cursor()

        cursor.execute(
            f"""
            CREATE DATABASE IF NOT EXISTS
            `{MYSQL_DATABASE}`
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
            """
        )

        server_connection.commit()

        cursor.close()
        server_connection.close()


        # ---------------------------------------------
        # Connect to application database
        # ---------------------------------------------

        connection = connect()

        cursor = connection.cursor()


        # ---------------------------------------------
        # Create items table
        # ---------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS items (

                id INT AUTO_INCREMENT PRIMARY KEY,

                type VARCHAR(20) NOT NULL,

                name VARCHAR(255) NOT NULL,

                category VARCHAR(100),

                description TEXT,

                location VARCHAR(255),

                event_time VARCHAR(100),

                image VARCHAR(500),

                status VARCHAR(50)
                    DEFAULT 'searching',

                created_at DATETIME

            )
            """
        )


        connection.commit()

        cursor.close()

        connection.close()


        print(
            "MySQL database initialized successfully."
        )


    except Error as error:

        print(
            "MySQL initialization error:",
            error
        )

        raise


    finally:

        if server_connection:

            try:
                server_connection.close()
            except Exception:
                pass

        if connection:

            try:
                connection.close()
            except Exception:
                pass


# ---------------------------------------------------------
# ADD ITEM
# ---------------------------------------------------------

def add_item(
    item_type,
    name,
    category,
    description,
    location,
    event_time,
    image
):

    connection = None
    cursor = None

    try:

        connection = connect()

        cursor = connection.cursor()


        cursor.execute(
            """
            INSERT INTO items
            (
                type,
                name,
                category,
                description,
                location,
                event_time,
                image,
                created_at
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW()
            )
            """,

            (
                item_type,
                name,
                category,
                description,
                location,
                event_time,
                image
            )
        )


        connection.commit()


        return cursor.lastrowid


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ---------------------------------------------------------
# GET ITEMS
# ---------------------------------------------------------

def get_items(item_type=None):

    connection = None
    cursor = None

    try:

        connection = connect()

        cursor = connection.cursor(
            dictionary=True
        )


        if item_type:

            cursor.execute(
                """
                SELECT *
                FROM items
                WHERE type = %s
                ORDER BY id DESC
                """,

                (item_type,)
            )

        else:

            cursor.execute(
                """
                SELECT *
                FROM items
                ORDER BY id DESC
                """
            )


        return cursor.fetchall()


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ---------------------------------------------------------
# GET SINGLE ITEM
# ---------------------------------------------------------

def get_item(item_id):

    connection = None
    cursor = None

    try:

        connection = connect()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(
            """
            SELECT *
            FROM items
            WHERE id = %s
            """,

            (item_id,)
        )


        return cursor.fetchone()


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ---------------------------------------------------------
# UPDATE STATUS
# ---------------------------------------------------------

def update_status(
    item_id,
    status
):

    connection = None
    cursor = None

    try:

        connection = connect()

        cursor = connection.cursor()


        cursor.execute(
            """
            UPDATE items

            SET status = %s

            WHERE id = %s
            """,

            (
                status,
                item_id
            )
        )


        connection.commit()


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()