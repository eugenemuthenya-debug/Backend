from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
# limiter->creates rate limiting system
from flask_limiter.util import get_remote_address
# get_remote_address->determines which client is making request using their IP address.
# our authentication
from flask_jwt_extended import JWTManager

bcrypt = Bcrypt()

limiter = Limiter(
    key_func=get_remote_address
)

jwt = JWTManager()