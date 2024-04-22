import json
import boto3

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    
    scanner_id = event["scanner_id"]
    basket_id = event["basket_id"]
    
    client = boto3.client('iot-data', region_name='eu-west-2')
    
    topic = f'topic/nutrition_app/SendBasketID/{scanner_id}'
    
    message = {
                "basket_id": basket_id
            }
    
    response = client.publish(
                topic=topic,
                qos=1,
                payload=json.dumps(message)
            )
    
    

    return {
        'statusCode': 200,
        'body': json.dumps("Processed DynamoDB Stream records.")
    }

    
