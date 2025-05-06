import asyncio
import threading
import logging

logger = logging.getLogger("event_loop")

# Global variables to store the event loop and thread
_event_loop = None
_event_loop_thread = None
_ready_event = threading.Event()


def initialize_event_loop():
    """Initialize the shared event loop in a background thread"""
    global _event_loop, _event_loop_thread

    # If already initialized, return the existing loop
    if _event_loop is not None and _ready_event.is_set():
        return _event_loop

    logger.info("Starting event loop initialization")

    def run_event_loop():
        logger.info("Event loop thread started")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        global _event_loop
        _event_loop = loop

        logger.info("Event loop created, setting ready event")
        _ready_event.set()

        logger.info("Shared event loop running")
        try:
            loop.run_forever()
        finally:
            logger.info("Shared event loop shutting down")
            loop.close()

    # Start the event loop in a background thread
    _event_loop_thread = threading.Thread(target=run_event_loop, daemon=True)
    _event_loop_thread.start()

    # Wait with a longer timeout
    logger.info("Waiting for event loop to be ready")
    success = _ready_event.wait(timeout=10.0)

    if not success:
        logger.error("Failed to initialize shared event loop")
        return None

    logger.info("Event loop successfully initialized")
    return _event_loop


def get_event_loop():
    """Get the shared event loop"""
    if _event_loop is None or not _ready_event.is_set():
        return initialize_event_loop()
    return _event_loop


def run_coroutine(coro, timeout=None):
    """Run a coroutine on the shared event loop"""
    loop = get_event_loop()
    if loop is None:
        raise RuntimeError("Event loop is not initialized")

    future = asyncio.run_coroutine_threadsafe(coro, loop)
    if timeout is not None:
        try:
            return future.result(timeout)
        except asyncio.TimeoutError:
            logger.error(f"Coroutine timed out after {timeout} seconds")
            raise
    return future  # Return the future object when no timeout is specified


def create_task(coro):
    """Create a task on the shared event loop"""
    loop = get_event_loop()
    if loop is None:
        raise RuntimeError("Event loop is not initialized")

    # We need to create a coroutine that will create the task in the event loop
    async def create_task_in_loop():
        return asyncio.create_task(coro)

    # Run this coroutine in the loop
    future = asyncio.run_coroutine_threadsafe(create_task_in_loop(), loop)
    return future


def shutdown_event_loop():
    """Shutdown the event loop"""
    global _event_loop, _event_loop_thread

    if _event_loop is not None:
        logger.info("Shutting down event loop")
        _event_loop.call_soon_threadsafe(_event_loop.stop)
        if _event_loop_thread is not None:
            _event_loop_thread.join(timeout=5.0)

        _event_loop = None
        _event_loop_thread = None
        _ready_event.clear()

        logger.info("Event loop shutdown complete")
