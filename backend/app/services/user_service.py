from app.models.user import User
from app.extensions import db
import bcrypt 
import uuid 
import jwt
import logging 
from datetime import datetime,timezone,timedelta
logger = logging.getLogger(__name__)
class UserService():
    
    def create_user(self,email: str,password: str): 
        user = User(
            id = uuid.uuid4().hex[:10],
            email=email,
            password_hash=bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt())
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
        [user]  = query.all()
        if not user:
            logger.info(f"no user found for email={email}")
        return user

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

        if bcrypt.checkpw(password.encode("utf-8"),user.password_hash):
            logger.info(f"password verified")
            return True
        return False



