"""
Rate limiter configuration.

Prevents users from flooding the server with too many requests.
For example, limits login attempts to stop brute-force password guessing.
This file lives separately so both the main app and individual routes
can use the same limiter without causing import errors.
"""

# SlowAPI is a library that counts requests and blocks users who send too many
from slowapi import Limiter
# This helper figures out who is making the request by their IP address
from slowapi.util import get_remote_address


# Create one shared rate limiter that identifies users by their IP address
# All API routes can use this same instance to enforce request limits
limiter = Limiter(key_func=get_remote_address)
