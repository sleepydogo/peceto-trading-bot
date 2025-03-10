from selenium import webdriver
import time

class WebPageCapture:
    def __init__(self, html_file, output_path="captura.png", window_size="1200x800"):
        """
        Inicializa el capturador de la página web.
        
        Args:
            html_file (str): Ruta al archivo HTML local.
            output_path (str): Ruta donde se guardará la captura.
            window_size (str): Tamaño de la ventana para la captura (ej. "1200x800").
        """
        self.html_file = html_file
        self.output_path = output_path
        self.window_size = window_size

    def capture(self):
        """
        Captura la página web y la guarda como imagen.
        """
        # Configurar opciones para Chrome
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Modo sin interfaz gráfica
        options.add_argument(f"--window-size={self.window_size}")  # Tamaño de la ventana

        # Inicializar el navegador
        driver = webdriver.Chrome(options=options)

        try:
            # Abrir el archivo HTML en el navegador
            driver.get(f"file:///{self.html_file}")
            
            # Esperar a que cargue la página (ajusta el tiempo si es necesario)
            time.sleep(3)

            # Capturar la pantalla y guardarla
            driver.save_screenshot(self.output_path)
            print(f"Captura guardada como '{self.output_path}'")
        
        finally:
            # Cerrar el navegador
            driver.quit()

# webpage_capturer = WebPageCapture()
# webpage_capturer.capture() # Inicializamos el servicio con una captura del estado actual 
