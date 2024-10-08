from .core import LuckyRobots

# Expose static methods
start = LuckyRobots.start
send_message = LuckyRobots.send_message
send_commands = LuckyRobots.send_commands
receiver = LuckyRobots.receiver

# Export the necessary functions and classes
__all__ = ['LuckyRobots', 'start', 'send_message', 'send_commands', 'receiver']
