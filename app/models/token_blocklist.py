"""
Token blocklist model.

Stores revoked JWT token identifiers (jti claims).
When a user logs out, their token's jti is added here so it cannot be reused
even before it expires — preventing session hijacking with stolen tokens.

Entries expire naturally alongside the JWT they track; a startup cleanup task
removes rows whose expires_at timestamp has passed to keep the table small.
"""

from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.sql import func

from app.database import Base


class TokenBlocklist(Base):
    """
    Tracks revoked JWT tokens by their unique jti claim.

    A token whose jti appears here is rejected even if the signature is valid
    and the expiry time has not yet passed.
    """

    __tablename__ = "token_blocklist"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # UUID string from the JWT's "jti" claim — guaranteed unique per token
    jti = Column(String(36), unique=True, nullable=False, index=True)

    # When the original JWT expires — used for cleanup
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # When the revocation was recorded
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_token_blocklist_expires", "expires_at"),
        {"extend_existing": True},
    )
