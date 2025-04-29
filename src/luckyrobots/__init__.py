from .core import LuckyRobots
from .check_updates import check_updates      
      
# Expose static methods
set_host = LuckyRobots.set_host
start = LuckyRobots.start
send_message = LuckyRobots.send_message
message_receiver = LuckyRobots.message_receiver

# Export the necessary functions and classes
__all__ = ['LuckyRobots', 'set_host', 'start', 'send_message', 'message_receiver', 'check_updates']