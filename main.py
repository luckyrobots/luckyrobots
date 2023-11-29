import time
import redis

POOL = redis.ConnectionPool(host='localhost', port=6379, db=0)

def getVariable(variable_name):
    my_server = redis.Redis(connection_pool=POOL)
    response = my_server.get(variable_name)
    return response

def setVariable(variable_name, variable_value):
    my_server = redis.Redis(connection_pool=POOL)
    my_server.set(variable_name, variable_value)



while True:    
    setVariable("next_move", "w")
    time.sleep(0.1)

    
    


