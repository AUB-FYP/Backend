from config.marshmallow import ma
from config.bcrypt import bcrypt
from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "user"
    __table_args__ = {"schema": "FYP"}
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(30), unique=True)
    funds = db.Column(db.Float, default=0)
    hashed_password = db.Column(db.String(128))
    stocks = db.relationship("UserStock", backref="user", cascade="all, delete-orphan")

    def __init__(self, user_name, password, funds=0.0, stocks=None):
        super(User, self).__init__(user_name=user_name)
        self.hashed_password = bcrypt.generate_password_hash(password)
        self.funds = funds


class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_name", "funds", "stocks")
        model = User


class UserStock(db.Model):
    __tablename__ = "user_stock"
    __table_args__ = {"schema": "FYP"}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("FYP.user.id", ondelete="CASCADE"))
    stock = db.Column(db.String(50))

    def __init__(self, user_id, stock):
        self.user_id = user_id
        self.stock = stock


user_schema = UserSchema()
