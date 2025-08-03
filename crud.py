import models,schemas
from sqlalchemy.orm import Session
from fastapi import HTTPException

def get_productos(db:Session, limit = 50, offset= 0):
    return db.query(models.Producto).limit(limit).offset(offset).all()
def get_producto_by_name(db:Session, prod_name = str):
    return db.query(models.Producto).filter(models.Producto.nombre == prod_name).first()

def get_precio_por_supermercado(db:Session, prod_name:str, supermercado_name :str):
    return(
        db.query(models.Precio)
        .join(models.Producto, models.Precio.producto_id == models.Producto.id)
        .join(models.Supermercado, models.Precio.super_id == models.Supermercado.id)
        .filter(
            models.Producto.nombre == prod_name,
            models.Supermercado.nombre == supermercado_name
            
        ).first()
    )

def crear_super(db:Session, supermercado: schemas.CrearSupermercado):
    super = models.Supermercado(nombre = supermercado.nombre)
    db.add(super)
    db.commit()
    db.refresh(super)
    return super

def crear_precio(db:Session, precio: schemas.CrearPrecio):
    prec = models.Precio(producto_id = precio.producto_id, super_id = precio.super_id, valor = precio.valor, fecha_act = precio.fecha_act,descuento = precio.descuento, precio_anterior = precio.precio_anterior, link_producto = precio.link_producto)
    db.add(prec)
    db.commit()
    db.refresh(prec)
    return prec

    # precios: List[Precio] = []
    # descuento:str
    # precio_anterior:float
    # link_producto:str

def crear_prod(db:Session, producto:schemas.CrearProducto):
    prod = models.Producto(nombre= producto.nombre, categoria = producto.categoria)
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod

from rapidfuzz import process, fuzz

def limpiar_mensaje(mensaje):
    mensaje = mensaje.lower()
    reemplazos = ["precio de", "cuánto sale", "cuánto cuesta", "en el", "en", "el", "la", "precio"]
    for r in reemplazos:
        mensaje = mensaje.replace(r, "")
    return mensaje.strip()


def procesar_mensaje(mensaje_usuario: str, db: Session):
    mensaje = limpiar_mensaje(mensaje_usuario)

    supermercados = db.query(models.Supermercado).all()
    productos = db.query(models.Producto).all()
    nombres_supers = [s.nombre for s in supermercados]
    nombres_productos = [p.nombre for p in productos]

    # Supermercado con Rapidfuzz
    super_match = process.extractOne(
        mensaje,
        nombres_supers,
        scorer=fuzz.partial_ratio,
        score_cutoff=60
    )

    if not super_match:
        return "No encontré ningún supermercado en tu mensaje."
    
    supermercado = next(s for s in supermercados if s.nombre == super_match[0])

    # Obtener los top 5 productos más similares
    producto_matches = process.extract(
        mensaje,
        nombres_productos,
        scorer=fuzz.token_set_ratio,
        limit=5
    )

    producto = None
    precio = None

    for match in producto_matches:
        nombre_match, score = match[0], match[1]
        if score < 50:
            continue

        posible_producto = next((p for p in productos if p.nombre == nombre_match), None)
        if not posible_producto:
            continue

        posible_precio = db.query(models.Precio).filter(
            models.Precio.producto_id == posible_producto.id,
            models.Precio.super_id == supermercado.id
        ).first()

        if posible_precio:
            producto = posible_producto
            precio = posible_precio
            break

    if not producto or not precio:
        return f"No encontré productos con precio disponible en {supermercado.nombre} que coincidan con tu mensaje."

    strDesc = (
        f"El producto tiene un descuento de {precio.descuento}. Y su precio anterior es de {precio.precio_anterior}"
        if precio.descuento else "El producto no tiene descuento."
    )

    return (
        f"El precio de {producto.nombre} en {supermercado.nombre} es ${precio.valor:.2f}.\n"
        f"{strDesc} \nLink del producto: {precio.link_producto}"
    )

