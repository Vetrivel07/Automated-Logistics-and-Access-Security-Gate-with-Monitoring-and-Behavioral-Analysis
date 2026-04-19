#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>
#include <Wire.h>
#include <rgb_lcd.h>
#include <string.h>

#define PIN_RFID_SDA   10
#define PIN_RFID_RST   7

#define PIN_SERVO      3
#define PIN_LED_GREEN  4
#define PIN_LED_RED    5
#define PIN_LED_BLUE   6
#define PIN_BUZZER     8

MFRC522 rfid(PIN_RFID_SDA, PIN_RFID_RST);
Servo gateServo;
rgb_lcd lcd;

// Authorized cards
const char AUTHORIZED_UIDS[][12] = {
  "B3 2B 1C 56",
  "C3 22 E0 56",
  "27 FB C9 06"
};
const int AUTHORIZED_COUNT = 3;

// Simple IN/OUT tracking
const int MAX_TRACKED_USERS = 10;
char trackedUIDs[MAX_TRACKED_USERS][12];
char trackedEvents[MAX_TRACKED_USERS][4];
int trackedCount = 0;

const int SERVO_CLOSED = 0;
const int SERVO_OPEN   = 90;

void setup() {
  Serial.begin(9600);
  SPI.begin();
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);

  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_BLUE, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);

  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_RED, LOW);
  digitalWrite(PIN_LED_BLUE, HIGH);
  digitalWrite(PIN_BUZZER, LOW);

  gateServo.attach(PIN_SERVO);
  gateServo.write(SERVO_CLOSED);

  lcd.begin(16, 2);
  lcd.setRGB(0, 0, 255);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Scan Your Card");
  lcd.setCursor(0, 1);
  lcd.print("Gate: CLOSED");

  delay(100);
}

void loop() {
  // keep same working RFID read pattern
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);

  if (!rfid.PICC_IsNewCardPresent()) {
    delay(50);
    return;
  }

  if (!rfid.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  char uid[12];
  readUID(uid);

  bool allowed = isAuthorized(uid);

  if (allowed) {
    char event[4];
    toggleEvent(uid, event);

    grantAccess(uid, event);
    sendSerialEvent(uid, "allowed", event);
  } else {
    denyAccess(uid);
    sendSerialEvent(uid, "denied", "NONE");
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  delay(1000);
  resetToIdle();
}

void readUID(char* buf) {
  int pos = 0;

  for (byte i = 0; i < rfid.uid.size; i++) {
    byte b = rfid.uid.uidByte[i];
    byte hi = (b >> 4) & 0x0F;
    byte lo = b & 0x0F;

    buf[pos++] = (hi < 10) ? ('0' + hi) : ('A' + hi - 10);
    buf[pos++] = (lo < 10) ? ('0' + lo) : ('A' + lo - 10);

    if (i < rfid.uid.size - 1) {
      buf[pos++] = ' ';
    }
  }

  buf[pos] = '\0';
}

bool isAuthorized(const char* uid) {
  for (int i = 0; i < AUTHORIZED_COUNT; i++) {
    if (strcasecmp(uid, AUTHORIZED_UIDS[i]) == 0) {
      return true;
    }
  }
  return false;
}

void toggleEvent(const char* uid, char* outEvent) {
  for (int i = 0; i < trackedCount; i++) {
    if (strcasecmp(trackedUIDs[i], uid) == 0) {
      if (strcmp(trackedEvents[i], "IN") == 0) {
        strcpy(trackedEvents[i], "OUT");
      } else {
        strcpy(trackedEvents[i], "IN");
      }
      strcpy(outEvent, trackedEvents[i]);
      return;
    }
  }

  if (trackedCount < MAX_TRACKED_USERS) {
    strcpy(trackedUIDs[trackedCount], uid);
    strcpy(trackedEvents[trackedCount], "IN");
    trackedCount++;
  }

  strcpy(outEvent, "IN");
}

void sendSerialEvent(const char* uid, const char* status, const char* event) {
  Serial.print("<{\"uid\":\"");
  Serial.print(uid);
  Serial.print("\",\"status\":\"");
  Serial.print(status);
  Serial.print("\",\"event\":\"");
  Serial.print(event);
  Serial.println("\"}>");
}

void grantAccess(const char* uid, const char* event) {
  gateServo.write(SERVO_OPEN);

  digitalWrite(PIN_LED_GREEN, HIGH);
  digitalWrite(PIN_LED_RED, LOW);
  digitalWrite(PIN_LED_BLUE, LOW);

  tone(PIN_BUZZER, 2000, 150);

  lcd.setRGB(0, 255, 0);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("ACCESS GRANTED");
  lcd.setCursor(0, 1);
  lcd.print(event);
  lcd.print(" ");
  lcd.print(uid);
}

void denyAccess(const char* uid) {
  gateServo.write(SERVO_CLOSED);

  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_RED, HIGH);
  digitalWrite(PIN_LED_BLUE, LOW);

  tone(PIN_BUZZER, 400, 300);

  lcd.setRGB(255, 0, 0);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("ACCESS DENIED");
  lcd.setCursor(0, 1);
  lcd.print(uid);
}

void resetToIdle() {
  gateServo.write(SERVO_CLOSED);

  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_RED, LOW);
  digitalWrite(PIN_LED_BLUE, HIGH);

  lcd.setRGB(0, 0, 255);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Scan Your Card");
  lcd.setCursor(0, 1);
  lcd.print("Gate: CLOSED");
}