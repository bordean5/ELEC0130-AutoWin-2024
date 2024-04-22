import json
import boto3

# Initialize the lambda client
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    """
    Given a barcode number, detect if it is associated with a user or a product.
    If the barcode is a product, trigger lambda function addToBasket.
    If the barcode is a user, trigger lambda function connectUserToBasket.
    
    Inputs:
    -> event['basket_id']: basket_id of the virtual basket in the DynamoDB Baskets associated to the scanner
    -> event["barcode_number"]: barcode_number scanned by the scanner
    """
    
    # Extract barcode number from event
    barcode_number = event["barcode_number"]
    
    # Check if the barcode is for a user
    if barcode_number.startswith('5000000'):
        # If it's a user, trigger connectUserToBasket
        response = lambda_client.invoke(
            FunctionName='connectUserToBasket',
            InvocationType='Event',  # asynchronous invocation
            Payload=json.dumps(event)  # passing the same event to the next lambda
        )
    else:
        # If it's a product, trigger addToBasket
        response = lambda_client.invoke(
            FunctionName='addToBasket',
            InvocationType='Event',  # asynchronous invocation
            Payload=json.dumps(event)  # passing the same event to the next lambda
        )
    
    # Return a response
    return {
        'statusCode': 200,
        'body': json.dumps('Lambda function triggered successfully!')
    }
