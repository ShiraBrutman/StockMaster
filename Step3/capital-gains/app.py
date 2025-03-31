from flask import Flask, request, jsonify
import requests
from pymongo import MongoClient
import os

app = Flask(__name__)
API_KEY = 'RMRgIp4laaBoVSyyoEg3oQ==kpRILqdNoYvzkjzX'
STOCK_SERVICE_URL = os.getenv('STOCKS_SERVICE_URL', "http://stock-service:5001/stocks")
BASE_URL = 'https://api.api-ninjas.com/v1/stockprice'
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://db:27017//stocks_db')

client = MongoClient(MONGO_URI)

# Define the database and collection
db = client['stocks_db']  # Database name
stocks_collection = db['stocks']


@app.route('/capital-gains', methods=['GET'])
def calculate_capital_gains():
    try:
        # Retrieve query parameters
        numsharesgt = request.args.get('numsharesgt', type=int)
        numshareslt = request.args.get('numshareslt', type=int)

        # Fetch stocks from the appropriate collection(s)
        stocks = list(stocks_collection.find())

        print("Initial stocks:", stocks)

        # Apply filters
        if numsharesgt is not None:
            stocks = [stock for stock in stocks if stock.get('shares', 0) > numsharesgt]
        if numshareslt is not None:
            stocks = [stock for stock in stocks if stock.get('shares', 0) < numshareslt]

        print("Stocks after fetching from database:", stocks)
        for stock in stocks:
            print("Stock type:", type(stock))  # Should always be <class 'dict'>

        if not stocks:
            return jsonify({"total_capital_gains": 0.0}), 200

        # Calculate total capital gains
        total_capital_gains = 0.0
        for stock in stocks:
            symbol = stock.get('symbol', '').upper()
            purchase_price = stock.get('purchase price', 0.0)
            shares = stock.get('shares', 0)


            response = requests.get(f"{BASE_URL}?ticker={symbol}", headers={"X-Api-Key": API_KEY})
            if response.status_code == 200:
                api_response = response.json()

                # Handle API response formats
                if isinstance(api_response, list) and len(api_response) > 0:
                    ticker_price = api_response[0].get('price', 0.0)
                elif isinstance(api_response, dict):
                    ticker_price = api_response.get('price', 0.0)
                else:
                    print(f"Unexpected API response format: {api_response}")
                    continue  # Skip this stock

                capital_gain = (ticker_price - purchase_price) * shares
                total_capital_gains += capital_gain
                print(f"Stock: {symbol}, Ticker: {ticker_price}, Gain: {capital_gain}")
            else:
                print(f"Failed to fetch ticker for {symbol}, API response: {response.status_code}")

        return jsonify({"total_capital_gains": round(total_capital_gains, 2)}), 200
    except Exception as e:
        print("Error occurred:", str(e))
        return jsonify({"error": "An internal error occurred", "details": str(e)}), 500


@app.route('/kill', methods=['GET'])
def kill_container():
    os._exit(1)  # Force the service to exit with code 1 (crash)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
