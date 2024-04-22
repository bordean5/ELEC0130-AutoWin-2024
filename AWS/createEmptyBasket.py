import boto3
from datetime import datetime
import uuid
import json

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Initialize a lambda client
client = boto3.client('lambda')

# Initialize an iot client
mqtt = boto3.client('iot-data', region_name='eu-west-2')


def lambda_handler(event, context):
    """
    Given an scanner id, create a virtual basket in the DynamoDB table Baskets.
    Trigger the AWS Lambda function sendBasketIDToScanner to send the virtualbasket identifier basket_id to the scanner.
    
    Inputs:
    -> event['scanner_id']: unique id of the scanner used by the user.

    """
    
    # Reference to the DynamoDB table
    table = dynamodb.Table('Baskets')

    # Get the id of the scanner used by the user
    scanner_id = event["scanner_id"]
    
    # Generate a unique basket_id
    basket_id = generate_unique_basket_id(table)

    # Get the current date in YYYY-MM-DD format
    creation_date = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    
    # Get user_id from the event, default to 0 if not provided
    user_id = event.get('user_id', 0)
    
    active = True
    
    
    # Create a new item in the DynamoDB table
    response_DB = table.put_item(
        Item={
            'basket_id': basket_id,
            'creation_date': creation_date,
            'scanner_id':scanner_id,
            'user_id': user_id,
            'status': active

        }
    )

    # Send basket_id back to scanner
    response_Lambda = client.invoke(
                    FunctionName='sendBasketIDToScanner',
                    InvocationType='Event',
                    Payload=json.dumps({
                        'scanner_id':scanner_id,
                        'basket_id': basket_id
                    })
    )

    # Update dashboard
    topic = 'topic/dashboard/Utils'
    
    response = mqtt.publish(
        topic=topic,
        qos=1,
        payload=json.dumps({"function":"count_active_baskets"})
    )
    return {
        'statusCode': 200,
        'body': f"Basket with ID {basket_id} created successfully"
        
    }


def generate_unique_basket_id(table):
    var = True
    while var:
        # Generate a potential unique basket_id using uuid
        basket_id = int(uuid.uuid4().int & (1<<32)-1)  # Generates a random integer
        
        # Check if this basket_id already exists in the table
        response = table.get_item(
            Key={
                'basket_id': basket_id
            }
        )
        
        # If the basket_id does not exist, it's unique, and we can use it
        if 'Item' not in response:
            var = False
            return basket_id
