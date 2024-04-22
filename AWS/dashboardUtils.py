import boto3
import json
dynamodb = boto3.resource('dynamodb')
client = boto3.client('lambda')

# Initialize an iot client
mqtt = boto3.client('iot-data', region_name='eu-west-2')

def lambda_handler(event, context):
    """
    Given an scanner id, create a virtual basket in the DynamoDB table Baskets.
    Trigger the AWS Lambda function sendBasketIDToScanner to send the virtualbasket identifier basket_id to the scanner.
    
    Inputs:
    -> event['function']: function to run
        - "set_all_baskets_status_to_False"
        - "count_active_baskets"
        - "set_baskets_status_to_False_from_scanner_id"
        - "count_active_baskets_from_scanner_id"
        - "count_articles_in_basket_from_scanner_id"
    

    """
    
    function = event['function']
    count_active_baskets()
    if function == "set_all_baskets_status_to_False":
        set_all_baskets_status_to_False()
    elif function == "count_active_baskets":
        count_active_baskets()
    elif function == "set_baskets_status_to_False_from_scanner_id":
        scanner_id = event['scanner_id']
        set_baskets_status_to_False_from_scanner_id(scanner_id)
    elif function == "count_active_baskets_from_scanner_id":
        scanner_id = event['scanner_id']
        count_active_baskets_from_scanner_id(scanner_id)
    elif function == "count_articles_in_basket_from_scanner_id":
        scanner_id = event['scanner_id']
        count_articles_in_basket_from_scanner_id(scanner_id)    
    
    
    

    return {
        'statusCode': 200,
        'body': 'Status attribute set to False for all items in the Baskets table.'
    }


def set_all_baskets_status_to_False():
    # Connect to DynamoDB
    table = dynamodb.Table('Baskets')

    # Scan all items in the table
    response = table.scan()

    # Update each item to add the 'status' attribute set to False
    for item in response['Items']:
        if 'status' not in item:
            basket_id = item['basket_id']  # Assuming 'id' is the primary key of the table
            response = table.update_item(
                    Key={
                        'basket_id': basket_id
                    },
                    UpdateExpression='SET #s = :val',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={':val': False}
                )
            count_active_baskets()
        elif item['status'] == True:
            basket_id = item['basket_id']  # Assuming 'id' is the primary key of the table
            response = table.update_item(
                    Key={
                        'basket_id': basket_id
                    },
                    UpdateExpression='SET #s = :val',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={':val': False}
                )
            count_active_baskets()
    
def set_baskets_status_to_False_from_scanner_id(scanner_id):
    # Connect to DynamoDB
    table = dynamodb.Table('Baskets')

    # Scan all items in the table
    response = table.scan()

    # Update each item to add the 'status' attribute set to False
    for item in response['Items']:
        if item['scanner_id']==scanner_id:
            if 'status' not in item:
                basket_id = item['basket_id']  # Assuming 'id' is the primary key of the table
                response = table.update_item(
                        Key={
                            'basket_id': basket_id
                        },
                        UpdateExpression='SET #s = :val',
                        ExpressionAttributeNames={'#s': 'status'},
                        ExpressionAttributeValues={':val': False}
                    )
                count_active_baskets()
                count_active_baskets_from_scanner_id
            elif item['status'] == True:
                basket_id = item['basket_id']  # Assuming 'id' is the primary key of the table
                response = table.update_item(
                        Key={
                            'basket_id': basket_id
                        },
                        UpdateExpression='SET #s = :val',
                        ExpressionAttributeNames={'#s': 'status'},
                        ExpressionAttributeValues={':val': False}
                    )
                count_active_baskets()
                count_active_baskets_from_scanner_id(scanner_id)
    
    
def count_active_baskets():
    count = 0
    # Connect to DynamoDB
    table = dynamodb.Table('Baskets')
    # Scan all items in the table
    response = table.scan()

    # Update each item to add the 'status' attribute set to False
    for item in response['Items']:
        if 'status' in item:
            if item['status']:
                count += 1
                
    topic = 'topic/dashboard/count_active_baskets'
    
    response = mqtt.publish(
        topic=topic,
        qos=1,
        payload=json.dumps(count)
    )
    
def count_active_baskets_from_scanner_id(scanner_id):
    count = 0
    # Connect to DynamoDB
    table = dynamodb.Table('Baskets')
    # Scan all items in the table
    response = table.scan()

    # Update each item to add the 'status' attribute set to False
    for item in response['Items']:
        if 'status' in item and item['scanner_id'] == scanner_id:
            if item['status']:
                count += 1
                
    topic = 'topic/dashboard/count_active_baskets_from_scanner_id'
    
    response = mqtt.publish(
        topic=topic,
        qos=1,
        payload=json.dumps(count)
    )
    
def count_articles_in_basket_from_scanner_id(scanner_id):
    
    # Connect to DynamoDB
    table = dynamodb.Table('Baskets')
    # Scan all items in the table
    response = table.scan()
    
    Active_baskets = []
    # Update each item to add the 'status' attribute set to False
    for item in response['Items']:
        if 'status' in item and item['scanner_id'] == scanner_id:
            if item['status']:
                Active_baskets.append([item['basket_id'],item['creation_date']])

                
    latest_creation_date = None
    latest_item_id = None

    for item in Active_baskets:
        item_id, creation_date = item
        if latest_creation_date is None or creation_date > latest_creation_date:
            latest_creation_date = creation_date
            latest_item_id = item_id

    # Get the item from DynamoDB
    response = table.get_item(
        Key={'basket_id': latest_item_id}
    )

    # Check if the item exists and if the attribute is present
    if 'basket_content' in response['Item']:
        # Get the string set attribute
        string_set = response['Item']['basket_content']
        count = len(string_set)
                
        
    else:
        count = 0
        
    topic = 'topic/dashboard/count_articles_in_basket_from_scanner_id'
        
    response = mqtt.publish(
        topic=topic,
        qos=1,
        payload=json.dumps({"n_articles":count,"scanner_id":scanner_id})
    )
    return {
        'statusCode': 200,
        'body': "success"
    }
