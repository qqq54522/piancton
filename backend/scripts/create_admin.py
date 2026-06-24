import argparse

from app.core.errors import AppError
from app.db.session import SessionLocal
from app.schemas.auth import UserCreate
from app.services.user_service import UserService


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the initial Piancton administrator")
    parser.add_argument("username")
    parser.add_argument("password")
    args = parser.parse_args()
    with SessionLocal() as db:
        try:
            user = UserService(db).create(
                UserCreate(username=args.username, password=args.password, role="admin")
            )
        except AppError as exc:
            raise SystemExit(exc.message) from exc
    print(f"Created administrator: {user.username}")


if __name__ == "__main__":
    main()
