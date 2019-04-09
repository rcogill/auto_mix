import time
import boto3
import json
import requests
import logging
from tempfile import TemporaryDirectory
import os

import config
import mix_worker

#----------------

def process_s3_file(response):
    '''Process a zip file dropped in the linked S3 bucket

    Inputs:
    - response : A json-formatted message containing information
        about the object to process
    Returns: The receipt handle associated with the queue message 
        that generated the input. Used to remove the message from the 
        queue upon successful processing
    '''

    # Try to parse the queue message and process the object 
    # specified in the message
    try:
        # Read details about the objet from the message
        message_body = json.loads(response['Messages'][0]['Body'])
        s3_key = message_body['Records'][0]['s3']['object']['key']
        receipt_handle = response['Messages'][0]['ReceiptHandle']
        s3 = boto3.client('s3',conf['region']) 
        bucket_name = conf['bucket_name'] 
        #---
        # Download the object, pass to the mix worker, and
        # send the result back to the S3 bucket
        with TemporaryDirectory() as tmp_dir:
            in_filename = s3_key
            full_in_fname = os.path.join(tmp_dir,in_filename)
            s3.download_file(bucket_name, s3_key, full_in_fname)
            out_filename = mix_worker.generate_mix(in_filename, tmp_dir)
            full_out_fname = os.path.join(tmp_dir,out_filename)
            s3.upload_file(full_out_fname, bucket_name, out_filename)
        return receipt_handle
    # If anything fails, return a null value
    # NEED TO LOG FAILURES....
    except:
        return None

#----------------

if __name__ == '__main__':

    # Load the configuration file, which contains details about
    # The AWS instances to use
    config.load_conf()
    conf = config.conf
 
    sqs = boto3.client('sqs', conf['region'])
    queue_url = conf['queue_url'] 

    # Keep polling the queue for jobs to process
    while 1:
        response = sqs.receive_message(QueueUrl=queue_url)
        # If there is a message in the queue, process the object described 
        # in the message
        if 'Messages' in response:
            # Attemp to get the input file, generate the mix, and
            # write the result back to S3
            receipt_handle = process_s3_file(response)
            # Remove the message from the queue if it was successfully processed
            if receipt_handle != None:
                sqs.delete_message(QueueUrl=queue_url,ReceiptHandle=receipt_handle)
            #---
        # if there are no more messages to process, shut down the worker
        else:
            print('Shutting down...')
            response = requests.get('http://169.254.169.254/latest/meta-data/instance-id')
            instance_id = response.text
            #--
            ec2 = boto3.client('ec2',conf['region'])
            #ec2_response = ec2.terminate_instances(InstanceIds=[instance_id], DryRun=False)

        time.sleep(1)