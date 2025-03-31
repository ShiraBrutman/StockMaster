import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId
import logging

# Configure logging
os.makedirs('logs', exist_ok=True)

# Create a logger
logger = logging.getLogger()  # Get the root logger
logger.setLevel(logging.INFO)  # Set logging level

# File handler (writes logs to logs/stocks_service.log)
file_handler = logging.FileHandler("logs/stocks_service.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# Stream handler (writes logs to stdout, so Docker can capture them)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Logging setup complete. Service is running.")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)  # Prevents hanging
    db = client["stocks_db"]
    stocks_collection = db["stocks"]
    client.server_info()  # Test connection
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise

API_KEY = 'RMRgIp4laaBoVSyyoEg3oQ==kpRILqdNoYvzkjzX'
BASE_URL = 'https://api.api-ninjas.com/v1/stockprice'



app = Flask(__name__)
app.logger.handlers = logger.handlers
app.logger.setLevel(logging.INFO)

logger.info("Flask is now using our logging system.")
app.logger.info("Flask is now using our logging system.")

@app.route('/')
def home():
    logger.info(f"Home endpoint accessed")
    return "Welcome to the Stock Portfolio API! Use the available endpoints to interact with the service."


@app.route('/stocks', methods=['POST'])
def add_stock():
    data = request.get_json()
    if not data or 'symbol' not in data or 'purchase price' not in data or 'shares' not in data:
        logger.warning("Malformed stock data received")
        return jsonify({'error': 'Malformed data'}), 400

    try:
        datetime.strptime(data["purchase date"], "%d-%m-%Y")
    except ValueError:
        logger.warning("Invalid date format in stock data")
        return jsonify({'error': 'Invalid date format. Expected DD-MM-YYYY'}), 400

    if stocks_collection.find_one({'symbol': data['symbol'].upper()}):
        logger.error(f"Stock with symbol {data['symbol']} already exists")
        return jsonify({'error': 'Stock with this symbol already exists'}), 400
    try:
        stock = {
            'name': data.get('name', 'NA'),
            'symbol': data['symbol'],
            'purchase price': round(float(data['purchase price']), 2),
            'shares': int(data['shares']),
            'price': data.get('price', 0.0),
            'purchase date': data.get('purchase date', 'NA')
        }
        # Insert into database
        result = stocks_collection.insert_one(stock)
        stock_id = str(result.inserted_id)
        logger.info(f"Successfully added stock with ID: {stock_id}")
        return jsonify({'id': stock_id}), 201

    except Exception as e:
        logger.error(f"Error adding stock: {str(e)}")
        return jsonify({'error': 'An error occurred while adding the stock', 'details': str(e)}), 500


@app.route('/stocks', methods=['GET'])
def get_stocks():
    try:
        logger.info("Received request to get stocks")
        symbol = request.args.get('symbol')

        # Log the query parameters
        if symbol:
            logger.info(f"Filtering stocks by symbol: {symbol}")
        else:
            logger.info("Retrieving all stocks")

        # Use MongoDB filter directly for efficiency
        query = {'symbol': symbol} if symbol else {}

        # Fetch stocks from the database
        result = list(stocks_collection.find(query))
        logger.info(f"Found {len(result)} stocks matching query")

        # Convert ObjectId to string
        for stock in result:
            stock['_id'] = str(stock['_id'])

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting stocks: {str(e)}")
        return jsonify({'error': 'An internal server error occurred', 'details': str(e)}), 500


@app.route('/stocks/<stock_id>', methods=['GET'])
def get_stock_by_id(stock_id):
    try:
        logger.info(f"Getting stock with ID: {stock_id}")
        stock = stocks_collection.find_one({'_id': ObjectId(stock_id)})
        if not stock:
            logger.warning(f"Stock with ID: {stock_id} not found")
            return jsonify({"error": "Stock not found"}), 404
        stock['_id'] = str(stock['_id'])
        return jsonify(stock), 200
    except Exception as e:
        logger.error(f"Error getting stock by ID {stock_id}: {str(e)}")
        return jsonify({'error': 'Invalid ID or server error', 'details': str(e)}), 400


@app.route('/stocks/<stock_id>', methods=['PUT'])
def update_stock(stock_id):
    try:
        logger.info(f"Updating stock with ID: {stock_id}")
        data = request.get_json()
        if not data:
            logger.error("No JSON data received for update")
            return jsonify({'error': 'Malformed data'}), 400

        # Update the stock in the database
        result = stocks_collection.update_one(
            {'_id': ObjectId(stock_id)},
            {'$set': data}
        )
        if result.matched_count == 0:
            logger.warning(f"Stock not found with ID: {stock_id}")
            return jsonify({"error": "Stock not found"}), 404
        logger.info(f"Successfully updated stock with ID: {stock_id}")
        return jsonify({'message': 'Stock updated successfully'}), 200
    except Exception as e:
        logger.error(f"Error updating stock with ID {stock_id}: {str(e)}")
        return jsonify({'error': 'Invalid ID or server error', 'details': str(e)}), 400


@app.route('/stocks/<stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    try:
        logger.info(f"Deleting stock with ID: {stock_id}")
        # Delete the stock by its `_id`
        result = stocks_collection.delete_one({'_id': ObjectId(stock_id)})
        if result.deleted_count == 0:
            logger.warning(f"Stock not found with ID: {stock_id}")
            return jsonify({'error': 'Stock not found'}), 404
        logger.info(f"Successfully deleted stock with ID: {stock_id}")
        return '', 204  # No Content
    except Exception as e:
        logger.error(f"Error deleting stock with ID {stock_id}: {str(e)}")
        return jsonify({'error': 'Invalid ID or server error', 'details': str(e)}), 400


@app.route('/stocks/stock-value/<stock_id>', methods=['GET'])
def fetch_stock_value(stock_id):
    try:
        logger.info(f"Fetching stock value for ID: {stock_id}")
        stock = stocks_collection.find_one({'_id': ObjectId(stock_id)})
        if not stock:
            logger.warning(f"Stock not found with ID: {stock_id}")
            return jsonify({'error': 'Stock not found'}), 404

        symbol = stock.get('symbol').upper()
        shares = stock.get('shares', 0)
        logger.info(f"Fetching current price for symbol: {symbol}")

        # Fetch the current ticker price from the external API
        try:

            response = requests.get(f"{BASE_URL}?ticker={symbol}", headers={"X-Api-Key": API_KEY})
            if response.status_code != 200:
                logger.error(f"API error for symbol {symbol}: {response.status_code}")
                return jsonify({'server error': f'API response code {response.status_code}'}), 500

            api_response = response.json()
            if isinstance(api_response, list):
                ticker_price = api_response[0].get('price', 0.0) if len(api_response) > 0 else 0.0
            elif isinstance(api_response, dict):
                ticker_price = api_response.get('price', 0.0)
            else:
                logger.error(f"Unexpected API response format for symbol {symbol}: {api_response}")
                return jsonify({'error': 'Unexpected API response format'}), 500

            stock_value = ticker_price * shares
            logger.info(f"Calculated stock value for {symbol}: ${stock_value}")

            return jsonify({
                'symbol': symbol,
                'ticker': round(ticker_price, 2),
                'stock_value': round(stock_value, 2),
            }), 200
        except requests.RequestException as e:
            logger.error(f"Request exception when fetching ticker for {symbol}: {str(e)}")
            return jsonify({'error': 'Failed to fetch current stock price', 'details': str(e)}), 500
    except Exception as e:
            logger.error(f"Error fetching stock value for ID {stock_id}: {str(e)}")
            return jsonify({'error': 'Invalid ID or server error', 'details': str(e)}), 400


@app.route('/stocks/portfolio-value', methods=['GET'])
def get_portfolio_value():
    try:
        logger.info("Calculating portfolio value")
        total_value = 0.0
        stocks = list(stocks_collection.find({}, {'_id': 0}))
        logger.info(f"Found {len(stocks)} stocks in portfolio")

        for stock in stocks:
            symbol = stock['symbol']
            shares = stock['shares']

            # Fetch current price
            try:
                response = requests.get(f"{BASE_URL}?ticker={symbol}", headers={"X-Api-Key": API_KEY})
                if response.status_code == 200:
                    api_response = response.json()
                    if isinstance(api_response, list):
                        ticker_price = api_response[0].get('price', 0.0) if len(api_response) > 0 else 0.0
                    elif isinstance(api_response, dict):
                        ticker_price = api_response.get('price', 0.0)
                    else:
                        logger.error(f"Unexpected API response format for {symbol}: {api_response}")
                        continue

                    total_value += ticker_price * shares
                    logger.info(f"Current value for {symbol}: ${ticker_price*shares}")
                else:
                    logger.error(f"API error for {symbol}: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"Request exception for {symbol}: {str(e)}")

        logger.info(f"Total portfolio value: ${total_value}")
        return jsonify({
            'portfolio_value': round(total_value, 2)
        }), 200

    except Exception as e:
        logger.error(f"Error calculating portfolio value: {str(e)}")
        return jsonify({'error': 'An internal server error occurred', 'details': str(e)}), 500


@app.route('/kill', methods=['GET'])
def kill_container():
    logger.warning("Kill endpoint accessed - shutting down service")
    os._exit(1)  # Force the service to exit with code 1 (crash)


if __name__ == "__main__":
    logger.info("Starting Flask application")
    app.run(host="0.0.0.0", port=8000, debug=True)






