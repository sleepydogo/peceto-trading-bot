import time
import numpy as np
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging
from datetime import datetime, timedelta
from tabulate import tabulate
from chart_module import TradingChart
import telegram_send
from alert_system import alert_system
from webpage_capturer import webpage_capturer
from decouple import config

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='prediction_bot.log'
)
logger = logging.getLogger('prediction_bot')

class PecetoPredictor:
    def __init__(self, api_key, api_secret, symbol='BTCUSDT', interval='15m', 
                 ema_short=9, ema_medium=21, ema_long=55, rsi_period=14, 
                 rsi_oversold=30, rsi_overbought=70, use_telegram=False, 
                 show_chart=True):
        """
        Inicialización del bot de predicción con estrategia Peceto
        
        Args:
            api_key (str): API Key de Binance
            api_secret (str): API Secret de Binance
            symbol (str): Par de trading (default: BTCUSDT)
            interval (str): Intervalo de tiempo para las velas (default: 15m)
            ema_short (int): Periodo para EMA corta (default: 9)
            ema_medium (int): Periodo para EMA media (default: 21)
            ema_long (int): Periodo para EMA larga (default: 55)
            rsi_period (int): Periodo para RSI (default: 14)
            rsi_oversold (int): Nivel de sobreventa para RSI (default: 30)
            rsi_overbought (int): Nivel de sobrecompra para RSI (default: 70)
            use_telegram (bool): Si es True, envía alertas por Telegram
            show_chart (bool): Si es True, muestra gráficos interactivos
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = Client(api_key, api_secret)
        self.symbol = symbol
        self.interval = interval
        self.ema_short = ema_short
        self.ema_medium = ema_medium
        self.ema_long = ema_long
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.use_telegram = use_telegram
        self.last_signal = None
        self.signal_time = None
        self.show_chart = show_chart
        
        # Para evitar alertas repetitivas
        self.last_buy_alert = None
        self.last_sell_alert = None
        self.cooldown_hours = 2  # Horas de espera entre alertas del mismo tipo
        
        # Inicializar módulo de gráficos
        if self.show_chart:
            self.chart = TradingChart(symbol=symbol, interval=interval)
            # Iniciar el servidor de gráficos en un hilo separado
            self.chart.start()
        else:
            self.chart = None
        
        logger.info(f"Bot de predicción inicializado para {symbol} con intervalos de {interval}")
        
    def get_historical_klines(self, limit=200):
        """
        Obtiene los datos históricos de velas de Binance
        
        Args:
            limit (int): Cantidad de velas a obtener
            
        Returns:
            pd.DataFrame: DataFrame con los datos de las velas
        """
        print('Obteniendo los datos históricos de velas de Binance ... ')
        try:
            klines = self.client.get_klines(
                symbol=self.symbol,
                interval=self.interval,
                limit=limit
            )
            
            data = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir a tipos numéricos y timestamps
            data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                data[col] = pd.to_numeric(data[col])
                
            return data
        
        except BinanceAPIException as e:
            logger.error(f"Error al obtener datos históricos: {e}")
            return None
            
    def calculate_indicators(self, data):
        """
        Calcula los indicadores técnicos para la estrategia Peceto
        
        Args:
            data (pd.DataFrame): DataFrame con datos históricos
            
        Returns:
            pd.DataFrame: DataFrame con indicadores calculados
        """
        print('Calcula los indicadores técnicos para la estrategia Peceto ... ')
        # Calcular EMAs
        data['ema_short'] = data['close'].ewm(span=self.ema_short, adjust=False).mean()
        data['ema_medium'] = data['close'].ewm(span=self.ema_medium, adjust=False).mean()
        data['ema_long'] = data['close'].ewm(span=self.ema_long, adjust=False).mean()
        
        # Calcular RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.rsi_period).mean()
        avg_loss = loss.rolling(window=self.rsi_period).mean()
        
        rs = avg_gain / avg_loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Calcular MACD
        data['macd'] = data['ema_short'] - data['ema_medium']
        data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean()
        data['macd_hist'] = data['macd'] - data['macd_signal']
        
        # Calcular bandas de Bollinger
        data['sma20'] = data['close'].rolling(window=20).mean()
        data['stddev'] = data['close'].rolling(window=20).std()
        data['upper_band'] = data['sma20'] + (data['stddev'] * 2)
        data['lower_band'] = data['sma20'] - (data['stddev'] * 2)
        
        # Calcular ATR (Average True Range)
        data['tr'] = np.maximum(
            np.maximum(
                data['high'] - data['low'],
                np.abs(data['high'] - data['close'].shift(1))
            ),
            np.abs(data['low'] - data['close'].shift(1))
        )
        data['atr'] = data['tr'].rolling(window=14).mean()
        
        return data
        
    def check_buy_signal(self, data):
        """
        Verifica si hay señal de compra según la estrategia Peceto
        
        Args:
            data (pd.DataFrame): DataFrame con indicadores
            
        Returns:
            tuple: (bool, dict) True si hay señal de compra y detalles de la señal
        """
        print('Verifica si hay señal de compra según la estrategia Peceto ... ')
        # Obtener las últimas filas para análisis
        last_row = data.iloc[-1]
        prev_row = data.iloc[-2]
        
        # Condiciones de la estrategia Peceto para compra:
        # 1. EMA corta cruza por encima de EMA media
        ema_cross_up = (prev_row['ema_short'] <= prev_row['ema_medium'] and 
                        last_row['ema_short'] > last_row['ema_medium'])
        
        # 2. Precio por encima de EMA larga (tendencia alcista)
        price_above_long_ema = last_row['close'] > last_row['ema_long']
        
        # 3. RSI saliendo de zona de sobreventa
        rsi_oversold_exit = (prev_row['rsi'] < self.rsi_oversold and 
                            last_row['rsi'] >= self.rsi_oversold)
        
        # 4. MACD cruzando por encima de la línea de señal
        macd_cross_up = (prev_row['macd'] <= prev_row['macd_signal'] and 
                        last_row['macd'] > last_row['macd_signal'])
        
        # 5. Precio cerca del soporte (banda inferior de Bollinger)
        near_support = last_row['close'] <= last_row['lower_band'] * 1.01
        
        # Señal de compra si se cumplen al menos 3 de las 5 condiciones
        buy_conditions = [ema_cross_up, price_above_long_ema, rsi_oversold_exit, macd_cross_up, near_support]
        buy_signals = sum(buy_conditions)
        
        # Crear resumen detallado de la señal
        signal_details = {
            "price": last_row['close'],
            "timestamp": last_row['timestamp'],
            "strength": buy_signals,
            "max_strength": 5,
            "conditions": {
                "ema_cross_up": ema_cross_up,
                "price_above_long_ema": price_above_long_ema,
                "rsi_oversold_exit": rsi_oversold_exit,
                "macd_cross_up": macd_cross_up,
                "near_support": near_support
            },
            "indicators": {
                "ema_short": last_row['ema_short'],
                "ema_medium": last_row['ema_medium'],
                "ema_long": last_row['ema_long'],
                "rsi": last_row['rsi'],
                "macd": last_row['macd'],
                "macd_signal": last_row['macd_signal'],
                "lower_band": last_row['lower_band']
            }
        }
        
        return buy_signals >= 3, signal_details
        
    def check_sell_signal(self, data):
        """
        Verifica si hay señal de venta según la estrategia Peceto
        
        Args:
            data (pd.DataFrame): DataFrame con indicadores
            
        Returns:
            tuple: (bool, dict) True si hay señal de venta y detalles de la señal
        """
        print('Verifica si hay señal de venta según la estrategia Peceto ...')
        # Obtener las últimas filas para análisis
        last_row = data.iloc[-1]
        prev_row = data.iloc[-2]
        
        # Condiciones de la estrategia Peceto para venta:
        # 1. EMA corta cruza por debajo de EMA media
        ema_cross_down = (prev_row['ema_short'] >= prev_row['ema_medium'] and 
                        last_row['ema_short'] < last_row['ema_medium'])
        
        # 2. Precio por debajo de EMA larga (tendencia bajista)
        price_below_long_ema = last_row['close'] < last_row['ema_long']
        
        # 3. RSI entrando en zona de sobrecompra
        rsi_overbought_entry = (prev_row['rsi'] > self.rsi_overbought and 
                                last_row['rsi'] <= self.rsi_overbought)
        
        # 4. MACD cruzando por debajo de la línea de señal
        macd_cross_down = (prev_row['macd'] >= prev_row['macd_signal'] and 
                            last_row['macd'] < last_row['macd_signal'])
        
        # 5. Precio cerca de la resistencia (banda superior de Bollinger)
        near_resistance = last_row['close'] >= last_row['upper_band'] * 0.99
        
        # Señal de venta si se cumplen al menos 3 de las 5 condiciones
        sell_conditions = [ema_cross_down, price_below_long_ema, rsi_overbought_entry, macd_cross_down, near_resistance]
        sell_signals = sum(sell_conditions)
        
        # Crear resumen detallado de la señal
        signal_details = {
            "price": last_row['close'],
            "timestamp": last_row['timestamp'],
            "strength": sell_signals,
            "max_strength": 5,
            "conditions": {
                "ema_cross_down": ema_cross_down,
                "price_below_long_ema": price_below_long_ema,
                "rsi_overbought_entry": rsi_overbought_entry,
                "macd_cross_down": macd_cross_down,
                "near_resistance": near_resistance
            },
            "indicators": {
                "ema_short": last_row['ema_short'],
                "ema_medium": last_row['ema_medium'],
                "ema_long": last_row['ema_long'],
                "rsi": last_row['rsi'],
                "macd": last_row['macd'],
                "macd_signal": last_row['macd_signal'],
                "upper_band": last_row['upper_band']
            }
        }
        
        return sell_signals >= 3, signal_details
        
    def format_signal_message(self, signal_type, details):
        """
        Formatea un mensaje detallado con la señal
        
        Args:
            signal_type (str): Tipo de señal ("COMPRA" o "VENTA")
            details (dict): Detalles de la señal
            
        Returns:
            str: Mensaje formateado
        """
        # Obtener emoji según tipo de señal
        emoji = "🟢" if signal_type == "COMPRA" else "🔴"
        
        # Formatear mensaje
        message = f"{emoji} SEÑAL DE {signal_type} DETECTADA {emoji}\n\n"
        message += f"📊 {self.symbol} @ {self.interval}\n"
        message += f"💰 Precio: {details['price']:.2f} USDT\n"
        message += f"⏰ Tiempo: {details['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"💪 Fuerza de señal: {details['strength']}/{details['max_strength']}\n\n"
        
        # Añadir condiciones cumplidas
        message += "✅ Condiciones cumplidas:\n"
        for condition, is_met in details['conditions'].items():
            check = "✓" if is_met else "✗"
            message += f"  {check} {condition.replace('_', ' ').title()}\n"
        
        # Añadir valores de indicadores clave
        message += "\n📈 Indicadores clave:\n"
        message += f"  RSI: {details['indicators']['rsi']:.2f}\n"
        message += f"  MACD: {details['indicators']['macd']:.4f}\n"
        message += f"  EMA Corta: {details['indicators']['ema_short']:.2f}\n"
        message += f"  EMA Media: {details['indicators']['ema_medium']:.2f}\n"
        message += f"  EMA Larga: {details['indicators']['ema_long']:.2f}\n"
        
        # Añadir recomendación
        if signal_type == "COMPRA":
            message += "\n💡 Recomendación: Considerar compra con stop loss a -3%."
        else:
            message += "\n💡 Recomendación: Considerar venta o toma de beneficios."
            
        return message
                
    def is_in_cooldown(self, signal_type):
        """
        Verifica si una alerta está en periodo de enfriamiento
        
        Args:
            signal_type (str): Tipo de señal ("COMPRA" o "VENTA")
            
        Returns:
            bool: True si está en cooldown, False si no
        """
        now = datetime.now()
        
        if signal_type == "COMPRA" and self.last_buy_alert:
            time_diff = now - self.last_buy_alert
            return time_diff.total_seconds() < self.cooldown_hours * 3600
            
        elif signal_type == "VENTA" and self.last_sell_alert:
            time_diff = now - self.last_sell_alert
            return time_diff.total_seconds() < self.cooldown_hours * 3600
            
        return False

    def format_signal_details(self, details, signal_type):
        if details is None:
            return []
        
        # Extraer información clave
        headers = ["Tipo", "Precio", "Fuerza", "RSI", "MACD", "EMA Corta", "EMA Media", "EMA Larga"]
        row = [
            signal_type,
            f"{details['price']:.2f}",
            f"{details['strength']}/{details['max_strength']}",
            f"{details['indicators']['rsi']:.2f}",
            f"{details['indicators']['macd']:.4f}",
            f"{details['indicators']['ema_short']:.2f}",
            f"{details['indicators']['ema_medium']:.2f}",
            f"{details['indicators']['ema_long']:.2f}"
        ]
        
        # Crear tabla principal
        main_table = [row]
        
        # Crear tabla de condiciones
        condition_headers = ["Condición", "Cumplida"]
        condition_rows = []
        for cond_name, is_met in details['conditions'].items():
            # Formatear nombre de condición
            cond_name = cond_name.replace('_', ' ').title()
            condition_rows.append([cond_name, "✓" if is_met else "✗"])
        
        return headers, main_table, condition_headers, condition_rows

    def run(self):
        """
        Ejecuta el bucle principal del bot de predicción
        """
        logger.info("Iniciando el bot de predicción...")
        print(f"Bot de predicción iniciado para {self.symbol} en intervalos de {self.interval}")
        print(f"Presiona Ctrl+C para detener el bot")
        print("-"*50)
        
        try:
            while True:
                try:
                    # Obtener datos históricos
                    data = self.get_historical_klines()
                    if data is None:
                        logger.error("No se pudieron obtener datos históricos. Esperando 1 minuto...")
                        time.sleep(60)
                        continue
                        
                    # Calcular indicadores
                    data = self.calculate_indicators(data)
                    
                    # Obtener precio actual
                    ticker = self.client.get_symbol_ticker(symbol=self.symbol)
                    current_price = float(ticker['price'])
                    
                    # webpage_capturer.capture()

                    # Verificar señales
                    buy_signal, buy_details = self.check_buy_signal(data)
                    sell_signal, sell_details = self.check_sell_signal(data)
                    
                    # Actualizar el gráfico con los nuevos datos
                    if self.show_chart and self.chart:
                        self.chart.update_data(
                            data=data,
                            buy_signal=buy_signal,
                            sell_signal=sell_signal,
                            buy_details=buy_details if buy_signal else None,
                            sell_details=sell_details if sell_signal else None
                        )
                    
                    # Priorizar la señal más fuerte si ambas están presentes
                    if buy_signal and sell_signal:
                        if buy_details['strength'] > sell_details['strength']:
                            sell_signal = False
                        else:
                            buy_signal = False
                    
                    # Procesar señal de compra
                    if buy_signal and not self.is_in_cooldown("COMPRA"):
                        message = self.format_signal_message("COMPRA", buy_details)
                        alert_system.send_telegram_message(message)
                        # alert_system.send_telegram_message('Estado de los graficos:', image_path="captura.png")
                        self.last_signal = "COMPRA"
                        self.signal_time = datetime.now()
                        self.last_buy_alert = datetime.now()
                        
                    # Procesar señal de venta
                    elif sell_signal and not self.is_in_cooldown("VENTA"):
                        message = self.format_signal_message("VENTA", sell_details)
                        alert_system.send_telegram_message(message)
                        # alert_system.send_telegram_message('Estado de los graficos:', image_path="captura.png")
                        self.last_signal = "VENTA"
                        self.signal_time = datetime.now()
                        self.last_sell_alert = datetime.now()
                    
                    # Estado actual (versión simplificada) cada ciclo
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    indicators = {
                        "price": current_price,
                        "rsi": data['rsi'].iloc[-1],
                        "macd": data['macd'].iloc[-1],
                        "signal": data['macd_signal'].iloc[-1],
                        "ema_short": data['ema_short'].iloc[-1],
                        "ema_medium": data['ema_medium'].iloc[-1],
                        "ema_long": data['ema_long'].iloc[-1]
                    }
                    
                    print(f"\r[{current_time}] Precio: {current_price:.2f} | RSI: {indicators['rsi']:.2f} | Última señal: {self.last_signal if self.last_signal else 'Ninguna'}", end="")
                    
                    # Esperar antes del siguiente ciclo (ajustar según el intervalo elegido)
                    if self.interval == '1m':
                        time.sleep(15)
                    elif self.interval == '1s':
                        time.sleep(2)
                    elif self.interval == '5m':
                        time.sleep(30)
                    elif self.interval == '15m':
                        time.sleep(60)
                    else:
                        time.sleep(120)
                        
                except Exception as e:
                    logger.error(f"Error en el ciclo principal: {e}")
                    time.sleep(60)
                    
        except KeyboardInterrupt:
            print("\n\nBot detenido manualmente.")
            logger.info("Bot detenido manualmente")
            if self.show_chart and self.chart:
                print("Guardando gráfico final como HTML...")
                self.chart.save_html(f"{self.symbol}_{self.interval}_chart.html")

if __name__ == "__main__":
    # Archivo config.py debe contener API_KEY y API_SECRET
    predictor = PecetoPredictor(
        api_key=config("BINANCE_API_KEY"),
        api_secret=config("BINANCE_API_SECRET"),
        symbol='BTCUSDT',    # Par de trading
        interval='1m',      # Intervalo de tiempo
        use_telegram=True,  # Cambiar a True para recibir alertas por Telegram
        show_chart=True     # Activar para mostrar gráficos interactivos
    )
    
    predictor.run()