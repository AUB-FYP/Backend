from flask import request, jsonify, Blueprint, abort
from config.database import User, user_schema, UserStock, user_stock_schema
from config.database import db
from services.authentication import extract_auth_token, decode_token
import jwt, re, json
from services.utils import (
    YahooDownloader,
    is_date_well_formatted,
    format_json,
    helperNews,
)
import modal
from datetime import datetime, timedelta
import pandas as pd
from flask.cli import load_dotenv

users = Blueprint("users", __name__, url_prefix="/user")

load_dotenv()


@users.route("/", methods=["POST"], strict_slashes=False)
def signup():

    errors = {}

    if "user_name" not in request.json:
        errors["user_name"] = "string is missing"
    elif type(request.json["user_name"]) != str:
        errors["user_name"] = "must be a string"

    if "password" not in request.json:
        errors["password"] = "string is missing"
    elif type(request.json["password"]) != str:
        errors["password"] = "must be a string"

    if len(errors) != 0:
        return jsonify(errors), 400

    user_name = request.json["user_name"]
    password = request.json["password"]

    userWithTheSameUsername = User.query.filter_by(user_name=user_name).first()
    if userWithTheSameUsername:
        return {"username": f"username {user_name} is taken"}, 409

    user = User(user_name=user_name, password=password)
    db.session.add(user)
    db.session.commit()
    print(user_schema.dump(user))

    return jsonify(user_schema.dump(user)), 201


# The user sends a GET request to the /user route
# The server responds with the user object.


@users.route("/", methods=["GET"], strict_slashes=False)
def get_user_info():

    auth_token = extract_auth_token(request)
    user_id = None
    if auth_token:
        try:
            user_id = decode_token(auth_token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            abort(401)
    else:
        return jsonify({"auth_token": "No token was provided"}), 401

    user = User.query.filter_by(id=user_id).first()

    if not user:
        return jsonify({"user": f"User with id {user_id} found"}), 404

    return jsonify(user_schema.dump(user)), 200


@users.route("/<string:username>", methods=["POST"])
def modify_user_info(username):

    data = request.get_json()
    user = User.query.filter_by(user_name=username).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    user_id = user.id
    errors = {}
    if "stock_tickers" not in data:
        errors["stock_tickers"] = "stock tickers are missing"
    elif not isinstance(data["stock_tickers"], list):
        errors["stock_tickers"] = "stock tickers must be a list"

    if "shares_owned" not in data:
        errors["shares_owned"] = "shares owned is missing"
    elif not isinstance(data["shares_owned"], list):
        errors["shares_owned"] = "shares owned must be a list"

    if "money_owned" not in data:
        errors["money_owned"] = "money owned is missing"
    elif not isinstance(data["money_owned"], float) and not isinstance(
        data["money_owned"], int
    ):
        errors["money_owned"] = "money owned must be a float or an int"

    if len(errors) != 0:
        return jsonify(errors), 400

    stock_tickers = data["stock_tickers"]
    shares_owned = data["shares_owned"]
    money_owned = data["money_owned"]

    for stock_ticker, shares in zip(stock_tickers, shares_owned):
        user_stock = UserStock.query.filter_by(
            user_id=user_id, stock=stock_ticker
        ).first()
        if not user_stock:
            user_stock = UserStock(user_id=user_id, stock=stock_ticker, shares=shares)
            db.session.add(user_stock)
        user_stock.shares = shares

    for stock in user.stocks:
        if stock.stock not in stock_tickers:
            db.session.delete(stock)

    user.funds = money_owned

    db.session.commit()
    return jsonify({"message": "User information updated"}), 200


@users.route("/<string:username>/stocks", methods=["POST"])
def add_stock_to_user(username):
    data = request.get_json()
    user = User.query.filter_by(user_name=username).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    user_id = user.id
    errors = {}

    if "stock_ticker" not in data:
        errors["stock_ticker"] = "stock ticker is missing"
    elif type(data["stock_ticker"]) != str:
        errors["stock_ticker"] = "stock ticker must be a string"

    if len(errors) != 0:
        return jsonify(errors), 400

    stock_ticker = data["stock_ticker"]

    user_stock = UserStock(user_id=user.id, stock=stock_ticker)

    try:
        db.session.add(user_stock)
        db.session.commit()
        return (
            jsonify({"message": f"Stock '{stock_ticker}' added for user {user_id}"}),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "An error occurred while adding the stock"}), 500


@users.route("/<string:username>/stocks", methods=["DELETE"])
def delete_stock_from_user(username):
    data = request.get_json()
    user = User.query.filter_by(user_name=username).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    user_id = user.id
    errors = {}

    if "stock_ticker" not in data:
        errors["stock_ticker"] = "stock ticker is missing"
    elif type(data["stock_ticker"]) != str:
        errors["stock_ticker"] = "stock ticker must be a string"

    if len(errors) != 0:
        return jsonify(errors), 400

    stock_ticker = data["stock_ticker"]

    user_stock = UserStock.query.filter_by(user_id=user.id, stock=stock_ticker).first()

    if not user_stock:
        return jsonify({"message": "Stock not found"}), 404

    try:
        db.session.delete(user_stock)
        db.session.commit()
        return (
            jsonify({"message": f"Stock '{stock_ticker}' deleted for user {user_id}"}),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "An error occurred while deleting the stock"}), 500


@users.route("/<string:username>/stocks", methods=["GET"])
def get_stock_information(username):

    data = request.get_json()
    user = User.query.filter_by(user_name=username).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    user_id = user.id
    errors = {}

    if "stock_ticker" not in data:
        errors["stock_ticker"] = "stock ticker is missing"
    elif not isinstance(data["stock_ticker"], str):
        errors["stock_ticker"] = "stock ticker must be a string"

    if "start_date" not in data:
        errors["start_date"] = "start date is missing"
    elif not isinstance(data["start_date"], str) or not is_date_well_formatted(
        data["start_date"]
    ):
        errors["start_date"] = "start date must be in 'YYYY-MM-DD' format"

    if "end_date" not in data:
        errors["end_date"] = "end date is missing"
    elif not isinstance(data["end_date"], str) or not is_date_well_formatted(
        data["end_date"]
    ):
        errors["end_date"] = "end date must be in 'YYYY-MM-DD' format"

    if len(errors) != 0:
        return jsonify(errors), 400

    stock_ticker = data["stock_ticker"]
    start_date = data["start_date"]
    end_date = data["end_date"]

    yahooDownloader = YahooDownloader(start_date, end_date, [stock_ticker])

    try:
        stock_data = yahooDownloader.fetch_data()
    except Exception as e:
        return jsonify({"message": "Error fetching data"}), 500

    return jsonify(stock_data.to_dict()), 200


@users.route("/<string:username>/model", methods=["GET"])
def train_model(username):
    user = User.query.filter_by(user_name=username).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    user_id = user.id

    username = user.user_name
    user_funds = user.funds
    user_stocks_tickers = [stock.stock for stock in user.stocks]
    start_date = "2020-01-01"
    end_date = "2021-01-01"

    # News, stock_info = helperNews(user_stocks_tickers, start_date, end_date)

    p = modal.Function.lookup("hello", "get_historical_sentiment_modal")
    response = p.remote(start_date, end_date, user_stocks_tickers)
    print(response)
    print(response.shape)
    yahooDownloader = YahooDownloader(start_date, end_date, user_stocks_tickers)
    stock_data = None
    try:
        stock_data = yahooDownloader.fetch_data()
    except Exception as e:
        return jsonify({"message": "Error fetching data"}), 500

    stock_data["sentiment"] = 0

    process = modal.Function.lookup("hello", "train")
    response = process.remote(username, user_funds, user_stocks_tickers, stock_data)

    return (
        jsonify(f"Model Trained for {username}, for stocks : {user_stocks_tickers}"),
        200,
    )


@users.route("/<string:username>/infer", methods=["GET"])
def infer(username):
    user = User.query.filter_by(user_name=username).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    user_id = user.id
    username = user.user_name
    end_date = datetime.today().date().strftime("%Y-%m-%d")
    start_date = datetime.today().date() - timedelta(days=45)
    user_stocks_tickers = [stock.stock for stock in user.stocks]
    user_stocks_number_of_shares_owned = [stock.shares for stock in user.stocks]

    data = {
        "stock_tickers": user_stocks_tickers,
        "shares_owned": user_stocks_number_of_shares_owned,
    }

    pstocks = pd.DataFrame(
        data["shares_owned"], index=data["stock_tickers"], columns=["shares_owned"]
    ).T
    print(pstocks)
    yahooDownloader = YahooDownloader(start_date, end_date, user_stocks_tickers)
    stock_data = None
    try:
        stock_data = yahooDownloader.fetch_data()
    except Exception as e:
        return jsonify({"message": "Error fetching data"}), 500

    stock_data["sentiment"] = 0
    process = modal.Function.lookup("hello", "infer")
    response = process.remote(username, stock_data, user.funds, pstocks)
    json_response = format_json(response)
    print(json_response)
    return jsonify(json.loads(json_response)), 200
