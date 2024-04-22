import json
import boto3

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')
# Initialize an iot client
client = boto3.client('iot-data', region_name='eu-west-2')

def lambda_handler(event, context):
    """
    Given a basket id, get the associated scanner_id.
    Send a string notification to the scanner associated with the scanner id.
    
    Inputs:
    -> event['scanner_id']: unique id of the scanner used by the user.
    -> event['notification']: String message to be displayed on the scanner's screen

    """
    
    ######################################      
    # GET SCANNER_ID FROM BASKET
    ######################################
    if 'notification' in event and 'basket_id' in event:
    
        basket_id = event['basket_id']
        notification_content = event['notification']
    
        # Reference to the DynamoDB table
        table_baskets = dynamodb.Table('Baskets')
        # Reference to the virtual basket
        response = table_baskets.get_item(Key={'basket_id': basket_id})
        # Get the scanner id
        scanner_id = response['Item']['scanner_id']
    
    
    ######################################       
    # SEND NOTIFICATION TO SCANNER
    ######################################
    
        topic = f'topic/nutrition_app/Notification/{scanner_id}'
    
        response = client.publish(
            topic=topic,
            qos=1,
            payload=json.dumps(notification_content)
        )
    
        return {
            'statusCode': 200,
            'body': json.dumps(f"Notification: {notification_content}.")
        }
        
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Required data not found in the event')
        }
    
