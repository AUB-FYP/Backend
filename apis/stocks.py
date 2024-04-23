from flask import Blueprint, request, jsonify
from services.utils import is_date_well_formatted, YahooDownloader
from config.database import Stock
from config.database import db
from apis.users import get_stock_information
from datetime import datetime


stocks = Blueprint("stocks", __name__, url_prefix="/stock")


@stocks.route("/", methods=["GET"], strict_slashes=False)
def get_stocks():

    errors = {}
    ticker = request.args.get("ticker")
    date = request.args.get("date")

    if not ticker:
        errors["ticker"] = "ticker is missing"
    elif type(ticker) != str:
        errors["ticker"] = "must be a string"

    if not date:
        errors["date"] = "date is missing"
    elif not is_date_well_formatted(date):
        errors["date"] = "date must be in the format YYYY-MM-DD"

    if len(errors) != 0:
        return jsonify(errors), 400

    stock = Stock.query.filter_by(ticker=ticker, date=date).first()

    if not stock:
        return jsonify({"error": "stock not found"}), 404

    answer = {
        "stock_ticker": ticker,
        "date": date,
        "stock_price": stock.stock_price,
        "sentiment": stock.sentiment,
    }
    return jsonify(answer), 200


@stocks.route("/", methods=["POST"], strict_slashes=False)
def add_stock():
    data = request.get_json()

    errors = {}

    if "ticker" not in data:
        errors["ticker"] = "ticker is missing"
    elif type(data["ticker"]) != str:
        errors["ticker"] = "must be a string"

    stock_ticker = data["ticker"]
    start_date = "2015-01-01"
    end_date = datetime.today().date().strftime("%Y-%m-%d")

    yahooDownloader = YahooDownloader(start_date, end_date, [stock_ticker])
    stock_data = yahooDownloader.fetch_data()

    for index, row in stock_data.iterrows():
        stock = Stock(
            ticker=row["ticker"],
            date=row["date"],
            stock_price=row["stock_price"],
            low=row["low"],
            high=row["high"],
            open=row["open"],
            close=row["close"],
            volume=row["volume"],
            adjcp=row["adjcp"],
            sentiment=row["sentiment"],
        )

        db.session.add(stock)
        db.session.commit()
