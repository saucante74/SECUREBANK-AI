import argparse
from getpass import getpass

from app.core.config import settings
from app.core.passwords import PasswordHasher, PasswordPolicyError
from app.core.rbac import Role
from app.services.users import (
    SQLiteUserRepository,
    UserAlreadyExistsError,
    create_user_account,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local SecureBank user")
    parser.add_argument("username")
    parser.add_argument("--role", choices=[role.value for role in Role], required=True)
    parser.add_argument("--disabled", action="store_true")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")

    repository = SQLiteUserRepository(settings.user_database_path)
    repository.initialize()
    try:
        account = create_user_account(
            repository,
            PasswordHasher(),
            arguments.username,
            password,
            Role(arguments.role),
            not arguments.disabled,
        )
    except (PasswordPolicyError, UserAlreadyExistsError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"User created: {account.username} ({account.role.value})")


if __name__ == "__main__":
    main()
