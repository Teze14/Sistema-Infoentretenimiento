/* Nombre del archivo: i2c_reto_dist.ino
* Descripción: Implementación de una alerta sonora de proximidad en FreeRTOS
* Autor:Andres Mendez,Jesus Garcia y Hector Castillo
* Versión: 2.3
*/

#include <Arduino.h>
#include <Wire.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>
#include "DHT.h"

// Configuración de pines
#define SLAVE_ADDRESS 0x08
const int trigPin1 = 26, echoPin1 = 25, buzzPin1 = 14;
const int trigPin2 = 13, echoPin2 = 12, buzzPin2 = 32;

// Estructura para datos compartidos
typedef struct {
  float distance1;
  float distance2;
  float temperature;
  bool tempValid;
  SemaphoreHandle_t mutex;
} SharedData;

SharedData sensorData;

// Prototipos
float readUltrasonic(int trigPin, int echoPin);
void distanceTask1(void *pvParameters);
void distanceTask2(void *pvParameters);
//void temperatureTask(void *pvParameters);
void i2cCommTask(void *pvParameters);
int controlBuzzer(int buzzerPin, float distance);
void sendI2CData();

void setup() {
  Serial.begin(9600);
  Wire.begin();

  
  // Configurar pines
  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);
  pinMode(buzzPin1, OUTPUT);
  pinMode(buzzPin2, OUTPUT);

  // Inicializar mutex
  sensorData.mutex = xSemaphoreCreateMutex();
  
  // Crear tareas
  xTaskCreate(distanceTask1, "Distance1", 2048, NULL, 3, NULL);
  xTaskCreate(distanceTask2, "Distance2", 2048, NULL, 3, NULL);
  xTaskCreate(i2cCommTask, "I2C Comm", 2048, NULL, 1, NULL);
}

void loop() {}

// Tarea para sensor ultrasónico 1
void distanceTask1(void *pvParameters) {
  while (1) {
    float distance = readUltrasonic(trigPin1, echoPin1);
    int estado=controlBuzzer(buzzPin1, distance);
    if (xSemaphoreTake(sensorData.mutex, portMAX_DELAY) == pdTRUE) {
      sensorData.distance1 = estado;
      xSemaphoreGive(sensorData.mutex);
    }
    
    // Control de buzzer y debug
    Serial.printf("[Distance1] %.2f cm\n", distance);
    
    
    vTaskDelay(50 / portTICK_PERIOD_MS); // ~20Hz
  }
}

// Tarea para sensor ultrasónico 2
void distanceTask2(void *pvParameters) {
  while (1) {
    float distance = readUltrasonic(trigPin2, echoPin2);
    int estado=controlBuzzer(buzzPin2, distance);
    
    if (xSemaphoreTake(sensorData.mutex, portMAX_DELAY) == pdTRUE) {
      sensorData.distance2 = estado;
      xSemaphoreGive(sensorData.mutex);
    }
    
    // Control de buzzer y debug
    Serial.printf("[Distance2] %.2f cm\n", distance);
    
    
    vTaskDelay(50 / portTICK_PERIOD_MS); // ~20Hz
  }
}

// Tarea para comunicación I2C
void i2cCommTask(void *pvParameters) {
  while (1) {
    sendI2CData();
    vTaskDelay(100 / portTICK_PERIOD_MS); // 10Hz
  }
}

// Función para controlar buzzer
int controlBuzzer(int buzzerPin, float distance) {
  int estado;
  if (distance < 10) { // Muy cerca - tono continuo
    digitalWrite(buzzerPin, HIGH);
    vTaskDelay(50 / portTICK_PERIOD_MS);
    digitalWrite(buzzerPin, LOW);
    vTaskDelay(50 / portTICK_PERIOD_MS);
    estado=3;
  } 
  else if (distance < 20) { // Cerca - tono rápido
    digitalWrite(buzzerPin, HIGH);
    vTaskDelay(100 / portTICK_PERIOD_MS);
    digitalWrite(buzzerPin, LOW);
    vTaskDelay(100 / portTICK_PERIOD_MS);
    estado=2;
  }
  else if (distance < 30) { // Moderado - tono lento
    digitalWrite(buzzerPin, HIGH);
    vTaskDelay(200 / portTICK_PERIOD_MS);
    digitalWrite(buzzerPin, LOW);
    vTaskDelay(300 / portTICK_PERIOD_MS);
    estado=1;
  }
  else { // Silencio
    digitalWrite(buzzerPin, LOW);
    estado=0;
  }
  return estado;
}

// Función para leer sensor ultrasónico
float readUltrasonic(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH);
  float distance = duration * 0.034 / 2;
  
  return (distance > 100) ? 100 : distance;
}

// Función para enviar datos por I2C
void sendI2CData() {
  float d1, d2;
  
  // Obtener copia segura solo de las distancias
  if (xSemaphoreTake(sensorData.mutex, portMAX_DELAY) == pdTRUE) {
    d1 = sensorData.distance1;
    d2 = sensorData.distance2;
    xSemaphoreGive(sensorData.mutex);
  }
  
  // Debug I2C 
  Serial.printf("[I2C] Sending - D1: %.2f, D2: %.2f\n", d1, d2);
  
  // Construir paquete más simple (9 bytes)
  uint8_t buffer[9];
  buffer[0] = 0xAA; // Header
  
  // Convertir floats a bytes de forma segura
  memcpy(&buffer[1], &d1, 4);
  memcpy(&buffer[5], &d2, 4);
  
  // Enviar datos
  Wire.beginTransmission(SLAVE_ADDRESS);
  Wire.write(buffer, 9);
  
  byte error = Wire.endTransmission();
  
  if(error != 0) {
    Serial.print("Error I2C: ");
    switch(error) {
      case 1: Serial.println("Mensaje demasiado largo"); break;
      case 2: Serial.println("NACK en dirección"); break;
      case 3: Serial.println("NACK en datos"); break;
      case 4: Serial.println("Otro error"); break;
    }
  }
}