import boto3
import json
import datetime


def get_rds_tarification():
    s3_client = boto3.client('s3', region_name='eu-west-3')
    
    response = s3_client.get_object(Bucket='offlinedata', Key='/tmp/tarifications_RDS.json')
    # Lisez le contenu JSON du fichier
    file_content = response['Body'].read().decode('utf-8')
    json_content = json.loads(file_content)
    
    # Retournez le contenu JSON du fichier
    return json_content


def get_rds_instances():
    rds_client = boto3.client('rds', region_name='eu-west-3')
    response = rds_client.describe_db_instances()
    instances = []
    for db_instance in response['DBInstances']:
        instance_id = db_instance['DBInstanceIdentifier']
        arn = db_instance['DBInstanceArn']
        class_name = db_instance['DBInstanceClass']
        engine = db_instance['Engine']
        ca_certificate_identifier = db_instance.get('CACertificateIdentifier', 'N/A')
        storage_type = db_instance['StorageType']
        
        instance = {
            'CACertificateIdentifier': ca_certificate_identifier,
            'DBInstanceArn': arn,
            'DBInstanceIdentifier': instance_id,
            'DBInstanceClass': class_name,
            'Engine': engine,
            'StorageType': storage_type,
        }
        instances.append(instance)
    return instances


def get_rds_cpuutilisation(dbInstanceIdentifier):
    cloudwatch_client = boto3.client('cloudwatch', region_name='eu-west-3')
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=30)
    
    response = cloudwatch_client.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'cpuUtilization',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': 'CPUUtilization',
                        'Dimensions': [
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': dbInstanceIdentifier
                            }
                        ]
                    },
                    'Period': 86400,
                    'Stat': 'Average'
                },
                'ReturnData': True
            }
        ],
        StartTime=start_time,
        EndTime=end_time
    )
    
    daily_cpu_usage = []
    for i, average_value in enumerate(response['MetricDataResults'][0]['Values']):
        daily_cpu_usage.append(average_value)
    
    if len(daily_cpu_usage) != 0:
        cpu_average = sum(daily_cpu_usage) / len(daily_cpu_usage)
    else:
        cpu_average = 0
    return cpu_average


def get_rds_memory(dbInstanceIdentifier):
    cloudwatch_client = boto3.client('cloudwatch', region_name='eu-west-3')
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=30)
    
    response = cloudwatch_client.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'freeableMemory',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': 'FreeableMemory',
                        'Dimensions': [
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': dbInstanceIdentifier
                            }
                        ]
                    },
                    'Period': 86400,
                    'Stat': 'Average'
                },
                'ReturnData': True
            }
        ],
        StartTime=start_time,
        EndTime=end_time
    )
    
    daily_memory_usage = []
    for i, average_value in enumerate(response['MetricDataResults'][0]['Values']):
        daily_memory_usage.append(average_value / (1024 * 1024))
    
    if len(daily_memory_usage) != 0:
        cpu_average = sum(daily_memory_usage) / len(daily_memory_usage)
    else:
        cpu_average = 0
    return cpu_average


def get_cost_saving(c1, c2):
    c1 = float(c1)
    c2 = float(c2)
    return (100 * abs(c1 - c2)) / max(c1, c2)


def get_recommendation(instanceclass, cost, vcpu, engine):
    recommendation = []
    x = get_rds_cpuutilisation(instanceclass)
    tarification = get_rds_tarification()
    if x < 50 and x != 0:
        for element in tarification:
            if element["VCPU"] < vcpu and element["Engine"].lower() == engine.lower():
                classinstance = element["Instance Class"]
                cpu = element["VCPU"]
                cout = get_cost_saving(element["Price per hour"], cost)
                dic = {
                    "Instance class": classinstance,
                    "Instance VCPU": cpu,
                    "Cost Saving": cout
                }
                recommendation.append(dic)
    
    return recommendation


def lambda_handler(event, context):
    recommendation = {}
    tarification = get_rds_tarification()
    rdsInstances = get_rds_instances()
    cout = 0
    vcpu = ''
    
    for element in rdsInstances:
        instancename = element["DBInstanceIdentifier"]
        instanceclass = element["DBInstanceClass"]
        if element["Engine"].lower() in ["postegres", "mysql", "mariadb", "aurora mysql", "aurora"]:
            engine = element["Engine"].lower()
        elif element["StorageType"].lower() in ["postegres", "mysql", "mariadb", "aurora mysql", "aurora"]:
            engine = element["StorageType"].lower()
        else:
            engine = "d"
            
        for tarif in tarification:
            if tarif["Instance Class"] == instanceclass:
                vcpu = tarif["VCPU"]
                cout = tarif["Price per hour"]
        
        if vcpu == 1:
            recommendation[instancename] = []
        else:
            recommendation[instancename] = get_recommendation(instanceclass, cout, vcpu, engine)
    
    return recommendation
