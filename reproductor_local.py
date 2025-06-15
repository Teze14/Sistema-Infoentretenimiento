import os
import cv2
import pygame
from mutagen.easyid3 import EasyID3
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.button import Button
from datetime import datetime
from mpu6050 import mpu6050
import time

CARPETA_MUSICA = "/home/pi/Music"
pygame.mixer.init()

# --- Configuración del MPU6050 ---
sensor = mpu6050(0x68)
print("Calibrando MPU6050 en reposo...")
time.sleep(2)
_offset = sum(sensor.get_gyro_data()['z'] for _ in range(100)) / 100.0
print(f"Offset yaw: {_offset:.2f} °/s")

_yaw_angle = 0.0
_prev_time = time.time()

# --- KV CODE COMO STRING ---
KV_CODE = '''
#:import os os
#:import ButtonBehavior kivy.uix.behaviors.button.ButtonBehavior

<ImageButton@ButtonBehavior+Image>:
    allow_stretch: True

<PantallaReproductor>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Rectangle:
                pos: self.pos
                size: self.size
                source: 'assets/fondo.jpg'
        BoxLayout:
            size_hint_y: None
            height: "40dp"
            padding: [10, 10, 10, 0]
            Label:
                text: ""
                size_hint_x: 0.8
                color: 0, 0, 0, 0
            Label:
                id: hora
                text: "00:00:00"
                font_size: 24
                halign: "right"
                valign: "middle"
                color: 1, 1, 1, 1
        Label:
            id: info
            text: '🎵 Sin canción'
            font_size: 46
            markup: True
            color: 1, 1, 1, 1
            size_hint_y: 0.2
        BoxLayout:
            size_hint_y: 0.6
            spacing: 20
            padding: 20
            ImageButton:
                source: 'assets/rewind.png'
                on_release: app.rewind()
            ImageButton:
                id: playpause
                source: 'assets/play.png'
                on_release: app.toggle_play()
            ImageButton:
                source: 'assets/next.png'
                on_release: app.siguiente()
            ImageButton:
                source: 'assets/camera.png'
                on_release: app.ir_a_camara()
        Button:
            text: "Volver a selección"
            size_hint_y: 0.1
            on_release: app.ir_a_seleccion()

<PantallaCamara>:
    BoxLayout:
        orientation: 'vertical'
        Image:
            id: cam_view
        Button:
            text: "Volver al reproductor"
            size_hint_y: 0.1
            on_press: app.ir_a_reproductor()

<PantallaSeleccion>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Rectangle:
                pos: self.pos
                size: self.size
                source: 'assets/fondo.jpg'
        Label:
            text: 'Selecciona una Playlist'
            font_size: 32
            size_hint_y: 0.2
            color: 1, 1, 1, 1
        ScrollView:
            BoxLayout:
                id: lista
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: 20
                spacing: 10
'''

# --- CLASES ---
class PantallaSeleccion(Screen):
    def on_pre_enter(self):
        self.ids.lista.clear_widgets()
        carpetas = sorted([f for f in os.listdir(CARPETA_MUSICA) if os.path.isdir(os.path.join(CARPETA_MUSICA, f))])
        for carpeta in carpetas:
            btn = Button(text=carpeta, size_hint_y=None, height=50)
            btn.bind(on_release=lambda btn: self.seleccionar_playlist(btn.text))
            self.ids.lista.add_widget(btn)

    def seleccionar_playlist(self, nombre_playlist):
        app = App.get_running_app()
        carpeta_path = os.path.join(CARPETA_MUSICA, nombre_playlist)
        app.archivos = [f for f in os.listdir(carpeta_path) if f.endswith(".mp3")]
        app.archivos.sort()
        app.carpeta_actual = carpeta_path
        app.indice_actual = 0
        app.sm.current = "reproductor"
        app.cargar_cancion()

class PantallaReproductor(Screen):
    pass

class PantallaCamara(Screen):
    def on_enter(self):
        global _prev_time
        self.captura = cv2.VideoCapture(0)
        _prev_time = time.time()
        Clock.schedule_interval(self.actualizar_camara, 1.0 / 30)

    def on_leave(self):
        Clock.unschedule(self.actualizar_camara)
        self.captura.release()

    def actualizar_camara(self, dt):
        global _yaw_angle, _prev_time
        ret, frame = self.captura.read()
        if not ret:
            return
        h, w = frame.shape[:2]

        ahora = time.time()
        dt_gyro = ahora - _prev_time
        _prev_time = ahora

        z_rate = sensor.get_gyro_data()['z'] - _offset
        _yaw_angle += z_rate * dt_gyro
        px_offset = int(_yaw_angle * 5)

        color = (0, 255, 0)
        thickness = 2
        x1 = int(w * 0.2) + px_offset
        y1 = h
        x2 = int(w * 0.4) + px_offset
        y2 = int(h * 0.5)
        cv2.line(frame, (x1, y1), (x2, y2), color, thickness)
        x3 = int(w * 0.8) + px_offset
        y3 = h
        x4 = int(w * 0.6) + px_offset
        y4 = int(h * 0.5)
        cv2.line(frame, (x3, y3), (x4, y4), color, thickness)
        cv2.line(frame, (x2, y2), (x4, y4), color, thickness)

        buf = cv2.flip(frame, 0).tobytes()
        tex = Texture.create(size=(w, h), colorfmt='bgr')
        tex.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.ids.cam_view.texture = tex

class MusicaApp(App):
    def build(self):
        Builder.load_string(KV_CODE)
        self.sm = ScreenManager()
        self.sm.add_widget(PantallaSeleccion(name="seleccion"))
        self.sm.add_widget(PantallaReproductor(name="reproductor"))
        self.sm.add_widget(PantallaCamara(name="camara"))

        self.archivos = []
        self.carpeta_actual = None
        self.indice_actual = 0
        self.reproduciendo = False
        Clock.schedule_interval(self.actualizar_hora, 1)
        return self.sm

    def ir_a_seleccion(self):
        self.sm.current = "seleccion"

    def on_start(self):
        self.sm.current = "seleccion"

    def actualizar_hora(self, dt):
        hora_actual = datetime.now().strftime("%H:%M:%S")
        pantalla_actual = self.sm.current
        if pantalla_actual == 'reproductor':
            try:
                pantalla = self.sm.get_screen('reproductor')
                if 'hora' in pantalla.ids:
                    pantalla.ids.hora.text = hora_actual
            except Exception as e:
                print("Error al actualizar hora:", e)

    def cargar_cancion(self):
        if not self.archivos:
            return
        archivo = os.path.join(self.carpeta_actual, self.archivos[self.indice_actual])
        pygame.mixer.music.load(archivo)
        try:
            meta = EasyID3(archivo)
            artista = meta.get('artist', ['Desconocido'])[0]
            titulo = meta.get('title', [archivo])[0]
        except:
            artista = "Desconocido"
            titulo = self.archivos[self.indice_actual]
        self.sm.get_screen('reproductor').ids.info.text = f"{titulo} - {artista}"

    def toggle_play(self):
        if self.reproduciendo:
            pygame.mixer.music.pause()
            self.sm.get_screen('reproductor').ids.playpause.source = 'assets/play.png'
        else:
            if pygame.mixer.music.get_pos() > 0:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.play()
            self.sm.get_screen('reproductor').ids.playpause.source = 'assets/pause.png'
        self.reproduciendo = not self.reproduciendo

    def siguiente(self):
        self.indice_actual = (self.indice_actual + 1) % len(self.archivos)
        self.cargar_cancion()
        pygame.mixer.music.play()
        self.sm.get_screen('reproductor').ids.playpause.source = 'assets/pause.png'
        self.reproduciendo = True

    def anterior(self):
        self.indice_actual = (self.indice_actual - 1) % len(self.archivos)
        self.cargar_cancion()
        pygame.mixer.music.play()
        self.sm.get_screen('reproductor').ids.playpause.source = 'assets/pause.png'
        self.reproduciendo = True

    def rewind(self):
        pygame.mixer.music.rewind()

    def ir_a_camara(self):
        self.sm.current = 'camara'

    def ir_a_reproductor(self):
        self.sm.current = 'reproductor'

if __name__ == '__main__':
    MusicaApp().run()
