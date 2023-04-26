def avg_word_length(sentence):
  words = sentence.split()
  return (sum(len(word) for word in words)/len(words))

def lambda_handler(event, context):
    input = event['output']
    stats = {}
    stats['text_length'] = len(input)
    stats['avg_word_length'] = avg_word_length(input)
    stats['num_digits'] = len([x for x in input.split() if x.isdigit()])
    stats['num_special_chars'] = len([x for x in input.split() if not x.isalnum()])
    return {
        'statusCode': 200,
        'stats': stats,
        'input': input
    }
