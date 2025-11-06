

from __future__ import annotations
import os
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Protocol
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk

from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

# =============== PATRÓN 1: SINGLETON para conexión MongoDB ==================
class MongoProvider:
    _instance: Optional["MongoProvider"] = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            load_dotenv()
            uri = os.getenv("MONGO_URI") or (
                # Fallback: usa la conexión que tenías en el proyecto original
                "mongodb+srv://edgarallanespinosah:rBJZFh6ZF6xZYXzh@cluster0.yvlnuwz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
            )
            client = MongoClient(uri)
            cls._instance.client = client
            cls._instance.db = client[os.getenv("DB_NAME", "supermercado")]
        return cls._instance
    @property
    def db(self):
        return self._db
    @db.setter
    def db(self, v):
        self._db = v

# ============================ PATRÓN 2: OBSERVER =============================
class EventBus:
    def __init__(self):
        self._subs: Dict[str, List] = {}
    def subscribe(self, event: str, callback):
        self._subs.setdefault(event, []).append(callback)
    def emit(self, event: str, payload: Any = None):
        for cb in self._subs.get(event, []):
            try:
                cb(payload)
            except Exception as e:
                print(f"Listener error on {event}: {e}")

# ============================== MODELOS =====================================
@dataclass
class Producto:
    nombre: str
    marca: str
    categoria: str
    cantidad: int
    precio: float
    proveedor: str
    fecha_caducidad: Optional[str] = None  # YYYY-MM-DD
    estado: str = "activo"
    _id: Optional[str] = None

@dataclass
class Proveedor:
    nombre: str
    contacto: str
    telefono: str
    correo: str
    direccion: str
    _id: Optional[str] = None

@dataclass
class Usuario:
    usuario: str
    password: str
    rol: str  # Administrador, Gerente, Encargado, Proveedor
    nombre: str = ""
    _id: Optional[str] = None

# ============================ REPOSITORIOS ==================================
class ProductoRepository:
    def __init__(self, db):
        self.col = db["productos"]
    def all(self, filtros: Optional[Dict] = None):
        return list(self.col.find(filtros or {}))
    def get(self, oid: str):
        return self.col.find_one({"_id": ObjectId(oid)})
    def insert(self, p: Producto) -> str:
        data = asdict(p); data.pop("_id", None)
        res = self.col.insert_one(data); return str(res.inserted_id)
    def update(self, oid: str, cambios: Dict[str, Any]):
        self.col.update_one({"_id": ObjectId(oid)}, {"$set": cambios})
    def delete(self, oid: str):
        self.col.delete_one({"_id": ObjectId(oid)})

class ProveedorRepository:
    def __init__(self, db):
        self.col = db["proveedores"]
    def all(self, filtros: Optional[Dict] = None):
        return list(self.col.find(filtros or {}))
    def get(self, oid: str):
        return self.col.find_one({"_id": ObjectId(oid)})
    def insert(self, p: Proveedor) -> str:
        data = asdict(p); data.pop("_id", None)
        res = self.col.insert_one(data); return str(res.inserted_id)
    def update(self, oid: str, cambios: Dict[str, Any]):
        self.col.update_one({"_id": ObjectId(oid)}, {"$set": cambios})
    def delete(self, oid: str):
        self.col.delete_one({"_id": ObjectId(oid)})

class UsuarioRepository:
    def __init__(self, db):
        self.col = db["usuarios"]
    def all(self, filtros: Optional[Dict] = None):
        return list(self.col.find(filtros or {}))
    def get(self, oid: str):
        return self.col.find_one({"_id": ObjectId(oid)})
    def get_by_user(self, usuario: str):
        return self.col.find_one({"usuario": usuario})
    def insert(self, u: Usuario) -> str:
        data = asdict(u); data.pop("_id", None)
        res = self.col.insert_one(data); return str(res.inserted_id)
    def update(self, oid: str, cambios: Dict[str, Any]):
        self.col.update_one({"_id": ObjectId(oid)}, {"$set": cambios})
    def delete(self, oid: str):
        self.col.delete_one({"_id": ObjectId(oid)})

class HistorialRepository:
    def __init__(self, db):
        self.historial = db["historial_cambios_stock"]
        self.ajustes = db["ajustes_stock"]
    def log_ajuste(self, producto_id: str, nombre: str, antes: int, despues: int, usuario: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.historial.insert_one({
            "producto_id": producto_id,
            "nombre": nombre,
            "cantidad_anterior": antes,
            "cantidad_nueva": despues,
            "fecha": now,
            "usuario": usuario,
        })
    def log_ajuste_simple(self, producto_id: str, nombre: str, tipo: str, cantidad: int, motivo: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.ajustes.insert_one({
            "producto_id": producto_id,
            "producto_nombre": nombre,
            "tipo_ajuste": tipo,
            "cantidad": cantidad,
            "motivo": motivo,
            "fecha": now,
        })

# =============== PATRÓN 3: STRATEGY (Exportación) ============================
class ExportStrategy(Protocol):
    def export(self, columns: List[str], rows: List[List[Any]], suggested_name: str) -> None: ...

class ExcelExportStrategy:
    def export(self, columns: List[str], rows: List[List[Any]], suggested_name: str) -> None:
        try:
            from openpyxl import Workbook
        except Exception as exc:
            messagebox.showerror("Exportación", f"openpyxl no disponible: {exc}")
            return
        ruta = filedialog.asksaveasfilename(
            initialfile=suggested_name,
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Guardar reporte"
        )
        if not ruta:
            return
        wb = Workbook(); ws = wb.active
        fecha = datetime.now().strftime("%Y-%m-%d")
        ws.append([f"Reporte generado el {fecha}"]); ws.append([]); ws.append(columns)
        for r in rows: ws.append(r)
        wb.save(ruta)
        messagebox.showinfo("Exportación", f"Archivo guardado:
{ruta}")

class CSVExportStrategy:
    def export(self, columns: List[str], rows: List[List[Any]], suggested_name: str) -> None:
        import csv
        ruta = filedialog.asksaveasfilename(
            initialfile=suggested_name.replace(".xlsx", ".csv"),
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Guardar CSV"
        )
        if not ruta:
            return
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([f"Reporte generado el {datetime.now().strftime('%Y-%m-%d')}"])
            w.writerow([]); w.writerow(columns); w.writerows(rows)
        messagebox.showinfo("Exportación", f"CSV guardado:
{ruta}")

# ================================ CONTROLLER ================================
class InventarioController:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.db = MongoProvider().db
        self.productos = ProductoRepository(self.db)
        self.proveedores = ProveedorRepository(self.db)
        self.usuarios = UsuarioRepository(self.db)
        self.historial = HistorialRepository(self.db)
        self.usuario_actual: Optional[Dict[str, Any]] = None

    # --- autenticación / usuarios ---
    def login(self, usuario: str, password: str) -> bool:
        u = self.usuarios.get_by_user(usuario)
        if u and u.get("password") == password:
            self.usuario_actual = u
            self.bus.emit("auth:login", {"usuario": u})
            return True
        return False
    def crear_usuario(self, u: Usuario) -> str:
        oid = self.usuarios.insert(u); self.bus.emit("usuarios:cambio"); return oid
    def actualizar_usuario(self, oid: str, cambios: Dict[str, Any]):
        self.usuarios.update(oid, cambios); self.bus.emit("usuarios:cambio")
    def eliminar_usuario(self, oid: str):
        self.usuarios.delete(oid); self.bus.emit("usuarios:cambio")

    # --- productos ---
    def listar_productos(self, filtros: Optional[Dict] = None) -> List[Dict[str, Any]]:
        return self.productos.all(filtros)
    def crear_producto(self, p: Producto) -> str:
        oid = self.productos.insert(p); self.bus.emit("productos:cambio"); return oid
    def actualizar_producto(self, oid: str, cambios: Dict[str, Any]):
        self.productos.update(oid, cambios); self.bus.emit("productos:cambio")
    def eliminar_producto(self, oid: str):
        self.productos.delete(oid); self.bus.emit("productos:cambio")

    # --- proveedores ---
    def listar_proveedores(self, filtros: Optional[Dict] = None) -> List[Dict[str, Any]]:
        return self.proveedores.all(filtros)
    def crear_proveedor(self, p: Proveedor) -> str:
        oid = self.proveedores.insert(p); self.bus.emit("proveedores:cambio"); return oid
    def actualizar_proveedor(self, oid: str, cambios: Dict[str, Any]):
        self.proveedores.update(oid, cambios); self.bus.emit("proveedores:cambio")
    def eliminar_proveedor(self, oid: str):
        self.proveedores.delete(oid); self.bus.emit("proveedores:cambio")

    # --- recepciones (ajuste positivo de stock) ---
    def recepcionar(self, producto_oid: str, cantidad: int, proveedor_nombre: str, motivo: str = "recepción"):
        prod = self.productos.get(producto_oid)
        if not prod:
            raise ValueError("Producto no encontrado")
        antes = int(prod.get("cantidad", 0)); despues = antes + int(cantidad)
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva")
        self.productos.update(producto_oid, {"cantidad": despues, "proveedor": proveedor_nombre})
        usuario = (self.usuario_actual or {}).get("nombre", "sistema")
        self.historial.log_ajuste(producto_oid, prod.get("nombre", ""), antes, despues, usuario)
        self.historial.log_ajuste_simple(producto_oid, prod.get("nombre", ""), "entrada", cantidad, motivo)
        self.bus.emit("productos:cambio")

    # --- alertas ---
    def alertas(self, low_stock: int = 10, dias_cad: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        hoy = datetime.now().date()
        bajos, proximos = [], []
        for p in self.listar_productos():
            if int(p.get("cantidad", 0)) <= low_stock:
                bajos.append(p)
            fc = p.get("fecha_caducidad")
            if fc:
                try:
                    f = datetime.strptime(fc, "%Y-%m-%d").date()
                    if (f - hoy).days <= dias_cad:
                        proximos.append(p)
                except Exception:
                    pass
        return {"stock_bajo": bajos, "proxima_caducidad": proximos}

# ================================ VISTAS =====================================
class MainView:
    def __init__(self, controller: InventarioController):
        self.c = controller
        self.bus = controller.bus

        ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("green")
        self.app = ctk.CTk(); self.app.geometry("1050x720"); self.app.title("Sistema de Inventario — MVC")
        self.active: Optional[ctk.CTkToplevel] = None

        title = ctk.CTkLabel(self.app, text="Sistema de Inventario", font=("Arial", 24)); title.pack(pady=12)
        ctk.CTkButton(self.app, text="Iniciar Sesión", command=self.open_login).pack(pady=6)
        ctk.CTkButton(self.app, text="Salir", command=self.app.destroy).pack(pady=6)

        self.bus.subscribe("auth:login", self.on_login)

    # ---------------- Login & menú ----------------
    def open_login(self):
        win = ctk.CTkToplevel(self.app); win.geometry("380x260"); win.title("Iniciar Sesión")
        ctk.CTkLabel(win, text="Usuario").pack(pady=4); euser = ctk.CTkEntry(win); euser.pack(pady=4)
        ctk.CTkLabel(win, text="Contraseña").pack(pady=4); epw = ctk.CTkEntry(win, show="*"); epw.pack(pady=4)
        def go():
            if self.c.login(euser.get().strip(), epw.get().strip()): win.destroy()
            else: messagebox.showerror("Login", "Usuario/contraseña incorrectos")
        ctk.CTkButton(win, text="Ingresar", command=go).pack(pady=10)

    def on_login(self, payload):
        rol = payload["usuario"].get("rol", "usuario"); self.open_menu(rol)

    def open_menu(self, rol: str):
        if self.active: self.active.destroy()
        win = ctk.CTkToplevel(self.app); win.geometry("1020x700"); win.title(f"Menú — {rol}"); self.active = win
        ctk.CTkLabel(win, text=f"Bienvenido: {rol}", font=("Arial", 20)).pack(pady=10)
        # Menú por rol (simple)
        ctk.CTkButton(win, text="Productos", command=self.open_productos).pack(pady=6)
        ctk.CTkButton(win, text="Proveedores", command=self.open_proveedores).pack(pady=6)
        if rol in ("Administrador", "Gerente"):
            ctk.CTkButton(win, text="Usuarios", command=self.open_usuarios).pack(pady=6)
        ctk.CTkButton(win, text="Recepciones", command=self.open_recepciones).pack(pady=6)
        ctk.CTkButton(win, text="Alertas", command=self.open_alertas).pack(pady=6)
        ctk.CTkButton(win, text="Cerrar Sesión", command=lambda: (win.destroy())).pack(pady=6)

    # ---------------- Productos ----------------
    def open_productos(self):
        self._open_table_window(
            title="Gestión de Productos",
            columns=("ID","Nombre","Marca","Categoría","Cantidad","Precio","Proveedor","Caducidad"),
            loader=lambda f=None: self.c.listar_productos(f),
            creator=self._crear_producto_dialog,
            updater=self._editar_producto_dialog,
            deleter=lambda oid: self.c.eliminar_producto(oid),
            on_change_event="productos:cambio",
            exporter_name="inventario"
        )

    def _crear_producto_dialog(self, reload_cb):
        w = ctk.CTkToplevel(self.app); w.title("Nuevo producto"); w.geometry("380x520")
        entries = {}
        for label in ("nombre","marca","categoria","cantidad","precio","proveedor","fecha_caducidad"):
            ctk.CTkLabel(w, text=label.capitalize()).pack(pady=2); e = ctk.CTkEntry(w); e.pack(pady=2); entries[label]=e
        def save():
            try:
                p = Producto(
                    nombre=entries['nombre'].get().strip(), marca=entries['marca'].get().strip(),
                    categoria=entries['categoria'].get().strip(), cantidad=int(entries['cantidad'].get()),
                    precio=float(entries['precio'].get()), proveedor=entries['proveedor'].get().strip(),
                    fecha_caducidad=entries['fecha_caducidad'].get().strip() or None
                )
            except Exception:
                messagebox.showerror("Validación","Cantidad debe ser entero y precio decimal"); return
            if not p.nombre or not p.marca or not p.categoria or not p.proveedor:
                messagebox.showwarning("Validación","Completa los campos obligatorios"); return
            self.c.crear_producto(p); reload_cb(); w.destroy()
        ctk.CTkButton(w, text="Guardar", command=save).pack(pady=10)

    def _editar_producto_dialog(self, oid: str, reload_cb):
        prod = self.c.productos.get(oid)
        if not prod: messagebox.showerror("Edición","Producto no encontrado"); return
        w = ctk.CTkToplevel(self.app); w.title("Editar producto"); w.geometry("380x560")
        fields = [("nombre", prod.get("nombre","")), ("marca", prod.get("marca","")), ("categoria", prod.get("categoria","")),
                  ("cantidad", str(prod.get("cantidad",0))), ("precio", str(prod.get("precio",0.0))),
                  ("proveedor", prod.get("proveedor","")), ("fecha_caducidad", prod.get("fecha_caducidad",""))]
        entries={}
        for label,val in fields:
            ctk.CTkLabel(w, text=label.capitalize()).pack(pady=2); e=ctk.CTkEntry(w); e.insert(0,val); e.pack(pady=2); entries[label]=e
        def save():
            try:
                cambios={
                    "nombre": entries['nombre'].get().strip(), "marca": entries['marca'].get().strip(), "categoria": entries['categoria'].get().strip(),
                    "cantidad": int(entries['cantidad'].get()), "precio": float(entries['precio'].get()),
                    "proveedor": entries['proveedor'].get().strip(), "fecha_caducidad": entries['fecha_caducidad'].get().strip() or None,
                }
            except Exception:
                messagebox.showerror("Validación","Cantidad debe ser entero y precio decimal"); return
            self.c.actualizar_producto(oid, cambios); reload_cb(); w.destroy()
        ctk.CTkButton(w, text="Guardar cambios", command=save).pack(pady=10)

    # ---------------- Proveedores ----------------
    def open_proveedores(self):
        self._open_table_window(
            title="Gestión de Proveedores",
            columns=("ID","Nombre","Contacto","Teléfono","Correo","Dirección"),
            loader=lambda f=None: self.c.listar_proveedores(f),
            creator=self._crear_proveedor_dialog,
            updater=self._editar_proveedor_dialog,
            deleter=lambda oid: self.c.eliminar_proveedor(oid),
            on_change_event="proveedores:cambio",
            exporter_name="proveedores"
        )

    def _crear_proveedor_dialog(self, reload_cb):
        w = ctk.CTkToplevel(self.app); w.title("Nuevo proveedor"); w.geometry("380x420")
        entries={}
        for label in ("nombre","contacto","telefono","correo","direccion"):
            ctk.CTkLabel(w, text=label.capitalize()).pack(pady=2); e=ctk.CTkEntry(w); e.pack(pady=2); entries[label]=e
        def save():
            p = Proveedor(
                nombre=entries['nombre'].get().strip(), contacto=entries['contacto'].get().strip(),
                telefono=entries['telefono'].get().strip(), correo=entries['correo'].get().strip(),
                direccion=entries['direccion'].get().strip()
            )
            if not p.nombre: messagebox.showwarning("Validación","Nombre requerido"); return
            self.c.crear_proveedor(p); reload_cb(); w.destroy()
        ctk.CTkButton(w, text="Guardar", command=save).pack(pady=10)

    def _editar_proveedor_dialog(self, oid: str, reload_cb):
        prov = self.c.proveedores.get(oid)
        if not prov: messagebox.showerror("Edición","Proveedor no encontrado"); return
        w = ctk.CTkToplevel(self.app); w.title("Editar proveedor"); w.geometry("380x460")
        fields = [("nombre",prov.get("nombre","")), ("contacto",prov.get("contacto","")), ("telefono",prov.get("telefono","")), ("correo",prov.get("correo","")), ("direccion",prov.get("direccion",""))]
        entries={}
        for label,val in fields:
            ctk.CTkLabel(w, text=label.capitalize()).pack(pady=2); e=ctk.CTkEntry(w); e.insert(0,val); e.pack(pady=2); entries[label]=e
        def save():
            cambios={k: entries[k].get().strip() for k,_ in fields}
            if not cambios["nombre"]: messagebox.showwarning("Validación","Nombre requerido"); return
            self.c.actualizar_proveedor(oid, cambios); reload_cb(); w.destroy()
        ctk.CTkButton(w, text="Guardar cambios", command=save).pack(pady=10)

    # ---------------- Recepciones ----------------
    def open_recepciones(self):
        w = ctk.CTkToplevel(self.app); w.title("Recepciones"); w.geometry("520x360")
        # Selector de producto (combo por nombre)
        ctk.CTkLabel(w, text="Producto").pack(pady=4)
        productos = self.c.listar_productos()
        nombres = [f"{p.get('nombre')} — {str(p.get('_id'))}" for p in productos]
        combo = ctk.CTkComboBox(w, values=nombres)
        combo.pack(pady=4)
        ctk.CTkLabel(w, text="Proveedor").pack(pady=4)
        provs = [p.get('nombre') for p in self.c.listar_proveedores()]
        cbprov = ctk.CTkComboBox(w, values=provs)
        cbprov.pack(pady=4)
        ctk.CTkLabel(w, text="Cantidad (+)").pack(pady=4); ecant = ctk.CTkEntry(w); ecant.pack(pady=4)
        ctk.CTkLabel(w, text="Motivo").pack(pady=4); emot = ctk.CTkEntry(w); emot.insert(0, "recepción"); emot.pack(pady=4)
        def guardar():
            sel = combo.get()
            if not sel:
                messagebox.showwarning("Recepción","Selecciona un producto"); return
            try:
                pid = sel.split("—")[-1].strip()
                cant = int(ecant.get())
                provname = cbprov.get() or ""
                if not provname:
                    messagebox.showwarning("Recepción","Selecciona proveedor"); return
                self.c.recepcionar(pid, cant, provname, emot.get().strip() or "recepción")
                messagebox.showinfo("Recepción","Stock actualizado")
            except ValueError:
                messagebox.showerror("Recepción","Cantidad debe ser un entero positivo")
        ctk.CTkButton(w, text="Guardar recepción", command=guardar).pack(pady=10)

    # ---------------- Usuarios ----------------
    def open_usuarios(self):
        self._open_table_window(
            title="Gestión de Usuarios",
            columns=("ID","Usuario","Rol","Nombre"),
            loader=lambda f=None: [{"_id":u.get("_id"), "usuario":u.get("usuario"), "rol":u.get("rol"), "nombre":u.get("nombre","") } for u in self.c.usuarios.all()],
            creator=self._crear_usuario_dialog,
            updater=self._editar_usuario_dialog,
            deleter=lambda oid: self.c.eliminar_usuario(oid),
            on_change_event="usuarios:cambio",
            exporter_name="usuarios"
        )

    def _crear_usuario_dialog(self, reload_cb):
        w = ctk.CTkToplevel(self.app); w.title("Nuevo usuario"); w.geometry("360x360")
        entries={}
        for label in ("usuario","password","rol","nombre"):
            ctk.CTkLabel(w, text=label.capitalize()).pack(pady=2); e=ctk.CTkEntry(w); e.pack(pady=2); entries[label]=e
        def save():
            if not entries['usuario'].get().strip() or not entries['password'].get().strip():
                messagebox.showwarning("Validación","Usuario y contraseña requeridos"); return
            u = Usuario(usuario=entries['usuario'].get().strip(), password=entries['password'].get().strip(), rol=entries['rol'].get().strip() or "Encargado", nombre=entries['nombre'].get().strip())
            self.c.crear_usuario(u); reload_cb(); w.destroy()
        ctk.CTkButton(w, text="Guardar", command=save).pack(pady=10)

    def _editar_usuario_dialog(self, oid: str, reload_cb):
        u = self.c.usuarios.get(oid)
        if not u: messagebox.showerror("Edición","Usuario no encontrado"); return
        w = ctk.CTkToplevel(self.app); w.title("Editar usuario"); w.geometry("360x420")
        fields = [("usuario",u.get("usuario","")), ("password",u.get("password","")), ("rol",u.get("rol","")), ("nombre",u.get("nombre",""))]
        entries={}
        for label,val in fields:
            ctk.CTkLabel(w, text=label.capitalize()).pack(pady=2); e=ctk.CTkEntry(w); e.insert(0,val); e.pack(pady=2); entries[label]=e
        def save():
            cambios = {k: entries[k].get().strip() for k,_ in fields}
            if not cambios["usuario"]: messagebox.showwarning("Validación","Usuario requerido"); return
            self.c.actualizar_usuario(oid, cambios); reload_cb(); w.destroy()
        ctk.CTkButton(w, text="Guardar cambios", command=save).pack(pady=10)

    # ---------------- Alertas ----------------
    def open_alertas(self):
        data = self.c.alertas()
        win = ctk.CTkToplevel(self.app); win.title("Alertas"); win.geometry("980x480")
        frame = ctk.CTkFrame(win); frame.pack(fill="both", expand=True, padx=10, pady=10)
        cols=("ID","Nombre","Cantidad","Proveedor","Caducidad")
        tree_low, tree_exp = self._make_tree_pair(frame, cols)
        def fill(tree, items):
            for i in tree.get_children(): tree.delete(i)
            for p in items:
                tree.insert("","end", values=(str(p.get("_id")), p.get("nombre",""), int(p.get("cantidad",0)), p.get("proveedor",""), p.get("fecha_caducidad","N/A")))
        ctk.CTkLabel(frame, text="Stock bajo (≤10)", font=("Arial",16)).pack(anchor="w")
        tree_low.pack(fill="both", expand=True, pady=6)
        ctk.CTkLabel(frame, text="Próxima caducidad (≤30 días)", font=("Arial",16)).pack(anchor="w")
        tree_exp.pack(fill="both", expand=True, pady=6)
        fill(tree_low, data["stock_bajo"]); fill(tree_exp, data["proxima_caducidad"])

    # ---------------- Helpers reutilizables ----------------
    def _make_tree_pair(self, parent, cols):
        tree1 = ttk.Treeview(parent, columns=cols, show="headings"); [tree1.heading(c,text=c) for c in cols]
        tree2 = ttk.Treeview(parent, columns=cols, show="headings"); [tree2.heading(c,text=c) for c in cols]
        for t in (tree1, tree2):
            for c in cols: t.column(c, width=140)
        return tree1, tree2

    def _open_table_window(self, title: str, columns: tuple, loader, creator, updater, deleter, on_change_event: str, exporter_name: str):
        if self.active: self.active.destroy()
        win = ctk.CTkToplevel(self.app); win.geometry("1100x720"); win.title(title); self.active = win
        # Filtros básicos por nombre
        f = ctk.CTkFrame(win); f.pack(fill="x", pady=6)
        efiltro = ctk.CTkEntry(f, placeholder_text="Buscar por texto..."); efiltro.pack(side="left", padx=5)
        def buscar():
            txt = efiltro.get().strip()
            q = {"$or": [{"nombre": {"$regex": txt, "$options": "i"}}, {"proveedor": {"$regex": txt, "$options": "i"}}]} if txt else None
            load(q)
        ctk.CTkButton(f, text="Buscar", command=buscar).pack(side="left", padx=5)
        ctk.CTkButton(f, text="Limpiar", command=lambda: (efiltro.delete(0,'end'), load(None))).pack(side="left", padx=5)

        # Contenedor para Tree + Scrollbar (corregido)
        cont = ctk.CTkFrame(win); cont.pack(fill="both", expand=True, padx=10, pady=8)
        tree = ttk.Treeview(cont, columns=columns, show="headings")
        for c_ in columns: tree.heading(c_, text=c_); tree.column(c_, width=140)
        vsb = ttk.Scrollbar(cont, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True); vsb.pack(side="right", fill="y")

        # Botonera
        bar = ctk.CTkFrame(win); bar.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(bar, text="Nuevo", command=lambda: creator(lambda: load(None))).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Editar", command=lambda: self._with_selected(tree, lambda oid: updater(oid, lambda: load(None)))).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Eliminar", command=lambda: self._with_selected(tree, lambda oid: (deleter(oid), load(None)))).pack(side="left", padx=4)

        # Exportaciones
        exp_excel = ExcelExportStrategy(); exp_csv = CSVExportStrategy()
        def export_common(strategy):
            cols = [tree.heading(c)['text'] for c in tree['columns']]
            rows = [tree.item(i)['values'] for i in tree.get_children()]
            sugerido = f"{exporter_name}_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
            strategy.export(cols, rows, sugerido)
        ctk.CTkButton(bar, text="Exportar Excel", command=lambda: export_common(exp_excel)).pack(side="right", padx=4)
        ctk.CTkButton(bar, text="Exportar CSV", command=lambda: export_common(exp_csv)).pack(side="right", padx=4)

        # Carga y suscripción a eventos
        def load(filtros):
            for i in tree.get_children(): tree.delete(i)
            try:
                for row in loader(filtros):
                    # normaliza a lista de valores en orden de columnas
                    vals = []
                    for ckey in columns:
                        key = ckey.lower().replace("teléfono","telefono")
                        if key == "id":
                            vals.append(str(row.get("_id")))
                        else:
                            vals.append(row.get(key, row.get(ckey, "")))
                    tree.insert("","end", values=vals)
            except Exception as e:
                messagebox.showerror("Cargar", f"Error al cargar datos: {e}")
        self.bus.subscribe(on_change_event, lambda _=None: load(None))
        load(None)

    def _with_selected(self, tree: ttk.Treeview, fn):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Selección","Selecciona un registro"); return
        vals = tree.item(sel[0])['values']
        if not vals: messagebox.showwarning("Selección","Registro inválido"); return
        oid = str(vals[0]); fn(oid)

    # ---------------- Run loop ----------------
    def run(self):
        self.app.mainloop()

# ================================ SELFTESTS ==================================
class TestFailure(Exception): ...

def assert_eq(a,b,msg=""):
    if a!=b: raise TestFailure(msg or f"{a}!={b}")

def run_selftests():
    print("[TEST] Iniciando self-tests breves...")
    bus = EventBus(); c = InventarioController(bus)
    # prepara usuario
    if not c.usuarios.get_by_user("admin"):
        c.crear_usuario(Usuario(usuario="admin", password="admin", rol="Administrador", nombre="Admin"))
    assert_eq(c.login("admin","admin"), True, "login admin")
    # crea proveedor
    pid = c.crear_proveedor(Proveedor("Proveedor A","Juan","555-000","a@a.com","CDMX"))
    # crea producto
    prod_id = c.crear_producto(Producto("Manzana","Verde","Fruta",5,12.5,"Proveedor A","2025-12-31"))
    # recepción +5 -> 10
    c.recepcionar(prod_id, 5, "Proveedor A", "reabastecimiento")
    p = c.productos.get(prod_id); assert_eq(int(p.get("cantidad")), 10, "+5 ok")
    # alertas: stock bajo umbral 10 -> sí aparece
    al = c.alertas(low_stock=10, dias_cad=400)
    assert any(str(x.get("_id")) == str(prod_id) for x in al["stock_bajo"]), "alerta stock bajo"
    print("[TEST] OK")

# ================================ BOOT =======================================
if __name__ == "__main__":
    if "--selftest" in (a.lower() for a in sys.argv[1:]):
        run_selftests(); sys.exit(0)

    bus = EventBus(); controller = InventarioController(bus)
    ui = MainView(controller)
    ui.run()

