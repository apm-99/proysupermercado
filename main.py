from fastapi import FastAPI,Depends,Form
from crud import procesar_mensaje,get_precio_por_supermercado, get_productos,crear_precio,crear_prod,crear_super
from schemas import Precio,Producto,Supermercado, CrearProducto,CrearPrecio,CrearSupermercado
from sqlalchemy.orm import Session
from database import get_db
from fastapi.responses import PlainTextResponse

from fastapi import HTTPException
from database import get_db


app = FastAPI()

@app.get("/", status_code=200)
def get_prod(db:Session =Depends(get_db)):
    try:
        return get_productos(db)
    except:
        raise HTTPException(status_code=404, detail= "Productos no encontrados")

    

@app.get("/{prod_name}/{super_name}", status_code=200, response_model = Precio)
def get_PriceBySupermarket(prod_name:str, super_name : str, db:Session = Depends(get_db)):
    precio =  get_precio_por_supermercado(db,prod_name, super_name)
    if precio:
        return precio
    raise HTTPException(status_code=404, detail= "Producto no encontrado")




@app.post("/{prod_name}/producto/", response_model=Producto, status_code=201)
def create_prod(prod:CrearProducto, db: Session= Depends(get_db)):
    try:
        return crear_prod(db,prod)
    except:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/{prod_name}/precio/", response_model = Precio, status_code=201)
def create_price(precio:CrearPrecio, db: Session = Depends(get_db)):
    try:
        return crear_precio( db,precio)
    except:
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.post("/{super_nombre}/supermercado/", response_model = Supermercado, status_code=201)
def create_super(super:CrearSupermercado, db: Session = Depends(get_db)):
    try:
        return crear_super(db,super)    
    except:
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    


@app.post("/webhook")
async def whattsap_response(
    Body: str = Form(...),
    From: str = Form(...),
    db:Session = Depends(get_db)
):
    response_text = procesar_mensaje(Body,db)

    return PlainTextResponse(response_text)
    

