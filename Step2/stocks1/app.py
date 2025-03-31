import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

API_KEY = 'RMRgIp4laaBoVSyyoEg3oQ==kpRILqdNoYvzkjzX'
BASE_URL = 'https://api.api-ninjas.com/v1/stockprice'
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
client = MongoClient(MONGO_URI)

# Define the database and collection
db = client['stocks_db']  # Database name
stocks1_collection = db['stocks1']


app = Flask(__name__)
stocks = {}
id_generator = 1

@app.route('/')
def home():
    return "Welcome to the Stock Portfolio API! Use the available endpoints to interact with the service."

@app.route('/stocks1', methods=['POST'])
def add_stock():
    data = request.get_json()
    if not data or 'symbol' not in data or 'purchase price' not in data or 'shares' not in data:
        return jsonify({'error': 'Malformed data'}), 400

    if stocks1_collection.find_one({'symbol': data['symbol'].upper()}):
        return jsonify({'error': 'Stock with this symbol already exists'}), 400

    stock = {
        'name': data.get('name', 'NA'),
        'symbol': data['symbol'],
        'purchase price': round(float(data['purchase price']), 2),
        'shares': int(data['shares']),
        'price': data.get('price', 0.0),
        'purchase date': data.get('purchase date', 'NA')
    }
    result = stocks1_collection.insert_one(stock)
    return jsonify({'id': str(result.inserted_id)}), 201


@app.route('/stocks1', methods=['GET'])
def get_stocks():
    try:
        all_stocks = list(stocks1_collection.find({}))
        for stock in all_stocks:
            stock['_id'] = str(stock['_id'])
        return jsonify(all_stocks), 200
    except Exception as e:
        return jsonify({'error': 'An internal server error occurred' , 'details': str(e) }), 500


@app.route('/stocks1/<stock_id>', methods=['GET'])
def get_stock_by_id(stock_id):
    try:
        stock = stocks1_collection.find_one({'_id': ObjectId(stock_id)})
        if not stock:
            return jsonify({"error": "Stock not found"}), 404
        stock['_id'] = str(stock['_id'])
        return jsonify(stock), 200
    except Exception as e:
        return jsonify({'error': 'Invalid ID or server error', 'details': str(e)}), 400

@app.route('/stocks1/<stock_id>', methods=['PUT'])
def update_stock(stock_id):
    if stock_id not in stocks:
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Malformed data'}), 400

            # Update the stock in the database
            result = stocks1_collection.update_one(
                {'_id': ObjectId(stock_id)},
                {'$set': data}
            )
            if result.matched_count == 0:
                return jsonify({"error": "Stock not found"}), 404
            return jsonify({'message': 'Stock updated successfully'}), 200
        except Exception as e:
            return jsonify({'error': 'Invalid ID or server error', 'details': str(e)}), 400


@app.route('/stocks1/<stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    try:
        # Delete the stock by its `_id`
        result = stocks1_collection.delete_one({'_id': ObjectId(stock_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Stock not found'}), 404
        return '', 204  # No Content
    except Exception as e:
        return jsonify({'error': 'Invalid ID or server error', 'details': str(e)}), 400


@app.route('/stocks1/stock-value/<stock_id>', methods=['GET'])
def fetch_stock_value(stock_id):
    try:
        stock = stocks1_collection.find_one({'_id': ObjectId(stock_id)})
        if not stock:
            return jsonify({'error': 'Stock not found'}), 404

        symbol = stock.get('symbol').upper()
        shares = stock.get('shares', 0)

        #Fetch the current ticker price from the external API
        response = requests.get(f"{BASE_URL}?ticker={symbol}", headers={"X-Api-Key": API_KEY})
        if response.status_code != 200:
            return jsonify({'server error': f'API response code {response.status_code}'}), 500

        api_response = response.json()
        if isinstance(api_response, list):
            ticker_price = api_response[0].get('price', 0.0) if len(api_response) > 0 else 0.0
        elif isinstance(api_response, dict):
            ticker_price = api_response.get('price', 0.0)
        else:
            return jsonify({'error': 'Unexpected API response format'}), 500

        stock_value = ticker_price * shares

        return jsonify({
            'symbol': symbol,
            'ticker': round(ticker_price, 2),
            'stock_value': round(stock_value, 2),
        }), 200
    except Exception as e:
        return jsonify({'error': 'Invalid ID or server error', 'details': str(e)}), 400


@app.route('/stocks1/portfolio-value', methods=['GET'])
def get_portfolio_value():
    try:
        total_value = 0.0
        stocks = list(stocks1_collection.find({}, {'_id': 0}))

        for stock in stocks:
            symbol = stock['symbol']
            shares = stock['shares']

            # Fetch current price
            response = requests.get(f"{BASE_URL}?ticker={symbol}", headers={"X-Api-Key": API_KEY})
            if response.status_code == 200:
                api_response = response.json()
                if isinstance(api_response, list):
                    ticker_price = api_response[0].get('price', 0.0) if len(api_response) > 0 else 0.0
                elif isinstance(api_response, dict):
                    ticker_price = api_response.get('price', 0.0)
                else:
                    return jsonify({'error': 'Unexpected API response format'}), 500
                total_value += ticker_price * shares

        return jsonify({
            'portfolio_value': round(total_value, 2)
        }), 200
    except Exception as e:
        return jsonify({'error': 'An internal server error occurred', 'details': str(e)}), 500


@app.route('/kill', methods=['GET'])
def kill_container():
    os._exit(1)  # Force the service to exit with code 1 (crash)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)






