import json
import boto3

def lambda_handler(event, context):
    
    if 'nutrition_content_of_basket' in event and 'scanner_id' in event :
        nutrition_content = event['nutrition_content_of_basket']
        scanner_id = event['scanner_id']
        
    
        client = boto3.client('iot-data', region_name='eu-west-2')
    
        topic = f'topic/nutrition_app/NutritionInformation/{scanner_id}'
    
        message = {
            "Energy": nutrition_content["Energy"],
            "Fat": nutrition_content["Fat"],
            "Carbohydrates": nutrition_content["Carbohydrates"],
            "Proteins": nutrition_content["Proteins"],
            "Salt": nutrition_content["Salt"]
        }
    
        response = client.publish(
            topic=topic,
            qos=1,
            payload=json.dumps(message)
        )
    
        return {
            'statusCode': 200,
            'body': json.dumps(f"Nutrition Values: {message}.")
        }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Required data not found in the event')
        }
    
