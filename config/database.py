from config.marshmallow import ma
from config.bcrypt import bcrypt
from flask_sqlalchemy import SQLAlchemy
from marshmallow_sqlalchemy.fields import Nested

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


class UserStock(db.Model):
    __tablename__ = "user_stock"
    __table_args__ = {"schema": "FYP"}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("FYP.user.id", ondelete="CASCADE"))
    stock = db.Column(db.String(50))
    shares = db.Column(db.Integer, default=0)

    def __init__(self, user_id, stock, shares):
        self.user_id = user_id
        self.stock = stock
        self.shares = shares


class UserStockSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_id", "stock", "shares")
        model = UserStock


class UserSchema(ma.Schema):
    stocks = Nested(UserStockSchema, many=True)

    class Meta:
        fields = ("id", "user_name", "funds", "stocks")
        model = User


user_stock_schema = UserStockSchema()
user_schema = UserSchema()


class Stock(db.Model):
    __tablename__ = "stock"
    __table_args__ = {"schema": "FYP"}

    ticker = db.Column(db.String(50), primary_key=True)
    date = db.Column(db.DateTime, primary_key=True)
    stock_price = db.Column(db.Float)
    low = db.Column(db.Float)
    high = db.Column(db.Float)
    open = db.Column(db.Float)
    close = db.Column(db.Float)
    volume = db.Column(db.Integer)
    adjcp = db.Column(db.Float)
    sentiment = db.Column(db.Float)

    def __init__(
        self,
        ticker,
        date,
        stock_price,
        sentiment,
        low,
        high,
        open,
        close,
        volume,
        adjcp,
    ):
        self.ticker = ticker
        self.date = date
        self.stock_price = stock_price
        self.sentiment = sentiment
        self.low = low
        self.high = high
        self.open = open
        self.close = close
        self.volume = volume
        self.adjcp = adjcp

    def __repr__(self):
        representation = f"Ticker: {self.ticker}, Date: {self.date}, Stock Price: {self.stock_price}, Sentiment: {self.sentiment}"
        return representation


class StockSchema(ma.Schema):
    class Meta:
        fields = (
            "ticker",
            "date",
            "stock_price",
            "sentiment",
            "low",
            "high",
            "open",
            "close",
            "volume",
            "adjcp",
        )
        model = Stock
