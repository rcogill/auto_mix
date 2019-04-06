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
    #try:
    if 1:
        message_body = json.loads(response['Messages'][0]['Body'])
        s3_key = message_body['Records'][0]['s3']['object']['key']
        receipt_handle = response['Messages'][0]['ReceiptHandle']
        s3 = boto3.client('s3',conf['region']) 
        bucket_name = conf['bucket_name'] 
        #---
        with TemporaryDirectory() as tmp_dir:
            in_filename = s3_key
            full_in_fname = os.path.join(tmp_dir,in_filename)
            s3.download_file(bucket_name, s3_key, full_in_fname)
            out_filename = mix_worker.generate_mix(in_filename, tmp_dir)
            full_out_fname = os.path.join(tmp_dir,out_filename)
            s3.upload_file(full_out_fname, bucket_name, out_filename)
        return receipt_handle
    #except:
    #    return None

#----------------

if __name__ == '__main__':

    config.load_conf()
    conf = config.conf
 
    sqs = boto3.client('sqs', conf['region'])
    queue_url = conf['queue_url'] 

    while 1:
        response = sqs.receive_message(QueueUrl=queue_url)
        if 'Messages' in response:
            receipt_handle = process_s3_file(response)
            if receipt_handle != None:
                sqs.delete_message(QueueUrl=queue_url,ReceiptHandle=receipt_handle)
            #---

        else:
            print('Shutting down...')
            response = requests.get('http://169.254.169.254/latest/meta-data/instance-id')
            instance_id = response.text
            #--
            ec2 = boto3.client('ec2',conf['region'])
            #ec2_response = ec2.terminate_instances(InstanceIds=[instance_id], DryRun=False)
        time.sleep(1)