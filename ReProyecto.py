"""
Patrones:
- Singleton: proveedor de DB (una instancia).
- Observer: EventBus para notificar cambios (productos/proveedores/usuarios/promos/ordenes).
- Strategy: exportación Excel/CSV conmutables.

"""

from __future__ import annotations
import os
import sys
import csv
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Protocol
from datetime import datetime, timedelta, date

# ===== GUI =====
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    import customtkinter as ctk
    GUI_AVAILABLE = True
except Exception:
    GUI_AVAILABLE = False
    tk = ttk = messagebox = filedialog = ctk = None  # type: ignore

# ===== Env & Mongo =====
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return None
try:
    from pymongo import MongoClient
    from bson.objectid import ObjectId
except Exception:
    MongoClient = None  # type: ignore
    class ObjectId:
        def __init__(self, x): self._v=x
        def __str__(self): return self._v

# ======================= PATRÓN 1: SINGLETON (DB Provider) ===================
class MongoProvider:
    _instance: Optional["MongoProvider"] = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            load_dotenv()
            # Mantiene tu URI por defecto y permite .env
            uri = os.getenv("MONGO_URI") or (
                "mongodb+srv://edgarallanespinosah:rBJZFh6ZF6xZYXzh@cluster0.yvlnuwz.mongodb.net"
                "/?retryWrites=true&w=majority&appName=Cluster0"
            )
            db_name = os.getenv("DB_NAME", "supermercado")
            if MongoClient:
                try:
                    client = MongoClient(uri, serverSelectionTimeoutMS=2000)
                    client.admin.command("ping")
                    cls._instance.client = client
                    cls._instance.db = client[db_name]
                except Exception:
                    # Fallback a memoria si no hay Mongo accesible
                    cls._instance.client = None
                    cls._instance.db = MemoryDB(db_name)
            else:
                cls._instance.client = None
                cls._instance.db = MemoryDB(os.getenv("DB_NAME", "supermercado"))
        return cls._instance
    @property
    def db(self): return self._db
    @db.setter
    def db(self, v): self._db=v

# ========= Fallback DB simple en memoria (para pruebas / sin Mongo) ==========
from uuid import uuid4
class _MemInsert: 
    def __init__(self, _id): self.inserted_id=_id
class MemoryCollection:
    def __init__(self): self._docs: Dict[str, Dict[str, Any]] = {}
    def find(self, q: Optional[Dict]=None):
        q=q or {}; return [d.copy() for d in self._docs.values() if _match(d,q)]
    def find_one(self, q: Dict):
        for d in self._docs.values():
            if _match(d,q): return d.copy()
        return None
    def insert_one(self, data: Dict[str, Any]):
        _id = str(uuid4()); data=data.copy(); data["_id"]=_id; self._docs[_id]=data; return _MemInsert(_id)
    def update_one(self, q: Dict, op: Dict):
        d=self.find_one(q); 
        if not d: return
        setv = op.get("$set", {}); d.update(setv); self._docs[d["_id"]] = d
    def delete_one(self, q: Dict):
        d=self.find_one(q); 
        if d: self._docs.pop(d["_id"], None)
class MemoryDB:
    def __init__(self, name="db"): self._cols: Dict[str, MemoryCollection] = {}; self.name=name
    def __getitem__(self, col:str):
        if col not in self._cols: self._cols[col]=MemoryCollection()
        return self._cols[col]
def _match(doc: Dict[str,Any], q: Dict[str,Any]):
    import re
    for k,v in (q or {}).items():
        if isinstance(v, dict) and "$regex" in v:
            pat=v["$regex"]; opts=re.I if v.get("$options")=="i" else 0
            if not re.search(pat, str(doc.get(k, "")), opts): return False
        elif isinstance(v, dict) and "$or" in v:
            if not any(_match(doc, sub) for sub in v["$or"]): return False
        elif isinstance(v, dict) and "$lt" in v:
            if not (doc.get(k, 0) < v["$lt"]): return False
        elif isinstance(v, dict) and "$gte" in v and "$lte" in v:
            val = str(doc.get(k, ""))
            if not (v["$gte"] <= val <= v["$lte"]): return False
        else:
            if doc.get(k)!=v: return False
    return True

# ======================= PATRÓN 2: OBSERVER (Event Bus) ======================
class EventBus:
    def __init__(self): self._subs: Dict[str, List] = {}
    def subscribe(self, event:str, cb): self._subs.setdefault(event, []).append(cb)
    def emit(self, event:str, payload:Any=None):
        for cb in self._subs.get(event, []):
            try: cb(payload)
            except Exception as e: print("Listener error", event, e)

# =============================== MODELOS =====================================
@dataclass
class Producto:
    nombre: str; marca: str; categoria: str; cantidad: int; precio: float; proveedor: str
    fecha_caducidad: Optional[str]=None; estado: str="activo"; _id: Optional[str]=None

@dataclass
class Proveedor:
    nombre:str; empresa:str; telefono:str; correo:str; _id:Optional[str]=None

@dataclass
class Usuario:
    usuario:str; password:str; rol:str; nombre:str=""; _id:Optional[str]=None

@dataclass
class Promocion:
    producto_id:str; descuento:int; inicio:str; fin:str; activa:bool=True; _id:Optional[str]=None

@dataclass
class OrdenItem:
    producto_id:str; nombre:str; cantidad:int; precio_unit:float; descuento:int=0

@dataclass
class Orden:
    proveedor_o_cliente:str
    fecha:str
    items:List[OrdenItem]
    total:float
    tipo:str="venta"
    estado:str="pendiente"
    fecha_entrega:Optional[str]=None
    facturada:bool=False
    _id:Optional[str]=None

# ============================= REPOSITORIOS ==================================
class BaseRepo:
    def __init__(self, db, name):
        self.col=db[name]
        self._mongo_backend = MongoClient is not None and not isinstance(self.col, MemoryCollection)
    def all(self, filtros:Optional[Dict]=None):
        return list(self.col.find(filtros or {}))
    def get(self, oid:str):
        if self._mongo_backend:
            return self.col.find_one({"_id": ObjectId(oid)})
        return self.col.find_one({"_id": oid})
    def insert(self, data:Dict[str,Any]) -> str:
        payload=data.copy()
        if payload.get("_id") in (None, ""):
            payload.pop("_id", None)
        res=self.col.insert_one(payload)
        inserted = getattr(res, "inserted_id", None)
        return str(inserted)
    def update(self, oid:str, cambios:Dict[str,Any]):
        key = ObjectId(oid) if self._mongo_backend else oid
        self.col.update_one({"_id": key},{"$set":cambios})
    def delete(self, oid:str):
        key = ObjectId(oid) if self._mongo_backend else oid
        self.col.delete_one({"_id": key})

class ProductoRepository(BaseRepo):
    def __init__(self, db):
        super().__init__(db, "productos")
class ProveedorRepository(BaseRepo):
    def __init__(self, db):
        super().__init__(db, "proveedores")
class UsuarioRepository(BaseRepo):
    def __init__(self, db): super().__init__(db, "usuarios")
    def get_by_user(self, user:str): return self.col.find_one({"usuario": user})
class PromocionRepository(BaseRepo):
    def __init__(self, db):
        super().__init__(db, "promociones")
class OrdenRepository(BaseRepo):
    def __init__(self, db):
        super().__init__(db, "ordenes_compra")
class FacturaRepository(BaseRepo):
    def __init__(self, db):
        super().__init__(db, "facturas")

class HistorialRepository:
    def __init__(self, db):
        self.hist=db["historial_cambios_stock"]; self.ajustes=db["ajustes_stock"]; self.recepciones=db["recepciones"]
    def log_cambio(self, pid:str, nombre:str, antes:int, despues:int, usuario:str):
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.hist.insert_one({"producto_id":pid,"nombre":nombre,"cantidad_anterior":antes,"cantidad_nueva":despues,"fecha":now,"usuario":usuario})
    def log_ajuste(self, pid:str, nombre:str, tipo:str, cantidad:int, motivo:str):
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.ajustes.insert_one({"producto_id":pid,"producto_nombre":nombre,"tipo_ajuste":tipo,"cantidad":cantidad,"motivo":motivo,"fecha":now})
    def log_recepcion(self, pid:str, nombre:str, proveedor:str, cantidad:int, cad:str, estado:str):
        self.recepciones.insert_one({"producto_id":pid,"producto_nombre":nombre,"proveedor":proveedor,"cantidad":cantidad,"fecha_caducidad":cad,"estado_fisico":estado})

# ============= PATRÓN 3: STRATEGY (Exportación Excel/CSV) ====================
class ExportStrategy(Protocol):
    def export(self, columns: List[str], rows: List[List[Any]], suggested_name: str) -> None: ...

class ExcelExportStrategy:
    def export(self, columns, rows, suggested_name):
        try:
            from openpyxl import Workbook
        except Exception as exc:
            if GUI_AVAILABLE: messagebox.showerror("Exportación", f"openpyxl no disponible: {exc}")
            else: print("[ERR] openpyxl:", exc)
            return
        ruta = (filedialog.asksaveasfilename(initialfile=suggested_name, defaultextension=".xlsx",
                filetypes=[("Excel files","*.xlsx")], title="Guardar reporte")
                if GUI_AVAILABLE else os.path.abspath(suggested_name))
        if not ruta: return
        wb=Workbook(); ws=wb.active; fecha=datetime.now().strftime("%Y-%m-%d")
        ws.append([f"Reporte generado el {fecha}"]); ws.append([]); ws.append(columns)
        for r in rows: ws.append(r)
        wb.save(ruta)
        if GUI_AVAILABLE: messagebox.showinfo("Exportación", f"Archivo guardado:\n{ruta}")
        else: print("[OK] Export:", ruta)

class CSVExportStrategy:
    def export(self, columns, rows, suggested_name):
        ruta = (filedialog.asksaveasfilename(initialfile=suggested_name.replace(".xlsx",".csv"),
                defaultextension=".csv", filetypes=[("CSV","*.csv")], title="Guardar CSV")
                if GUI_AVAILABLE else os.path.abspath(suggested_name.replace(".xlsx",".csv")))
        if not ruta: return
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w=csv.writer(f)
            w.writerow([f"Reporte generado el {datetime.now().strftime('%Y-%m-%d')}"]); w.writerow([])
            w.writerow(columns); w.writerows(rows)
        if GUI_AVAILABLE: messagebox.showinfo("Exportación", f"CSV guardado:\n{ruta}")
        else: print("[OK] CSV:", ruta)

# ================================ CONTROLADOR ================================
class InventarioController:
    def __init__(self, bus: EventBus):
        self.bus=bus; self.db=MongoProvider().db
        self.productos=ProductoRepository(self.db)
        self.proveedores=ProveedorRepository(self.db)
        self.usuarios=UsuarioRepository(self.db)
        self.promos=PromocionRepository(self.db)
        self.ordenes=OrdenRepository(self.db)
        self.facturas=FacturaRepository(self.db)
        self.hist=HistorialRepository(self.db)
        self.usuario_actual: Optional[Dict[str,Any]] = None

    # ---- auth/usuarios ----
    def login(self, usuario:str, password:str)->bool:
        u=self.usuarios.get_by_user(usuario)
        if u and u.get("password")==password:
            self.usuario_actual=u; self.bus.emit("auth:login", {"usuario":u}); return True
        return False
    def registrar_usuario(self, u:Usuario)->str:
        oid=self.usuarios.insert(asdict(u)); self.bus.emit("usuarios:cambio"); return oid
    def actualizar_usuario(self, oid:str, cambios:Dict[str,Any]):
        self.usuarios.update(oid, cambios); self.bus.emit("usuarios:cambio")
    def eliminar_usuario(self, oid:str):
        self.usuarios.delete(oid); self.bus.emit("usuarios:cambio")

    # ---- productos ----
    def listar_productos(self, filtros:Optional[Dict]=None)->List[Dict[str,Any]]:
        return self.productos.all(filtros)
    def crear_producto(self, p:Producto)->str:
        oid=self.productos.insert(asdict(p)); self.bus.emit("productos:cambio"); return oid
    def actualizar_producto(self, oid:str, cambios:Dict[str,Any]):
        self.productos.update(oid, cambios); self.bus.emit("productos:cambio")
    def eliminar_producto(self, oid:str):
        self.productos.delete(oid); self.bus.emit("productos:cambio")

    # ---- proveedores ----
    def listar_proveedores(self, filtros:Optional[Dict]=None)->List[Dict[str,Any]]:
        return self.proveedores.all(filtros)
    def crear_proveedor(self, p:Proveedor)->str:
        oid=self.proveedores.insert(asdict(p)); self.bus.emit("proveedores:cambio"); return oid
    def actualizar_proveedor(self, oid:str, cambios:Dict[str,Any]):
        self.proveedores.update(oid, cambios); self.bus.emit("proveedores:cambio")
    def eliminar_proveedor(self, oid:str):
        self.proveedores.delete(oid); self.bus.emit("proveedores:cambio")

    # ---- recepciones / ajustes ----
    def recepcionar(self, producto_oid:str, cantidad:int, proveedor_nombre:str, cad:str, estado:str):
        prod=self._get_prod(producto_oid)
        antes=int(prod.get("cantidad",0)); despues=antes+int(cantidad)
        if despues<0: raise ValueError("El stock no puede ser negativo")
        self.productos.update(producto_oid, {"cantidad":despues, "proveedor": proveedor_nombre})
        self.hist.log_cambio(producto_oid, prod.get("nombre",""), antes, despues, (self.usuario_actual or {}).get("nombre","sistema"))
        self.hist.log_recepcion(producto_oid, prod.get("nombre",""), proveedor_nombre, int(cantidad), cad, estado)
        self.hist.log_ajuste(producto_oid, prod.get("nombre",""), "entrada", int(cantidad), "recepción")
        self.bus.emit("productos:cambio")

    def ajustar_stock(self, oid:str, delta:int, motivo:str):
        prod=self._get_prod(oid)
        antes=int(prod.get("cantidad",0)); despues=antes+int(delta)
        if despues<0: raise ValueError("El stock no puede ser negativo")
        self.productos.update(oid, {"cantidad":despues})
        self.hist.log_cambio(oid, prod.get("nombre",""), antes, despues, (self.usuario_actual or {}).get("nombre","sistema"))
        self.hist.log_ajuste(oid, prod.get("nombre",""), "entrada" if delta>=0 else "salida", abs(int(delta)), motivo)
        self.bus.emit("productos:cambio")

    def _get_prod(self, oid:str)->Dict[str,Any]:
        p=self.productos.get(oid)
        if not p: raise ValueError("Producto no encontrado")
        return p

    # ---- promociones ----
    def listar_promos(self): return self.promos.all()
    def crear_promo(self, promo:Promocion)->str:
        oid=self.promos.insert(asdict(promo)); self.bus.emit("promos:cambio"); return oid
    def actualizar_promo(self, oid:str, cambios:Dict[str,Any]):
        self.promos.update(oid, cambios); self.bus.emit("promos:cambio")
    def eliminar_promo(self, oid:str):
        self.promos.delete(oid); self.bus.emit("promos:cambio")
    def precio_con_promo(self, prod:Dict[str,Any])->float:
        base=float(prod.get("precio",0.0)); hoy=date.today()
        for pr in self.listar_promos():
            if not pr.get("activa",True): continue
            if str(pr.get("producto_id"))!=str(prod.get("_id")): continue
            try:
                ini=datetime.strptime(pr.get("inicio"), "%Y-%m-%d").date()
                fin=datetime.strptime(pr.get("fin"), "%Y-%m-%d").date()
                if ini<=hoy<=fin:
                    desc=int(pr.get("descuento",0)); return round(base*(1-desc/100.0),2)
            except Exception: pass
        return base

    # ---- órdenes / facturas ----
    def crear_orden(self, proveedor_o_cliente:str, items:List[Dict[str,Any]])->str:
        detalle=[]; total=0.0
        for it in items:
            p=self._get_prod(it["producto_id"])
            qty=int(it["cantidad"])
            if qty<=0: raise ValueError("Cantidad invalida")
            precio_final=self.precio_con_promo(p)
            total += precio_final*qty
            detalle.append(OrdenItem(str(p.get("_id")), p.get("nombre",""), qty, precio_final))
        for it in items:
            self.ajustar_stock(it["producto_id"], -int(it["cantidad"]), "venta/orden")
        orden=Orden(proveedor_o_cliente=proveedor_o_cliente,
                    fecha=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    items=detalle, total=round(total,2), tipo="venta", estado="completada", facturada=False)
        oid=self.ordenes.insert(asdict(orden))
        self.bus.emit("ordenes:cambio")
        return oid

    def crear_orden_compra(self, proveedor:str, items:List[Dict[str,Any]], fecha_entrega:str)->str:
        if not proveedor: raise ValueError("Proveedor requerido")
        if not items: raise ValueError("Selecciona al menos un producto")
        detalle=[]
        for it in items:
            p=self._get_prod(it["producto_id"])
            qty=int(it.get("cantidad",0))
            if qty<=0: raise ValueError("Cantidad invalida")
            detalle.append(OrdenItem(str(p.get("_id")), p.get("nombre",""), qty, 0.0))
        orden=Orden(proveedor_o_cliente=proveedor,
                    fecha=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    items=detalle, total=0.0, tipo="compra", estado="pendiente",
                    fecha_entrega=fecha_entrega or "", facturada=False)
        oid=self.ordenes.insert(asdict(orden))
        self.bus.emit("ordenes:cambio")
        return oid

    def actualizar_orden(self, oid:str, cambios:Dict[str,Any]):
        self.ordenes.update(oid, cambios)
        self.bus.emit("ordenes:cambio")

    def listar_ordenes(self, filtros:Optional[Dict[str,Any]]=None)->List[Dict[str,Any]]:
        return self.ordenes.all(filtros or {})

    def crear_factura(self, orden_id:str, items_con_precios:List[Dict[str,Any]])->str:
        total=0.0
        detalles=[]
        for it in items_con_precios:
            cantidad=int(it.get("cantidad",0))
            precio=float(it.get("precio_unitario", it.get("precio_unit", 0.0)))
            subtotal=round(precio*cantidad,2)
            total+=subtotal
            detalles.append({"producto": it.get("producto") or it.get("nombre") or it.get("producto_nombre",""),
                              "cantidad": cantidad,
                              "precio_unitario": precio,
                              "subtotal": subtotal})
        doc={"orden_id": orden_id, "productos": detalles,
             "precio_total": round(total,2), "fecha_emision": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        orden_doc=None
        try:
            orden_doc=self.ordenes.get(orden_id)
        except Exception:
            orden_doc=None
        if orden_doc:
            doc["proveedor"]=orden_doc.get("proveedor_o_cliente","")
            doc["tipo_orden"]=orden_doc.get("tipo","")
        fid=self.facturas.insert(doc)
        try:
            self.actualizar_orden(orden_id, {"facturada": True, "estado": "facturada"})
        except Exception:
            pass
        self.bus.emit("facturas:cambio")
        return fid

    def listar_facturas(self, filtros:Optional[Dict[str,Any]]=None)->List[Dict[str,Any]]:
        return self.facturas.all(filtros or {})

    def ordenes_por_proveedor(self, proveedor:str, estado:Optional[str]=None, solo_factura_pendiente:bool=False)->List[Dict[str,Any]]:
        filtros={"tipo": "compra", "proveedor_o_cliente": proveedor}
        if estado:
            filtros["estado"]=estado
        if solo_factura_pendiente:
            filtros["facturada"]=False
        return self.listar_ordenes(filtros)

    # ---- alertas ----    # ---- alertas ----
    def alertas(self)->Dict[str,List[Dict[str,Any]]]:
        res={"stock_bajo":[], "proxima_caducidad":[]}
        hoy=date.today(); limite=hoy+timedelta(days=15)
        for p in self.listar_productos():
            if int(p.get("cantidad",0))<10: res["stock_bajo"].append(p)
            cad=p.get("fecha_caducidad")
            if cad:
                try:
                    f=datetime.strptime(cad, "%Y-%m-%d").date()
                    if hoy<=f<=limite: res["proxima_caducidad"].append(p)
                except Exception: pass
        return res

# =================================== VISTAS ==================================
class MainView:
    def __init__(self, controller: InventarioController):
        if not GUI_AVAILABLE:
            print("[WARN] GUI no disponible. Usa --selftest para validar lógica.")
        self.c=controller; self.bus=controller.bus
        ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("green")
        self.app=ctk.CTk(); self.app.geometry("800x600"); self.app.title("Sistema de Inventario")
        self.active: Optional[ctk.CTkToplevel] = None

        ctk.CTkLabel(self.app, text="Sistema de Inventario", font=("Arial", 24)).pack(pady=30)
        ctk.CTkButton(self.app, text="Iniciar Sesión", command=self.login).pack(pady=10)
        ctk.CTkButton(self.app, text="Registrar Cuenta", command=self.registrar_usuario).pack(pady=10)

        self.bus.subscribe("auth:login", self._on_login)

    def abrir_nueva_ventana(self, titulo, tamano="800x600"):
        if self.active:
            try: self.active.destroy()
            except: pass
        ventana = ctk.CTkToplevel(self.app)
        ventana.geometry(tamano)
        ventana.title(titulo)
        self.active = ventana
        return ventana

    # --------- LOGIN / REGISTRO ----------
    def login(self):
        w=ctk.CTkToplevel(self.app); w.geometry("400x300"); w.title("Iniciar Sesión")
        ctk.CTkLabel(w, text="Iniciar Sesión", font=("Arial", 20)).pack(pady=20)
        euser=ctk.CTkEntry(w, placeholder_text="Usuario"); euser.pack(pady=10)
        epw=ctk.CTkEntry(w, placeholder_text="Contraseña", show="*"); epw.pack(pady=10)
        def go():
            if self.c.login(euser.get().strip(), epw.get().strip()): w.destroy()
            else: messagebox.showerror("Error", "Usuario o contraseña incorrectos")
        ctk.CTkButton(w, text="Ingresar", command=go).pack(pady=20)

    def registrar_usuario(self):
        w=ctk.CTkToplevel(self.app); w.geometry("400x500"); w.title("Registrar Usuario")
        ctk.CTkLabel(w, text="Nuevo Usuario", font=("Arial", 20)).pack(pady=10)
        enom=ctk.CTkEntry(w, placeholder_text="Nombre completo"); enom.pack(pady=5)
        euser=ctk.CTkEntry(w, placeholder_text="Usuario"); euser.pack(pady=5)
        epw=ctk.CTkEntry(w, placeholder_text="Contraseña", show="*"); epw.pack(pady=5)
        ctk.CTkLabel(w, text="Rol").pack(pady=5)
        cb=ctk.CTkComboBox(w, values=["administrador","gerente","encargado","proveedor"]); cb.set("encargado"); cb.pack(pady=5)
        def save():
            if not euser.get() or not epw.get() or not enom.get(): 
                messagebox.showwarning("Campos", "Completa todos los campos"); return
            self.c.registrar_usuario(Usuario(euser.get().strip(), epw.get().strip(), cb.get().strip(), enom.get().strip()))
            messagebox.showinfo("Éxito", "Usuario registrado"); w.destroy()
        ctk.CTkButton(w, text="Registrar", command=save).pack(pady=20)

    # --------- MENÚ POR ROL -------------
    def _on_login(self, payload):
        rol=payload["usuario"].get("rol","encargado")
        self.abrir_menu_por_rol(rol)

    def abrir_menu_por_rol(self, rol):
        menu = ctk.CTkToplevel(self.app); menu.geometry("800x600")
        menu.title(f"Menu - {rol.capitalize()}")
        ctk.CTkLabel(menu, text=f"Bienvenido, rol: {rol}", font=("Arial", 18)).pack(pady=20)

        def add_support():
            ctk.CTkButton(menu, text="Soporte", command=self.mostrar_soporte, width=120).place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

        if rol == "administrador":
            ctk.CTkButton(menu, text="Gestionar Productos", command=self.abrir_gestion_productos).pack(pady=10)
            ctk.CTkButton(menu, text="Gestionar Proveedores", command=self.abrir_gestion_proveedores).pack(pady=10)
            ctk.CTkButton(menu, text="Gestionar Usuarios", command=self.abrir_gestion_usuarios).pack(pady=10)
            ctk.CTkButton(menu, text="Asignar Proveedor a Producto", command=self.abrir_asignar_proveedor_producto).pack(pady=10)
            ctk.CTkButton(menu, text="Actualizar Proveedor de Producto", command=self.abrir_actualizar_proveedor_producto).pack(pady=10)
            ctk.CTkButton(menu, text="Promociones", command=self.abrir_promos).pack(pady=10)
            ctk.CTkButton(menu, text="Recepciones", command=self.abrir_recepciones).pack(pady=10)
            ctk.CTkButton(menu, text="Ajustes de Stock", command=self.abrir_ajustes).pack(pady=10)
            ctk.CTkButton(menu, text="Ordenes / Facturas (Venta)", command=self.abrir_ordenes).pack(pady=10)
            ctk.CTkButton(menu, text="Crear Orden de Compra", command=self.abrir_crear_orden_compra).pack(pady=10)
            ctk.CTkButton(menu, text="Consultar Facturas", command=lambda: self.abrir_consulta_facturas()).pack(pady=10)
            ctk.CTkButton(menu, text="Alertas", command=self.abrir_alertas).pack(pady=10)
        elif rol == "gerente":
            ctk.CTkButton(menu, text="Consultar Inventario", command=self.abrir_consulta_inventario).pack(pady=10)
            ctk.CTkButton(menu, text="Registrar Producto", command=self.abrir_registro_producto).pack(pady=10)
            ctk.CTkButton(menu, text="Crear Orden de Compra", command=self.abrir_crear_orden_compra).pack(pady=10)
            ctk.CTkButton(menu, text="Recepciones", command=self.abrir_recepciones).pack(pady=10)
            ctk.CTkButton(menu, text="Ajustes de Stock", command=self.abrir_ajustes).pack(pady=10)
            ctk.CTkButton(menu, text="Ordenes / Facturas (Venta)", command=self.abrir_ordenes).pack(pady=10)
            ctk.CTkButton(menu, text="Consultar Facturas", command=lambda: self.abrir_consulta_facturas()).pack(pady=10)
            ctk.CTkButton(menu, text="Alertas", command=self.abrir_alertas).pack(pady=10)
        elif rol == "encargado":
            ctk.CTkButton(menu, text="Registrar Recepcion", command=self.abrir_recepciones).pack(pady=10)
            ctk.CTkButton(menu, text="Actualizar Stock", command=self.abrir_ajustes).pack(pady=10)
            ctk.CTkButton(menu, text="Consultar Inventario", command=self.abrir_consulta_inventario).pack(pady=10)
        elif rol == "proveedor":
            ctk.CTkButton(menu, text="Ver Ordenes de Compra", command=self.abrir_ordenes_proveedor).pack(pady=10)
            ctk.CTkButton(menu, text="Generar Factura", command=self.abrir_generar_factura).pack(pady=10)
            ctk.CTkButton(menu, text="Consultar Facturas", command=lambda: self.abrir_consulta_facturas(True)).pack(pady=10)
        else:
            ctk.CTkLabel(menu, text="Rol sin opciones configuradas").pack(pady=10)

        add_support()
        ctk.CTkButton(menu, text="Cerrar Sesion", command=menu.destroy).pack(pady=20)

    # --------- UTILIDADES UI ------------
    def _build_table(self, parent, columns:tuple):
        cont=ctk.CTkFrame(parent); cont.pack(fill="both", expand=True, padx=10, pady=8)
        tree=ttk.Treeview(cont, columns=columns, show="headings")
        for c_ in columns: tree.heading(c_, text=c_); tree.column(c_, width=140)
        vsb=ttk.Scrollbar(cont, orient="vertical", command=tree.yview); tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True); vsb.pack(side="right", fill="y")
        return tree
    def _with_selected(self, tree:ttk.Treeview, fn):
        sel=tree.selection()
        if not sel: messagebox.showwarning("Selección","Selecciona un registro"); return
        vals=tree.item(sel[0])['values']
        if not vals: messagebox.showwarning("Selección","Registro inválido"); return
        oid=str(vals[0]); fn(oid)

    def _abrir_config_proveedor_producto(self, titulo:str, success_msg:str):
        win=self.abrir_nueva_ventana(titulo, "820x560")
        ctk.CTkLabel(win, text=titulo, font=("Arial", 18)).pack(pady=10)
        cols=("ID","Nombre","Marca","Categoria","Cantidad","Proveedor")
        tree=self._build_table(win, cols)

        def load():
            for item in tree.get_children(): tree.delete(item)
            for prod in self.c.listar_productos():
                tree.insert("", "end", values=(str(prod.get("_id")), prod.get("nombre",""), prod.get("marca",""),
                                               prod.get("categoria",""), int(prod.get("cantidad",0)), prod.get("proveedor", "Sin asignar")))

        load()
        proveedores=[p.get("nombre","") for p in self.c.listar_proveedores() if p.get("nombre")]
        if not proveedores:
            ctk.CTkLabel(win, text="Registra proveedores para asignarlos a productos").pack(pady=6)
        combo=ctk.CTkComboBox(win, values=proveedores or [""]); combo.pack(pady=8)

        def aplicar():
            sel=tree.selection()
            if not sel:
                messagebox.showwarning("Seleccion", "Selecciona un producto"); return
            proveedor=combo.get().strip()
            if not proveedor:
                messagebox.showwarning("Seleccion", "Selecciona un proveedor"); return
            prod_id=str(tree.item(sel[0])["values"][0])
            self.c.actualizar_producto(prod_id, {"proveedor": proveedor})
            messagebox.showinfo("Proveedor", success_msg)
            load()

        ctk.CTkButton(win, text="Guardar", command=aplicar).pack(pady=10)
        ctk.CTkButton(win, text="Cerrar", command=win.destroy).pack(pady=5)
        self.bus.subscribe("productos:cambio", lambda _=None: load())

    def abrir_asignar_proveedor_producto(self):
        self._abrir_config_proveedor_producto("Asignar Proveedor a Producto", "Proveedor actualizado")

    def abrir_actualizar_proveedor_producto(self):
        self._abrir_config_proveedor_producto("Actualizar Proveedor de Producto", "Proveedor actualizado")

    # =================== PRODUCTOS ===================
    def abrir_gestion_productos(self):
        win=self.abrir_nueva_ventana("Gestión de Productos")
        ef=ctk.CTkEntry(win, placeholder_text="Buscar por nombre / proveedor..."); ef.pack(pady=6)
        cols=("ID","Nombre","Marca","Categoría","Cantidad","Precio","Proveedor","Caducidad")
        tree=self._build_table(win, cols)
        expX, expC = ExcelExportStrategy(), CSVExportStrategy()

        def load():
            for i in tree.get_children(): tree.delete(i)
            txt=ef.get().strip()
            filtros=None
            if txt:
                filtros={"$or":[{"nombre":{"$regex":txt,"$options":"i"}},{"proveedor":{"$regex":txt,"$options":"i"}}]}
            for p in self.c.listar_productos(filtros):
                tree.insert("","end", values=(str(p.get("_id")),p.get("nombre",""),p.get("marca",""),
                                              p.get("categoria",""),int(p.get("cantidad",0)),
                                              float(p.get("precio",0.0)),p.get("proveedor",""),
                                              p.get("fecha_caducidad","N/A")))
        def nuevo():
            self.abrir_registro_producto(after_save=load)

        def editar(oid):
            prod=self.c.productos.get(oid)
            if not prod: messagebox.showerror("Edición","No encontrado"); return
            w=ctk.CTkToplevel(win); w.title("Editar producto"); w.geometry("380x560")
            entries={}
            fields=[("nombre",prod.get("nombre","")),("marca",prod.get("marca","")),("categoria",prod.get("categoria","")),
                    ("cantidad",str(prod.get("cantidad",0))),("precio",str(prod.get("precio",0.0))),
                    ("proveedor",prod.get("proveedor","")),("fecha_caducidad",prod.get("fecha_caducidad",""))]
            for k,v in fields:
                ctk.CTkLabel(w, text=k.capitalize()).pack(pady=2); e=ctk.CTkEntry(w); e.insert(0,v); e.pack(pady=2); entries[k]=e
            def save():
                try:
                    cambios={"nombre":entries['nombre'].get().strip(),"marca":entries['marca'].get().strip(),
                             "categoria":entries['categoria'].get().strip(),"cantidad":int(entries['cantidad'].get()),
                             "precio":float(entries['precio'].get()),"proveedor":entries['proveedor'].get().strip(),
                             "fecha_caducidad":entries['fecha_caducidad'].get().strip() or None}
                except Exception:
                    messagebox.showerror("Validación","Cantidad entero y precio decimal"); return
                self.c.actualizar_producto(oid, cambios); load(); w.destroy()
            ctk.CTkButton(w, text="Guardar cambios", command=save).pack(pady=10)

        def borrar(oid):
            if messagebox.askyesno("Confirmar","¿Eliminar el producto?"):
                self.c.eliminar_producto(oid); load()

        def export_common(strategy):
            columns=[tree.heading(c)['text'] for c in tree['columns']]
            rows=[tree.item(i)['values'] for i in tree.get_children()]
            sugerido=f"inventario_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
            strategy.export(columns, rows, sugerido)

        bar=ctk.CTkFrame(win); bar.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(bar, text="Buscar", command=load).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Nuevo", command=nuevo).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Editar", command=lambda: self._with_selected(tree, editar)).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Eliminar", command=lambda: self._with_selected(tree, borrar)).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Excel", command=lambda: export_common(expX)).pack(side="right", padx=4)
        ctk.CTkButton(bar, text="CSV", command=lambda: export_common(expC)).pack(side="right", padx=4)

        self.bus.subscribe("productos:cambio", lambda _=None: load())
        load()

    def abrir_registro_producto(self, after_save=None):
        proveedores = [p.get("nombre") for p in self.c.listar_proveedores()]
        w=ctk.CTkToplevel(self.app); w.geometry("400x600"); w.title("Registrar Producto")
        ctk.CTkLabel(w, text="Registrar Producto", font=("Arial", 18)).pack(pady=10)
        e_nom=ctk.CTkEntry(w, placeholder_text="Nombre"); e_nom.pack(pady=5)
        e_marca=ctk.CTkEntry(w, placeholder_text="Marca"); e_marca.pack(pady=5)
        e_cat=ctk.CTkEntry(w, placeholder_text="Categoría"); e_cat.pack(pady=5)
        e_cant=ctk.CTkEntry(w, placeholder_text="Cantidad"); e_cant.pack(pady=5)
        e_prec=ctk.CTkEntry(w, placeholder_text="Precio"); e_prec.pack(pady=5)
        cad_var=tk.BooleanVar(); chk=ctk.CTkCheckBox(w, text="¿Tiene caducidad?", variable=cad_var); chk.pack(pady=5)
        e_cad=ctk.CTkEntry(w, placeholder_text="YYYY-MM-DD"); e_cad.pack(pady=5); e_cad.configure(state="disabled")
        def toggle(): e_cad.configure(state=("normal" if cad_var.get() else "disabled")); 
        chk.configure(command=toggle)
        ctk.CTkLabel(w, text="Proveedor").pack(pady=5)
        cb=ctk.CTkComboBox(w, values=proveedores or [""]); cb.pack(pady=5)
        def save():
            try:
                p=Producto(e_nom.get().strip(), e_marca.get().strip(), e_cat.get().strip(),
                           int(e_cant.get()), float(e_prec.get()), cb.get().strip(),
                           e_cad.get().strip() if cad_var.get() and e_cad.get().strip() else None)
            except Exception:
                messagebox.showerror("Validación","Cantidad entero y precio decimal"); return
            if not p.nombre or not p.marca or not p.categoria or not p.proveedor:
                messagebox.showwarning("Validación","Completa los campos obligatorios"); return
            self.c.crear_producto(p); messagebox.showinfo("Éxito", "Producto registrado"); w.destroy()
            if after_save: after_save()
        ctk.CTkButton(w, text="Guardar", command=save).pack(pady=15)

    # =================== PROVEEDORES ==================
    def abrir_gestion_proveedores(self):
        win=self.abrir_nueva_ventana("Gestión de Proveedores")
        cols=("ID","Nombre","Empresa","Teléfono","Correo")
        tree=self._build_table(win, cols)

        def load():
            for i in tree.get_children(): tree.delete(i)
            for p in self.c.listar_proveedores():
                tree.insert("","end", values=(str(p.get("_id")), p.get("nombre",""), p.get("empresa",""),
                                              p.get("telefono",""), p.get("correo","")))
        def nuevo():
            w=ctk.CTkToplevel(win); w.geometry("380x420"); w.title("Nuevo proveedor")
            entries={}
            for k in ("nombre","empresa","telefono","correo"):
                ctk.CTkLabel(w, text=k.capitalize()).pack(pady=2); e=ctk.CTkEntry(w); e.pack(pady=2); entries[k]=e
            def save():
                pv=Proveedor(entries['nombre'].get().strip(), entries['empresa'].get().strip(),
                             entries['telefono'].get().strip(), entries['correo'].get().strip())
                if not pv.nombre: messagebox.showwarning("Validación","Nombre requerido"); return
                self.c.crear_proveedor(pv); w.destroy()
            ctk.CTkButton(w, text="Guardar", command=save).pack(pady=10)

        def editar(oid):
            p=self.c.proveedores.get(oid)
            if not p: messagebox.showerror("Edición","No encontrado"); return
            w=ctk.CTkToplevel(win); w.geometry("380x460"); w.title("Editar proveedor")
            entries={}
            for k in ("nombre","empresa","telefono","correo"):
                ctk.CTkLabel(w, text=k.capitalize()).pack(pady=2); e=ctk.CTkEntry(w); e.insert(0,p.get(k,"")); e.pack(pady=2); entries[k]=e
            def save():
                cambios={k: entries[k].get().strip() for k in entries}
                if not cambios['nombre']: messagebox.showwarning("Validación","Nombre requerido"); return
                self.c.actualizar_proveedor(oid, cambios); w.destroy()
            ctk.CTkButton(w, text="Guardar cambios", command=save).pack(pady=10)

        def borrar(oid):
            if messagebox.askyesno("Confirmar","¿Eliminar proveedor?"): self.c.eliminar_proveedor(oid)

        bar=ctk.CTkFrame(win); bar.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(bar, text="Nuevo", command=nuevo).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Editar", command=lambda: self._with_selected(tree, editar)).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Eliminar", command=lambda: self._with_selected(tree, borrar)).pack(side="left", padx=4)

        self.bus.subscribe("proveedores:cambio", lambda _=None: load())
        load()

    # =================== USUARIOS =====================
    def abrir_gestion_usuarios(self):
        win=self.abrir_nueva_ventana("Gestión de Usuarios")
        cols=("ID","Usuario","Rol","Nombre")
        tree=self._build_table(win, cols)

        def load():
            for i in tree.get_children(): tree.delete(i)
            for u in self.c.usuarios.all():
                tree.insert("","end", values=(str(u.get("_id")), u.get("usuario",""), u.get("rol",""), u.get("nombre","")))
        def nuevo():
            self.registrar_usuario()
        def editar(oid):
            u=self.c.usuarios.get(oid); 
            if not u: messagebox.showerror("Edición","No encontrado"); return
            w=ctk.CTkToplevel(win); w.geometry("360x420"); w.title("Editar usuario")
            entries={}
            for k in ("usuario","password","rol","nombre"):
                ctk.CTkLabel(w, text=k.capitalize()).pack(pady=2); e=ctk.CTkEntry(w); e.insert(0,u.get(k,"")); e.pack(pady=2); entries[k]=e
            def save():
                cambios={k: entries[k].get().strip() for k in entries}
                if not cambios['usuario']: messagebox.showwarning("Validación","Usuario requerido"); return
                self.c.actualizar_usuario(oid, cambios); w.destroy()
            ctk.CTkButton(w, text="Guardar cambios", command=save).pack(pady=10)
        def borrar(oid):
            if messagebox.askyesno("Confirmar","¿Eliminar usuario?"): self.c.eliminar_usuario(oid)

        bar=ctk.CTkFrame(win); bar.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(bar, text="Nuevo", command=nuevo).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Editar", command=lambda: self._with_selected(tree, editar)).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Eliminar", command=lambda: self._with_selected(tree, borrar)).pack(side="left", padx=4)

        self.bus.subscribe("usuarios:cambio", lambda _=None: load())
        load()

    # =================== RECEPCIONES ==================
    def abrir_recepciones(self):
        w=self.abrir_nueva_ventana("Recepción de Productos","800x600")
        ctk.CTkLabel(w, text="Registrar Recepción de Productos", font=("Arial", 18)).pack(pady=10)
        f=ctk.CTkFrame(w); f.pack(pady=10)
        # Producto
        prods=self.c.listar_productos(); valores=[f"{p.get('nombre')} — {str(p.get('_id'))}" for p in prods]
        ctk.CTkLabel(f, text="Producto").pack(pady=5); cb=ctk.CTkComboBox(f, values=valores); cb.pack(pady=5)
        # Proveedor
        ctk.CTkLabel(f, text="Proveedor").pack(pady=5)
        provs=[p.get('nombre') for p in self.c.listar_proveedores()]
        cbprov=ctk.CTkComboBox(f, values=provs); cbprov.pack(pady=5)
        # Cantidad, caducidad, estado
        ec=ctk.CTkEntry(f, placeholder_text="Cantidad"); ec.pack(pady=5)
        ecd=ctk.CTkEntry(f, placeholder_text="Fecha caducidad (YYYY-MM-DD)"); ecd.pack(pady=5)
        eest=ctk.CTkEntry(f, placeholder_text="Estado físico (nuevo/bueno/etc)"); eest.pack(pady=5)
        def go():
            try:
                sel=cb.get(); pid=sel.split("—")[-1].strip(); cant=int(ec.get()); prov=cbprov.get().strip()
                if not prov: messagebox.showwarning("Recepción","Selecciona proveedor"); return
                self.c.recepcionar(pid, cant, prov, ecd.get().strip() or "", eest.get().strip() or "bueno")
                messagebox.showinfo("Recepción","Stock actualizado")
            except Exception:
                messagebox.showerror("Recepción","Revisa selección y cantidad")
        ctk.CTkButton(w, text="Guardar recepción", command=go).pack(pady=10)

        # Historial de recepciones
        ctk.CTkLabel(w, text="Historial de Recepciones", font=("Arial", 16)).pack(pady=10)
        cols=("Producto","Proveedor","Cantidad","Fecha","Estado")
        tree=self._build_table(w, cols)
        def load_recep():
            for i in tree.get_children(): tree.delete(i)
            for r in self.c.hist.recepciones.find():
                tree.insert("","end", values=(r.get("producto_nombre",""), r.get("proveedor",""),
                                              r.get("cantidad",0), r.get("fecha_caducidad",""), r.get("estado_fisico","")))
        load_recep()

    # =================== AJUSTES =====================
    def abrir_ajustes(self):
        w=self.abrir_nueva_ventana("Ajustes de Stock","700x600")
        ctk.CTkLabel(w, text="Actualizar Stock Manualmente", font=("Arial", 18)).pack(pady=10)
        prods=self.c.listar_productos(); valores=[f"{p.get('nombre')} — {str(p.get('_id'))}" for p in prods]
        cb=ctk.CTkComboBox(w, values=valores); cb.pack(pady=5)
        ed=ctk.CTkEntry(w, placeholder_text="Delta (+ entrada / - salida)"); ed.pack(pady=5)
        em=ctk.CTkEntry(w, placeholder_text="Motivo"); em.pack(pady=5)
        def go():
            try:
                pid=cb.get().split("—")[-1].strip(); delta=int(ed.get()); self.c.ajustar_stock(pid, delta, em.get().strip() or "ajuste")
                messagebox.showinfo("Ajuste","Stock actualizado")
            except ValueError as ve:
                messagebox.showerror("Ajuste", str(ve))
            except Exception:
                messagebox.showerror("Ajuste","Revisa selección y delta")
        ctk.CTkButton(w, text="Aplicar ajuste", command=go).pack(pady=10)

        # Historial
        ctk.CTkLabel(w, text="Historial de Ajustes", font=("Arial", 16)).pack(pady=10)
        cols=("Producto","Tipo","Cantidad","Motivo","Fecha")
        tree=self._build_table(w, cols)
        def load_adj():
            for i in tree.get_children(): tree.delete(i)
            for a in self.c.hist.ajustes.find():
                tree.insert("","end", values=(a.get("producto_nombre",""), a.get("tipo_ajuste",""),
                                              a.get("cantidad",0), a.get("motivo",""), a.get("fecha","")))
        load_adj()

    # =================== PROMOS ======================
    def abrir_promos(self):
        win=self.abrir_nueva_ventana("Promociones")
        cols=("ID","ProductoID","Descuento%","Inicio","Fin","Activa")
        tree=self._build_table(win, cols)

        def load():
            for i in tree.get_children(): tree.delete(i)
            for pr in self.c.listar_promos():
                tree.insert("","end", values=(str(pr.get("_id")), pr.get("producto_id",""),
                                              int(pr.get("descuento",0)), pr.get("inicio",""),
                                              pr.get("fin",""), bool(pr.get("activa",True))))
        def nueva():
            w=ctk.CTkToplevel(win); w.geometry("420x400"); w.title("Nueva promoción")
            eprod=ctk.CTkEntry(w, placeholder_text="Producto (ID)"); eprod.pack(pady=5)
            ed=ctk.CTkEntry(w, placeholder_text="Descuento %"); ed.pack(pady=5)
            ei=ctk.CTkEntry(w, placeholder_text="Inicio YYYY-MM-DD"); ei.pack(pady=5)
            ef=ctk.CTkEntry(w, placeholder_text="Fin YYYY-MM-DD"); ef.pack(pady=5)
            def save():
                try:
                    pr=Promocion(eprod.get().strip(), int(ed.get()), ei.get().strip(), ef.get().strip(), True)
                    self.c.crear_promo(pr); w.destroy()
                except Exception:
                    messagebox.showerror("Promo","Datos inválidos")
            ctk.CTkButton(w, text="Guardar", command=save).pack(pady=10)
        def editar(oid):
            pr=self.c.promos.get(oid)
            if not pr: messagebox.showerror("Promo","No encontrada"); return
            w=ctk.CTkToplevel(win); w.geometry("420x420"); w.title("Editar promoción")
            entries={}
            for k in ("producto_id","descuento","inicio","fin","activa"):
                ctk.CTkLabel(w, text=k.capitalize()).pack(pady=2); e=ctk.CTkEntry(w); e.insert(0, str(pr.get(k,""))); e.pack(pady=2); entries[k]=e
            def save():
                cambios={k: (int(entries[k].get()) if k=="descuento" else (entries[k].get().strip() if k!="activa" else entries[k].get().strip().lower() in ("true","1","si"))) for k in entries}
                self.c.actualizar_promo(oid, cambios); w.destroy()
            ctk.CTkButton(w, text="Guardar cambios", command=save).pack(pady=10)
        def borrar(oid):
            if messagebox.askyesno("Confirmar","¿Eliminar la promoción?"): self.c.eliminar_promo(oid)
        bar=ctk.CTkFrame(win); bar.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(bar, text="Nueva", command=nueva).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Editar", command=lambda: self._with_selected(tree, editar)).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Eliminar", command=lambda: self._with_selected(tree, borrar)).pack(side="left", padx=4)
        self.bus.subscribe("promos:cambio", lambda _=None: load())
        load()

    # =================== ÓRDENES / FACTURAS =========
    def abrir_ordenes(self):
        w=ctk.CTkToplevel(self.app); w.geometry("860x640"); w.title("Ordenes / Facturas (Venta)")
        ctk.CTkLabel(w, text="Cliente", font=("Arial", 14)).pack(pady=6)
        ecli=ctk.CTkEntry(w); ecli.pack(pady=5)

        prods=self.c.listar_productos(); items=[]
        ctk.CTkLabel(w, text="Agregar producto").pack(pady=6)
        opciones=[f"{p.get('nombre','')} | {str(p.get('_id'))}" for p in prods]
        cb=ctk.CTkComboBox(w, values=opciones or [""]); cb.pack(pady=4)
        ctk.CTkLabel(w, text="Cantidad").pack(pady=2)
        eq=ctk.CTkEntry(w); eq.insert(0, "1"); eq.pack(pady=2)

        cart_cols=("ProductoID","Nombre","Cantidad","PrecioUnit")
        cart=self._build_table(w, cart_cols)

        def add_item():
            try:
                sel=cb.get()
                if "|" not in sel:
                    raise ValueError
                pid=sel.split('|')[-1].strip()
                qty=int(eq.get())
                if qty<=0:
                    raise ValueError
                prod=None
                for registro in prods:
                    if str(registro.get('_id'))==pid:
                        prod=registro
                        break
                if not prod:
                    raise ValueError
                precio=self.c.precio_con_promo(prod)
                items.append({"producto_id": pid, "cantidad": qty, "nombre": prod.get("nombre",""), "precio_unitario": precio})
                cart.insert("", "end", values=(pid, prod.get("nombre",""), qty, precio))
            except Exception:
                messagebox.showerror("Orden", "Datos invalidos")

        def facturar():
            if not items:
                messagebox.showwarning("Orden", "Agrega articulos"); return
            try:
                cliente=ecli.get().strip() or "Mostrador"
                orden_id=self.c.crear_orden(cliente, items)
                factura_items=[{"producto": it.get("nombre",""), "cantidad": it.get("cantidad",0), "precio_unitario": it.get("precio_unitario",0.0)} for it in items]
                self.c.crear_factura(orden_id, factura_items)
                cols=["ProductoID","Nombre","Cantidad","PrecioUnit"]
                rows=[cart.item(i)["values"] for i in cart.get_children()]
                sugerido=f"venta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                CSVExportStrategy().export(cols, rows, sugerido)
                messagebox.showinfo("Orden", f"Orden creada: {orden_id}")
                w.destroy()
            except Exception as err:
                messagebox.showerror("Orden", str(err))

        ctk.CTkButton(w, text="Agregar", command=add_item).pack(pady=6)
        ctk.CTkButton(w, text="Facturar", command=facturar).pack(pady=6)

    def abrir_crear_orden_compra(self):
        win=self.abrir_nueva_ventana("Crear Orden de Compra", "820x640")
        ctk.CTkLabel(win, text="Crear Orden de Compra", font=("Arial", 18)).pack(pady=10)
        proveedores=[p.get("nombre","") for p in self.c.listar_proveedores() if p.get("nombre")]
        if not proveedores:
            ctk.CTkLabel(win, text="No hay proveedores registrados").pack(pady=4)
        combo=ctk.CTkComboBox(win, values=proveedores or [""])
        combo.pack(pady=6)

        productos=self.c.listar_productos()
        frame=ctk.CTkScrollableFrame(win, height=320)
        frame.pack(pady=10, fill="both", expand=True)
        registros=[]
        for prod in productos:
            var=tk.BooleanVar()
            cant=tk.StringVar(value="0")
            fila=ctk.CTkFrame(frame)
            fila.pack(fill="x", pady=2, padx=2)
            tk.Checkbutton(fila, text=f"{prod.get('nombre','')} | Stock: {prod.get('cantidad',0)}", variable=var).pack(side="left", padx=4)
            tk.Entry(fila, textvariable=cant, width=6).pack(side="right", padx=4)
            registros.append((prod, var, cant))

        ctk.CTkLabel(win, text="Fecha estimada (YYYY-MM-DD)").pack(pady=6)
        efecha=ctk.CTkEntry(win)
        efecha.pack(pady=4)

        def guardar():
            proveedor=combo.get().strip()
            fecha=efecha.get().strip()
            seleccion=[]
            for prod, var, cant in registros:
                if var.get():
                    try:
                        cantidad=int(cant.get())
                        if cantidad<=0:
                            raise ValueError
                    except Exception:
                        messagebox.showerror("Orden", f"Cantidad invalida para {prod.get('nombre','')}")
                        return
                    seleccion.append({"producto_id": str(prod.get("_id")), "cantidad": cantidad})
            if not proveedor or not fecha or not seleccion:
                messagebox.showwarning("Orden", "Completa proveedor, fecha y productos"); return
            try:
                self.c.crear_orden_compra(proveedor, seleccion, fecha)
                messagebox.showinfo("Orden", "Orden de compra creada")
                win.destroy()
            except Exception as err:
                messagebox.showerror("Orden", str(err))

        ctk.CTkButton(win, text="Guardar Orden", command=guardar).pack(pady=10)
        ctk.CTkButton(win, text="Cancelar", command=win.destroy).pack(pady=4)

    def abrir_ordenes_proveedor(self):
        usuario=self.c.usuario_actual or {}
        nombre=usuario.get("nombre","")
        if not nombre:
            messagebox.showwarning("Ordenes", "El usuario no tiene un nombre asociado"); return
        win=self.abrir_nueva_ventana("Ordenes de Compra", "860x600")
        ctk.CTkLabel(win, text=f"Ordenes para {nombre}", font=("Arial", 18)).pack(pady=10)
        cols=("ID","Proveedor","Fecha","Entrega","Estado","Productos")
        tree=self._build_table(win, cols)

        def render():
            for item in tree.get_children(): tree.delete(item)
            for orden in self.c.ordenes_por_proveedor(nombre):
                if orden.get("tipo")!="compra":
                    continue
                productos=", ".join([f"{itm.get('nombre','')} x{itm.get('cantidad',0)}" for itm in orden.get("items",[])])
                tree.insert("", "end", values=(str(orden.get("_id")), orden.get("proveedor_o_cliente",""), orden.get("fecha",""),
                                               orden.get("fecha_entrega",""), orden.get("estado",""), productos))

        def confirmar(oid):
            try:
                self.c.actualizar_orden(oid, {"estado": "confirmada"})
                messagebox.showinfo("Orden", "Orden confirmada")
                render()
            except Exception as err:
                messagebox.showerror("Orden", str(err))

        bar=ctk.CTkFrame(win); bar.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(bar, text="Confirmar", command=lambda: self._with_selected(tree, confirmar)).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Actualizar", command=render).pack(side="left", padx=4)

        self.bus.subscribe("ordenes:cambio", lambda _=None: render())
        render()

    def abrir_generar_factura(self):
        usuario=self.c.usuario_actual or {}
        nombre=usuario.get("nombre","")
        if not nombre:
            messagebox.showwarning("Facturas", "El usuario no tiene un nombre asociado"); return
        win=self.abrir_nueva_ventana("Generar Factura", "860x600")
        ctk.CTkLabel(win, text=f"Ordenes confirmadas de {nombre}", font=("Arial", 18)).pack(pady=10)
        cols=("ID","Proveedor","Fecha","Entrega","Estado","Productos")
        tree=self._build_table(win, cols)

        def load():
            for item in tree.get_children(): tree.delete(item)
            ordenes=self.c.ordenes_por_proveedor(nombre, estado="confirmada", solo_factura_pendiente=True)
            for orden in ordenes:
                productos=", ".join([f"{itm.get('nombre','')} x{itm.get('cantidad',0)}" for itm in orden.get("items",[])])
                tree.insert("", "end", values=(str(orden.get("_id")), orden.get("proveedor_o_cliente",""), orden.get("fecha",""),
                                               orden.get("fecha_entrega",""), orden.get("estado",""), productos))

        def facturar():
            sel=tree.selection()
            if not sel:
                messagebox.showwarning("Facturas", "Selecciona una orden"); return
            oid=str(tree.item(sel[0])["values"][0])
            orden=self.c.ordenes.get(oid)
            if not orden:
                messagebox.showerror("Facturas", "No se encontro la orden"); return
            top=ctk.CTkToplevel(win); top.geometry("420x520"); top.title("Detalle de factura")
            entradas={}
            for item in orden.get("items", []):
                frame=ctk.CTkFrame(top); frame.pack(fill="x", pady=4, padx=4)
                ctk.CTkLabel(frame, text=f"{item.get('nombre','')} x{item.get('cantidad',0)}").pack(side="left", padx=4)
                entry=ctk.CTkEntry(frame)
                entry.pack(side="right", padx=4)
                entradas[item.get("nombre","")]=(item, entry)

            def guardar():
                detalles=[]
                for nombre_item, (info, entry) in entradas.items():
                    try:
                        precio=float(entry.get())
                        if precio<0:
                            raise ValueError
                    except Exception:
                        messagebox.showerror("Facturas", f"Precio invalido para {nombre_item}")
                        return
                    detalles.append({"producto": nombre_item, "cantidad": info.get("cantidad",0), "precio_unitario": precio})
                try:
                    self.c.crear_factura(oid, detalles)
                    messagebox.showinfo("Facturas", "Factura generada")
                    top.destroy()
                    load()
                except Exception as err:
                    messagebox.showerror("Facturas", str(err))

            ctk.CTkButton(top, text="Guardar Factura", command=guardar).pack(pady=12)

        ctk.CTkButton(win, text="Generar Factura", command=facturar).pack(pady=8)
        ctk.CTkButton(win, text="Actualizar", command=load).pack(pady=4)
        self.bus.subscribe("ordenes:cambio", lambda _=None: load())
        self.bus.subscribe("facturas:cambio", lambda _=None: load())
        load()

    def abrir_consulta_facturas(self, solo_propias:bool=False):
        filtros={}
        if solo_propias:
            usuario=self.c.usuario_actual or {}
            nombre=usuario.get("nombre","")
            if not nombre:
                messagebox.showwarning("Facturas", "El usuario no tiene un nombre asociado"); return
            filtros["proveedor"]=nombre
        win=self.abrir_nueva_ventana("Consulta de Facturas", "900x600")
        ctk.CTkLabel(win, text="Facturas", font=("Arial", 18)).pack(pady=10)
        cols=("Orden","Proveedor","Total","Fecha","Productos")
        tree=self._build_table(win, cols)

        def load():
            for item in tree.get_children(): tree.delete(item)
            for factura in self.c.listar_facturas(filtros):
                productos=", ".join([f"{p.get('producto','')} x{p.get('cantidad',0)} = {p.get('subtotal',0):.2f}" for p in factura.get("productos",[])])
                tree.insert("", "end", values=(factura.get("orden_id",""), factura.get("proveedor",""),
                                               factura.get("precio_total",0), factura.get("fecha_emision",""), productos))

        ctk.CTkButton(win, text="Actualizar", command=load).pack(pady=8)
        self.bus.subscribe("facturas:cambio", lambda _=None: load())
        load()

    def mostrar_soporte(self):
        win=ctk.CTkToplevel(self.app); win.geometry("400x300"); win.title("Soporte Tecnico")
        ctk.CTkLabel(win, text="Soporte Tecnico", font=("Arial", 20)).pack(pady=20)
        ctk.CTkLabel(win, text="Nombre: Edgar Espinosa", font=("Arial", 14)).pack(pady=5)
        ctk.CTkLabel(win, text="Correo: edgar.espinosa@lasallistas.org.mx", font=("Arial", 14)).pack(pady=5)
        ctk.CTkLabel(win, text="Telefono: 5536977657", font=("Arial", 14)).pack(pady=5)
        def copiar():
            win.clipboard_clear()
            win.clipboard_append("edgar.espinosa@lasallistas.org.mx")
            messagebox.showinfo("Soporte", "Correo copiado al portapapeles")
        ctk.CTkButton(win, text="Copiar Correo", command=copiar).pack(pady=10)
        ctk.CTkButton(win, text="Cerrar", command=win.destroy).pack(pady=10)

    def abrir_alertas(self):
        data=self.c.alertas()
        win=self.abrir_nueva_ventana("Alertas","980x480")
        frame=ctk.CTkFrame(win); frame.pack(fill="both", expand=True, padx=10, pady=10)
        cols=("ID","Nombre","Cantidad","Proveedor","Caducidad")
        tree_low=self._build_table(frame, cols); tree_exp=self._build_table(frame, cols)
        def fill(tree, items):
            for i in tree.get_children(): tree.delete(i)
            for p in items:
                tree.insert("","end", values=(str(p.get("_id")), p.get("nombre",""), int(p.get("cantidad",0)),
                                              p.get("proveedor",""), p.get("fecha_caducidad","N/A")))
        ctk.CTkLabel(frame, text="Stock bajo (≤10)", font=("Arial",16)).pack(anchor="w")
        tree_low.pack(fill="both", expand=True, pady=6)
        ctk.CTkLabel(frame, text="Próxima caducidad (≤15 días)", font=("Arial",16)).pack(anchor="w")
        tree_exp.pack(fill="both", expand=True, pady=6)
        fill(tree_low, data["stock_bajo"]); fill(tree_exp, data["proxima_caducidad"])

    # =================== CONSULTA / EXPORT ==========
    def abrir_consulta_inventario(self):
        ventana = self.abrir_nueva_ventana("Consulta de Inventario", "950x650")
        ctk.CTkLabel(ventana, text="Consulta de Inventario", font=("Arial", 18)).pack(pady=10)

        frame_filtros = ctk.CTkFrame(ventana); frame_filtros.pack(pady=10)
        e_nom=ctk.CTkEntry(frame_filtros, placeholder_text="Nombre"); e_nom.pack(side="left", padx=5)
        e_cat=ctk.CTkEntry(frame_filtros, placeholder_text="Categoría"); e_cat.pack(side="left", padx=5)
        e_prov=ctk.CTkEntry(frame_filtros, placeholder_text="Proveedor"); e_prov.pack(side="left", padx=5)

        cols=("Nombre","Marca","Categoría","Cantidad","Precio","Caducidad","Proveedor")
        tree = self._build_table(ventana, cols)

        def aplicar():
            filtros={}
            if e_nom.get(): filtros["nombre"]={"$regex": e_nom.get(), "$options":"i"}
            if e_cat.get(): filtros["categoria"]={"$regex": e_cat.get(), "$options":"i"}
            if e_prov.get(): filtros["proveedor"]={"$regex": e_prov.get(), "$options":"i"}
            self._cargar_filtrado(tree, filtros)
        def limpiar():
            e_nom.delete(0,"end"); e_cat.delete(0,"end"); e_prov.delete(0,"end")
            self._cargar_filtrado(tree, {})
        def bajo():
            self._cargar_filtrado(tree, {"cantidad":{"$lt":10}})
        def proximos():
            hoy=datetime.now(); limite=hoy+timedelta(days=15)
            self._cargar_filtrado(tree, {"fecha_caducidad":{"$gte": hoy.strftime("%Y-%m-%d"), "$lte": limite.strftime("%Y-%m-%d")}})
        ctk.CTkButton(frame_filtros, text="Buscar", command=aplicar).pack(side="left", padx=5)
        ctk.CTkButton(frame_filtros, text="Limpiar", command=limpiar).pack(side="left", padx=5)
        ctk.CTkButton(frame_filtros, text="Stock bajo", command=bajo).pack(side="left", padx=5)
        ctk.CTkButton(frame_filtros, text="Próximos a caducar", command=proximos).pack(side="left", padx=5)

        self._cargar_filtrado(tree, {})
        # Export
        ctk.CTkButton(ventana, text="Exportar Excel", command=lambda: self._export_tree(tree,"inventario")).pack(pady=6)
        ctk.CTkButton(ventana, text="Exportar CSV", command=lambda: self._export_tree(tree,"inventario",csv_only=True)).pack(pady=3)

    def _cargar_filtrado(self, tree, filtros):
        for i in tree.get_children(): tree.delete(i)
        for prod in self.c.listar_productos(filtros):
            tree.insert("", "end", values=(prod.get("nombre",""), prod.get("marca",""), prod.get("categoria",""),
                                           prod.get("cantidad",0), prod.get("precio",0.0),
                                           prod.get("fecha_caducidad","N/A"), prod.get("proveedor","N/A")))

    def _export_tree(self, tree, base, csv_only=False):
        cols=[tree.heading(c)["text"] for c in tree["columns"]]
        rows=[tree.item(i)["values"] for i in tree.get_children()]
        if not rows:
            messagebox.showinfo("Sin datos","No hay registros para exportar"); return
        fecha=datetime.now().strftime("%Y-%m-%d")
        if csv_only: CSVExportStrategy().export(cols, rows, f"{base}_{fecha}.xlsx")
        else: ExcelExportStrategy().export(cols, rows, f"{base}_{fecha}.xlsx")

    # ------------------------------------
    def run(self): self.app.mainloop()

# ============================== SELF-TESTS ===================================
class TestFailure(Exception): ...
def assert_eq(a,b,msg=""):
    if a!=b: raise TestFailure(msg or f"{a}!={b}")

def run_selftests():
    print("[TEST] Iniciando self-tests...")
    bus=EventBus(); c=InventarioController(bus)
    if not c.usuarios.get_by_user("admin"):
        c.registrar_usuario(Usuario("admin","admin","administrador","Admin"))
    assert_eq(c.login("admin","admin"), True, "login admin")

    prov_id=c.crear_proveedor(Proveedor("ProvA","Emp","555","a@a.com"))
    prod_id=c.crear_producto(Producto("Manzana","Verde","Fruta",10,10.0,"ProvA","2026-01-01"))

    c.ajustar_stock(prod_id, -2, "merma")
    prod=c.productos.get(prod_id); assert_eq(int(prod.get("cantidad")), 8, "ajuste -2")

    hoy=date.today().strftime("%Y-%m-%d"); fin=(date.today()+timedelta(days=7)).strftime("%Y-%m-%d")
    c.crear_promo(Promocion(prod_id, 20, hoy, fin, True))
    price=c.precio_con_promo(c.productos.get(prod_id)); assert_eq(price, 8.0, "precio con 20%")

    venta_items=[{"producto_id": prod_id, "cantidad": 2}]
    orden_venta=c.crear_orden("Mostrador", venta_items)
    prod=c.productos.get(prod_id); assert_eq(int(prod.get("cantidad")), 6, "stock tras orden")
    doc_venta=c.ordenes.get(orden_venta); assert_eq(round(float(doc_venta.get("total")),2), 16.0, "total orden")
    factura_venta=c.crear_factura(orden_venta, [{"producto": "Manzana", "cantidad": 2, "precio_unitario": 8.0}])
    doc_factura_venta=c.facturas.get(factura_venta); assert_eq(round(float(doc_factura_venta.get("precio_total")),2), 16.0, "factura venta total")
    doc_venta_final=c.ordenes.get(orden_venta); assert_eq(doc_venta_final.get("facturada"), True, "orden venta facturada")

    compra_id=c.crear_orden_compra("ProvA", [{"producto_id": prod_id, "cantidad": 5}], "2026-02-01")
    doc_compra=c.ordenes.get(compra_id); assert_eq(doc_compra.get("tipo"), "compra", "tipo compra")
    assert_eq(doc_compra.get("estado"), "pendiente", "estado pendiente")
    c.actualizar_orden(compra_id, {"estado": "confirmada"})
    doc_compra_conf=c.ordenes.get(compra_id); assert_eq(doc_compra_conf.get("estado"), "confirmada", "estado confirmada")
    factura_compra=c.crear_factura(compra_id, [{"producto": "Manzana", "cantidad": 5, "precio_unitario": 9.5}])
    doc_factura_compra=c.facturas.get(factura_compra); assert_eq(round(float(doc_factura_compra.get("precio_total")),2), 47.5, "factura compra total")
    doc_compra_final=c.ordenes.get(compra_id); assert_eq(doc_compra_final.get("facturada"), True, "orden compra facturada")
    ordenes_prov=c.ordenes_por_proveedor("ProvA")
    assert_eq(any(str(o.get("_id"))==str(compra_id) for o in ordenes_prov), True, "orden proveedor listada")
    facturas_prov=c.listar_facturas({"proveedor": "ProvA"})
    assert_eq(any(str(f.get("_id"))==str(factura_compra) for f in facturas_prov), True, "factura proveedor listada")

    cols=["A","B"]; rows=[[1,2],[3,4]]; CSVExportStrategy().export(cols, rows, "selftest.xlsx")
    print("[TEST] OK")

# ================================= BOOT =====================================
if __name__ == "__main__":
    if "--selftest" in (a.lower() for a in sys.argv[1:]):
        run_selftests(); sys.exit(0)

    bus=EventBus(); controller=InventarioController(bus)
    if not GUI_AVAILABLE:
        print("GUI no disponible en este entorno. Ejecuta --selftest para pruebas.")
        run_selftests(); sys.exit(0)
    MainView(controller).run()
