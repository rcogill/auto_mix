import os
import json
import boto3

def lambda_handler(event, context):
    
    sqs = boto3.client('sqs')
    queue_url = os.environ['QUEUE_URL']
    
    #----
    # Get the number of messages already in the queue
    num_message = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    
    try:
        q_len = int(num_message["Attributes"]["ApproximateNumberOfMessages"])
    except: 
        q_len = 0

    #----
    # Queue the event info, which contains the input file name
    response = sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageBody=(json.dumps(event))
    )

    #----
    # Return
    return {
        'statusCode': 200,
        'body': 'Success'
    }
