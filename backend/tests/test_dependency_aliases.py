from typing import Annotated, get_args, get_origin

from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUserDep, OrganizerUserDep, ParticipantUserDep
from app.db.session import SessionDep, get_db_session


def test_session_dependency_alias_uses_database_session_provider() -> None:
    assert get_origin(SessionDep) is Annotated
    session_type, dependency = get_args(SessionDep)

    assert session_type is AsyncSession
    assert isinstance(dependency, Depends)
    assert dependency.dependency is get_db_session


def test_authenticated_user_dependency_aliases_are_available() -> None:
    assert get_origin(CurrentUserDep) is Annotated
    assert get_origin(OrganizerUserDep) is Annotated
    assert get_origin(ParticipantUserDep) is Annotated
