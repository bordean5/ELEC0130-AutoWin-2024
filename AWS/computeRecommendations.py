import boto3
import json
import numpy as np

# Initialize a DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Initialize a lambda client
client = boto3.client('lambda')

def lambda_handler(event, context):
    """
    Given a basket's nutrition_number_of_days and its user's nutrition_daily_targets:
    - compute the nutritional defficiencies of the basket
    - generate product recommendations
    
    Given the scanner_id of the scanner associated to the basket
    - trigger lambda function sendRecommendationToScanner with the product recommendations
    
    Inputs:
    -> event['scanner_id']: 
    -> event['nutrition_number_of_days']: 
    -> event['nutrition_daily_targets']: 

    """ 
    scanner_id = event['scanner_id']
    nutrition_number_of_days = event['nutrition_number_of_days']
    nutrition_daily_targets = event['nutrition_daily_targets']
    
    table_articles_for_recommendations = dynamodb.Table('Articles_for_recommendation')
    
    ################### 
    # COMPUTE NUTRITIONAL DEFICIENCIES
    ###################
    nutrition_defficiencies = {
        "Energy": 0,
        "Fat": 0,
        "Carbohydrates": 0,
        "Proteins": 0,
        "Salt": 0
    }
    max_nutrition_number_of_days = max(nutrition_number_of_days.values())
    for feature in nutrition_defficiencies.keys():
        nutrition_defficiencies[feature] = round(max_nutrition_number_of_days-nutrition_number_of_days[feature],1)
        

    ###################
    # Generate article recommendation to meet those deficiencies
    ###################
    
    
    
    response = table_articles_for_recommendations.scan()
    articles = response['Items']
    
    # Calculate loss for each article
    articles_with_loss = []
    for article in articles:
        article_nutrition = {
            "Energy": article.get("Energy", 0),
            "Fat": article.get("Fat", 0),
            "Carbohydrates": article.get("Carbohydrates", 0),
            "Proteins": article.get("Proteins", 0),
            "Salt": article.get("Salt", 0)
        }
        
        loss = nutrition_loss_function(article_nutrition, nutrition_defficiencies, nutrition_daily_targets)
        articles_with_loss.append((article, loss))
    
    # Sort articles by loss and select the top N
    N = 5  # Change N to your desired number of recommendations
    sorted_articles = sorted(articles_with_loss, key=lambda x: x[1])[:N]
    
    # Prepare recommendations format
    recommendations = {
        "Articles": [{"barcode_number": article[0]["barcode_number"], "article_name": article[0]["article_name"]} for article in sorted_articles]
    }
    
    # Invoke lambda function sendRecommendationToScanner to send the article recommendations
    response_Lambda = client.invoke(
                    FunctionName='sendRecommendationToScanner',
                    InvocationType='Event',
                    Payload=json.dumps({
                        'scanner_id': scanner_id,
                        'recommendations':recommendations
                    })
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(recommendations)
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
