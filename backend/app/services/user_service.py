from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import SessionRepository, UserRepository
from app.schemas.auth import RegisterRequest, UserCreate, UserRead, UserUpdate
from app.services.unit_of_work import UnitOfWork


class UserService:
    def __init__(self, db):
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)
        self.uow = UnitOfWork(db)

    def list(self) -> list[UserRead]:
        return [UserRead.model_validate(user) for user in self.users.list()]

    def register(self, payload: RegisterRequest) -> UserRead:
        return self.create(UserCreate(
            username=payload.username,
            password=payload.password,
            role="business",
        ))

    def create(self, payload: UserCreate) -> UserRead:
        user = User(
            username=payload.username.strip(),
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        try:
            self.users.add(user)
            self.uow.commit()
        except IntegrityError as exc:
            self.uow.rollback()
            raise ConflictError("username_exists", "账号已存在") from exc
        return UserRead.model_validate(user)

    def update(self, user_id: str, payload: UserUpdate, actor_id: str) -> UserRead:
        user = self._get(user_id)
        values = payload.model_dump(exclude_unset=True)
        if user.id == actor_id and values.get("is_active") is False:
            raise AppError("cannot_disable_self", "不能停用当前账号")
        if user.id == actor_id and values.get("role") not in (None, "admin"):
            raise AppError("cannot_demote_self", "不能降低当前账号权限")
        for key, value in values.items():
            setattr(user, key, value)
        self.users.save(user)
        if values.get("is_active") is False:
            self.sessions.delete_for_user(user.id)
        self.uow.commit()
        return UserRead.model_validate(user)

    def reset_password(self, user_id: str, password: str) -> None:
        user = self._get(user_id)
        user.password_hash = hash_password(password)
        self.users.save(user)
        self.sessions.delete_for_user(user.id)
        self.uow.commit()

    def _get(self, user_id: str) -> User:
        user = self.users.get(user_id)
        if not user:
            raise NotFoundError("user_not_found", "用户不存在")
        return user
