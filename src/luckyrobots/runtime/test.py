import time


class Test:
    @staticmethod
    def receiver(func):
        Test.receiver_function = func
        return func

    @staticmethod
    def message_received(message):
        print("Test message_received", message)
        if Test.receiver_function is not None:
            Test.receiver_function(message)
        else:
            print("Test message_received no receiver function")


@Test.receiver
def receiver(message):
    print("receiver ", message)
    pass


while True:
    time.sleep(1)
    Test.message_received("hello from python")
