from sqlalchemy.exc import IntegrityError


def integrity_constraint_name(error: IntegrityError) -> str | None:
    """Extract a database constraint name from common driver error shapes."""
    candidates = (
        error.orig,
        getattr(error.orig, "__cause__", None),
        getattr(error.orig, "__context__", None),
        getattr(error.orig, "diag", None),
    )
    for candidate in candidates:
        constraint_name = getattr(candidate, "constraint_name", None)
        if constraint_name:
            return str(constraint_name)
    return None
