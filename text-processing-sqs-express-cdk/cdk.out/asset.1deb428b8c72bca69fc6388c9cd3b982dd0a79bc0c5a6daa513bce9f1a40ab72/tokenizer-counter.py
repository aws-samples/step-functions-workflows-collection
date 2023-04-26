def lambda_handler(event, context):
    input = event['output']
    lowered_string = " ".join(x.lower() for x in input.split())
    lowered_string = lowered_string.replace('[^\w\s]','')
    split_string = lowered_string.split()
    word_count_map = {}
    for word in split_string:
        if word in word_count_map:
            word_count_map[word] += 1
        else:
            word_count_map[word] = 1
    return {
        'statusCode': 200,
        'input': input,
        'word_counts': word_count_map
    }
