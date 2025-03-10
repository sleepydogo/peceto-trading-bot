import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import threading
import time
from datetime import datetime
import webbrowser
import os

class TradingChart:
    def __init__(self, symbol='BTCUSDT', interval='15m', update_interval=5, port=8050):
        """
        Inicializa el módulo de gráficos para el bot de trading
        
        Args:
            symbol (str): Par de trading a mostrar
            interval (str): Intervalo de tiempo para las velas
            update_interval (int): Intervalo de actualización en segundos
            port (int): Puerto para el servidor Dash
        """
        self.symbol = symbol
        self.interval = interval
        self.update_interval = update_interval
        self.port = port
        
        # Datos para el gráfico
        self.data = None
        self.buy_signals = []
        self.sell_signals = []
        
        # Estado del servidor
        self.running = False
        self.server_thread = None
        self.dashboard = None
        
    def update_data(self, data, buy_signal=False, sell_signal=False, buy_details=None, sell_details=None):
        """
        Actualiza los datos del gráfico
        
        Args:
            data (pd.DataFrame): DataFrame con datos de velas e indicadores
            buy_signal (bool): Si hay señal de compra
            sell_signal (bool): Si hay señal de venta
            buy_details (dict): Detalles de la señal de compra
            sell_details (dict): Detalles de la señal de venta
        """
        self.data = data.copy()
        
        # Registrar señales si existen
        if buy_signal and buy_details:
            self.buy_signals.append({
                'timestamp': buy_details['timestamp'],
                'price': buy_details['price'],
                'strength': buy_details['strength'],
                'details': buy_details
            })
        
        if sell_signal and sell_details:
            self.sell_signals.append({
                'timestamp': sell_details['timestamp'],
                'price': sell_details['price'],
                'strength': sell_details['strength'],
                'details': sell_details
            })
            
    def create_chart(self):
        """
        Crea un gráfico interactivo con Plotly
        
        Returns:
            go.Figure: Figura de Plotly con el gráfico
        """
        if self.data is None or len(self.data) == 0:
            # Crear figura vacía si no hay datos
            fig = make_subplots(rows=3, cols=1, 
                                shared_xaxes=True, 
                                vertical_spacing=0.03, 
                                row_heights=[0.6, 0.2, 0.2],
                                subplot_titles=('Precio', 'RSI', 'MACD'))
            return fig
            
        # Crear subplots
        fig = make_subplots(rows=3, cols=1, 
                           shared_xaxes=True, 
                           vertical_spacing=0.03, 
                           row_heights=[0.6, 0.2, 0.2],
                           subplot_titles=('Precio', 'RSI', 'MACD'))
        
        # Añadir velas
        fig.add_trace(go.Candlestick(
            x=self.data['timestamp'],
            open=self.data['open'],
            high=self.data['high'],
            low=self.data['low'],
            close=self.data['close'],
            name='Precio'
        ), row=1, col=1)
        
        # Añadir EMAs
        fig.add_trace(go.Scatter(
            x=self.data['timestamp'],
            y=self.data['ema_short'],
            line=dict(color='rgba(255, 165, 0, 0.7)', width=1),
            name=f'EMA {self.data["ema_short"].name.split("_")[-1]}'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=self.data['timestamp'],
            y=self.data['ema_medium'],
            line=dict(color='rgba(46, 139, 87, 0.7)', width=1),
            name=f'EMA {self.data["ema_medium"].name.split("_")[-1]}'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=self.data['timestamp'],
            y=self.data['ema_long'],
            line=dict(color='rgba(25, 25, 112, 0.7)', width=1),
            name=f'EMA {self.data["ema_long"].name.split("_")[-1]}'
        ), row=1, col=1)
        
        # Añadir Bandas de Bollinger
        fig.add_trace(go.Scatter(
            x=self.data['timestamp'],
            y=self.data['upper_band'],
            line=dict(color='rgba(173, 216, 230, 0.5)', width=1),
            name='Banda Superior',
            showlegend=False
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=self.data['timestamp'],
            y=self.data['lower_band'],
            line=dict(color='rgba(173, 216, 230, 0.5)', width=1),
            fill='tonexty',
            fillcolor='rgba(173, 216, 230, 0.1)',
            name='Banda Inferior',
            showlegend=False
        ), row=1, col=1)
        
        # Añadir RSI
        fig.add_trace(go.Scatter(
            x=self.data['timestamp'],
            y=self.data['rsi'],
            line=dict(color='rgba(70, 130, 180, 1)', width=1),
            name='RSI'
        ), row=2, col=1)
        
        # Líneas de referencia para RSI
        fig.add_shape(
            type="line", line=dict(dash='dash', width=1, color="red"),
            y0=70, y1=70, x0=self.data['timestamp'].iloc[0], x1=self.data['timestamp'].iloc[-1],
            row=2, col=1
        )
        
        fig.add_shape(
            type="line", line=dict(dash='dash', width=1, color="green"),
            y0=30, y1=30, x0=self.data['timestamp'].iloc[0], x1=self.data['timestamp'].iloc[-1],
            row=2, col=1
        )
        
        # Añadir MACD
        fig.add_trace(go.Scatter(
            x=self.data['timestamp'],
            y=self.data['macd'],
            line=dict(color='rgba(0, 0, 255, 1)', width=1),
            name='MACD'
        ), row=3, col=1)
        
        fig.add_trace(go.Scatter(
            x=self.data['timestamp'],
            y=self.data['macd_signal'],
            line=dict(color='rgba(255, 0, 0, 1)', width=1),
            name='Señal MACD'
        ), row=3, col=1)
        
        # Añadir histograma MACD
        colors = ['green' if val >= 0 else 'red' for val in self.data['macd_hist']]
        fig.add_trace(go.Bar(
            x=self.data['timestamp'],
            y=self.data['macd_hist'],
            marker_color=colors,
            name='Histograma MACD'
        ), row=3, col=1)
        
        # Añadir señales de compra y venta
        buy_timestamps = [signal['timestamp'] for signal in self.buy_signals 
                         if signal['timestamp'] in self.data['timestamp'].values]
        buy_prices = [signal['price'] for signal in self.buy_signals 
                     if signal['timestamp'] in self.data['timestamp'].values]
        
        sell_timestamps = [signal['timestamp'] for signal in self.sell_signals 
                          if signal['timestamp'] in self.data['timestamp'].values]
        sell_prices = [signal['price'] for signal in self.sell_signals 
                      if signal['timestamp'] in self.data['timestamp'].values]
        
        if buy_timestamps:
            fig.add_trace(go.Scatter(
                x=buy_timestamps,
                y=buy_prices,
                mode='markers',
                marker=dict(symbol='triangle-up', size=10, color='green'),
                name='Señal de Compra'
            ), row=1, col=1)
        
        if sell_timestamps:
            fig.add_trace(go.Scatter(
                x=sell_timestamps,
                y=sell_prices,
                mode='markers',
                marker=dict(symbol='triangle-down', size=10, color='red'),
                name='Señal de Venta'
            ), row=1, col=1)
            
        # Configurar diseño del gráfico
        fig.update_layout(
            title=f'{self.symbol} ({self.interval}) - Actualizado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            xaxis_title='Tiempo',
            yaxis_title='Precio',
            xaxis_rangeslider_visible=False,
            height=800,
            width=1200,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Configuración específica de cada subplot
        fig.update_yaxes(title_text="Precio", row=1, col=1)
        fig.update_yaxes(title_text="RSI", row=2, col=1)
        fig.update_yaxes(title_text="MACD", row=3, col=1)
        
        return fig
    
    def save_html(self, filename='trading_chart.html'):
        """
        Guarda el gráfico como archivo HTML
        
        Args:
            filename (str): Nombre del archivo HTML
        """
        fig = self.create_chart()
        fig.write_html(filename, auto_open=True)
        
    def start_dash_server(self):
        """
        Inicia un servidor Dash para mostrar el gráfico en tiempo real
        """
        import dash
        from dash import dcc, html
        from dash.dependencies import Input, Output
        
        # Crear aplicación Dash
        app = dash.Dash(__name__)
        
        app.layout = html.Div([
            html.H1(f'Bot de Trading - {self.symbol} ({self.interval})'),
            dcc.Graph(id='live-chart'),
            dcc.Interval(
                id='interval-component',
                interval=self.update_interval * 1000,  # en milisegundos
                n_intervals=0
            )
        ])
        
        @app.callback(
            Output('live-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_graph(n):
            return self.create_chart()
        
        # Guardar referencia a la app
        self.dashboard = app
        
        # Iniciar el servidor
        print(f"\n[INFO] Iniciando servidor de gráficos en http://localhost:{self.port}")
        print(f"[INFO] Abre esa URL en tu navegador para ver los gráficos en tiempo real")
        
        # Abrir navegador automáticamente
        webbrowser.open_new_tab(f'http://localhost:{self.port}')
        
        # Iniciar el servidor
        app.run_server(debug=False, port=self.port, use_reloader=False)
        
    def start(self):
        """
        Inicia el servidor de gráficos en un hilo separado
        """
        # Verificar si ya está corriendo
        if self.running:
            print("[INFO] El servidor de gráficos ya está corriendo")
            return
            
        # Iniciar un nuevo hilo para el servidor
        self.running = True
        self.server_thread = threading.Thread(target=self.start_dash_server)
        self.server_thread.daemon = True  # El hilo termina cuando el programa principal termina
        self.server_thread.start()
        
    def stop(self):
        """
        Detiene el servidor de gráficos
        """
        self.running = False
        print("[INFO] Servidor de gráficos detenido")