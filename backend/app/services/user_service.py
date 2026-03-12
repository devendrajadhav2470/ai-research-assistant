from app.models.user import User
from app.extensions import db
import bcrypt 
import uuid 
import jwt
import logging 
from datetime import datetime,timezone,timedelta
logger = logging.getLogger(__name__)
class UserService():
    
    def create_user(self,email: str,password: str, guest_user_session_id: str=None): 
        user = User(
            id = uuid.uuid4(),
            email=email,
            password_hash=bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt()).decode("utf-8"),
            guest_user_session_id=guest_user_session_id
        )
        try:
            db.session.add(user)
        except Exception as e:
            logger.info(f"there was an error creating the user {email}: {e}")
        db.session.commit()
    
    def get_user_from_id(self, user_id: str):
        user = db.session.get(User,user_id=user_id)
        if not user:
            logger.info(f"no user found for user_id={user_id}")
        return user
    
    def get_user_from_email(self, email: str):
        query = User.query.filter_by(email=email)
        users  = query.all()
        if not len(users):
            logger.info(f"no user found for email={email}")
        return users[0]

    def get_guest_user(self, guest_user_session_id: str):
        # optionally validate the session_id to check if its uuid 
        # guest_user email = guest_user_{session_id}@temporary.com
        # guest_user_id = generate new one 
        # guest user password = password
        query = User.query.filter_by(guest_user_session_id = guest_user_session_id)
        users = query.all()

        if len(users):
            return users[0]

        logger.info(f"guest user not found, creating new user")
        guest_user_email = f"guest_user_{guest_user_session_id}@temporary.com"
        guest_user_password = "password"
        self.create_user(
            email=guest_user_email,
            password=guest_user_password,
            guest_user_session_id=guest_user_session_id
        )

        query = User.query.filter_by(guest_user_session_id = guest_user_session_id)
        users = query.all()
        return users[0]
            # return {
            #     "email":,
            #     "id": 
            #     "exp":
            # }

    def create_token(self,payload):
        # TO DO: replace with env variable
        secret_key = "temporary_secret_key"
        payload['exp'] = datetime.now(timezone.utc) + timedelta(hours= 1)
        return jwt.encode(payload, secret_key,algorithm="HS256")
    def decode_token(self,token):
        # TO DO: r
        # eplace with env variable
        secret_key = "temporary_secret_key"
        try:
            return jwt.decode(token,secret_key,algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            logger.error(f"Token has expired")
            return "Token has expired"
        except jwt.InvalidTokenError:
            logger.error(f"Token is Invalid")
            return "Token is Invalied"
        except Exception as e:
            logger.error(f"{e}")
            return "Unknown Exection while decoding token"
    def verify_user_pwd(self, password: str,user_id: str=None,email: str=None):
        if not user_id and not email:
            logger.info(f"user id or email are required to verify the password")
            return 
        
        user = None

        if(user_id):
            user = self.get_user_from_id(user_id = user_id)
        else:
            user = self.get_user_from_email(email = email)
        
        if not user:
            logger.info(f"no user found")
            return

        if bcrypt.checkpw(password.encode("utf-8"),user.password_hash.encode("utf-8")):
            logger.info(f"password verified")
            return user.id
        return



