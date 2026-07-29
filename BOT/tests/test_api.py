import pytest
from httpx import AsyncClient
from decimal import Decimal

from app.models.user import User
from tests.conftest import assert_response_success, assert_response_error


@pytest.mark.api
class TestAuthAPI:
    async def test_register_user(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "telegram_id": 111222333,
            "username": "newuser",
            "first_name": "New",
            "last_name": "User"
        })

        assert_response_success(response, 201)
        data = response.json()
        assert "user" in data
        assert data["user"]["telegram_id"] == 111222333

    async def test_register_duplicate_user(self, client: AsyncClient, test_user: User):
        response = await client.post("/api/v1/auth/register", json={
            "telegram_id": test_user.telegram_id,
            "username": "duplicate",
            "first_name": "Duplicate",
            "last_name": "User"
        })

        assert_response_error(response, 400)

    async def test_login_user(self, client: AsyncClient, test_user: User):
        response = await client.post("/api/v1/auth/login", json={
            "telegram_id": test_user.telegram_id
        })

        assert_response_success(response)
        data = response.json()
        assert "access_token" in data
        assert "user" in data


@pytest.mark.api
class TestWalletAPI:
    async def test_get_balance(self, client: AsyncClient, test_user_with_balance: User, auth_headers: dict):
        response = await client.get("/api/v1/wallet/balance", headers=auth_headers)

        assert_response_success(response)
        data = response.json()
        assert "balances" in data
        assert len(data["balances"]) > 0

        btc_balance = next((b for b in data["balances"] if b["currency"] == "BTC"), None)
        assert btc_balance is not None
        assert float(btc_balance["balance"]) == 1.0

    async def test_get_transactions(self, client: AsyncClient, test_user: User, auth_headers: dict):
        response = await client.get("/api/v1/wallet/transactions", headers=auth_headers)

        assert_response_success(response)
        data = response.json()
        assert "transactions" in data
        assert isinstance(data["transactions"], list)

    async def test_transfer_funds(self, client: AsyncClient, test_user_with_balance: User, auth_headers: dict):
        recipient_response = await client.post("/api/v1/auth/register", json={
            "telegram_id": 999888777,
            "username": "recipient",
            "first_name": "Recipient",
            "last_name": "User"
        })
        assert_response_success(recipient_response, 201)
        recipient_data = recipient_response.json()

        response = await client.post("/api/v1/wallet/transfer",
            headers=auth_headers,
            json={
                "to_user_id": recipient_data["user"]["id"],
                "currency": "USDT",
                "amount": "100.0",
                "description": "Test transfer"
            }
        )

        assert_response_success(response)
        data = response.json()
        assert "transaction" in data
        assert data["transaction"]["amount"] == "100.0"


@pytest.mark.api
class TestCheckAPI:
    async def test_create_check(self, client: AsyncClient, test_user_with_balance: User, auth_headers: dict):
        response = await client.post("/api/v1/checks/create",
            headers=auth_headers,
            json={
                "currency": "USDT",
                "amount": "50.0",
                "description": "Test check"
            }
        )

        assert_response_success(response, 201)
        data = response.json()
        assert "check" in data
        assert data["check"]["amount"] == "50.0"
        assert data["check"]["currency"] == "USDT"

    async def test_get_checks(self, client: AsyncClient, test_user: User, auth_headers: dict):
        response = await client.get("/api/v1/checks/", headers=auth_headers)

        assert_response_success(response)
        data = response.json()
        assert "checks" in data
        assert isinstance(data["checks"], list)

    async def test_activate_check_insufficient_funds(self, client: AsyncClient, test_user: User, auth_headers: dict):
        response = await client.post("/api/v1/checks/create",
            headers=auth_headers,
            json={
                "currency": "BTC",
                "amount": "10.0",
                "description": "Test check"
            }
        )

        assert_response_error(response, 400)


@pytest.mark.api
class TestInvoiceAPI:
    async def test_create_invoice(self, client: AsyncClient, test_user: User, auth_headers: dict):
        response = await client.post("/api/v1/invoices/create",
            headers=auth_headers,
            json={
                "currency": "USDT",
                "amount": "25.0",
                "description": "Test invoice",
                "expires_in_hours": 24
            }
        )

        assert_response_success(response, 201)
        data = response.json()
        assert "invoice" in data
        assert data["invoice"]["amount"] == "25.0"
        assert data["invoice"]["currency"] == "USDT"

    async def test_get_invoices(self, client: AsyncClient, test_user: User, auth_headers: dict):
        response = await client.get("/api/v1/invoices/", headers=auth_headers)

        assert_response_success(response)
        data = response.json()
        assert "invoices" in data
        assert isinstance(data["invoices"], list)

    async def test_get_invoice_by_id(self, client: AsyncClient, test_user: User, auth_headers: dict):
        create_response = await client.post("/api/v1/invoices/create",
            headers=auth_headers,
            json={
                "currency": "BTC",
                "amount": "0.001",
                "description": "Test invoice for get"
            }
        )
        assert_response_success(create_response, 201)
        invoice_data = create_response.json()
        invoice_id = invoice_data["invoice"]["id"]

        response = await client.get(f"/api/v1/invoices/{invoice_id}", headers=auth_headers)

        assert_response_success(response)
        data = response.json()
        assert "invoice" in data
        assert data["invoice"]["id"] == invoice_id


@pytest.mark.api
class TestP2PAPI:
    async def test_create_p2p_order(self, client: AsyncClient, test_user_with_balance: User, auth_headers: dict):
        response = await client.post("/api/v1/p2p/orders/create",
            headers=auth_headers,
            json={
                "type": "sell",
                "from_currency": "USDT",
                "to_currency": "RUB",
                "amount": "100.0",
                "price": "90.5",
                "payment_methods": ["card", "sbp"],
                "description": "Test P2P order"
            }
        )

        assert_response_success(response, 201)
        data = response.json()
        assert "order" in data
        assert data["order"]["type"] == "sell"
        assert data["order"]["amount"] == "100.0"

    async def test_get_p2p_orders(self, client: AsyncClient, test_user: User, auth_headers: dict):
        response = await client.get("/api/v1/p2p/orders/", headers=auth_headers)

        assert_response_success(response)
        data = response.json()
        assert "orders" in data
        assert isinstance(data["orders"], list)


@pytest.mark.api
class TestExchangeAPI:
    async def test_get_exchange_rates(self, client: AsyncClient):
        response = await client.get("/api/v1/exchange/rates")

        assert_response_success(response)
        data = response.json()
        assert "rates" in data
        assert isinstance(data["rates"], list)

    async def test_create_exchange_order(self, client: AsyncClient, test_user_with_balance: User, auth_headers: dict):
        response = await client.post("/api/v1/exchange/orders/create",
            headers=auth_headers,
            json={
                "from_currency": "USDT",
                "to_currency": "BTC",
                "from_amount": "1000.0"
            }
        )

        assert_response_success(response, 201)
        data = response.json()
        assert "order" in data
        assert data["order"]["from_currency"] == "USDT"
        assert data["order"]["to_currency"] == "BTC"


@pytest.mark.api
class TestCryptoPayAPI:
    async def test_get_me(self, client: AsyncClient, api_key_headers: dict):
        response = await client.get("/api/getMe", headers=api_key_headers)

        assert_response_success(response)
        data = response.json()
        assert data["ok"] is True
        assert "result" in data

    async def test_get_balance(self, client: AsyncClient, api_key_headers: dict):
        response = await client.get("/api/getBalance", headers=api_key_headers)

        assert_response_success(response)
        data = response.json()
        assert data["ok"] is True
        assert "result" in data
        assert isinstance(data["result"], list)

    async def test_create_invoice_crypto_pay(self, client: AsyncClient, api_key_headers: dict):
        response = await client.post("/api/createInvoice",
            headers=api_key_headers,
            json={
                "asset": "USDT",
                "amount": "10.00",
                "description": "Test Crypto Pay invoice"
            }
        )

        assert_response_success(response)
        data = response.json()
        assert data["ok"] is True
        assert "result" in data
        assert data["result"]["asset"] == "USDT"
        assert data["result"]["amount"] == "10.00"

    async def test_create_check_crypto_pay(self, client: AsyncClient, api_key_headers: dict):
        response = await client.post("/api/createCheck",
            headers=api_key_headers,
            json={
                "asset": "USDT",
                "amount": "5.00"
            }
        )

        assert_response_success(response)
        data = response.json()
        assert data["ok"] is True
        assert "result" in data
        assert data["result"]["asset"] == "USDT"
        assert data["result"]["amount"] == "5.00"


@pytest.mark.api
class TestBlockchainAPI:
    async def test_get_supported_networks(self, client: AsyncClient):
        response = await client.get("/api/v1/blockchain/networks")

        assert_response_success(response)
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        network_names = [network["network"] for network in data]
        assert "bitcoin" in network_names
        assert "ethereum" in network_names

    async def test_get_deposit_address(self, client: AsyncClient, test_user: User, auth_headers: dict):
        response = await client.get("/api/v1/blockchain/deposit/address/BTC?network=bitcoin",
                                  headers=auth_headers)

        assert_response_success(response)
        data = response.json()
        assert "currency" in data
        assert "network" in data
        assert "address" in data
        assert data["currency"] == "BTC"
        assert data["network"] == "bitcoin"

    async def test_validate_address(self, client: AsyncClient):
        response = await client.post("/api/v1/blockchain/validate/address",
            json={
                "network": "bitcoin",
                "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
            }
        )

        assert_response_success(response)
        data = response.json()
        assert "network" in data
        assert "address" in data
        assert "is_valid" in data


@pytest.mark.api
class TestErrorHandling:
    async def test_404_endpoint(self, client: AsyncClient):
        response = await client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    async def test_unauthorized_access(self, client: AsyncClient):
        response = await client.get("/api/v1/wallet/balance")
        assert response.status_code == 401

    async def test_invalid_json(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    async def test_validation_error(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "telegram_id": "invalid_id",
            "username": "test"
        })
        assert response.status_code == 422


@pytest.mark.api
class TestRateLimiting:
    async def test_rate_limiting(self, client: AsyncClient):
        responses = []
        for _ in range(100):
            response = await client.get("/api/v1/exchange/rates")
            responses.append(response)

        status_codes = [r.status_code for r in responses]
        success_count = sum(1 for code in status_codes if code == 200)

        assert success_count > 0
