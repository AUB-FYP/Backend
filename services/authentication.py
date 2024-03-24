import jwt
import datetime
import os


def create_token(user_id):

    payload = {
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=4),
        "iat": datetime.datetime.utcnow(),
        "sub": user_id,
    }

    return jwt.encode(payload, os.environ.get("SECRET_KEY"), algorithm="HS256")


def extract_auth_token(authenticated_request):
    auth_header = authenticated_request.headers.get("Authorization")
    if auth_header:
        return auth_header.split(" ")[1]
    else:
        return None


def decode_token(token):
    payload = jwt.decode(token, os.environ.get("SECRET_KEY"), "HS256")
    return payload["sub"]
