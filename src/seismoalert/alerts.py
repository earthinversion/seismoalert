"""Alert system for earthquake monitoring.

1. Create rules
    ┌──────────────────────────────────────────┐
    │ AlertRule("Large Earthquake",             │
    │   condition=large_earthquake_condition(6.0),│
    │   template="Max magnitude: M{max_mag}")   │
    │                                            │
    │ AlertRule("High Rate",                     │
    │   condition=high_rate_condition(50),        │
    │   template="{count} events detected")      │
    └──────────────────────────────────────────┘
                    │
2. Register with manager
                    │
    ┌──────────────────────────────────────────┐
    │ AlertManager                              │
    │   rules: [rule_1, rule_2]                 │
    └──────────────────────────────────────────┘
                    │
3. Evaluate against catalog
                    │
    ┌──────────────────────────────────────────┐
    │ manager.evaluate(catalog)                 │
    │   → rule_1: condition(catalog) → True     │
    │     → Alert("Large Earthquake", "M7.2")   │
    │   → rule_2: condition(catalog) → False    │
    │     → None (skipped)                      │
    └──────────────────────────────────────────┘
                    │
4. Output: [Alert("Large Earthquake", "M7.2")]
                    │
5. Optionally send via stubs
    │
    WebhookAlert.send(alert)  → logs it
    EmailAlert.send(alert)    → logs it

"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from seismoalert.models import EarthquakeCatalog

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """A triggered alert.

    Attributes:
        rule_name: Name of the rule that triggered the alert.
        message: Formatted alert message.
    """

    rule_name: str
    message: str


@dataclass
class AlertRule:
    """A configurable alert rule.

    Attributes:
        name: Human-readable rule name.
        condition: Callable that takes an EarthquakeCatalog
            and returns True if triggered.
        message_template: Format string for the alert message.
            Receives the catalog as 'catalog'.
    """

    name: str
    condition: Callable[[EarthquakeCatalog], bool]
    message_template: str

    def evaluate(self, catalog: EarthquakeCatalog) -> Alert | None:
        """Evaluate the rule against a catalog.

        Args:
            catalog: Earthquake catalog to check.

        Returns:
            An Alert if the condition is met, None otherwise.
        """
        if self.condition(catalog):
            message = self.message_template.format(
                count=len(catalog),
                max_mag=catalog.max_magnitude,
            )
            return Alert(rule_name=self.name, message=message)
        return None


def large_earthquake_condition(
    min_magnitude: float,
) -> Callable[[EarthquakeCatalog], bool]:
    """Create a condition that triggers when any event exceeds a magnitude threshold.

    Args:
        min_magnitude: Magnitude threshold.

    Returns:
        Condition callable.
    """

    def condition(catalog: EarthquakeCatalog) -> bool:
        return any(eq.magnitude >= min_magnitude for eq in catalog)

    return condition


def high_rate_condition(max_count: int) -> Callable[[EarthquakeCatalog], bool]:
    """Create a condition that triggers when event count exceeds a threshold.

    Args:
        max_count: Maximum event count before triggering.

    Returns:
        Condition callable.
    """

    def condition(catalog: EarthquakeCatalog) -> bool:
        return len(catalog) > max_count

    return condition


@dataclass
class AlertManager:
    """Manages alert rules and evaluates them against earthquake catalogs.

    Attributes:
        rules: List of registered alert rules.
    """

    rules: list[AlertRule] = field(default_factory=list)

    def add_rule(self, rule: AlertRule) -> None:
        """Register an alert rule.

        Args:
            rule: AlertRule to add.
        """
        self.rules.append(rule)

    def evaluate(self, catalog: EarthquakeCatalog) -> list[Alert]:
        """Evaluate all rules against a catalog.

        Args:
            catalog: Earthquake catalog to check.

        Returns:
            List of triggered Alert objects.
        """
        alerts = []
        for rule in self.rules:
            alert = rule.evaluate(catalog)
            if alert is not None:
                alerts.append(alert)
        return alerts


class WebhookAlert:
    """Stub for sending alerts via webhook.

    In a production system, this would POST to a webhook URL.
    Currently logs the payload for demonstration.

    Args:
        webhook_url: Target URL for the webhook.
    """

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, alert: Alert) -> None:
        """Send an alert via webhook (stub).

        Args:
            alert: The alert to send.
        """
        logger.info(
            "Webhook alert [%s]: %s -> %s",
            alert.rule_name,
            alert.message,
            self.webhook_url,
        )


class EmailAlert:
    """Stub for sending alerts via email.

    In a production system, this would send an actual email.
    Currently logs the email content for demonstration.

    Args:
        recipient: Email recipient address.
    """

    def __init__(self, recipient: str):
        self.recipient = recipient

    def send(self, alert: Alert) -> None:
        """Send an alert via email (stub).

        Args:
            alert: The alert to send.
        """
        logger.info(
            "Email alert to %s - Subject: [SeismoAlert] %s - Body: %s",
            self.recipient,
            alert.rule_name,
            alert.message,
        )
