"""Unit tests for the alert system."""

import pytest

from seismoalert.alerts import (
    Alert,
    AlertManager,
    AlertRule,
    EmailAlert,
    WebhookAlert,
    high_rate_condition,
    large_earthquake_condition,
)
from seismoalert.models import EarthquakeCatalog

pytestmark = pytest.mark.unit


class TestAlertRule:
    def test_evaluate_triggered(self, sample_catalog):
        rule = AlertRule(
            name="Test Rule",
            condition=lambda cat: len(cat) > 5,
            message_template="Found {count} events, max M{max_mag}",
        )
        alert = rule.evaluate(sample_catalog)
        assert alert is not None
        assert isinstance(alert, Alert)
        assert alert.rule_name == "Test Rule"
        assert "10" in alert.message

    def test_evaluate_not_triggered(self, sample_catalog):
        rule = AlertRule(
            name="Never Triggers",
            condition=lambda cat: len(cat) > 1000,
            message_template="Too many events: {count}",
        )
        alert = rule.evaluate(sample_catalog)
        assert alert is None

    def test_evaluate_empty_catalog(self):
        catalog = EarthquakeCatalog()
        rule = AlertRule(
            name="Empty Check",
            condition=lambda cat: len(cat) > 0,
            message_template="Events found: {count}",
        )
        assert rule.evaluate(catalog) is None


class TestConditionFactories:
    def test_large_earthquake_condition_triggered(self, sample_catalog):
        cond = large_earthquake_condition(5.0)
        assert cond(sample_catalog) is True

    def test_large_earthquake_condition_not_triggered(self, sample_catalog):
        cond = large_earthquake_condition(9.0)
        assert cond(sample_catalog) is False

    def test_high_rate_condition_triggered(self, sample_catalog):
        cond = high_rate_condition(5)
        assert cond(sample_catalog) is True

    def test_high_rate_condition_not_triggered(self, sample_catalog):
        cond = high_rate_condition(100)
        assert cond(sample_catalog) is False


class TestAlertManager:
    def test_add_and_evaluate(self, sample_catalog):
        manager = AlertManager()
        manager.add_rule(
            AlertRule(
                name="Big Quake",
                condition=large_earthquake_condition(6.0),
                message_template="Max magnitude: M{max_mag}",
            )
        )
        manager.add_rule(
            AlertRule(
                name="High Rate",
                condition=high_rate_condition(5),
                message_template="{count} events detected",
            )
        )
        alerts = manager.evaluate(sample_catalog)
        assert len(alerts) == 2
        names = {a.rule_name for a in alerts}
        assert "Big Quake" in names
        assert "High Rate" in names

    def test_no_alerts(self, sample_catalog):
        manager = AlertManager()
        manager.add_rule(
            AlertRule(
                name="Impossible",
                condition=lambda cat: False,
                message_template="Never",
            )
        )
        alerts = manager.evaluate(sample_catalog)
        assert alerts == []

    def test_empty_manager(self, sample_catalog):
        manager = AlertManager()
        assert manager.evaluate(sample_catalog) == []


class TestWebhookAlert:
    def test_send_logs(self, sample_catalog, caplog):
        import logging

        with caplog.at_level(logging.INFO):
            webhook = WebhookAlert(webhook_url="https://hooks.example.com/test")
            alert = Alert(rule_name="Test", message="Test message")
            webhook.send(alert)
        assert "Webhook alert" in caplog.text
        assert "Test message" in caplog.text

    def test_webhook_url_stored(self):
        webhook = WebhookAlert(webhook_url="https://hooks.example.com/xyz")
        assert webhook.webhook_url == "https://hooks.example.com/xyz"


class TestEmailAlert:
    def test_send_logs(self, caplog):
        import logging

        with caplog.at_level(logging.INFO):
            email = EmailAlert(recipient="test@example.com")
            alert = Alert(rule_name="Big Event", message="M7.0 detected")
            email.send(alert)
        assert "Email alert" in caplog.text
        assert "test@example.com" in caplog.text

    def test_recipient_stored(self):
        email = EmailAlert(recipient="user@example.com")
        assert email.recipient == "user@example.com"
