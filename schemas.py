from pydantic import BaseModel,Field
from typing import List, Optional
from datetime import datetime

class PrecioBase(BaseModel):
    valor: float
    fecha_act:Optional[datetime] = Field(default_factory = datetime.now)
    
class CrearPrecio(PrecioBase):
    producto_id: int
    super_id:int 
    descuento: Optional[str] = None
    precio_anterior: Optional[float] = None
    link_producto:str

class Precio(PrecioBase):
    producto_id: int
    super_id:int
    descuento: Optional[str] = None
    precio_anterior: Optional[float] = None
    link_producto:str
    class Config:
        from_attributes = True

class ProductoBase(BaseModel):
    nombre: str
    categoria: Optional[str]= None

class CrearProducto(ProductoBase):
    pass



class Producto(ProductoBase):
    id: int
    precios: List[Precio] = []
    class Config:
        from_attributes = True


class SupermercadoBase(BaseModel):
    nombre: str

class CrearSupermercado(SupermercadoBase):
    pass

class Supermercado(SupermercadoBase):
    id: int
    class Config:
        from_attributes = True




