#!/usr/bin/env python3
"""
Automatically initializes a fresh Metabase instance via its REST API.
This script is designed to run in a Docker Compose environment alongside Metabase.
"""

import urllib.request
import urllib.error
import json
import time
import os
import sys

METABASE_URL = os.environ.get("METABASE_URL", "http://metabase:3000")
ADMIN_EMAIL = os.environ.get("MB_ADMIN_EMAIL", "admin@ghostwriter.local")
ADMIN_PASSWORD = os.environ.get("MB_ADMIN_PASSWORD", "Ghostwriter123!")

DB_HOST = os.environ.get("POSTGRES_HOST", "postgres")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "ghostwriter")
DB_USER = os.environ.get("POSTGRES_USER", "ghostwriter")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "ghostwriter")

def get_setup_token():
    """Polls Metabase until it is up and a setup token is available."""
    print(f"Waiting for Metabase at {METABASE_URL} to become ready...")
    for _ in range(60):
        try:
            req = urllib.request.Request(f"{METABASE_URL}/api/session/properties")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get("has-user-setup") is True:
                        print("Metabase is already set up.")
                        return None
                    token = data.get("setup-token")
                    if token:
                        print("Obtained setup token.")
                        return token
        except urllib.error.URLError:
            pass
        except Exception as e:
            print(f"Error checking session properties: {e}")
        time.sleep(2)
    print("Failed to get setup token after 120 seconds.")
    sys.exit(1)

def setup_metabase(token):
    """Sends the setup POST request to initialize Metabase without the DB connection."""
    setup_payload = {
        "token": token,
        "user": {
            "first_name": "Ghostwriter",
            "last_name": "Admin",
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "site_name": "Beacon Ghostwriter Explorer"
        },
        "prefs": {
            "site_name": "Beacon Ghostwriter Explorer",
            "site_locale": "en",
            "allow_tracking": False
        }
    }

    data = json.dumps(setup_payload).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(f"{METABASE_URL}/api/setup", data=data, headers=headers, method='POST')

    print("Sending initial setup configuration to Metabase...")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                print("Successfully created Metabase admin account!")
                print(f"Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
            else:
                print(f"Setup returned status: {response.status}")
                print(response.read().decode('utf-8'))
                sys.exit(1)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("Setup already completed (403 Forbidden). Moving to DB check.")
        else:
            print(f"HTTP error during setup: {e.code} - {e.reason}")
            print(e.read().decode('utf-8'))
            sys.exit(1)
    except Exception as e:
        print(f"Error during setup: {e}")
        sys.exit(1)

def setup_database():
    """Authenticates and sets up the Postgres database connection separately."""
    login_payload = {
        "username": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }

    # 1. Get session token
    print("Authenticating to Metabase API...")
    try:
        data = json.dumps(login_payload).encode('utf-8')
        req = urllib.request.Request(f"{METABASE_URL}/api/session", data=data, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            session_data = json.loads(response.read().decode('utf-8'))
            session_id = session_data.get("id")
    except Exception as e:
        print(f"Failed to authenticate: {e}")
        sys.exit(1)

    headers = {
        'Content-Type': 'application/json',
        'X-Metabase-Session': session_id
    }

    # 2. Check existing databases
    print("Checking existing database connections...")
    try:
        req = urllib.request.Request(f"{METABASE_URL}/api/database", headers=headers, method='GET')
        with urllib.request.urlopen(req, timeout=10) as response:
            dbs = json.loads(response.read().decode('utf-8'))
            db_data = dbs.get("data", dbs) if isinstance(dbs, dict) else dbs
            for db in db_data:
                if db.get("name") == "Ghostwriter Beacon DB":
                    print("Database 'Ghostwriter Beacon DB' already exists. Setup complete.")
                    return
    except Exception as e:
        print(f"Failed to list databases: {e}")
        sys.exit(1)

    # 3. Create database
    db_payload = {
        "name": "Ghostwriter Beacon DB",
        "engine": "postgres",
        "details": {
            "host": DB_HOST,
            "port": int(DB_PORT),
            "dbname": DB_NAME,
            "user": DB_USER,
            "password": DB_PASS,
            "ssl": False
        },
        "is_full_sync": True,
        "is_on_demand": False,
        "schedules": {}
    }

    print("Adding PostgreSQL database connection...")
    try:
        data = json.dumps(db_payload).encode('utf-8')
        req = urllib.request.Request(f"{METABASE_URL}/api/database", data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print("Successfully added the Ghostwriter Postgres database!")
            else:
                print(f"Failed to add database. Status: {response.status}")
                sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"HTTP error creating database: {e.code} - {e.reason}")
        print(e.read().decode('utf-8'))
        sys.exit(1)
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    token = get_setup_token()
    if token:
        setup_metabase(token)

    # Always try to setup/verify the database connection, even if already set up
    time.sleep(2)
    setup_database()
