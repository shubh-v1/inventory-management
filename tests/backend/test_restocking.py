"""
Tests for restocking order API endpoints.
"""
from datetime import datetime, timedelta

import pytest

import main


@pytest.fixture(autouse=True)
def clear_restock_orders():
    """Restock orders are module-level in-memory state; reset around each test."""
    main.restock_orders.clear()
    yield
    main.restock_orders.clear()


class TestRestockingData:
    """Test that restocking has the data it needs."""

    def test_every_forecast_sku_is_in_inventory_with_lead_time(self, client):
        """Test that each demand forecast SKU has a priced inventory item with a lead time."""
        forecasts = client.get("/api/demand").json()
        inventory = {item["sku"]: item for item in client.get("/api/inventory").json()}

        assert len(forecasts) > 0
        for forecast in forecasts:
            item = inventory.get(forecast["item_sku"])
            assert item is not None, f"{forecast['item_sku']} missing from inventory"
            assert item["unit_cost"] > 0
            assert isinstance(item["lead_time_days"], int)
            assert item["lead_time_days"] > 0


class TestRestockOrderEndpoints:
    """Test suite for restocking order endpoints."""

    def test_get_restock_orders_empty(self, client):
        """Test that there are no restock orders before any are submitted."""
        response = client.get("/api/restock-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_restock_order(self, client):
        """Test submitting a restock order within budget."""
        payload = {
            "items": [
                {"sku": "WDG-001", "name": "Industrial Widget Type A", "quantity": 10, "unit_cost": 12.50},
                {"sku": "MTR-304", "name": "Electric Motor 5HP", "quantity": 2, "unit_cost": 489.00},
            ],
            "budget": 5000,
        }
        before = datetime.now().replace(microsecond=0)
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("RST-")
        assert order["budget"] == 5000
        assert len(order["items"]) == 2
        assert order["total_value"] == pytest.approx(10 * 12.50 + 2 * 489.00)

        # Lead time is the slowest item: MTR-304 (21 days) vs WDG-001 (10 days)
        assert order["lead_time_days"] == 21
        submitted = datetime.fromisoformat(order["submitted_date"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert submitted >= before
        assert expected - submitted == timedelta(days=21)

    def test_created_order_appears_in_list_newest_first(self, client):
        """Test that submitted orders are listed, newest first."""
        item = {"sku": "GSK-203", "name": "High-Temperature Gasket", "quantity": 5, "unit_cost": 4.80}
        first = client.post("/api/restock-orders", json={"items": [item], "budget": 100}).json()
        second = client.post("/api/restock-orders", json={"items": [item], "budget": 100}).json()

        orders = client.get("/api/restock-orders").json()
        assert [o["id"] for o in orders] == [second["id"], first["id"]]
        assert first["order_number"] != second["order_number"]

    def test_create_restock_order_uses_server_prices(self, client):
        """Test that client-supplied unit costs are ignored in favour of inventory data."""
        payload = {
            "items": [{"sku": "CTL-330", "name": "Logic Controller Board", "quantity": 1, "unit_cost": 0.01}],
            "budget": 1000,
        }
        order = client.post("/api/restock-orders", json=payload).json()
        assert order["items"][0]["unit_cost"] == 215.00
        assert order["total_value"] == 215.00

    def test_create_restock_order_over_budget(self, client):
        """Test that an order exceeding the budget is rejected."""
        payload = {
            "items": [{"sku": "MTR-304", "name": "Electric Motor 5HP", "quantity": 10, "unit_cost": 489.00}],
            "budget": 1000,
        }
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 400
        assert "budget" in response.json()["detail"]
        assert client.get("/api/restock-orders").json() == []

    def test_create_restock_order_unknown_sku(self, client):
        """Test that an unknown SKU returns 404."""
        payload = {
            "items": [{"sku": "NOPE-999", "name": "Missing", "quantity": 1, "unit_cost": 1.0}],
            "budget": 1000,
        }
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 404

    def test_create_restock_order_empty_items(self, client):
        """Test that an order with no items fails validation."""
        response = client.post("/api/restock-orders", json={"items": [], "budget": 1000})
        assert response.status_code == 422

    def test_create_restock_order_zero_quantity(self, client):
        """Test that a zero quantity line fails validation."""
        payload = {
            "items": [{"sku": "WDG-001", "name": "Industrial Widget Type A", "quantity": 0, "unit_cost": 12.50}],
            "budget": 1000,
        }
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 422
