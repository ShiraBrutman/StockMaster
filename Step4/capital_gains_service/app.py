from flask import Flask, request, jsonify
import requests
from pymongo import MongoClient
import os
import logging

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Create a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove existing handlers to prevent duplicate logs
if logger.hasHandlers():
    logger.handlers.clear()

# File handler (writes logs to file)
file_handler = logging.FileHandler("logs/capital_gains_service.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# Stream handler (writes logs to stdout for Docker logs)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Logging setup complete. Capital Gains service is running.")

app = Flask(__name__)
API_KEY = 'RMRgIp4laaBoVSyyoEg3oQ==kpRILqdNoYvzkjzX'
STOCKS_URL = "http://localhost:5001/stocks"
BASE_URL = 'https://api.api-ninjas.com/v1/stockprice'
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')

logger.info(f"Starting capital gains service with MONGO_URI: {MONGO_URI}")
try:
    client = MongoClient(MONGO_URI)
    # Define the database and collection
    db = client['stocks_db']  # Database name
    stocks_collection = db['stocks']
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise


@app.route('/capital-gains', methods=['GET'])
def calculate_capital_gains():
    try:
        logger.info("Received request for capital gains calculation")
        # Retrieve query parameters
        portfolio = request.args.get('portfolio', None)
        numsharesgt = request.args.get('numsharesgt', type=int)
        numshareslt = request.args.get('numshareslt', type=int)

        logger.info(f"Query parameters - portfolio: {portfolio}, numsharesgt: {numsharesgt}, numshareslt: {numshareslt}")

        # Fetch stocks from the appropriate collection(s)
        stocks = list(stocks_collection.find({}))
        logger.info(f"Found {len(stocks)} stocks in database")

        # Apply filters
        if numsharesgt is not None:
            stocks = [stock for stock in stocks if stock.get('shares', 0) > numsharesgt]
            logger.info(f"After applying numsharesgt filter: {len(stocks)} stocks remaining")
        if numshareslt is not None:
            stocks = [stock for stock in stocks if stock.get('shares', 0) < numshareslt]
            logger.info(f"After applying numshareslt filter: {len(stocks)} stocks remaining")


        if not stocks:
            logger.info("No stocks match the filtering criteria")
            return jsonify({"total_capital_gains": 0.0}), 200

        # Calculate total capital gains
        total_capital_gains = 0.0
        for stock in stocks:
            symbol = stock.get('symbol', '').upper()
            purchase_price = stock.get('purchase price', 0.0)
            shares = stock.get('shares', 0)

            logger.info(f"Processing stock: {symbol}, shares: {shares}, purchase price: {purchase_price}")

            try:
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
                    logger.info(f"Stock: {symbol}, Current price: {ticker_price}, Capital gain: {capital_gain}")
                else:
                    logger.error(f"Failed to fetch ticker for {symbol}, API response: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Request exception for {symbol}: {str(e)}")

        logger.info(f"Total capital gains calculated: {total_capital_gains}")
        return jsonify({"total_capital_gains": round(total_capital_gains, 2)}), 200

    except Exception as e:
        logger.error(f"Error calculating capital gains: {str(e)}")
        return jsonify({"error": "An internal error occurred", "details": str(e)}), 500
@app.route('/', methods=['GET'])
def home():
    logger.info("Home endpoint accessed")
    return "Capital Gains Service API. Use /capital-gains endpoint to calculate capital gains."

@app.route('/kill', methods=['GET'])
def kill_container():
    logger.warning("Kill endpoint accessed - shutting down service")
    os._exit(1)  # Force the service to exit with code 1 (crash)

if __name__ == "__main__":
    logger.info("Starting capital gains service")
    app.run(host="0.0.0.0", port=8080)
