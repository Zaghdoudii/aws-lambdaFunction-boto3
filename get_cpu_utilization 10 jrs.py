import boto3
import json
from datetime import datetime, timedelta


def get_cpu_utilization(instance_id):
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-3')
    cpu_utilization = {}
    for i in range(10):
        start_time = datetime.utcnow() - timedelta(days=10 - i)
        end_time = datetime.utcnow() - timedelta(days=9 - i)
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[
                {
                    'Name': 'InstanceId',
                    'Value': instance_id
                },
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=60 * 60 * 24,
            Statistics=['Maximum'],
            Unit='Percent'
        )
        datapoints = response['Datapoints']
        if datapoints:
            average_cpu = datapoints[-1]['Maximum']
            cpu_utilization[start_time.strftime('%Y-%m-%d')] = average_cpu
        else:
            cpu_utilization[start_time.strftime('%Y-%m-%d')] = 'No data'
    return cpu_utilization


instances_ID = []
instances_cpu_utilization = {}
ec2_eu_west = boto3.client('ec2', region_name='eu-west-3')
response_eu_west = ec2_eu_west.describe_instances()
for reservation in response_eu_west["Reservations"]:
    for instance in reservation["Instances"]:
        instance_id = instance['InstanceId']
        instances_ID.append(instance_id)
        instances_cpu_utilization[instance_id] = {'name': instance['Tags'][0]['Value'],
                                                  'utilization': get_cpu_utilization(instance_id)}


def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.loads(json.dumps({
            'instances_cpu_utilization': instances_cpu_utilization
        }))
    }
