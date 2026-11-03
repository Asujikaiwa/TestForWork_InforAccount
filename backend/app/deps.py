"""Request dependencies: who is calling, and which group they may access."""

from typing import Annotated

from fastapi import Depends, Header, Path
from sqlalchemy.orm import Session

from app import repository as repo
from app.db import get_session
from app.errors import GroupNotFound, InvalidRequest, MissingUser, UnknownUser
from app.models import Group, User

SessionDep = Annotated[Session, Depends(get_session)]


def current_user(
    session: SessionDep,
    x_user: Annotated[str | None, Header(alias="X-User")] = None,
) -> User:
    """Identify the caller from X-User (authentication is out of scope)."""
    if x_user is None or not x_user.strip():
        raise MissingUser("The X-User header is required.")
    user = repo.get_user(session, x_user.strip())
    if user is None:
        raise UnknownUser(f"Unknown user {x_user.strip()!r}.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def member_group(
    session: SessionDep,
    user: CurrentUser,
    group_id: Annotated[int, Path()],
) -> Group:
    """The group in the path, if the caller is a member.

    Non-members get the same 404 as a group that does not exist, so the API
    does not reveal which group ids exist (see README).
    """
    group = repo.get_group_for_member(session, group_id, user.id)
    if group is None:
        raise GroupNotFound("Group not found.")
    return group


MemberGroup = Annotated[Group, Depends(member_group)]


def idempotency_key(
    key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str | None:
    if key is None:
        return None
    key = key.strip()
    if not 1 <= len(key) <= 255:
        raise InvalidRequest("Idempotency-Key must be 1 to 255 characters.")
    return key
