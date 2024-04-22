import boto3
import json

def lambda_handler(event, context):
    
    if 'recommendations' in event and 'scanner_id' in event:
        
        recommendations_content = event['recommendations']
        scanner_id = event['scanner_id']
    
        client = boto3.client('iot-data', region_name='eu-west-2')
    
        topic = f'topic/nutrition_app/Recommendation/{scanner_id}'
    
        response = client.publish(
            topic=topic,
            qos=1,
            payload=json.dumps(recommendations_content)
        )
    
        return {
            'statusCode': 200,
            'body': json.dumps(f"Recommendations: {recommendations_content}.")
        }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Required data not found in the event')
        }
