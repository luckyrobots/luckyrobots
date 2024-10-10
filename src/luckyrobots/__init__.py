from .core import LuckyRobots
from .check_updates import check_updates            
# Expose static methods
start = LuckyRobots.start
send_message = LuckyRobots.send_message
send_commands = LuckyRobots.send_commands
message_receiver = LuckyRobots.message_receiver

# Export the necessary functions and classes
__all__ = ['LuckyRobots', 'start', 'send_message', 'send_commands', 'message_receiver', 'check_updates']