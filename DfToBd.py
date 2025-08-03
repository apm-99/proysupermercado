from sqlalchemy.orm import sessionmaker
from database import engine
from models import Producto,Precio
from datetime import datetime
import re
from scraping import getDF, cleanup
from scrapingCarrefour import getDFCarrefour
from rapidfuzz import fuzz
from comparator import ComparadorProductos

try:
    # df,supermercado_id = getDF()
    df,supermercado_id = getDFCarrefour()
finally:
    cleanup()

# AGREGAR ESTAS LÍNEAS PARA DEBUGGEAR:
print(f"DataFrame shape: {df.shape}")
print(f"Columnas: {list(df.columns)}")
print(f"Supermercado ID: {supermercado_id}")
print("\nPrimeras 3 filas:")
print(df.head(3))
print("\nProductos únicos encontrados:", len(df))

Session = sessionmaker(bind=engine)
# if not precio_str or precio_str == "Sin precio anterior":
#     precio_limpio =  None
# else:
#     precio_limpio = re.sub(r'[^\d,.]', '', str(precio_str))
#     precio_limpio = precio_limpio.replace(".","")
#     precio_limpio = precio_limpio.replace(',', '.')
#     try:
#         precio_limpio=  float(precio_limpio)
#     except      Exception as e:
#         precio_limpio =  None
#         print(e)



def limpiar_precio(precio_str):
    if not precio_str or precio_str == "Sin precio anterior":
        return None
    precio_limpio = re.sub(r'[^\d,.]', '', str(precio_str))
    precio_limpio = precio_limpio.replace(".","")
    precio_limpio = precio_limpio.replace(',', '.')
    try:
        return float(precio_limpio)
    except (ValueError, TypeError):
        return None

def insertar_producto_con_precio(session, row_data, supermercado_id):
    nombre = row_data['Nombre'].strip()
    categoria = row_data['Categoria']
    descuento = row_data['Descuento'] if row_data['Descuento'] != "Sin descuento" else None
    precio_anterior = limpiar_precio(row_data['Precio anterior'])
    link_producto = row_data['Link del producto']
    precio_actual = limpiar_precio(row_data['Precio'])
    if not precio_actual:
        return False
    
    producto = session.query(Producto).filter(Producto.nombre == nombre).first()
    if not producto:
        # Buscar producto similar con RapidFuzz
        productos = session.query(Producto).filter(Producto.categoria == categoria)
        comparador = ComparadorProductos()

        for prod in productos:
            score = comparador.comparar(prod.nombre, nombre)
            if score:  # umbral, ajustá según necesidad
                producto = prod
                break

    # Si no encontró por nombre ni parecido, crear nuevo producto
    if not producto:
        producto = Producto(nombre=nombre, categoria=categoria)
        session.add(producto)
        session.flush()
    else:
        producto.categoria = categoria

    precio_existente = session.query(Precio).filter(
        Precio.producto_id == producto.id,
        Precio.super_id == supermercado_id
    ).first()
    
    if precio_existente:
        precio_existente.valor = precio_actual
        precio_existente.fecha_act = datetime.now()
        precio_existente.descuento = descuento
        precio_existente.precio_anterior = precio_anterior
        precio_existente.link_producto = link_producto
    else:
        nuevo_precio = Precio(
            producto_id=producto.id,
            super_id=supermercado_id,
            valor=precio_actual,
            fecha_act=datetime.now(),
            descuento= descuento,
            precio_anterior = precio_anterior,
            link_producto = link_producto
        )
        session.add(nuevo_precio)
    
    return True

def insertar_dataframe_completo(df, supermercado_id):
    session = Session()
    productos_procesados = 0
    errores = 0
    
    try:
        print(f"Iniciando inserción de {len(df)} productos...")
        
        for index, row in df.iterrows():
            try:
                if insertar_producto_con_precio(session, row, supermercado_id):
                    productos_procesados += 1
                    print(f"Procesado: {row['Nombre']} ({productos_procesados}/{len(df)})")
            except Exception as e:
                print(f"Error en producto {index}: {e}")
                errores += 1
                continue
        
        # COMMIT FINAL
        session.commit()
        print(f"✅ COMPLETADO - Procesados: {productos_procesados} | Errores: {errores}")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error general: {e}")
        return False
        
    finally:
        session.close()

# Llamar la función
print("El dataframe -> : ", df)
insertar_dataframe_completo(df, supermercado_id)


