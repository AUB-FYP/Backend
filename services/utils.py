from __future__ import annotations

import pandas as pd
import yfinance as yf
import re
import requests
from datetime import datetime, timedelta
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
import time
import wikipediaapi
from bs4 import BeautifulSoup
import os
import json


def is_date_well_formatted(date: str) -> bool:
    """Check if the date is well formatted"""
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    return date_pattern.match(date)


class News_object:
    def __init__(self, headline, url, publisher, date, stock):
        self.headline = headline
        self.date = date
        self.publisher = publisher
        self.stock = stock
        self.url = url
        self.sentiment = 0

    def __str__(self):
        return f"Headline: {self.headline}, URL: {self.url}, Publisher: {self.publisher}, Date: {self.date}, Stock: {self.stock}"


def helperNews(start_date, end_date, stock_tickers):

    ALPACA_API_KEY = "PKSEJNX9YPTO2VEG3A0P"
    ALPACA_SECRET_KEY = "EyexfhDMKEy4f01cDEfZpbyXMUApt8nGI29fkP0f"

    symbol = "AAPL"

    headers = {
        "APCA-API-KEY-ID": "PKSEJNX9YPTO2VEG3A0P",
        "APCA-API-SECRET-KEY": "EyexfhDMKEy4f01cDEfZpbyXMUApt8nGI29fkP0f",
    }

    tickers = ",".join(stock_tickers)
    alpaca_news_url = f"https://data.alpaca.markets/v1beta1/news?symbols={tickers}&limit=10&start={start_date}&end={end_date}&sort=ASC"
    alpaca_stock_url = f"https://paper-api.alpaca.markets"
    print(alpaca_stock_url)
    response = requests.get(alpaca_news_url, headers=headers)
    financial_data = response.json()
    print(financial_data)
    print(len(financial_data["news"]))
    News = []
    token = ""
    last_status_code = 0
    while (
        last_status_code == 429
        or last_status_code == 403
        or (financial_data["next_page_token"] != None)
    ):
        if last_status_code != 429 and last_status_code != 403:
            for raw_news in financial_data["news"]:
                for stock_symbol in raw_news["symbols"]:
                    if stock_symbol == None or stock_symbol == "":
                        continue
                    News.append(
                        News_object(
                            headline=raw_news["headline"],
                            url=raw_news["url"] or "X",
                            publisher=raw_news["source"] or "X",
                            date=raw_news["created_at"],
                            stock=stock_symbol,
                        )
                    )
        try:
            token = financial_data[
                "next_page_token"
            ]  # Tries to modify token with new one
        except:
            pass  # Token not modified
        response = requests.get(
            f"https://data.alpaca.markets/v1beta1/news?symbols={tickers}&limit=50&start={start_date}&end={end_date}&sort=ASC&page_token={token}",
            headers=headers,
        )

        if response.status_code == 429 or response.status_code == 403:
            print("Waiting")
            time.sleep(20)
        financial_data = response.json()
        last_status_code = response.status_code

    company_info = {}
    ticker_to_name = {}

    def save_cache_to_disk():
        directory = "scratch/localdata"

        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(os.path.join(directory, "company_info.json"), "w") as file:
            json.dump(company_info, file)
        with open(os.path.join(directory, "ticker_to_name.json"), "w") as file:
            json.dump(ticker_to_name, file)

    def load_cache_from_disk():
        directory = "/localdata"
        if not os.path.exists(directory):
            return None, None
        with open(os.path.join(directory, "company_info.json"), "r") as file:
            company_info = json.load(file)
        with open(os.path.join(directory, "ticker_to_name.json"), "r") as file:
            ticker_to_name = json.load(file)

    def get_company_name_from_ticker(ticker):
        if ticker in ticker_to_name:
            return ticker_to_name[ticker]

        company_name = None
        url = f"https://finance.yahoo.com/quote/{ticker}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            company_name_element = soup.find("h1", class_="D(ib) Fz(18px)")
            if company_name_element:
                company_name = company_name_element.text
            else:
                company_name_element = soup.find("title")
                if company_name_element:
                    company_name = company_name_element.text.split(" (")[0]

        if company_name:
            ticker_to_name[ticker] = company_name
        return company_name

    def get_wikipedia_first_paragraph(company_name):
        if not company_name:
            return ""

        user_agent = "my_script/1.0"
        wiki = wikipediaapi.Wikipedia(user_agent=user_agent)
        page = wiki.page(company_name + " company")
        if not page.exists():
            page = wiki.page(company_name)
        if not page.exists():
            return ""

        content = page.text
        first_section_index = content.find("==")
        if first_section_index != -1:
            content = content[:first_section_index]
        end_first_paragraph_index = content.find("\n\n")
        if end_first_paragraph_index != -1:
            first_paragraph = content[:end_first_paragraph_index]
            return first_paragraph

        return content

    def getBackground(ticker):
        ## Ticker could be a $APPL ticker, or APPL ticker, or a company name, Apple
        company_name = ticker
        if ticker[0] == "$" or ticker.isupper():
            if ticker[0] == "$":
                ticker = ticker[1:]
            company_name_temp = get_company_name_from_ticker(ticker)
            if company_name_temp:
                company_name = company_name_temp
        if company_name not in company_info:
            first_paragraph = get_wikipedia_first_paragraph(company_name)
            company_info[company_name] = first_paragraph
        return company_info[company_name]

    def get_financial_info(ticker):

        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
        params = {"modules": "summaryDetail,defaultKeyStatistics,financialData"}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            # Process and extract relevant financial information from the response data
            return data
        else:
            return None

    stock = {}
    for comp in stock_tickers:
        stock[comp] = ""

    for comp in stock:
        stock[comp] = getBackground(comp)
        
    return News, stock


"""Contains methods and classes to collect data from
Yahoo Finance API
"""


class YahooDownloader:
    """Provides methods for retrieving daily stock data from
    Yahoo Finance API

    Attributes
    ----------
        start_date : str
            start date of the data (modified from neofinrl_config.py)
        end_date : str
            end date of the data (modified from neofinrl_config.py)
        ticker_list : list
            a list of stock tickers (modified from neofinrl_config.py)

    Methods
    -------
    fetch_data()
        Fetches data from yahoo API

    """

    def __init__(self, start_date: str, end_date: str, ticker_list: list):
        self.start_date = start_date
        self.end_date = end_date
        self.ticker_list = ticker_list

    def fetch_data(self, proxy=None) -> pd.DataFrame:
        """Fetches data from Yahoo API
        Parameters
        ----------

        Returns
        -------
        `pd.DataFrame`
            7 columns: A date, open, high, low, close, volume and tick symbol
            for the specified stock ticker
        """
        # Download and save the data in a pandas DataFrame:
        data_df = pd.DataFrame()
        num_failures = 0
        for tic in self.ticker_list:
            temp_df = yf.download(
                tic, start=self.start_date, end=self.end_date, proxy=proxy
            )
            temp_df["tic"] = tic
            if len(temp_df) > 0:
                # data_df = data_df.append(temp_df)
                data_df = pd.concat([data_df, temp_df], axis=0)
            else:
                num_failures += 1
        if num_failures == len(self.ticker_list):
            raise ValueError("no data is fetched.")
        # reset the index, we want to use numbers as index instead of dates
        data_df = data_df.reset_index()
        try:
            # convert the column names to standardized names
            data_df.columns = [
                "date",
                "open",
                "high",
                "low",
                "close",
                "adjcp",
                "volume",
                "tic",
            ]
            # use adjusted close price instead of close price
            data_df["close"] = data_df["adjcp"]
            # drop the adjusted close price column
            data_df = data_df.drop(labels="adjcp", axis=1)
        except NotImplementedError:
            print("the features are not supported currently")
        # create day of the week column (monday = 0)
        data_df["day"] = data_df["date"].dt.dayofweek
        # convert date to standard string format, easy to filter
        data_df["date"] = data_df.date.apply(lambda x: x.strftime("%Y-%m-%d"))
        # drop missing data
        data_df = data_df.dropna()
        data_df = data_df.reset_index(drop=True)
        print("Shape of DataFrame: ", data_df.shape)
        # print("Display DataFrame: ", data_df.head())

        data_df = data_df.sort_values(by=["date", "tic"]).reset_index(drop=True)

        return data_df

    def select_equal_rows_stock(self, df):
        df_check = df.tic.value_counts()
        df_check = pd.DataFrame(df_check).reset_index()
        df_check.columns = ["tic", "counts"]
        mean_df = df_check.counts.mean()
        equal_list = list(df.tic.value_counts() >= mean_df)
        names = df.tic.value_counts().index
        select_stocks_list = list(names[equal_list])
        df = df[df.tic.isin(select_stocks_list)]
        return df


def format_json(df):
    # Convert DataFrame to JSON, orient it as 'index' to use the index as keys
    formatted_json = df.to_json(orient="index")
    return formatted_json
