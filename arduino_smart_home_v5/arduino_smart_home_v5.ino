#define SWITCH_PIN 7
#define POT_PIN    A0
#define LED_PIN    8
#define BUZZER_PIN 9

unsigned long lastSend = 0;

void setup() {
  Serial.begin(9600);
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  Serial.println("Ready");
}

void loop() {
  // Check commands first (no delay blocking)
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    Serial.print("Got: ");
    Serial.println(cmd);

    if (cmd == "LED_ON") {
      digitalWrite(LED_PIN, HIGH);
      Serial.println("LED ON");
    } else if (cmd == "LED_OFF") {
      digitalWrite(LED_PIN, LOW);
      Serial.println("LED OFF");
   } else if (cmd == "BUZZER_ON") {
      for (int i = 0; i < 3; i++) {
        tone(BUZZER_PIN, 1000); // Phát âm thanh tần số 1000Hz
        delay(300);
        noTone(BUZZER_PIN);     // Tắt âm thanh
        delay(200);
      }
      Serial.println("BUZZER DONE");
    } else if (cmd == "ALL_OFF") {
      digitalWrite(LED_PIN, LOW);
      digitalWrite(BUZZER_PIN, LOW);
      Serial.println("ALL OFF");
    }
  }

  // Send sensor data every 2 seconds
  if (millis() - lastSend >= 2000) {
    lastSend = millis();
    int doorOpen = (digitalRead(SWITCH_PIN) == LOW) ? 1 : 0;
    int lightLevel = map(analogRead(POT_PIN), 0, 1023, 0, 100);
    Serial.print(doorOpen);
    Serial.print(",");
    Serial.println(lightLevel);
  }
}
