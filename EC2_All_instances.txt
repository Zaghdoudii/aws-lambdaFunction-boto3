import json
from datetime import datetime, date, timedelta
import boto3

AWS_REGION = 'eu-west-3'
AWS_ACCESS_KEY = 'AKIA3VX54KIZPNJAUEPZ'
AWS_SECRET_KEY = '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'
session = boto3.Session(
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)
s3_client = boto3.client('s3', region_name=AWS_REGION)


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def get_cpu_utilization(instance_id):
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-3')
    total_cpu = 0
    for i in range(30):
        start_time = datetime.utcnow() - timedelta(days=30 - i)
        end_time = datetime.utcnow() - timedelta(days=29 - i)
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
            Statistics=['Average']
        )
        datapoints = response['Datapoints']
        if datapoints:
            average_cpu = datapoints[-1]['Average']
            total_cpu += average_cpu
    if total_cpu == 0:
        return 0
    else:
        return total_cpu / 30


def lambda_handler(event, context):
    ec2_eu_west = boto3.client('ec2', region_name='eu-west-3')
    ce = boto3.client('ce')

    instances = []

    response_eu_west = ec2_eu_west.describe_instances()
    for reservation in response_eu_west["Reservations"]:
        for instance in reservation["Instances"]:
            instance_name = ''
            for tag in instance['Tags']:
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']
            instance_details = {'InstanceId': instance['InstanceId'],
                                'InstanceName': instance_name,
                                'InstanceType': instance['InstanceType'],
                                'State': instance['State']['Name'],
                                'vCPU': instance['CpuOptions']['CoreCount'] * instance['CpuOptions']['ThreadsPerCore'],
                                'OS': instance['Platform'] if 'Platform' in instance else 'Linux/UNIX',
                                'average_cpu': get_cpu_utilization(instance['InstanceId'])}
            # Récupérer le coût de l'instance d'un mois
            cost_response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                    'End': datetime.now().strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=[
                    'AmortizedCost'
                ],
                Filter={
                    'Dimensions': {
                        'Key': 'INSTANCE_TYPE',
                        'Values': [
                            instance_details['InstanceType']
                        ]
                    }
                }
            )
            instance_details['Cost'] = cost_response['ResultsByTime'][0]['Total']['AmortizedCost']['Amount']

            instances.append(instance_details)

    return {
        'statusCode': 200,
        'body': json.loads(json.dumps(instances, cls=MyEncoder))
    }
