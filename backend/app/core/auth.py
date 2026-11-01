from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


@dataclass(frozen=True)
class Principal:
    subject: str
    business_lines: tuple[str, ...]

    def can_access(self, business_line: str) -> bool:
        return business_line in self.business_lines


DEMO_TOKENS: dict[str, Principal] = {
    "analyst-autos": Principal("analyst-autos", ("autos",)),
    "analyst-hogar": Principal("analyst-hogar", ("hogar",)),
    "analyst-all": Principal("analyst-all", ("autos", "hogar", "vida")),
}

_bearer = HTTPBearer(auto_error=False)


def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    principal = DEMO_TOKENS.get(credentials.credentials) if credentials else None
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def resolve_business_lines(principal: Principal, requested: str | None) -> tuple[str, ...]:
    if requested is None:
        return principal.business_lines
    if not principal.can_access(requested):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No access to business line '{requested}'",
        )
    return (requested,)
