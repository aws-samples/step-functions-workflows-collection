
import json 
import math 
import random 


#generate a random int between 2 values
def getRandomInt(min,max):
    min = math.ceil(min)
    max = math.floor(max)
    return math.floor(random.random() * (max - min) + min )

# Sample function with mocks the operation of checking the number of batch jobs needing fan out.
# For demo purposes, it will return a random number between 2 and 10.
def handler(event,context):
    num = getRandomInt(2,10)

    result = {"input": str(num)} 
    return result