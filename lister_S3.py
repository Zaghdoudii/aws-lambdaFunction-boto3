import boto3


def lambda_handler(event, context):
    # Creer un client S3
    s3 = boto3.client('s3')
    try:
        # Recuperer la liste de tous les buckets S3 disponibles
        response = s3.list_buckets()

        # Afficher les noms de tous les buckets dans la console
        for bucket in response['Buckets']:
            print(bucket['Name'])
    except Exception as e:
        print(e)
