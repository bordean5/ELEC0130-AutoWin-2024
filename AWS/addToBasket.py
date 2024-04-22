import boto3
import json
import requests
from datetime import datetime


# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')

client = boto3.client('lambda')

def lambda_handler(event, context):
    """
    Given an item barcode number query its informations (name, nutritional features...).
    Given a basket_id, add the item and its informations to the virtual basket associated with the scanner.
    
    Inputs:
    -> event['basket_id']: basket_id of the virtual basket in the DynamoDB Baskets associated to the scanner
    -> event["barcode_number"]: barcode_number of the item scanned by the scanner

    
    """
    
    # Reference to the DynamoDB table
    table = dynamodb.Table('Baskets')
    
    # Assume basket_id is passed in the event object
    basket_id = event['basket_id']
    
    # New attribute and its value you want to add
    barcode_number = event['barcode_number']
    
    # Get the current date in YYYY-MM-DD format
    scan_date = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    
    ###############################
    # TODO : 
    # -> query an API or a database to get the article name and its properties 
    # -> format the properties to be added as a JSON 
    
    data = requests.get(f"https://world.openfoodfacts.net/api/v2/product/5020364010144?fields=product_name,nutriments,quantity")
    if data.status_code == 200:
        d = data.json()
        #print (d)
        product = d.get('product', {})
        article_name = product.get("product_name",'')
        quantity = product.get('quantity', '')
        nutriments = product.get('nutriments', {})
        print(product)
        quantity_g = 0
        try:
            quantity_g = float(quantity.replace('g', '').strip())
        except Exception as e:
             # Send notification to scanner
            response_Lambda = client.invoke(
                            FunctionName='sendUserNotificationToScanner',
                            InvocationType='Event',
                            Payload=json.dumps({
                                'basket_id':basket_id,
                                'notification': "addToBasket Error: Error converting quantity " + str(e)
                            })
            )
            print('Error converting quantity:', e)
        
        total_nutriments = {}
        #if quantity_g:
        for key, value in nutriments.items():
            if key.endswith('_100g'):
                nutriments_per_100g = value
                total_nutriments[key] = nutriments_per_100g
    
        total_energy = total_nutriments.get('energy-kcal_100g', 'Unknown')/100 * quantity_g
        total_fat = total_nutriments.get('fat_100g', 'Unknown')/100 * quantity_g
        total_carbohydrates = total_nutriments.get('carbohydrates_100g', 'Unknown')/100 * quantity_g
        total_proteins = total_nutriments.get('proteins_100g', 'Unknown')/100 * quantity_g
        total_salt = total_nutriments.get('salt_100g', 'Unknown')/100 * quantity_g
        
        energy = total_energy
        fat = total_fat
        carbohydrates = total_carbohydrates
        proteins = total_proteins
        salt = total_salt
    
    ###############################
        new_content = json.dumps({
            "barcode_number":barcode_number,
            "article_name":article_name,
            "Energy":energy,
            "Fat":fat,
            "Carbohydrates":carbohydrates,
            "Proteins":proteins,
            "Salt":salt,
            "scan_date":scan_date 
        })
        
        try:
            # Update the item in DynamoDB to add a new element to the 'basket_content' string set
            response = table.update_item(
                Key={
                    'basket_id': basket_id
                },
                UpdateExpression="ADD basket_content :new_content",
                ExpressionAttributeValues={
                    ':new_content': {new_content}
                },
                ReturnValues="UPDATED_NEW"
            )
        except Exception as e:
            error = json.dumps({"error":str(e)})
            return {'statusCode': 500, 'body': error}
    
    
        
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
                            'notification': "Article "+ article_name + " added to basket."
                        })
        )
        
    else: 
         # Send notification to scanner
        response_Lambda = client.invoke(
                        FunctionName='sendUserNotificationToScanner',
                        InvocationType='Event',
                        Payload=json.dumps({
                            'basket_id':basket_id,
                            'notification': "API Error."
                        })
        )
        
    
    return {
        'statusCode': 200,
        'body': new_content
        
    }
