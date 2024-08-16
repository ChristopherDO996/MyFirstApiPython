import re

from fastapi import FastAPI, Body, Path, Query, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import Optional,List
from config.base_de_datos import sesion, motor, base
from modelos.ventas import Ventas as VentasModelo
from jwt_config import dame_token,valida_token
from collections import Counter

# crea instancia de fastapi
app = FastAPI()
app.title = 'Aplicacion de ventas'
app.version = '1.0.1'
base.metadata.create_all(bind=motor)

# creamos el modelo
class Usuario(BaseModel):
    email:str
    clave:str
class Ventas(BaseModel):
    #id: int = Field(ge=0, le=20)
    id: Optional[int]=None
    fecha: str
    #tienda: str = Field(default="Tienda01",min_length=4, max_length=10)
    tienda: str = Field(min_length=4, max_length=10)
    #tienda:str
    importe:float
    class Config:
        schema_extra = {
            "example":{
                "id":1,
                "fecha":"01/02/23",
                "tienda":"Tienda09",
                "importe":131
            }
        }
# Portador token
class Portador(HTTPBearer):
    async def __call__(self, request:Request):
        autorizacion = await super().__call__(request)
        dato = valida_token(autorizacion.credentials)
        if dato['email'] != 'josecodetech@gmail.com':
            raise HTTPException(status_code=403, detail='No autorizado')
# crear punto de entrada o endpoint


@app.get('/', tags=['Inicio'])  # cambio de etiqueta en documentacion
def mensaje():
    return HTMLResponse('<h2>Titulo html desde FastAPI</h2>')

# @app.get('/dictionary/', tags=['Diccionario'])  # cambio de etiqueta en documentacion
# def mensaje():
#     return HTMLResponse('<h2>Envíame la palabra</h2>')


# @app.route('/dictionary/', methods=['GET'])
@app.get('/dictionary/', tags=['Diccionario'])
def api_id(request:Request):
    # Get Parameter
    if 'word' in request.args:
        word = request.args['word']
    else:
        return "Error: Ningún parámetro recibido (Agrega el parámetro 'word' a la URL)"
    # Text to Lower
    def words(text): return re.findall(r'\w+', text.lower())
    # Read dictionary
    WORDS = Counter(words(open('dictionary.txt').read()))
    # Return words from dictionary
    def P(word, N=sum(WORDS.values())):
        return WORDS[word]/N
    # Compare size word and make the correction
    def correction(word):
        newWord = max(candidates(word), key=P)
        if(newWord == word):
            print("Error")
        else:
            return max(candidates(word), key=P)
    # Check three options of word
    def candidates(word):
        return (known([word]) or known(edits1(word)) or known(edits2(word)) or [word])
    # Find word fixed in dictionary
    def known(words):
        return set(w for w in words if w in WORDS)
    # Edit and build word
    def edits1(word):
        letters = 'abcdefghijklmnopqrstuvwxyz'
        splits = [(word[:i], word[i:])          for i in range(len(word) + 1)]
        deletes = [L + R[1:]                    for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:]   for L, R in splits if len(R)>1]
        replaces = [L + c + R[1:]               for L, R in splits if R for c in letters]
        inserts = [L + c + R                    for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)
    # Check more options
    def edits2(word):
        return (e2 for e1 in edits1(word) for e2 in edits1(e1))
    # Paint correction
    return(correction(word))

@app.get('/ventas', tags=['Ventas'], response_model=List[Ventas], status_code=200, dependencies=[Depends(Portador())])
def dame_ventas() -> List[Ventas]:
    db = sesion()
    resultado = db.query(VentasModelo).all()
    return JSONResponse(status_code=200,content=jsonable_encoder(resultado))


@app.get('/ventas/{id}', tags=['Ventas'], response_model = Ventas, status_code = 200)
def dame_ventas(id: int = Path(ge=1,le=1000)) -> Ventas:
    db = sesion()
    resultado = db.query(VentasModelo).filter(VentasModelo.id == id).first()
    if not resultado:
        return JSONResponse(status_code=404, content={'mensaje':'No se encontro ese identificador'})
    
    return JSONResponse(status_code=200, content=jsonable_encoder(resultado)) 


@app.get('/ventas/', tags=['Ventas'], response_model=List[Ventas], status_code=200)
# para mas parametros ,id:int
def dame_ventas_por_tienda(tienda: str = Query(min_length=4, max_length=20)) -> List[Ventas]:
    # return tienda
    db = sesion()
    resultado = db.query(VentasModelo).filter(VentasModelo.tienda == tienda).all()
    if not resultado:
        return JSONResponse(status_code=404, content={'mensaje': 'No se encontro esa tienda'})
    return JSONResponse(content = jsonable_encoder(resultado))



@app.post('/ventas', tags=['Ventas'], response_model=dict, status_code=201)
def crea_venta(venta:Ventas) -> dict:
    db = sesion()
    # extraemos atributos para paso como parametros
    nueva_venta = VentasModelo(**venta.dict())
    # añadir a bd y hacemos commit para actualizar datos
    db.add(nueva_venta)
    db.commit()
    return JSONResponse(content={'mensaje': 'Venta registrada'}, status_code=200)


@app.put('/ventas/{id}', tags=['Ventas'], response_model=dict, status_code=201)
def actualiza_ventas(id: int, venta: Ventas) -> dict:
    db = sesion()
    resultado = db.query(VentasModelo).filter(VentasModelo.id == id).first()
    if not resultado:
        return JSONResponse(status_code=404, content={'mensaje': 'No se ha podido actualizar'})
    resultado.fecha = venta.fecha
    resultado.tienda = venta.tienda
    resultado.importe = venta.importe
    db.commit()    
    # recorrer los elementos de la lista
    return JSONResponse(content={'mensaje': 'Venta actualizada'}, status_code=201)


@app.delete('/ventas/{id}', tags=['Ventas'], response_model=dict, status_code=200)
def borra_venta(id: int) -> dict:
    db = sesion()
    resultado = db.query(VentasModelo).filter(VentasModelo.id == id).first()
    if not resultado:
        return JSONResponse(status_code=404, content={'mensaje': 'No se pudo borrar'})
    db.delete(resultado)
    db.commit()
    return JSONResponse(content={'mensaje': 'Venta borrada'}, status_code=200)

#creamos ruta para login
@app.post('/login',tags=['autenticacion'])
def login(usuario:Usuario):
    if usuario.email == 'josecodetech@gmail.com' and usuario.clave == '1234':
        # obtenemos el token con la funcion pasandole el diccionario de usuario
        token:str=dame_token(usuario.dict())
        return JSONResponse(status_code=200,content=token)
    else:
        return JSONResponse(content={'mensaje':'Acceso denegado'}, status_code=404)