"""Canonical RabbitMQ exchange, queue, and routing key names."""


class ExchangeNames:
    CRAWL = "nexus.crawl"
    INDEX = "nexus.index"
    EVENTS = "nexus.events"
    DEAD_LETTER = "nexus.dlx"


class QueueNames:
    CRAWL_COMMANDS = "crawl.commands"
    CRAWL_RESULTS = "crawl.results"
    INDEX_REQUESTED = "document.index.requested"
    INDEX_DEAD_LETTER = "document.index.dead-letter"
    OPERATIONAL_EVENTS = "operational.events"


class RoutingKeys:
    INDEX_REQUESTED = "document.index.requested"
    CRAWL_COMMAND = "crawl.command"
    OPERATIONAL = "operational.event"


__all__ = ["ExchangeNames", "QueueNames", "RoutingKeys"]
