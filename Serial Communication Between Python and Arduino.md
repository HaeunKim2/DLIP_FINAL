#  Serial Communication Between Python and Arduino

**Author:** Haeun Kim

**Date:** 2025-06-04

## Setting

**Python-side:** Sends flag values to the serial port using the `pyserial` library. 

**Arduino-side:** Receives and parses the serial input. 

**Serial Baudrate:** 9600 bps

**Port:** Check on the Arduino "COM5"



## Installation

  The `pyserial` library is required to enable serial communication between the Python script and the Arduino board. It allows the Python program to send and receive data through the computer's serial (COM) port.

```bash
pip install pyserial
```



## Code

### Python

This code sends a binary flag (`0` or `1`) to the Arduino via serial communication to simulate control signals for testing motor and LED responses.

```python
import serial
import time

# 아두이노 연결된 포트로 수정 (Windows: 'COMx', mac/Linux: '/dev/ttyUSBx')
ser = serial.Serial('COM5', 9600)
time.sleep(2)  # 아두이노 초기화 대기

# 테스트용 flag 값 순환 전송
flag = 0

for i in range (1, 20):
    if i > 10 and i <= 15:
        flag = 1
    else:
        flag = 0
        
    ser.write(str(flag).encode())
    print(f"Sent flag: {flag}")
    time.sleep(1)
```



### Arduino

This code receives a binary flag from Python via serial communication and controls a LED accordingly: turning it on when the flag is `'1'` (indicating a fault) and off when the flag is `'0'` (indicating normal operation).

```idl
volatile bool stopFlag = false;
const int ledPin = 6;

void setup() {
  Serial.begin(9600);
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);
}

void loop() {
  // 파이썬 코드에서 flag 받아오기 
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == '1') {         // flag = 1 이 들어오면 불량
      stopFlag = true;       // 모터 stop flag
      digitalWrite(ledPin, HIGH); // Red LED 켜기
    } else if (cmd == '0') {  // flag = 0 이 들어오면 정상
      stopFlag = false;        // 모터 계속 작동
      digitalWrite(ledPin, LOW); // Red LED 끄기
    }
  }
}
```

