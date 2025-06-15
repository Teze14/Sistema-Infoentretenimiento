
# ----------- IMPORTS DE LIBRERÍAS -----------
from kivymd.app import MDApp                  # App principal de KivyMD
from kivymd.uix.boxlayout import MDBoxLayout  # Layout en cajas, versión Material Design
from kivymd.uix.label import MDLabel          # Etiquetas (textos) con estilos MD
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFloatingActionButton # Botones Material Design
from kivymd.uix.screen import MDScreen        # Pantalla (Screen) individual
from kivymd.uix.screenmanager import MDScreenManager # Gestor de pantallas
from kivy.uix.image import AsyncImage, Image  # Para mostrar imágenes (locales o por URL)
from kivymd.uix.progressbar import MDProgressBar # Barra de progreso Material Design
from kivy.clock import Clock                  # Para programar tareas periódicas
from kivy.core.window import Window           # Control de ventana principal
from kivy.uix.widget import Widget            # Widget base
from kivy.graphics import Color, Line         # Dibujo de líneas y colores personalizados
from datetime import datetime                 # Para mostrar la hora actual
import spotipy                               # Cliente para la API de Spotify
from spotipy.oauth2 import SpotifyOAuth       # OAuth para autenticar Spotify
from kivy.uix.anchorlayout import AnchorLayout # Layout para anclar widgets en posiciones
from kivymd.uix.behaviors import RectangularRippleBehavior # Efecto ripple
from kivy.uix.behaviors import ButtonBehavior # Permite que otros widgets sean "clickeables"
from functools import partial                 # Para crear funciones parciales (no se usa aquí)
from kivy.app import App                     # App base de Kivy
from kivy.uix.button import Button
import subprocess


# ---------- CLASE PARA BOTÓN DE IMAGEN ----------
class ImageButton(ButtonBehavior, RectangularRippleBehavior, Image):
    # Hereda comportamientos de botón y efecto ripple para una imagen.
    pass

# ----------- SPOTIFY CONFIG (con tus credenciales de app Spotify) -----------
CLIENT_ID = 'f65edd8124a84bdeb94c44db6d763aa6'
CLIENT_SECRET = 'bd212769c3574be19cca094de15b9f48'
REDIRECT_URI = 'http://127.0.0.1:8888'
SCOPE = 'user-modify-playback-state user-read-playback-state user-read-currently-playing'

# Autenticación y cliente Spotify listo para usar
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

# ----------- TOPBAR: BARRA SUPERIOR CON HORA -----------
class TopBar(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'              # Layout horizontal
        self.size_hint_y = None                      # Altura fija
        self.height = 40
        self.padding = (20, 10, 10, 5)               # Espaciado
        self.time_label = MDLabel(                   # Widget para la hora
            text='', halign='left', valign='top', font_style='H6', size_hint=(1, 1)
        )
        Clock.schedule_interval(self.update_time, 1) # Actualizar cada segundo
        self.add_widget(self.time_label)             # Añadir etiqueta a barra

    def update_time(self, *args):
        # Actualiza la hora en pantalla
        self.time_label.text = datetime.now().strftime('%H:%M')

# ----------- BOTÓN PARA VOLVER A LA HOME -----------
class BackButton(MDIconButton):
    def __init__(self, screen, **kwargs):
        super().__init__(**kwargs)
        self.icon = "arrow-left"                     # Icono de flecha
        self.pos_hint = {"right": 1, "y": 0}
        # Cuando se pulsa, cambia la pantalla a 'home'
        self.on_release = lambda: setattr(screen.manager, 'current', 'home')

# ----------- PANTALLA PRINCIPAL (HOME) -----------
class HomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical')
        layout.add_widget(TopBar())                  # Añade la barra superior

        body = MDBoxLayout(orientation='horizontal') # Layout horizontal para contenido

        # Panel izquierdo vacío (espaciador)
        left_panel = MDBoxLayout(orientation='vertical', size_hint_x=0.15, padding=10, spacing=10)
        left_panel.add_widget(Widget())
        body.add_widget(left_panel)

        # Divider: línea vertical separadora
        divider = Widget(size_hint_x=0.02)
        with divider.canvas:
            Color(1, 1, 1, 1)                       # Color blanco
            self.line = Line(points=[0, 0, 0, Window.height], width=1.5)
        def update_line(*_):
            self.line.points = [divider.center_x, 0, divider.center_x, self.height]
        divider.bind(size=update_line, pos=update_line)
        body.add_widget(divider)

        # Panel de botones ONLINE/OFFLINE
        buttons_panel = MDBoxLayout(orientation='horizontal', spacing=80, padding=60)
        for name, icon, screen in [("ONLINE", "wifi", "online"), ("OFFLINE", "wifi-off", "offline")]:
            box = MDBoxLayout(orientation='vertical', spacing=20, size_hint=(None, None), size=(200, 250))
            icon_btn = MDIconButton(icon=icon, icon_size="96sp", pos_hint={"center_x": 0.5})
            # Botón de texto, cambia de pantalla al hacer clic
            btn = MDRaisedButton(text=name, pos_hint={"center_x": 0.5}, on_release=lambda x, s=screen: self.go_to(s))
            box.add_widget(icon_btn)
            box.add_widget(btn)
            buttons_panel.add_widget(box)

        body.add_widget(buttons_panel)
        layout.add_widget(body)
        self.add_widget(layout)

    def go_to(self, screen_name):
        # Cambia de pantalla según el nombre recibido
        self.manager.current = screen_name

class ScreenImageButton(ImageButton):
    def __init__(self, target_screen, **kwargs):
        super().__init__(**kwargs)
        self.target_screen = target_screen
        self.bind(on_release=self.go_to_screen)

    def go_to_screen(self, instance):
        # Obtiene el screen manager a través de la jerarquía de widgets
        screen = self.parent.parent.parent  # Ajusta según tu estructura real
        if hasattr(screen, 'manager'):
            screen.manager.current = self.target_screen
        else:
            print("Error: No se pudo acceder al ScreenManager")

# ----------- PANTALLA ONLINE (con botones de imagen) -----------
class OnlineScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical')
        layout.add_widget(TopBar())  # Reloj y barra superior

        main = MDBoxLayout(orientation='horizontal')

        # --- Panel izquierdo (imágenes sin etiquetas) ---
        left_panel = MDBoxLayout(
            orientation='vertical',
            size_hint_x=0.15,
            padding=10,
            spacing=10,  # Reducimos el espaciado entre imágenes
            pos_hint={'center_x': 0.5}  # Centramos el panel
        )

        # Función para crear imágenes con botones transparentes
        def create_image_button(source, target_screen):
            box = AnchorLayout(
                size_hint=(None, None),
                size=(100, 100)  # Ajustamos el tamaño para más espacio
            )
            img = Image(
                source=source,
                size_hint=(1, 1),
                allow_stretch=True,
                keep_ratio=True  # Mantiene la proporción de la imagen
            )
            btn = Button(
                size_hint=(1, 1),
                background_color=(0, 0, 0, 0),  # Botón transparente
                on_release=lambda x: setattr(self.manager, 'current', target_screen)
            )
            box.add_widget(img)
            box.add_widget(btn)
            return box

        # Botón 1: Mapa (sin etiqueta)
        img_btn1 = create_image_button('img/mapa.png', 'map_screen')
        left_panel.add_widget(img_btn1)

        # Botón 2: Cámara (sin etiqueta)
        img_btn2 = create_image_button('img/camara.png', 'camera_screen')
        left_panel.add_widget(img_btn2)

        main.add_widget(left_panel)

        # --- Línea divisoria (se mantiene igual) ---
        divider = Widget(size_hint_x=0.02)
        with divider.canvas:
            Color(1, 1, 1, 1)
            self.line = Line(points=[0, 0, 0, Window.height], width=1.5)
        def update_line(*_):
            self.line.points = [divider.center_x, 0, divider.center_x, self.height]
        divider.bind(size=update_line, pos=update_line)
        main.add_widget(divider)

        # --- Panel derecho (Spotify) ---
        main.add_widget(SpotifyControl(size_hint_x=0.83))

        # --- Botón de retroceso ---
        layout.add_widget(main)
        layout.add_widget(BackButton(self))
        self.add_widget(layout)

# ----------- PANTALLA OFFLINE (solo texto y back) -----------
class OfflineScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical')
        layout.add_widget(TopBar())
        layout.add_widget(MDLabel(text="Pantalla OFFLINE", halign='center'))
        layout.add_widget(BackButton(self))
        self.add_widget(layout)
        self.reproductor_process = None

    def on_pre_enter(self, *args):
        # Al entrar a la pantalla, abre el reproductor local si no está abierto
        if self.reproductor_process is None or self.reproductor_process.poll() is not None:
            self.reproductor_process = subprocess.Popen(['python3', 'reproductor_local.py'])
            # Si usas Windows y tu archivo es .py: cambia a 'python' en lugar de 'python3'

    def on_leave(self, *args):
        # Opcional: cuando dejas la pantalla, puedes cerrar el reproductor local si quieres
        if self.reproductor_process and self.reproductor_process.poll() is None:
            self.reproductor_process.terminate()
            self.reproductor_process = None


# ----------- CONTROL DE SPOTIFY (Panel con controles y progreso) -----------
class SpotifyControl(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.padding = 20
        self.spacing = 20

        self.album_image = AsyncImage(source='', size_hint=(None, None), size=(300, 300)) # Imagen de álbum

        # Panel derecho para info/canción/controles
        right_panel = MDBoxLayout(orientation='vertical', spacing=20, size_hint=(None, None), size=(500, 400), padding=(10, 10))
        self.song_label = MDLabel(text='Cancion: ---', font_style='H6')
        self.artist_label = MDLabel(text='Artista: ---')
        progress_row = MDBoxLayout(orientation='horizontal', size_hint=(1, None), height=30, spacing=10)
        self.current_time_label = MDLabel(text='0:00', size_hint=(None, 1), width=50)
        self.total_time_label = MDLabel(text='0:00', size_hint=(None, 1), width=50)
        self.progress_bar = MDProgressBar(value=0, max=100)
        progress_row.add_widget(self.current_time_label)
        progress_row.add_widget(self.progress_bar)
        progress_row.add_widget(self.total_time_label)

        controls = MDBoxLayout(orientation='horizontal', spacing=20, size_hint=(None, None), width=260, height=70, pos_hint={"center_x": 0.5})
        prev_btn = MDIconButton(icon="skip-previous", icon_size="64sp", on_release=self.previous_track)
        self.play_pause_btn = MDIconButton(icon="play", icon_size="64sp", on_release=self.toggle_play_pause)
        next_btn = MDIconButton(icon="skip-next", icon_size="64sp", on_release=self.next_track)
        controls.add_widget(prev_btn)
        controls.add_widget(self.play_pause_btn)
        controls.add_widget(next_btn)

        right_panel.add_widget(self.song_label)
        right_panel.add_widget(self.artist_label)
        right_panel.add_widget(progress_row)
        right_panel.add_widget(controls)

        self.add_widget(self.album_image)
        self.add_widget(right_panel)

        self.last_track_id = None
        self.is_playing = False
        Clock.schedule_interval(self.update_song_info, 1) # Actualiza info cada segundo

    # --------- Métodos para controlar Spotify ---------
    def toggle_play_pause(self, instance):
        try:
            playback = sp.current_playback()
            if playback and playback['is_playing']:
                sp.pause_playback()
                self.play_pause_btn.icon = 'play'
                self.is_playing = False
            else:
                sp.start_playback()
                self.play_pause_btn.icon = 'pause'
                self.is_playing = True
        except Exception as e:
            print(f"Error al cambiar estado de reproduccion: {e}")

    def next_track(self, instance):
        try:
            sp.next_track()
            self.update_song_info(0)
        except Exception as e:
            print(f"Error al avanzar cancion: {e}")

    def previous_track(self, instance):
        try:
            sp.previous_track()
            self.update_song_info(0)
        except Exception as e:
            print(f"Error al retroceder cancion: {e}")

    # --------- Actualiza los datos de la canción ----------
    def update_song_info(self, dt):
        try:
            current = sp.current_playback()
            if current and current['item']:
                track = current['item']
                track_id = track['id']
                name = track['name']
                artist = ', '.join([a['name'] for a in track['artists']])
                duration_ms = track['duration_ms']
                progress_ms = current['progress_ms']
                album_images = track['album']['images']
                image_url = album_images[0]['url'] if album_images else ''

                duration_sec = duration_ms // 1000
                progress_sec = progress_ms // 1000

                self.song_label.text = f"Cancion: {name}"
                self.artist_label.text = f"Artista: {artist}"
                self.current_time_label.text = f"{progress_sec // 60}:{progress_sec % 60:02d}"
                self.total_time_label.text = f"{duration_sec // 60}:{duration_sec % 60:02d}"

                self.progress_bar.max = duration_sec
                self.progress_bar.value = progress_sec

                if self.last_track_id != track_id:
                    self.last_track_id = track_id
                    self.album_image.source = image_url
                    self.album_image.reload()

                self.play_pause_btn.icon = 'pause' if current['is_playing'] else 'play'
            else:
                # Si no hay reproducción, muestra valores por defecto
                self.song_label.text = "Cancion: ---"
                self.artist_label.text = "Artista: ---"
                self.current_time_label.text = "0:00"
                self.total_time_label.text = "0:00"
                self.progress_bar.value = 0
                self.album_image.source = ''
                self.last_track_id = None
                self.play_pause_btn.icon = 'play'
        except Exception as e:
            print(f"Error al actualizar info: {e}")

class ScrcpyController(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 20
        self.padding = 20
        self.add_widget(MDLabel(text="Control de Scrcpy (USB)", font_size=24))
        self.toggle_btn = Button(text="Iniciar Scrcpy", size_hint=(1, 0.2))
        self.toggle_btn.bind(on_press=self.toggle_scrcpy)
        self.add_widget(self.toggle_btn)
        self.scrcpy_process = None

    def toggle_scrcpy(self, instance):
        if self.scrcpy_process is None:
           # scrcpy_width = 1000
            try:
                self.scrcpy_process = subprocess.Popen([
                    "scrcpy",
                    "--window-borderless"
                   # "--max-size", str(scrcpy_width)
                ])
                self.toggle_btn.text = "Detener Scrcpy"
            except Exception as e:
                self.add_widget(MDLabel(text=f"Error: {e}"))
        else:
            self.scrcpy_process.terminate()
            self.scrcpy_process = None
            self.toggle_btn.text = "Iniciar Scrcpy"

# ----------- PANTALLA DE MAPA -----------
class MapScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical')
        layout.add_widget(TopBar())
        layout.add_widget(MDLabel(text="Pantalla de Mapa", halign='center'))
        layout.add_widget(ScrcpyController())   # <- Aquí se integra el control de scrcpy
        layout.add_widget(BackButton(self))
        self.add_widget(layout)

# ----------- PANTALLA DE CÁMARA -----------
class CameraScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical')
        layout.add_widget(TopBar())
        layout.add_widget(MDLabel(text="Pantalla de Cámara", halign='center'))
        layout.add_widget(BackButton(self))
        self.add_widget(layout)

# ----------- APP PRINCIPAL (MainApp) -----------
class MainApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"         # Tema oscuro
        self.theme_cls.primary_palette = "Green"    # Paleta principal verde
        Window.clearcolor = (0.07, 0.07, 0.07, 1)   # Color de fondo
        Window.fullscreen = False                    # Ventana en pantalla completa
        Window.size = (1024, 775)  # o el tamaño exacto de tu monitor
        Window.left = 0
        Window.top = 0

        sm = MDScreenManager()                      # Instancia el gestor de pantallas
        sm.add_widget(HomeScreen(name='home'))      # Agrega pantalla Home
        sm.add_widget(OnlineScreen(name='online'))  # Agrega pantalla Online
        sm.add_widget(OfflineScreen(name='offline'))# Agrega pantalla Offline
        sm.add_widget(MapScreen(name='map_screen')) # Agrega pantalla Mapa
        sm.add_widget(CameraScreen(name='camera_screen')) # Agrega pantalla Cámara
        return sm                                   # Retorna el screen manager como raíz de la app

if __name__ == '__main__':
    MainApp().run()                                # Lanza la app


