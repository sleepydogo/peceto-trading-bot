import io
import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate
import telegram_send
from PIL import Image

# Esta función convierte una tabla en imagen
def table_to_image(data, headers, title="", figsize=(10, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis('tight')
    ax.axis('off')
    
    # Crear la tabla en matplotlib
    table = ax.table(
        cellText=data,
        colLabels=headers,
        loc='center',
        cellLoc='center'
    )
    
    # Ajustar tamaño de fuente
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    
    # Ajustar ancho de columnas
    table.auto_set_column_width(col=list(range(len(headers))))
    
    # Agregar título
    plt.title(title)
    plt.tight_layout()
    
    # Guardar en un buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    
    return buf