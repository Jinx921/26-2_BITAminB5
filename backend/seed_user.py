import argparse
import getpass
import sqlite3

from pydantic import EmailStr, TypeAdapter, ValidationError

from backend.app.auth import password_hash
from backend.app.database import Database
from backend.app.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a local development administrator or field-worker account."
    )
    parser.add_argument(
        "--role", choices=("admin", "field_worker"), required=True
    )
    args = parser.parse_args()

    settings = Settings.from_environment()
    if settings.environment != "development":
        parser.error("Privileged account seeding is available only in development.")

    email = input("Account email: ").strip()
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    except ValidationError:
        parser.error("Enter a valid email address.")
    password = getpass.getpass("Password (at least 12 characters): ")
    if len(password) < 12 or len(password) > 128:
        parser.error("Password must be between 12 and 128 characters.")

    database = Database(settings.database_path)
    database.initialize()
    try:
        user = database.create_user(
            email, password_hash.hash(password), role=args.role
        )
    except sqlite3.IntegrityError:
        parser.error("Unable to create privileged account.")
    print(f"Created {user['role']} account with id {user['id']}.")


if __name__ == "__main__":
    main()
