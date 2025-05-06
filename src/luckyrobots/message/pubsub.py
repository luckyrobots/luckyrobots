"""
Publisher/subscriber implementation with integrated WebSocket communication.

This module provides Publisher and Subscriber classes for implementing
publisher/subscriber patterns with integrated WebSocket transport for distributed
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
        """Initialize a new publisher.

        Args:
            topic: The topic to publish messages on
            message_type: The type of messages to publish
            queue_size: Maximum queue size for messages
        """
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
        """Clean up when this publisher is garbage collected"""
        with Publisher._lock:
            if self.topic in Publisher._publishers_by_topic:
                if self in Publisher._publishers_by_topic[self.topic]:
                    Publisher._publishers_by_topic[self.topic].remove(self)
                if not Publisher._publishers_by_topic[self.topic]:
                    del Publisher._publishers_by_topic[self.topic]

    def publish(self, message: Any) -> None:
        """Publish a message to all subscribers.

        Args:
            message: The message to publish

        Raises:
            TypeError: If the message is not of the expected type
        """
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
        # wraps this publish method to also publish to the WebSocket transport

    def add_subscriber(self, subscriber: Callable[[Any], None]) -> None:
        """Add a subscriber to the publisher.

        Args:
            subscriber: The subscriber function to add
        """
        if subscriber not in self._subscribers:
            self._subscribers.append(subscriber)
            logger.debug(f"Added subscriber to topic: {self.topic}")

    def remove_subscriber(self, subscriber: Callable[[Any], None]) -> None:
        """Remove a subscriber from the publisher.

        Args:
            subscriber: The subscriber function to remove
        """
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)
            logger.debug(f"Removed subscriber from topic: {self.topic}")

    @classmethod
    def get_publishers_for_topic(cls, topic: str) -> List["Publisher"]:
        """Get all publishers for a specific topic.

        Args:
            topic: The topic to get publishers for

        Returns:
            A list of publishers for the specified topic
        """
        with cls._lock:
            return cls._publishers_by_topic.get(topic, [])

    @classmethod
    def get_all_topics(cls) -> List[str]:
        """Get a list of all available topics.

        Returns:
            A list of all topics with active publishers
        """
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
        """Initialize a new subscriber.

        Args:
            topic: The topic to subscribe to
            message_type: The type of messages to expect
            callback: The function to call when a message is received
            queue_size: Maximum queue size for messages
        """
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
        """Clean up when this subscriber is garbage collected"""
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
        """Connect to all publishers for this topic"""
        publishers = Publisher.get_publishers_for_topic(self.topic)
        for publisher in publishers:
            if publisher.message_type == self.message_type:
                publisher.add_subscriber(self.callback)
                logger.debug(f"Connected to publisher for topic: {self.topic}")

    @classmethod
    def get_subscribers_for_topic(cls, topic: str) -> List["Subscriber"]:
        """Get all subscribers for a specific topic.

        Args:
            topic: The topic to get subscribers for

        Returns:
            A list of subscribers for the specified topic
        """
        with cls._lock:
            return cls._subscribers_by_topic.get(topic, [])
