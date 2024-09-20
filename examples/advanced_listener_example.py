import luckyrobots as lr

def main():
    lr.start()  # Start the robot simulation

    lr.send_message([["MOVE 100"]])  
    lr.send_message([["SCAN"]]) 
    lr.send_message([["CHECK_BATTERY"]]) 
    lr.send_message([["EXECUTE_TASK Clean"]])  

    # Simulate an error
    lr.send_message([["INVALID_COMMAND"]]) 

    lr.stop()  # Stop the robot simulation

if __name__ == "__main__":
    main()