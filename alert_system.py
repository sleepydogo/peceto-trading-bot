import requests
import logging
import threading
import pandas as pd
from webpage_capturer import webpage_capturer

logger = logging.getLogger(__name__)

import threading
import requests
import logging

logger = logging.getLogger(__name__)

class AlertSystem:
    def __init__(self, use_telegram=True):
        self.use_telegram = use_telegram
        self.TELEGRAM_TOKEN = "7471140414:AAEUMY3Zj3IRUXB0tQZRAvUnjrbF4qEPnr8"  
        self.CHAT_ID = "-4655509942"
    
    def send_telegram_message(self, message, image_path=None):
        """Envía un mensaje de texto por Telegram en un hilo separado, con opción a incluir una imagen"""
        thread = threading.Thread(target=self._send_telegram_message, args=(message, image_path))
        thread.start()

    def _send_telegram_message(self, text, image_path=None):
        """Método interno para enviar el mensaje y opcionalmente una imagen"""
        print('Send alert ejecutándose en un hilo separado')
        
        # Convertir Timestamp a string si es necesario
        if isinstance(text, pd.Timestamp):
            text = text.strftime("%Y-%m-%d %H:%M:%S")  # Formatear el timestamp

        try:
            # Enviar mensaje de texto
            url = f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": self.CHAT_ID,
                "text": str(text)  # Convertir a string en caso de que haya otros objetos no serializables
            }
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Mensaje enviado por Telegram")
            else:
                logger.error(f"Error al enviar mensaje: {response.json()}")
            
            # Enviar imagen si se proporciona
            if image_path:
                self._send_telegram_image(image_path)
        
        except Exception as e:
            logger.error(f"Error al enviar mensaje por Telegram: {e}", exc_info=True)
    
    def _send_telegram_image(self, image_path):
        """Método para enviar una imagen por Telegram"""
        url = f"https://api.telegram.org/bot{self.TELEGRAM_TOKEN}/sendPhoto"
        
        try:
            with open(image_path, 'rb') as image_file:
                payload = {
                    "chat_id": self.CHAT_ID
                }
                files = {
                    "photo": image_file
                }
                response = requests.post(url, data=payload, files=files)
                
                if response.status_code == 200:
                    logger.info(f"Imagen '{image_path}' enviada correctamente.")
                else:
                    logger.error(f"Error al enviar la imagen: {response.json()}")
        except Exception as e:
            logger.error(f"Error al enviar la imagen por Telegram: {e}", exc_info=True)

# Ejemplo de uso
alert_system = AlertSystem()
# alert_system.send_telegram_message(
#     "🔥 ¡Bienvenido a las señales de Peceto Trading Bot! 🚀\n\n"
#     "📊 *¿Qué es Peceto Trading Bot?*\n"
#     "Es un bot de trading automatizado que analiza el mercado en Binance y envía señales de compra y venta basadas en indicadores técnicos.\n\n"
#     "📈 *Estrategia Utilizada:*\n"
#     "✅ *EMAs (9, 21, 55)* → Cruces entre medias móviles para detectar tendencias.\n"
#     "✅ *RSI (14 períodos)* → Sobrecompra (>70) y sobreventa (<30) para detectar puntos clave.\n"
#     "✅ *MACD* → Identificación de cambios de tendencia.\n"
#     "✅ *Bandas de Bollinger* → Reversiones y volatilidad del mercado.\n"
#     "✅ *ATR* → Análisis de volatilidad para gestionar riesgos.\n\n"
#     "🔔 *¿Cómo funciona?*\n"
#     "📡 Analiza los datos en intervalos de *15 minutos* y detecta oportunidades.\n"
#     "📢 Envía alertas cuando hay una posible operación rentable.\n"
#     "📊 (Opcional) Muestra gráficos para un mejor análisis.\n\n"
#     "💡 *Recuerda:* Las señales no son consejos financieros. Usa gestión de riesgo y opera con responsabilidad.\n\n"
#     "¡Vamos a cazar oportunidades! 🚀📊"
#     , image_path='captura.png'
# )
