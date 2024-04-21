#include <U8glib.h>
#include <DFRobot_GM60.h>
#include <ArduinoBearSSL.h>
#include <ArduinoECCX08.h>
#include <ArduinoMqttClient.h>
#include <WiFiNINA.h> // change to #include <WiFi101.h> for MKR1000
#include "arduino_secrets.h"
#include <ArduinoJson.h>
#include <ArduinoLowPower.h>


U8GLIB_NHD_C12864 u8g(9, 8, 7, 6, 0);  // SPI Com: SCK = 9, MOSI = 8, CS = 7, A0 = 9, RST = 0 ,CD=6
DFRobot_GM60_IIC  gm60;
// SPI Com: SCK = 9, MOSI = 8, CS = 7, CD = 6 , RST = 0


#define KEY_NONE 0
#define KEY_PREV 1
#define KEY_NEXT 2
#define KEY_SELECT 3
#define KEY_LEFT 4
#define KEY_RIGHT 5

//Network setting
const char ssid[]        = SECRET_SSID;
const char pass[]        = SECRET_PASS;
const char broker[]      = SECRET_BROKER;

WiFiClient    wifiClient;            // Used for the TCP socket connection
BearSSLClient sslClient(wifiClient); // Used for SSL/TLS connection, integrates with ECC508
MqttClient    mqttClient(sslClient);


unsigned long lastScanTime = 0; 
const unsigned long scanInterval = 4500; 
volatile unsigned long lastActivityTime;


String barcode_number = "";
String createJsonString(int basket_id, int barcode_number);
String article_name = "";
String scanner_id = "01";
String basket_id = "";
String notification = "";
int scanner_status=0;


#define MENU_ITEMS 7
#define NUTR_ITEMS 5
#define RECO_ITEMS 5
char *menu_strings[MENU_ITEMS] = { "Energy","Fat","Carbohydrates","Protein","Salt"};
char nutrition_strings[NUTR_ITEMS][10];
char *recommend[RECO_ITEMS];
int mode=0 ;   // 0= menu, 1=delete, 2= recommend list

// LCD
uint8_t uiKeyCodeFirst = KEY_NONE;
uint8_t uiKeyCodeSecond = KEY_NONE;
uint8_t uiKeyCode = KEY_NONE;

int adc_key_in;
int key = -1;
int oldkey = -1;


// Convert ADC value to key number
//         4
//         |
//   0 --  1 -- 3
//         |
//         2
int get_key(unsigned int input) {
    if (input < 100) return 0;
    else  if (input < 300) return 1;
    else  if (input < 500) return 2;
    else  if (input < 700) return 3;
    else  if (input < 900) return 4;    
    else  return -1;
}

void uiStep(void) {

  adc_key_in = analogRead(0);  // read the value from the sensor
  key = get_key(adc_key_in);   // convert into key press
  if (key != oldkey)           // if keypress is detected
  {
    delay(50);                   // wait for debounce time
    adc_key_in = analogRead(0);  // read the value from the sensor
    key = get_key(adc_key_in);   // convert into key press
    if (key != oldkey) {
      oldkey = key;
      if (key >= 0) {
        //Serial.println(key);
        if (key == 0)
          uiKeyCodeFirst = KEY_LEFT;
        else if (key == 1)
          uiKeyCodeFirst = KEY_SELECT;
        else if (key == 2)
          uiKeyCodeFirst = KEY_NEXT;
        else if (key == 3)
          uiKeyCodeFirst = KEY_RIGHT;
        else if (key == 4)
          uiKeyCodeFirst = KEY_PREV;
        else
          uiKeyCodeFirst = KEY_NONE;

        uiKeyCode = uiKeyCodeFirst;
      }
    }
  }
  delay(100);
}

uint8_t menu_current = 0;
uint8_t menu_redraw_required = 0;
uint8_t last_key_code = KEY_NONE;

void drawMenu(void) {
  uint8_t i, h;
  u8g_uint_t w, d;

  u8g.setFont(u8g_font_6x12);  //4x6 5x7 5x8 6x10 6x12 6x13
  u8g.setFontRefHeightText();
  u8g.setFontPosTop();

  h = u8g.getFontAscent() - u8g.getFontDescent();
  w = u8g.getWidth();
  for (i = 0; i < MENU_ITEMS; i++) {
    //d = (w - u8g.getStrWidth(menu_strings[i])) / 2;
    u8g.setDefaultForegroundColor();
    if (i == menu_current) {
      u8g.drawBox(0, i * h + 1, w, h);
      u8g.setDefaultBackgroundColor();
    }
    //u8g.drawStr(d, i * h + 1, menu_strings[i]);
    if(i < 5){
      u8g.drawStr(0, i * h + 1, menu_strings[i]);
      if(nutrition_strings[i][0] != '\0'){
        int length = strlen(nutrition_strings[i]);
        char newString[length + 2];
        strcpy(newString, nutrition_strings[i]);
        newString[length] = 'd';
        newString[length+1] = '\0';    
        u8g.drawStr(w-(length+1)*6, i * h + 1, newString);        
      }
    }
  }
  /*
  if(recommend[0]!=""){
      int length = strlen(recommend[0]); 
      char showRecommend[length + 5];   
      strcpy(showRecommend, "buy: ");      
      strcat(showRecommend, recommend[0]);       
      u8g.drawStr(0, 6 * h + 1, showRecommend);
  }
  */
  if(basket_id != ""){ 
    int length = basket_id.length(); 
    char showRecommend[length + 9]; 
    strcpy(showRecommend, "basket: ");
    strcat(showRecommend, basket_id.c_str()); 
    u8g.drawStr(0, 6 * h + 1, showRecommend);
  }
}

void updateMenu(void) {
  switch (uiKeyCode) {
    case KEY_NEXT:
      menu_current++;
      if (menu_current >= MENU_ITEMS) menu_current = 0;
      menu_redraw_required = 1;
      mode=0;
      break;

    case KEY_PREV:
      if (menu_current == 0) menu_current = MENU_ITEMS;
      menu_current--;
      menu_redraw_required = 1;
      mode=0;
      break;

    case KEY_SELECT:   // Delete function
      if(mode==0){
      char *deleteMessage="Scan to remove item";
      showMessage(0,10,deleteMessage);
      mode=1;
      break;   
      };
      if(mode==1){
      menu_redraw_required = 1;
      mode=0;
      break;   
      };
    case KEY_LEFT:  
    case KEY_RIGHT:
        if(mode==0){
        uint8_t i, h;
        h = u8g.getFontAscent() - u8g.getFontDescent();        
          u8g.firstPage();  
          do {
            u8g.setFont(u8g_font_6x12); //
            char* info ="Recommendations";
            u8g.drawStr(0, 0, info); //
            for (i = 0; i <RECO_ITEMS; i++) {
              u8g.drawStr(0, (i+1) * h + 1, recommend[i]);
            };
          } while (u8g.nextPage());
          mode=2;
          break;   
        };
        if(mode==2){
          menu_redraw_required = 1;
          mode=0;
          break;   
        };
  }
  uiKeyCode = KEY_NONE;
}

void showMessage(int x, int y,const char *text) {
    u8g.firstPage();
    do {
        u8g.setFont(u8g_font_6x12); 
        int charWidth = 6; 
        int h = u8g.getFontAscent() - u8g.getFontDescent();

        int currentX = x;
        int currentY = y;

        char word[30]; 
        int wordLength = 0;
        int lineWidth = u8g.getWidth();
        for (int i = 0; text[i] != '\0'; i++) {
            if (text[i] == ' ' || text[i] == '\n') { 
                word[wordLength] = '\0'; 
                int wordWidth = wordLength * charWidth; 
                
                
                if (currentX + wordWidth > lineWidth) {
                    currentX = x; 
                    currentY += h;
                }

                
                u8g.drawStr(currentX, currentY, word);

                
                currentX += wordWidth + charWidth; 

                
                wordLength = 0;
            } else {
              
                word[wordLength++] = text[i];
            }
        }

        
        word[wordLength] = '\0';
        u8g.drawStr(currentX, currentY, word);

    } while (u8g.nextPage());
}



unsigned long getTime() {
  // get the current time from the WiFi module  
  return WiFi.getTime();
}

void connectWiFi() {
  Serial.print("Attempting to connect to SSID: ");
  Serial.print(ssid);
  Serial.print(" ");

  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    // failed, retry
    Serial.print(".");
    delay(5000);
  }
  Serial.println();

  Serial.println("You're connected to the network");
  Serial.println();
}

void connectMQTT() {
  Serial.print("Attempting to MQTT broker: ");
  Serial.print(broker);
  Serial.println(" ");

  while (!mqttClient.connect(broker, 8883)) {
    // failed, retry
    Serial.print(".");
    delay(5000);
  }
  Serial.println();

  Serial.println("You're connected to the MQTT broker");
  Serial.println();

  // subscribe to a topic
  mqttClient.subscribe("topic/nutrition_app/NutritionInformation/01");
  mqttClient.subscribe("topic/nutrition_app/Recommendation/01");
  mqttClient.subscribe("topic/nutrition_app/Notification/01");
  mqttClient.subscribe("topic/nutrition_app/SendBasketID/01");
}


void publish_new_session(String message) {
  Serial.println("Publishing create new session message");
  // send message, the Print interface can be used to set the message contents
  mqttClient.beginMessage("topic/nutrition_app/newSession");
  mqttClient.print(message);
  mqttClient.endMessage();
}

void publish_add_basket(String message) {
  Serial.println("Publishing add message");
  // send message, the Print interface can be used to set the message contents
  mqttClient.beginMessage("topic/nutrition_app/addToBasket");
  mqttClient.print(message);
  mqttClient.endMessage();
}

void publish_remove_basket(String message) {
  Serial.println("Publishing remove message");
  // send message, the Print interface can be used to set the message contents
  mqttClient.beginMessage("topic/nutrition_app/removeFromBasket");
  mqttClient.print(message);
  mqttClient.endMessage();
}



void onMessageReceived(int messageSize) {

  String topic = mqttClient.messageTopic();

  String message;
  while (mqttClient.available()) {
    char c = (char)mqttClient.read();
    message += c;
  }

  StaticJsonDocument<1024> doc;
  DeserializationError error = deserializeJson(doc, message);

  if (topic == "topic/nutrition_app/SendBasketID/01") {
    basket_id = doc["basket_id"].as<String>();
    Serial.println("basket_id:");
    Serial.println(basket_id);
    menu_redraw_required = 1;

  } else if (topic == "topic/nutrition_app/NutritionInformation/01") {

    float nutrition_values[NUTR_ITEMS]; 
    nutrition_values[0] = doc["Energy"];
    nutrition_values[1] = doc["Fat"];
    nutrition_values[2] = doc["Carbohydrates"];
    nutrition_values[3] = doc["Proteins"];
    nutrition_values[4] = doc["Salt"];
    
    // Float to char
    for (int i = 0; i < NUTR_ITEMS; i++) {
        snprintf(nutrition_strings[i], sizeof(nutrition_strings[i]), "%.1f", nutrition_values[i]);
    }

    Serial.println("Finished processing nutrition values");
    menu_redraw_required = 1;

  } else if (topic == "topic/nutrition_app/Notification/01") {
    scanner_status = 0;
    notification = doc.as<String>();
    Serial.println("notification:");
    Serial.println(notification);
    showMessage(0,0,notification.c_str());
    menu_redraw_required = 1;
    delay(3000);

    
  } else if (topic == "topic/nutrition_app/Recommendation/01") {
    Serial.println("Received recommandation values");

    JsonArray articles = doc["Articles"];
    int i = 0;
    for (JsonObject article : articles) {
        if (i < RECO_ITEMS) {
            if (recommend[i] != nullptr) {
                free(recommend[i]);
            }

            String articleName = article["article_name"].as<String>(); 
            char tempBuffer[21]; 
            articleName.toCharArray(tempBuffer, sizeof(tempBuffer)); 
            tempBuffer[20] = '\0'; 

            recommend[i] = strdup(tempBuffer); 
        }
        i++;
    }

    Serial.println("Article Names:");
    for (int i = 0; i < RECO_ITEMS; i++) {
        Serial.println(recommend[i]);
    }
    Serial.println("finished value define");
    menu_redraw_required = 1;
  }
}



void setup() {
  
  u8g.setRot180();           // rotate screen, if required
  menu_redraw_required = 1;  // force initial redraw


  Serial.begin(115200);


  if (!ECCX08.begin()) {
    Serial.println("No ECCX08 present!");
    while (1);
  }

  // Set a callback to get the current time
  // used to validate the servers certificate
  ArduinoBearSSL.onGetTime(getTime);

  // Set the ECCX08 slot to use for the private key
  // and the accompanying public certificate for it
  sslClient.setEccSlot(0, SECRET_CERTIFICATE);
  // mqttClient.setId("clientId");
  mqttClient.onMessage(onMessageReceived);

  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (!mqttClient.connected()) {
    // MQTT client is disconnected, connect
    connectMQTT();
  }
  //Init chip
  gm60.begin();
  //Restore to factory settings
  gm60.reset();

  gm60.encode(gm60.eUTF8);
  
  gm60.setupCode(/*on =*/true,/*content=*/true);
  
  gm60.setIdentify(gm60.eEnableAllBarcode);
  
  Serial.println("Start to recognize");

// Initialise (to create new basket)
  String new_session_message = "{\"scanner_id\":\"01\"}";
  publish_new_session(new_session_message);

  lastActivityTime = millis();

}

void loop() {

  unsigned long currentMillis = millis();
  
  // poll for new MQTT messages and send keep alive
  mqttClient.poll();

// screen 

  uiStep();
  updateMenu(); 
  if (menu_redraw_required != 0) {
    u8g.firstPage();
    do {
      drawMenu();
    } while (u8g.nextPage());
    menu_redraw_required = 0;
  }

 
//  // scanner
  if (currentMillis - lastScanTime > scanInterval) { 
    lastScanTime = currentMillis;
    String barContent= gm60.detection();
    if (barContent != "null" && scanner_status == 0){
      scanner_status = 1; 
      lastActivityTime = millis();
      Serial.print("Detected barcode: ");
      Serial.println(barContent); 
      String message;
      if (mode == 0) { // add function
        message = "{\"basket_id\": " + String(basket_id) + ", \"barcode_number\": \"" + barContent + "\"}";
        publish_add_basket(message);
        Serial.println("Added! barcode:");
        Serial.println(barContent); 

      } else if (mode == 1) { // remove function
        message = "{\"basket_id\": " + String(basket_id) + ", \"barcode_number\": \"" + barContent + "\"}";
        publish_remove_basket(message);
        Serial.println("Removed! barcode:");
        Serial.println(barContent); 
      }
    }
  }
  if (millis() - lastActivityTime > 900000) {  // Free for 15min to sleep
    LowPower.deepSleep();
  }
}
