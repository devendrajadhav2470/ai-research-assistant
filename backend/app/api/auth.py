from flask import Blueprint, g
import logging
from flask import request
from flask import jsonify 
from email_validator import validate_email,EmailNotValidError
from app.services.user_service import UserService
from functools import wraps

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)

def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')
        guest_user_session_id = request.headers.get('GuestUserSessionId')
        # optionally validate the session id to check if its a valid session id or not
        logger.info(f"guest_user_session_id: {guest_user_session_id}")
        if not token and not guest_user_session_id:
            logger.info(f"no session id and no token")
            return jsonify({"error": "Authentication token or Session Id is required"}), 401

        user_service = UserService()

        if guest_user_session_id:
            guest_user = user_service.get_guest_user(guest_user_session_id)
            g.user = {
                "email": guest_user.email,
                "exp": "temporary",
                "id": guest_user.id
            }
            return f(*args,**kwargs)
    
        try:
            payload = user_service.decode_token(token=token)
            if isinstance(payload,str):
                return jsonify({"error": payload}), 401
            
            g.user = payload
        except:
            return jsonify({"error": "Invalid token"}), 401
        
        return f(*args,**kwargs)
    return decorator

@auth_bp.route("/signup",methods=['POST'])
def register_user():
    data= request.get_json()

    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and Password are required for registering"}), 401

    # email validation 
    email = data.get("email").strip()
    if not email:
        return jsonify({"error": "Email cannot be empty"}), 401
    
    try:
        valid = validate_email(email)
        normalized_email = valid.email
        logger.info(f"Email validated and normalized: {normalized_email}")
    except EmailNotValidError as e:
        logger.info(f"Email validation failure: {e}")
        return jsonify({"error": "Email validation failed"}), 401

    # password validation
    # for now it can be any string of 6 letters
    password = data.get("password")
    if len(password)!=6:
        return jsonify({"error": "password length is not equal to 6 chars"}), 401
    
    user_service = UserService()
    user_service.create_user(email=normalized_email,password=password)
    return jsonify({"message": f"user created {email}"})

@auth_bp.route("/signin",methods=['POST'])
def login_user():
    data= request.get_json()
    if not data:
        logger.info(f"no request body")
        return jsonify({"error": "you must provide email and password for logging in"}), 401
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "you must provide email and password for logging in"}), 401

    user_service = UserService()
    user_id = user_service.verify_user_pwd(password = password,email=email);
    if user_id:
        # create jwt tokens 
        token = user_service.create_token(payload = {
            "email": email,
            "id": user_id
        })
        return jsonify({"token": token})
    
    return jsonify({"error": "user verification failed"}), 401

        


    







