# Bot de Predicción Peceto

Este bot implementa la estrategia de trading "Peceto" para análisis técnico de criptomonedas en Binance. El bot analiza patrones de precio utilizando múltiples indicadores técnicos para generar señales de compra y venta.

## Características

- Análisis de múltiples indicadores técnicos (EMA, RSI, MACD, Bandas de Bollinger, ATR)
- Configuración personalizable para diferentes pares de trading y marcos temporales
- Sistema de alertas con detalles sobre la fuerza de la señal y condiciones cumplidas
- Opción para recibir alertas por Telegram
- Sistema de enfriamiento para evitar alertas repetitivas
- Registro detallado de actividades y señales

## Indicadores utilizados

- **EMA (Media Móvil Exponencial)**: EMA corta (9), media (21) y larga (55)
- **RSI (Índice de Fuerza Relativa)**: Para identificar condiciones de sobrecompra y sobreventa
- **MACD (Convergencia/Divergencia de Medias Móviles)**: Para identificar cambios de impulso
- **Bandas de Bollinger**: Para identificar soportes y resistencias dinámicos
- **ATR (Rango Verdadero Promedio)**: Para medir la volatilidad

## Estrategia Peceto

La estrategia Peceto genera señales basadas en la combinación de múltiples condiciones técnicas:

### Señales de compra
- EMA corta cruza por encima de EMA media
- Precio por encima de EMA larga (tendencia alcista)
- RSI saliendo de zona de sobreventa
- MACD cruzando por encima de la línea de señal
- Precio cerca del soporte (banda inferior de Bollinger)

### Señales de venta
- EMA corta cruza por debajo de EMA media
- Precio por debajo de EMA larga (tendencia bajista)
- RSI entrando en zona de sobrecompra
- MACD cruzando por debajo de la línea de señal
- Precio cerca de la resistencia (banda superior de Bollinger)

Se genera una señal cuando se cumplen al menos 3 de las 5 condiciones.

## Requisitos

- Python 3.7+
- Cuenta de Binance con API Key y Secret
- Conexión a Internet estable
- Opcional: Configuración de Telegram para alertas

## Instalación

1. Clona este repositorio:
```
git clone https://github.com/tuusuario/bot-prediccion-peceto.git
cd bot-prediccion-peceto
```

2. Instala las dependencias:
```
pip install -r requirements.txt
```

3. Configura tus credenciales de Binance:
   - Edita el archivo directamente o crea un archivo `config.py` con tus credenciales:
   ```python
   API_KEY = "tu_api_key"
   API_SECRET = "tu_api_secret"
   ```

## Uso

Para ejecutar el bot con la configuración predeterminada:

```
python bot_peceto.py
```

Para personalizar los parámetros, modifica la instancia del predictor al final del archivo:

```python
predictor = PecetoPredictor(
    api_key="TU_API_KEY",
    api_secret="TU_API_SECRET",
    symbol='BTCUSDT',    # Par de trading
    interval='15m',      # Intervalo de tiempo
    use_telegram=True    # Cambiar a True para recibir alertas por Telegram
)
```

## Configuración de Telegram (opcional)

1. Instala telegram-send:
```
pip install telegram-send
```

2. Configura telegram-send:
```
telegram-send --configure
```

3. Sigue las instrucciones para vincular con tu bot de Telegram

## Parámetros personalizables

Al iniciar la clase `PecetoPredictor`, puedes personalizar los siguientes parámetros:

- `symbol`: Par de trading (por defecto: 'BTCUSDT')
- `interval`: Intervalo de tiempo (por defecto: '15m')
- `ema_short`: Periodo para EMA corta (por defecto: 9)
- `ema_medium`: Periodo para EMA media (por defecto: 21)
- `ema_long`: Periodo para EMA larga (por defecto: 55)
- `rsi_period`: Periodo para RSI (por defecto: 14)
- `rsi_oversold`: Nivel de sobreventa para RSI (por defecto: 30)
- `rsi_overbought`: Nivel de sobrecompra para RSI (por defecto: 70)
- `use_telegram`: Activar alertas por Telegram (por defecto: False)

## Registro y logs

El bot genera un archivo de registro `prediction_bot.log` con información detallada sobre su funcionamiento y las señales generadas.

## Aviso de riesgo

Este bot es una herramienta de análisis técnico y no garantiza resultados. El trading de criptomonedas implica riesgos significativos y puede resultar en pérdidas financieras. Utiliza este bot bajo tu propia responsabilidad y realiza siempre tu propia investigación antes de tomar decisiones de inversión.

## Licencia

[MIT](https://choosealicense.com/licenses/mit/)

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue para discutir los cambios antes de enviar un pull request.