import boto3
import json
import numpy as np
import simplejson as json

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Initialize a lambda client
client = boto3.client('lambda')

def lambda_handler(event, context):
    """
    Given a basket_id:
    - compute the total nutritional content of the virtual basker in number of days/feature.
    - compute the nutritional defficiencies of the basket
    - generate product recommendations
    - trigger lambda function sendNutritionValuesToScanner with the nutritional content of the basket
    - trigger lambda function sendRecommendationToScanner with the product recommendations
    
    Inputs:
    -> event['basket_id']: basket_id of the virtual basket in the DynamoDB Baskets associated to the scanner.
    """
    
    table_baskets = dynamodb.Table('Baskets')
    table_users = dynamodb.Table('Users')
    
    
    ################### 
    # QUERY BASKETS DB FOR THE CONTENT OF THE VIRTUAL BASKET
    ################### 
    basket_id = event['basket_id']
    
    try:
        response_basket = table_baskets.get_item(Key={'basket_id': basket_id})
    except Exception as e:
        print(e)
         # Send notification to scanner
        response_Lambda = client.invoke(
                        FunctionName='sendUserNotificationToScanner',
                        InvocationType='Event',
                        Payload=json.dumps({
                            'basket_id':basket_id,
                            'notification': "computeNutritionValues Error: invalid basket_id"
                        })
        )
        return {'statusCode': 500, 'body': json.dumps('Error accessing DynamoDB.')}

    if 'Item' not in response_basket or 'basket_content' not in response_basket['Item']:
        print("Basket empty")
        response_Lambda = client.invoke(
                            FunctionName='sendUserNotificationToScanner',
                            InvocationType='Event',
                            Payload=json.dumps({
                                'basket_id':basket_id,
                                'notification': "Basket is empty"
                            })
            )
        return {'statusCode': 200, 'body': json.dumps('Basket empty')}

    # Initialize nutrition sums
    nutrition_sums = {
        "Energy": 0,
        "Fat": 0,
        "Carbohydrates": 0,
        "Proteins": 0,
        "Salt": 0
    }

    # Iterate over each JSON string in the basket_content attribute
    for article_json in response_basket['Item']['basket_content']:
        article = json.loads(article_json)
        # Sum up the values for each nutritional field
        for nutrient in nutrition_sums.keys():
            if nutrient in article:
                nutrition_sums[nutrient] += article[nutrient]
                
    ###################       
    # COMPUTE NUTRITIONAL CONTENT IN NUMBER OF DAYS
    ###################
    # For each nutrition features, compute for how many days can the basket provide nutrition (energy: 5 days...)
    try:
        response_user = table_users.get_item(Key={'user_id': int(response_basket['Item']['user_id'])})
    except Exception as e:
        print(e)
        # Send notification to scanner
        response_Lambda = client.invoke(
                        FunctionName='sendUserNotificationToScanner',
                        InvocationType='Event',
                        Payload=json.dumps({
                            'basket_id':basket_id,
                            'notification': "computeNutritionValues Error: invalid user_id"
                        })
        )
        
        return {'statusCode': 500, 'body': json.dumps('Error accessing DynamoDB.')}
        
    nutrition_daily_targets = response_user['Item']['nutrition_daily_targets']
    
    nutrition_number_of_days = {
        "Energy": 0,
        "Fat": 0,
        "Carbohydrates": 0,
        "Proteins": 0,
        "Salt": 0
    }
    
    for feature in nutrition_number_of_days.keys():
        nutrition_number_of_days[feature] = float(round(nutrition_sums[feature]/float(nutrition_daily_targets[feature]),1))

    
    ###################
    # INVOKA LAMBDA FUNCTIONS TO SEND NUTRITIONAL CONTENT OF BASKET TO SCANNER AND COMPUTE RECOMMANDATIONS 
    ###################

    
    # Invoke lambda function sendNutritionValuesToScanner to send the nutritional content of basket
    response_Lambda = client.invoke(
                    FunctionName='sendNutritionValuesToScanner',
                    InvocationType='Event',
                    Payload=json.dumps({
                        'scanner_id': response_basket['Item']['scanner_id'],
                        'nutrition_content_of_basket':nutrition_number_of_days
                    })
    )
    
    # Invoke lambda function computeRecommendations to send the article recommendations
    response_Lambda = client.invoke(
                    FunctionName='computeRecommendations',
                    InvocationType='Event',
                    Payload=json.dumps({
                        'scanner_id': response_basket['Item']['scanner_id'],
                        'nutrition_number_of_days': nutrition_number_of_days,
                        'nutrition_daily_targets': nutrition_daily_targets
                        
                    })
    )
    
    # Invoke lambda function dashboardUtils to update the dashboard
    response_Lambda = client.invoke(
                    FunctionName='dashboardUtils',
                    InvocationType='Event',
                    Payload=json.dumps({
                        'scanner_id': response_basket['Item']['scanner_id'],
                        'function': "count_articles_in_basket_from_scanner_id"
                        
                    })
    )
    

    return {
        'statusCode': 200,
        'body': json.dumps(nutrition_number_of_days)
    }



def nutrition_loss_function(nutrition_values_recommendation,nutrition_defficiencies,nutrition_daily_targets):
    """
    Loss function evaluating how well a product recommendation compensates the user's basket nutritional defficiencies 
    
    Inputs:
    -> nutrition_values_recommendation (dict): Nutritional content of recommendation
    { 
        "Energy"(float): [kcal],
        "Fat" (float): [g],
        "Carbohydrates" (float): [g],
        "Proteins" (float): [g],
        "Salt" (float): [g]
    }
    -> nutrition_defficiencies (dict): 
    { 
        "Energy" (float): [days],
        "Fat" (float): [days],
        "Carbohydrates" (float): [days],
        "Proteins" (float): [days],
        "Salt" (float): [days]
    }
    -> nutrition_values_recommendation (dict): Daily nutritional needs of user
    { 
        "Energy"(float): [kcal/day],
        "Fat" (float): [g/day],
        "Carbohydrates" (float): [g/day],
        "Proteins" (float): [g/day],
        "Salt" (float): [g/day]
    }
    """
    loss = 0
    for feature in nutrition_values_recommendation.keys():
        loss += (round(float(nutrition_defficiencies[feature])-float(nutrition_values_recommendation[feature])/float(nutrition_daily_targets[feature]),1))**2
  
    return(np.sqrt(loss))
