const int pulPin = 3;
const int dirPin = 4;
const int enPin  = 5;
const int ledPin = 6;
volatile bool stopFlag = false;
int x;

int stepCount = 0;
unsigned long lastStepTime = 0;
const int totalSteps = 400 * 5;
const int stepDelay = 12000;  // in microseconds

void setup() {
  pinMode(pulPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode( enPin, OUTPUT);
  pinMode(ledPin, OUTPUT);

  digitalWrite(dirPin, LOW);  // 정방향
  digitalWrite( enPin, LOW);    // 드라이버 활성화
  digitalWrite(ledPin, LOW);

  Serial.begin(9600);
}

void loop() {
  
  // 파이썬 코드에서 flag 받아오기 
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == '1') {                 // flag = 1 이 들어오면 불량
      stopFlag = true;                // 모터 stop flag
      digitalWrite( enPin, HIGH);     // 모터 드라이버 비활성화 (모터 정지)
      digitalWrite(ledPin, HIGH);     // LED 켜기
      stepCount = 0;  // 현재 회전 중단

    } else if (cmd == '0') {          // flag = 0 이 들어오면 정상
      stopFlag = false;               // 모터 계속 작동
      digitalWrite( enPin, LOW);      // 모터 드라이버 활성화 (모터 동작)
      digitalWrite(ledPin, LOW);      // LED 끄기

      stepCount = 0;                  // 새 회전 시작
      lastStepTime = micros();
    }
  }


  //모터 회전 처리 (non-blocking)
  if (!stopFlag) {
    unsigned long now = micros();
    if (now - lastStepTime >= stepDelay * 2) {
      digitalWrite(pulPin, HIGH);
      delayMicroseconds(stepDelay);
      digitalWrite(pulPin, LOW);
      lastStepTime = now;
      stepCount++;
      if (stepCount >= totalSteps) stepCount = 0;
    }
  }
}
