# AWS backend

The backend is an AWS Lambda based cloud web service that concists of 12 Lambda functions, 3 NoSQL Amazon DynamoDB Tables, an EC2 hosted NodeRed Dashboard. It uses AWS IoT rules to enable MQTT communication with the fleet of scanners, and communicates with the OpenFoodFact API to retreive nutritional information about products.

![backend architecture](/images/NutritionApp_V1-5.jpg)


The DynamoDB Baskets tables contains the virtual baskets that are meant to mirror a user's real world basket, store nutritional information about the products it contains, as well as different types of metadata.
It is structured as follows:

![backend architecture](/images/Basket.png)
