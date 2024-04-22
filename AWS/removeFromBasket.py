
import boto3
import json

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')

client = boto3.client('lambda')


def lambda_handler(event, context):
    """
    Given a barcode number, and given a basket_id, remove one of the articles matching the barcode.
    
    Inputs:
    -> event['basket_id']: basket_id of the virtual basket in the DynamoDB Baskets associated to the scanner
    -> event["barcode_number"]: barcode_number of the article scanned by the scanner
    """
    table = dynamodb.Table('Baskets')
    basket_id = event['basket_id']
    barcode_number = event['barcode_number']
    
    

    # Retrieve the current basket item
    response = table.get_item(Key={'basket_id': basket_id})
    if 'Item' not in response:
        response_Lambda = client.invoke(
                            FunctionName='sendUserNotificationToScanner',
                            InvocationType='Event',
                            Payload=json.dumps({
                                'basket_id':basket_id,
                                'notification': "removeFromBasket Error: wrong basket_id"
                            })
            )
        return {'statusCode': 404, 'body': json.dumps('Basket not found.')}
        
        

    basket_content = response['Item'].get('basket_content', [])
    modified_content = []
    barcode_found = False



    # Deserialize JSON strings and check for the barcode_number
    for content in basket_content:
        content_json = json.loads(content)
        if not barcode_found and 'barcode_number' in content_json and content_json['barcode_number'] == barcode_number:
            barcode_found = True
            continue  # Skip adding this item to modified_content to remove it
        modified_content.append(content)
        article_name = content_json['article_name']



    if not barcode_found:
        # Send notification to scanner
        response_Lambda = client.invoke(
                    FunctionName='sendUserNotificationToScanner',
                    InvocationType='Event',
                    Payload=json.dumps({
                        'basket_id':basket_id,
                        'notification': "Article not found in basket."
                    })
        )
        
        return {'statusCode': 200, 'body': json.dumps('Article not found in basket.')}



    # Update or delete the basket_content attribute based on modified_content
    if modified_content:
        # There are remaining items, so update the attribute
        table.update_item(
            Key={'basket_id': basket_id},
            UpdateExpression='SET basket_content = :val',
            ExpressionAttributeValues={':val': modified_content}
        )
    else:
        # No remaining items, delete the attribute
        table.update_item(
            Key={'basket_id': basket_id},
            UpdateExpression='REMOVE basket_content'
        )
    
    # Send notification to scanner
    response_Lambda2 = client.invoke(
                    FunctionName='computeNutritionValues',
                    InvocationType='Event',
                    Payload=json.dumps({
                        'basket_id':basket_id
                    })
    )
        
    # Send notification to scanner
    response_Lambda = client.invoke(
                    FunctionName='sendUserNotificationToScanner',
                    InvocationType='Event',
                    Payload=json.dumps({
                        'basket_id':basket_id,
                        'notification': "Article "+ article_name + " removed from basket."
                    })
    )
    
    
    return {'statusCode': 200, 'body': json.dumps('Basket updated successfully.')}


