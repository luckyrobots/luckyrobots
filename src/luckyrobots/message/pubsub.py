"""
Publisher/subscriber implementation with WebSocket transport.

This module provides Publisher and Subscriber classes for implementing
publisher/subscriber patterns with WebSocket transport for distributed
communication.
"""

import logging
import threading
from typing import Any, Callable, Dict, List, Type

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pubsub")


class Publisher:
    # Class dictionary to keep track of all publishers by topic
    _publishers_by_topic: Dict[str, List["Publisher"]] = {}
    _lock = threading.RLock()

    def __init__(self, topic: str, message_type: Type, queue_size: int = 10):
        self.topic = topic
        self.message_type = message_type
        self.queue_size = queue_size
        self._subscribers: List[Callable[[Any], None]] = []

        # Register this publisher in the class dictionary
        with Publisher._lock:
            if topic not in Publisher._publishers_by_topic:
                Publisher._publishers_by_topic[topic] = []
            Publisher._publishers_by_topic[topic].append(self)

        logger.debug(f"Created publisher for topic: {topic}")

    def __del__(self):
        """Delete the publisher"""
        with Publisher._lock:
            if self.topic in Publisher._publishers_by_topic:
                if self in Publisher._publishers_by_topic[self.topic]:
                    Publisher._publishers_by_topic[self.topic].remove(self)
                if not Publisher._publishers_by_topic[self.topic]:
                    del Publisher._publishers_by_topic[self.topic]

    def publish(self, message: Any) -> None:
        # Type check the message
        if not isinstance(message, self.message_type):
            raise TypeError(
                f"Expected message of type {self.message_type.__name__}, got {type(message).__name__}"
            )

        # Publish to all local subscribers
        for subscriber in self._subscribers:
            try:
                subscriber(message)
            except Exception as e:
                logger.error(
                    f"Error in subscriber callback for topic {self.topic}: {e}"
                )

        # Note: Remote publishing is handled by the Node class, which
        # wraps this publish method to publish to the WebSocket transport

    def add_subscriber(self, subscriber: Callable[[Any], None]) -> None:
        """Add a subscriber to the publisher"""
        if subscriber not in self._subscribers:
            self._subscribers.append(subscriber)
            logger.debug(f"Added subscriber to topic: {self.topic}")

    def remove_subscriber(self, subscriber: Callable[[Any], None]) -> None:
        """Remove a subscriber from the publisher"""
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)
            logger.debug(f"Removed subscriber from topic: {self.topic}")

    @classmethod
    def get_publishers_for_topic(cls, topic: str) -> List["Publisher"]:
        """Get all publishers for a given topic"""
        with cls._lock:
            return cls._publishers_by_topic.get(topic, [])

    @classmethod
    def get_all_topics(cls) -> List[str]:
        """Get all topics"""
        with cls._lock:
            return list(cls._publishers_by_topic.keys())


class Subscriber:
    # Class dictionary to keep track of all subscribers
    _subscribers_by_topic: Dict[str, List["Subscriber"]] = {}
    _lock = threading.RLock()

    def __init__(
        self,
        topic: str,
        message_type: Type,
        callback: Callable[[Any], None],
        queue_size: int = 10,
    ):
        self.topic = topic
        self.message_type = message_type
        self.callback = callback
        self.queue_size = queue_size

        # Find publishers for this topic and subscribe
        self._connect_to_publishers()

        # Register this subscriber in the class dictionary
        with Subscriber._lock:
            if topic not in Subscriber._subscribers_by_topic:
                Subscriber._subscribers_by_topic[topic] = []
            Subscriber._subscribers_by_topic[topic].append(self)

        logger.debug(f"Created subscriber for topic: {topic}")

    def __del__(self):
        """Delete the subscriber"""
        # Unsubscribe from all publishers
        publishers = Publisher.get_publishers_for_topic(self.topic)
        for publisher in publishers:
            publisher.remove_subscriber(self.callback)

        # Remove from class dictionary
        with Subscriber._lock:
            if self.topic in Subscriber._subscribers_by_topic:
                if self in Subscriber._subscribers_by_topic[self.topic]:
                    Subscriber._subscribers_by_topic[self.topic].remove(self)
                if not Subscriber._subscribers_by_topic[self.topic]:
                    del Subscriber._subscribers_by_topic[self.topic]

    def _connect_to_publishers(self) -> None:
        """Connect to all publishers for a given topic"""
        publishers = Publisher.get_publishers_for_topic(self.topic)
        for publisher in publishers:
            if publisher.message_type == self.message_type:
                publisher.add_subscriber(self.callback)

    @classmethod
    def get_subscribers_for_topic(cls, topic: str) -> List["Subscriber"]:
        """Get all subscribers for a given topic"""
        with cls._lock:
            return cls._subscribers_by_topic.get(topic, [])
