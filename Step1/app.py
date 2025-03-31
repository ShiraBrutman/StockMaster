import requests
from flask import Flask, request, jsonify
from datetime import datetime

API_KEY = 'RMRgIp4laaBoVSyyoEg3oQ==kpRILqdNoYvzkjzX'
BASE_URL = 'https://api.api-ninjas.com/v1/stockprice'
MONGO_URI = 'mongodb://omer_kuriel:12345@<hostname>/?ssl=true&replicaSet=atlas-wfoqbl-shard-0&authSource=admin&retryWrites=true&w=majority&appName=Cluster0'


app = Flask(__name__)
stocks = {}
id_generator = 1

@app.route('/')
def home():
    return "Welcome to the Stock Portfolio API! Use the available endpoints to interact with the service."


@app.route('/stocks', methods=['POST'])
def add_stock():
    global id_generator
    data = request.get_json()
    if not data or 'symbol' not in data or 'purchase_price' not in data or 'shares' not in data:
        return jsonify({'error': 'Malformed data'}), 400
    for stock in stocks.values():
        if stock['symbol'].upper() == data['symbol'].upper():
            return jsonify({'error': 'Stock with this symbol already exists in the portfolio'}), 400
    stock_id = str(id_generator)
    id_generator += 1
    stock = {
        'id': stock_id,
        'name': data.get('name', 'NA'),
        'symbol': data['symbol'],
        'purchase_price': round(float(data['purchase_price']), 2),
        'shares': int(data['shares']),
        'price': data.get('price', 0.0),
        'purchase_date': data.get('purchase_date', 'NA')
    }
    stocks[stock_id] = stock
    return jsonify({'id': stock_id}), 201

@app.route('/stocks', methods=['GET'])
def get_stocks():
    try:
        return jsonify(list(stocks.values())), 200
    except Exception as e:
        return jsonify({'error': 'An internal server error occurred' , 'details': str(e) }), 500

@app.route('/stocks/<stock_id>', methods=['GET'])
def get_stock_by_id(stock_id):
    if stock_id not in stocks:
        return jsonify({"error": "Stock not found"}), 404
    stock = stocks[stock_id]
    return jsonify(stock), 200

@app.route('/stocks/<stock_id>', methods=['PUT'])
def update_stock(stock_id):
    if stock_id not in stocks:
        return jsonify({"error": "Stock not found"}), 404
    data = request.get_json()
    if set(data.keys()) != {'stock_id', 'symbol', 'purchase_price', 'shares', 'price', 'purchase_date', 'name'}:
        return jsonify({'error': 'Malformed data'}), 400
    stocks[stock_id].update({
        'name': data.get('name', stocks[stock_id]['name']),
        'symbol': data.get('symbol', stocks[stock_id]['symbol']),
        'purchase_price': round(float(data.get('purchase_price', stocks[stock_id]['purchase_price'])), 2),
        'shares': int(data.get('shares', stocks[stock_id]['shares'])),
        'price': data.get('price', stocks[stock_id]['price']),
        'purchase_date': data.get('purchase_date', stocks[stock_id]['purchase_date'])
    })
    return jsonify({'stock_id': stock_id}), 200


@app.route('/stocks/<stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    if stock_id in stocks:
        del stocks[stock_id]
        return '', 204
    else: return jsonify({'error': 'Not found'}), 404

@app.route('/stock-value/<stock_id>', methods=['GET'])
def fetch_stock_value(stock_id):
        stock = stocks.get(stock_id)
        if not stock:
            return jsonify({'error': 'Stock not found'}), 404

        symbol = stock.get('symbol').upper()
        shares = stock.get('shares', 0)
        # Fetch the current ticker price from the external API
        response =  requests.get(f"{BASE_URL}?ticker={symbol}", headers={"X-Api-Key": API_KEY})

        if response.status_code != 200:
            return jsonify({'server error': f'API response code {response.status_code}'}), 500

        ticker_price = response.json().get('price', 0.0)
        stock_value = ticker_price * shares
        result = {
            'symbol': symbol,
            'ticker': round(ticker_price, 2),
            'stock_value': round(stock_value, 2),
            }
        return result

@app.route('/stock-value/<stock_id>', methods=['GET'])
def get_stock_value(stock_id):
    try:
        stock_data = fetch_stock_value(stock_id)
        return jsonify(stock_data), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/portfolio-value', methods=['GET'])
def get_portfolio_value():
    try:
        total_value = 0.0
        for stock_id in stocks.keys():
            try:
                stock_data = fetch_stock_value(stock_id)
                total_value += stock_data.get('stock_value')
            except ValueError as e:
                print(f"Error fetching stock value for {stock_id}: {e}")
                continue

        return jsonify({
            'date': datetime.now().strftime('%d/%m/%y'),
            'portfolio_value': round(total_value, 2),
                }), 200

    except Exception as e:
            return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)






