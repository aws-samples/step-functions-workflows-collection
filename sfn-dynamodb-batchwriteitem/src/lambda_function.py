import json
import uuid
import random
import os

def generate_dynamic_name():
    adjectives = ['Happy', 'Brave', 'Clever', 'Gentle', 'Sunny', 'Witty', 'Charming']
    nouns = ['Panda', 'Phoenix', 'Whale', 'Butterfly', 'Lion', 'Owl', 'Dolphin']
    adjective = random.choice(adjectives)
    noun = random.choice(nouns)
    return f"{adjective} {noun}"

def generate_random_rating():
    ratings = ['Excellent', 'Good', 'Average', 'Fair', 'Poor']
    return random.choice(ratings)

def lambda_handler(event, context):
    data = []

    for _ in range(51):
        obj = {
            os.environ['unique_id']: str(uuid.uuid4()),
            os.environ['attribute_1']: generate_dynamic_name(),
            os.environ['attribute_2']: generate_random_rating()
        }
        data.append(obj)

    return {
        "Items": data
    }
