"""
Simple local user authentication for the Pokémon PC Box simulator.
Users are stored in data/users.json; each user's save is in data/saves/<username>.json
"""
import json
import os
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_PATH = os.path.join(BASE_DIR, "data", "users.json")
SAVES_DIR = os.path.join(BASE_DIR, "data", "saves")


def _hash_password(password: str) -> str:
    """Return SHA-256 hash of password (with a simple salt for slightly better security)."""
    salt = "pokemon_pc_box"
    return hashlib.sha256((salt + password).encode()).hexdigest()


def _load_users() -> dict:
    """Load user map { username -> hashed_password }."""
    if not os.path.exists(USERS_PATH):
        return {}
    try:
        with open(USERS_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(users: dict) -> bool:
    """Persist user map. Returns True on success."""
    os.makedirs(os.path.dirname(USERS_PATH), exist_ok=True)
    try:
        with open(USERS_PATH, "w") as f:
            json.dump(users, f, indent=2)
        return True
    except OSError:
        return False


def register_user(username: str, password: str) -> tuple[bool, str]:
    """
    Register a new user. Returns (success, message).
    Username is case-insensitive for lookup but stored as given.
    """
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if not password:
        return False, "Password cannot be empty."
    if len(username) < 2:
        return False, "Username must be at least 2 characters."

    users = _load_users()
    key = username.lower()
    if key in {k.lower(): k for k in users}:
        return False, "That username is already taken."

    users[username] = _hash_password(password)
    if not _save_users(users):
        return False, "Failed to save user data."
    os.makedirs(SAVES_DIR, exist_ok=True)
    return True, "Account created! You can log in now."


def verify_user(username: str, password: str) -> tuple[bool, str]:
    """
    Verify username and password. Returns (success, message).
    On success, message is the actual stored username (for display/save path).
    """
    username = username.strip()
    if not username or not password:
        return False, "Please enter username and password."

    users = _load_users()
    key_lower = username.lower()
    for stored_name, hashed in users.items():
        if stored_name.lower() == key_lower:
            if hashed == _hash_password(password):
                return True, stored_name
            return False, "Incorrect password."
    return False, "No account found with that username."


def get_save_path_for_user(username: str) -> str:
    """Return the path to the save file for this user."""
    os.makedirs(SAVES_DIR, exist_ok=True)
    # Sanitize filename: only allow alphanumeric and underscore
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in username)
    if not safe:
        safe = "user"
    return os.path.join(SAVES_DIR, f"{safe}.json")
