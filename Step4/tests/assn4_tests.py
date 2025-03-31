import pytest
import requests
import json
import time

# Base URLs for our services
STOCKS_URL = "http://localhost:5001"
CAPITAL_GAINS_URL = "http://localhost:5003"

# Stock data for testing
stock1 = {"name": "NVIDIA Corporation", "symbol": "NVDA", "purchase price": 134.66, "purchase date": "18-06-2024",
          "shares": 7}
stock2 = {"name": "Apple Inc.", "symbol": "AAPL", "purchase price": 183.63, "purchase date": "22-02-2024", "shares": 19}
stock3 = {"name": "Alphabet Inc.", "symbol": "GOOG", "purchase price": 140.12, "purchase date": "24-10-2024",
          "shares": 14}
stock7 = {"name": "Amazon.com, Inc.", "purchase price": 134.66, "purchase date": "18-06-2024", "shares": 7}
stock8 = {"name": "Amazon.com, Inc.", "symbol": "AMZN", "purchase price": 134.66,
          "purchase date": "Tuesday, June 18, 2024", "shares": 7}

# Store IDs globally as module variables so they're accessible across tests
stock_ids = {}


def wait_for_services(max_retries=10, retry_delay=2):
    """Wait for services to be ready"""
    for i in range(max_retries):
        try:
            resp_stocks = requests.get(f"{STOCKS_URL}/")
            resp_gains = requests.get(f"{CAPITAL_GAINS_URL}/capital-gains")
            if resp_stocks.status_code < 500 and resp_gains.status_code < 500:
                return True
        except requests.RequestException:
            pass
        print(f"Waiting for services to be ready (attempt {i + 1}/{max_retries})...")
        time.sleep(retry_delay)
    return False


@pytest.fixture(scope="module", autouse=True)
def setup():
    """Setup for tests, ensure services are ready"""
    assert wait_for_services(), "Services not ready after max retries"
    yield


def test_1_post_stocks():
    """Test 1: Create three stocks and check IDs and status codes"""
    # Clear any existing stocks from previous test runs
    try:
        resp = requests.get(f"{STOCKS_URL}/stocks")
        if resp.status_code == 200:
            for stock in resp.json():
                if '_id' in stock:
                    requests.delete(f"{STOCKS_URL}/stocks/{stock['_id']}")
    except:
        pass

    # Add stock1
    response1 = requests.post(
        f"{STOCKS_URL}/stocks",
        json=stock1,
        headers={"Content-Type": "application/json"}
    )
    assert response1.status_code == 201
    assert "id" in response1.json()
    stock_ids['stock1'] = response1.json()["id"]

    # Add stock2
    response2 = requests.post(
        f"{STOCKS_URL}/stocks",
        json=stock2,
        headers={"Content-Type": "application/json"}
    )
    assert response2.status_code == 201
    assert "id" in response2.json()
    stock_ids['stock2'] = response2.json()["id"]

    # Add stock3
    response3 = requests.post(
        f"{STOCKS_URL}/stocks",
        json=stock3,
        headers={"Content-Type": "application/json"}
    )
    assert response3.status_code == 201
    assert "id" in response3.json()
    stock_ids['stock3'] = response3.json()["id"]

    # Print IDs for debugging
    print(f"Stock IDs: {stock_ids}")

    # Ensure all IDs are unique
    assert len({stock_ids['stock1'], stock_ids['stock2'], stock_ids['stock3']}) == 3


def test_2_get_stock_by_id():
    """Test 2: Get stock1 by ID and check its symbol"""
    # Skip if test_1 failed
    if 'stock1' not in stock_ids:
        pytest.skip("stock1 ID not available")

    response = requests.get(f"{STOCKS_URL}/stocks/{stock_ids['stock1']}")
    assert response.status_code == 200
    assert response.json()["symbol"] == "NVDA"


def test_3_get_all_stocks():
    """Test 3: Get all stocks and check count"""
    response = requests.get(f"{STOCKS_URL}/stocks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 3  # At least the 3 stocks we added


def test_4_get_stock_values():
    """Test 4: Get stock values for all three stocks"""
    # Skip if test_1 failed
    for stock_key in ['stock1', 'stock2', 'stock3']:
        if stock_key not in stock_ids:
            pytest.skip(f"{stock_key} ID not available")

    # Get stock value for stock1
    response1 = requests.get(f"{STOCKS_URL}/stocks/stock-value/{stock_ids['stock1']}")
    assert response1.status_code == 200
    assert response1.json()["symbol"] == "NVDA"

    # Get stock value for stock2
    response2 = requests.get(f"{STOCKS_URL}/stocks/stock-value/{stock_ids['stock2']}")
    assert response2.status_code == 200
    assert response2.json()["symbol"] == "AAPL"

    # Get stock value for stock3
    response3 = requests.get(f"{STOCKS_URL}/stocks/stock-value/{stock_ids['stock3']}")
    assert response3.status_code == 200
    assert response3.json()["symbol"] == "GOOG"


def test_5_portfolio_value():
    """Test 5: Check portfolio value is close to sum of stock values"""
    # Skip if test_1 failed
    for stock_key in ['stock1', 'stock2', 'stock3']:
        if stock_key not in stock_ids:
            pytest.skip(f"{stock_key} ID not available")

    # Get individual stock values
    sv1 = float(requests.get(f"{STOCKS_URL}/stocks/stock-value/{stock_ids['stock1']}").json()["stock_value"])
    sv2 = float(requests.get(f"{STOCKS_URL}/stocks/stock-value/{stock_ids['stock2']}").json()["stock_value"])
    sv3 = float(requests.get(f"{STOCKS_URL}/stocks/stock-value/{stock_ids['stock3']}").json()["stock_value"])

    # Get portfolio value
    response = requests.get(f"{STOCKS_URL}/stocks/portfolio-value")
    assert response.status_code == 200
    pv = float(response.json()["portfolio_value"])

    # Check that portfolio value is within 3% of sum of stock values
    sum_of_values = sv1 + sv2 + sv3
    assert pv * 0.97 <= sum_of_values <= pv * 1.03 or abs(pv - sum_of_values) < 0.1


def test_6_missing_symbol():
    """Test 6: Check error when required field 'symbol' is missing"""
    response = requests.post(
        f"{STOCKS_URL}/stocks",
        json=stock7,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400


def test_7_delete_stock():
    """Test 7: Delete stock2 (Apple Inc.)"""
    # Skip if test_1 failed
    if 'stock2' not in stock_ids:
        pytest.skip("stock2 ID not available")

    response = requests.delete(f"{STOCKS_URL}/stocks/{stock_ids['stock2']}")
    assert response.status_code == 204


def test_8_get_deleted_stock():
    """Test 8: Check that deleted stock cannot be retrieved"""
    # Skip if test_1 failed
    if 'stock2' not in stock_ids:
        pytest.skip("stock2 ID not available")

    response = requests.get(f"{STOCKS_URL}/stocks/{stock_ids['stock2']}")
    assert response.status_code == 404


def test_9_invalid_date_format():
    """Test 9: Check error when purchase date has incorrect format"""
    response = requests.post(
        f"{STOCKS_URL}/stocks",
        json=stock8,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400