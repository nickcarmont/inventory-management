"""
Tests for restocking API endpoints (/api/restock-orders) and
the demand forecast cost fields that drive restock recommendations.
"""
from datetime import datetime, timedelta

import pytest


class TestDemandForecastCosts:
    """Test suite for the cost fields on demand forecast records."""

    def test_demand_forecasts_have_cost_fields(self, client):
        """Test that every forecast record carries unit_cost and lead_time_days."""
        response = client.get("/api/demand")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for forecast in data:
            assert "unit_cost" in forecast
            assert "lead_time_days" in forecast
            assert isinstance(forecast["unit_cost"], (int, float))
            assert isinstance(forecast["lead_time_days"], int)
            assert forecast["unit_cost"] > 0
            assert forecast["lead_time_days"] > 0


class TestCreateRestockOrder:
    """Test suite for POST /api/restock-orders."""

    def test_create_restock_order(self, client):
        """Test submitting a valid restock order."""
        payload = {
            "budget": 2000,
            "items": [
                {"sku": "WDG-001", "quantity": 150},
                {"sku": "GSK-203", "quantity": 10}
            ]
        }
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"].startswith("RST-")
        assert order["status"] == "Submitted"

        # Server recomputes prices from forecast data: 150*12.50 + 10*8.75
        assert abs(order["total_value"] - 1962.50) < 0.01

        # Lead time is the max over ordered items (WDG-001: 7, GSK-203: 10)
        assert order["lead_time_days"] == 10

        # expected_delivery = order_date + lead_time_days
        order_date = datetime.fromisoformat(order["order_date"])
        expected_delivery = datetime.fromisoformat(order["expected_delivery"])
        assert expected_delivery - order_date == timedelta(days=order["lead_time_days"])

    def test_create_restock_order_items_structure(self, client):
        """Test that created order items echo server-side pricing."""
        payload = {"budget": 500, "items": [{"sku": "FLT-405", "quantity": 20}]}
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert len(order["items"]) == 1
        item = order["items"][0]
        assert item["sku"] == "FLT-405"
        assert "name" in item
        assert item["quantity"] == 20
        assert isinstance(item["unit_cost"], (int, float))
        assert abs(item["line_cost"] - item["quantity"] * item["unit_cost"]) < 0.01

    def test_create_restock_order_unknown_sku(self, client):
        """Test that an unknown SKU is rejected."""
        payload = {"budget": 100, "items": [{"sku": "NOPE-999", "quantity": 5}]}
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "NOPE-999" in data["detail"]

    def test_create_restock_order_zero_quantity(self, client):
        """Test that a zero quantity is rejected."""
        payload = {"budget": 100, "items": [{"sku": "WDG-001", "quantity": 0}]}
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_create_restock_order_empty_items(self, client):
        """Test that an empty items list is rejected."""
        payload = {"budget": 100, "items": []}
        response = client.post("/api/restock-orders", json=payload)
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data


class TestGetRestockOrders:
    """Test suite for GET /api/restock-orders."""

    def test_get_restock_orders(self, client):
        """Test that submitted orders appear in the list."""
        payload = {"budget": 1000, "items": [{"sku": "SNR-420", "quantity": 2}]}
        created = client.post("/api/restock-orders", json=payload).json()

        response = client.get("/api/restock-orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        order_numbers = [order["order_number"] for order in data]
        assert created["order_number"] in order_numbers

    def test_restock_orders_do_not_leak_into_orders(self, client):
        """Test that /api/orders is unaffected by submitted restock orders."""
        # Ensure at least one restock order exists
        client.post("/api/restock-orders",
                    json={"budget": 100, "items": [{"sku": "PSU-501", "quantity": 1}]})

        response = client.get("/api/orders")
        assert response.status_code == 200

        for order in response.json():
            assert order["status"].lower() != "submitted"
