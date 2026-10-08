import boto3

def lambda_handler(event, context):
    # Créer un client S3
    s3_client = boto3.client('s3')

    # Nom du bucket S3 et clé de l'objet à récupérer
    bucket_name = 'your-bucket-name'
    object_key = 'path/to/your/object.txt'

    try:
        # Récupérer l'objet depuis S3
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read().decode('utf-8')
        print("Contenu de l'objet S3 :", content)

        # Ici, vous pouvez ajouter le code pour traiter le contenu récupéré

    except Exception as e:
        print("Erreur lors de la récupération de l'objet S3 :", e)