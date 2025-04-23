from jwst import decode, ExpiredSignatureError, InvalidTokenError
from flask import jsonify

SECRET_KEY = "your-secret-key"

def verify_token(token):
    try:
        payload = decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload  # Token is valid
    except ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 403