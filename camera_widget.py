import cv2
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
import time

class CameraWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.cam_view = Image()
        self.add_widget(self.cam_view)
        self.captura = None
        self._yaw_angle = 0.0
        self._prev_time = time.time()
        self.sensor = None
        self._offset = 0.0

    def start(self):
        from mpu6050 import mpu6050
        try:
            self.sensor = mpu6050(0x68)
            print("Calibrando MPU6050 en reposo...")
            time.sleep(2)
            self._offset = sum(self.sensor.get_gyro_data()['z'] for _ in range(100)) / 100.0
            print(f"Offset yaw: {self._offset:.2f} °/s")
        except Exception as e:
            print(f"Error inicializando MPU6050: {e}")
            self.sensor = None
            self._offset = 0.0
        self.captura = cv2.VideoCapture(0)
        self._prev_time = time.time()
        Clock.schedule_interval(self.actualizar_camara, 1.0 / 30)

    def stop(self):
        Clock.unschedule(self.actualizar_camara)
        if self.captura:
            self.captura.release()
            self.captura = None

    def actualizar_camara(self, dt):
        ret, frame = self.captura.read()
        if not ret:
            return
        h, w = frame.shape[:2]
        ahora = time.time()
        dt_gyro = ahora - self._prev_time
        self._prev_time = ahora
        if self.sensor:
            try:
                z_rate = self.sensor.get_gyro_data()['z'] - self._offset
            except Exception as e:
                print(f"Error leyendo sensor: {e}")
                z_rate = 0.0
        else:
            z_rate = 0.0
        self._yaw_angle += z_rate * dt_gyro
        px_offset = int(self._yaw_angle * 5)

        color = (0, 255, 0)
        thickness = 2
        x1 = int(w * 0.2) + px_offset
        y1 = h
        x2 = int(w * 0.4) + px_offset
        y2 = int(h * 0.5)
        x3 = int(w * 0.8) + px_offset
        y3 = h
        x4 = int(w * 0.6) + px_offset
        y4 = int(h * 0.5)

        cv2.line(frame, (x1, y1), (x2, y2), color, thickness)
        cv2.line(frame, (x3, y3), (x4, y4), color, thickness)
        cv2.line(frame, (x2, y2), (x4, y4), color, thickness)

        buf = cv2.flip(frame, 0).tobytes()
        tex = Texture.create(size=(w, h), colorfmt='bgr')
        tex.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.cam_view.texture = tex
