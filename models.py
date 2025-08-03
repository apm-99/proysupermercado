from sqlalchemy import Column, Integer,String, Float,DateTime,func,ForeignKey,Text
from database import Base
from sqlalchemy.orm import relationship

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer,primary_key=True,autoincrement=True)
    nombre = Column(String, index= True, unique=True, nullable=False)
    categoria = Column(String, nullable=False)
    precios = relationship("Precio", back_populates="producto", cascade="all, delete-orphan")

class Supermercado(Base):
    __tablename__ = "supermercados"
    id = Column(Integer,primary_key=True)
    nombre = Column(String, index= True, unique=True, nullable=False)
    precios = relationship("Precio", back_populates="supermercado", cascade="all, delete-orphan")

class Precio(Base):
    __tablename__ = "precios"
    producto_id = Column(Integer,ForeignKey("productos.id"), primary_key=True)
    super_id = Column(Integer, ForeignKey("supermercados.id"), primary_key=True)
    valor = Column(Float, nullable=False)
    fecha_act = Column(DateTime, server_default=func.now())
    descuento = Column(String)
    precio_anterior = Column(Float)
    link_producto = Column(Text)
    producto= relationship("Producto", back_populates="precios")
    supermercado= relationship("Supermercado", back_populates="precios")


