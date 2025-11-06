import customtkinter as ctk
from pymongo import MongoClient
from tkinter import messagebox
from tkinter import ttk
from bson.objectid import ObjectId
from openpyxl import Workbook
from tkinter import filedialog
from datetime import datetime
import tkinter as tk


class SistemaInventario:
    def __init__(self):
        self.client = MongoClient("mongodb+srv://edgarallanespinosah:rBJZFh6ZF6xZYXzh@cluster0.yvlnuwz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
        self.db = self.client["supermercado"]
        self.historial_cambios = self.db["historial_cambios_stock"]
        self.usuarios = self.db["usuarios"]
        self.productos = self.db["productos"]
        self.proveedores = self.db["proveedores"]
        self.recepciones = self.db["recepciones"]
        self.ajustes_stock = self.db["ajustes_stock"]
        self.promociones = self.db["promociones"]
        self.ordenes_compra = self.db["ordenes_compra"]
        self.facturas = self.db["facturas"]


        self.app = ctk.CTk()
        self.app.geometry("800x600")  # Ventana más grande
        self.app.title("Sistema de Inventario")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        
        self.ventana_activa = None

        self.configurar_interfaz()

    def abrir_nueva_ventana(self, titulo, tamano="800x600"):
        if self.ventana_activa:
            self.ventana_activa.destroy()
        ventana = ctk.CTkToplevel(self.app)
        ventana.geometry(tamano)
        ventana.title(titulo)
        self.ventana_activa = ventana
        return ventana

        
    def configurar_interfaz(self):
        ctk.CTkLabel(self.app, text="Sistema de Inventario", font=("Arial", 24)).pack(pady=30)
        ctk.CTkButton(self.app, text="Iniciar Sesión", command=self.login).pack(pady=10)
        ctk.CTkButton(self.app, text="Registrar Cuenta", command=self.registrar_usuario).pack(pady=10)
        
    def login(self):
        ventana_login = ctk.CTkToplevel(self.app)
        ventana_login.geometry("400x300")
        ventana_login.title("Iniciar Sesión")
        
        ctk.CTkLabel(ventana_login, text="Iniciar Sesión", font=("Arial", 20)).pack(pady=20)
        entry_usuario = ctk.CTkEntry(ventana_login, placeholder_text="Usuario")
        entry_usuario.pack(pady=10)
        entry_contrasena = ctk.CTkEntry(ventana_login, placeholder_text="Contraseña", show="*")
        entry_contrasena.pack(pady=10)
        
        def procesar_login():
            usuario = entry_usuario.get()
            contrasena = entry_contrasena.get()
            
            if not usuario or not contrasena:
                messagebox.showwarning("Campos vacíos", "Por favor completa todos los campos")
                return
                
            user = self.usuarios.find_one({"usuario": usuario, "password": contrasena})
            
            if user:
                self.usuario_actual = user  # ← Guardamos usuario actual
                ventana_login.destroy()
                self.abrir_menu_por_rol(user["rol"])
            else:
                messagebox.showerror("Error", "Usuario o contraseña incorrectos")
                
        ctk.CTkButton(ventana_login, text="Ingresar", command=procesar_login).pack(pady=20)
        
    def abrir_menu_por_rol(self, rol):
        menu = ctk.CTkToplevel(self.app)
        menu.geometry("800x600")  # Ventana más grande
        menu.title(f"Menú - {rol.capitalize()}")
        ctk.CTkLabel(menu, text=f"Bienvenido, rol: {rol}", font=("Arial", 18)).pack(pady=20)
        
        if rol == "administrador":
            ctk.CTkButton(menu, text="Gestionar Productos", command=self.abrir_gestion_productos).pack(pady=10)
            ctk.CTkButton(menu, text="Gestionar Proveedores", command=self.abrir_gestion_proveedores).pack(pady=10)
            ctk.CTkButton(menu, text="Actualizar Proveedor de Producto", command=self.abrir_actualizar_proveedor_producto).pack(pady=10)
            ctk.CTkButton(menu, text="Asignar Proveedor a Producto", command=self.abrir_asignar_proveedor_producto).pack(pady=10)
            ctk.CTkButton(menu, text="Gestionar Usuarios", command=self.abrir_gestion_usuarios).pack(pady=10)
            ctk.CTkButton(menu, text="Gestionar Promociones", command=self.abrir_gestion_promociones).pack(pady=10)
            ctk.CTkButton(menu, text="Consultar Facturas", command=self.abrir_consulta_facturas).pack(pady=10)
            ctk.CTkButton(menu, text="Ver Alertas de Inventario", command=self.abrir_alertas_productos).pack(pady=10)
            ctk.CTkButton(menu, text="🛟 Soporte", command=self.mostrar_soporte, width=120).place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
            ctk.CTkButton(menu, text="Cerrar Sesión", command=lambda: self.cerrar_sesion(menu)).pack(pady=20)

        elif rol == "gerente":
            ctk.CTkButton(menu, text="Consultar Inventario", command=self.abrir_consulta_inventario).pack(pady=10)
            ctk.CTkButton(menu, text="Registrar Producto", command=self.abrir_registro_producto).pack(pady=10)
            ctk.CTkButton(menu, text="Crear Orden de Compra", command=self.abrir_crear_orden).pack(pady=10)
            ctk.CTkButton(menu, text="Ver Alertas de Inventario", command=self.abrir_alertas_productos).pack(pady=10)
            ctk.CTkButton(menu, text="Actualizar Stock", command=self.abrir_actualizacion_stock_gerente).pack(pady=10)
            ctk.CTkButton(menu, text="🛟 Soporte", command=self.mostrar_soporte, width=120).place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
            ctk.CTkButton(menu, text="Cerrar Sesión", command=lambda: self.cerrar_sesion(menu)).pack(pady=20)


        elif rol == "encargado":
            ctk.CTkButton(menu, text="Registrar Recepción de Productos", command=self.abrir_registro_recepcion).pack(pady=10)
            ctk.CTkButton(menu, text="Actualizar Stock Manual", command=self.abrir_actualizacion_stock).pack(pady=10)
            ctk.CTkButton(menu, text="🛟 Soporte", command=self.mostrar_soporte, width=120).place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
            ctk.CTkButton(menu, text="Cerrar Sesión", command=lambda: self.cerrar_sesion(menu)).pack(pady=20)



        elif rol == "proveedor":
            ctk.CTkButton(menu, text="Ver Órdenes de Compra", command=self.abrir_ordenes_proveedor).pack(pady=10)
            ctk.CTkButton(menu, text="Generar Factura", command=self.abrir_generar_factura).pack(pady=10)
            ctk.CTkButton(menu, text="🛟 Soporte", command=self.mostrar_soporte, width=120).place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
            ctk.CTkButton(menu, text="Cerrar Sesión", command=lambda: self.cerrar_sesion(menu)).pack(pady=20)
            

    def cerrar_sesion(self, ventana_actual):
        # Cierra la ventana del menú del rol
        if ventana_actual:
            ventana_actual.destroy()
        # Cierra cualquier ventana secundaria que esté abierta
        if self.ventana_activa:
            try:
                self.ventana_activa.destroy()
            except:
                pass
            self.ventana_activa = None
        # Vuelve a mostrar la ventana principal limpia
        for widget in self.app.winfo_children():
            widget.destroy()
        self.configurar_interfaz()


    def registrar_usuario(self):
        ventana_registro = ctk.CTkToplevel(self.app)
        ventana_registro.geometry("400x500")
        ventana_registro.title("Registrar Usuario")

        ctk.CTkLabel(ventana_registro, text="Nuevo Usuario", font=("Arial", 20)).pack(pady=10)

        entry_nombre = ctk.CTkEntry(ventana_registro, placeholder_text="Nombre completo")
        entry_nombre.pack(pady=5)

        entry_usuario = ctk.CTkEntry(ventana_registro, placeholder_text="Nombre de usuario")
        entry_usuario.pack(pady=5)

        entry_contrasena = ctk.CTkEntry(ventana_registro, placeholder_text="Contraseña", show="*")
        entry_contrasena.pack(pady=5)

        ctk.CTkLabel(ventana_registro, text="Selecciona el rol del usuario").pack(pady=5)

        combo_rol = ctk.CTkComboBox(ventana_registro, values=["administrador", "gerente", "encargado", "proveedor"])
        combo_rol.pack(pady=5)

        def procesar_registro():
            usuario = entry_usuario.get()
            contrasena = entry_contrasena.get()
            nombre = entry_nombre.get()
            rol = combo_rol.get()

            if not usuario or not contrasena or not nombre or not rol:
                messagebox.showwarning("Campos vacíos", "Por favor completa todos los campos")
                return

            self.usuarios.insert_one({
                "usuario": usuario,
                "password": contrasena,
                "nombre": nombre,
                "rol": rol
            })

            messagebox.showinfo("Éxito", "Usuario registrado correctamente")
            ventana_registro.destroy()

        ctk.CTkButton(ventana_registro, text="Registrar", command=procesar_registro).pack(pady=20)
        ctk.CTkButton(ventana_registro, text="Regresar", command=ventana_registro.destroy).pack(pady=5)

        
    def abrir_gestion_productos(self):
        ventana_productos = self.abrir_nueva_ventana("Gestión de Productos")


        frame_tree = ctk.CTkFrame(ventana_productos)
        frame_tree.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Guardar el Treeview como atributo de la clase
        self.tree_productos = ttk.Treeview(frame_tree, columns=("ID", "Nombre", "Marca", "Categoría", "Cantidad", "Precio"), show="headings")
        self.tree_productos.heading("ID", text="ID")
        self.tree_productos.heading("Nombre", text="Nombre")
        self.tree_productos.heading("Marca", text="Marca")
        self.tree_productos.heading("Categoría", text="Categoría")
        self.tree_productos.heading("Cantidad", text="Cantidad")
        self.tree_productos.heading("Precio", text="Precio")
        
        self.tree_productos.column("ID", width=100)
        self.tree_productos.column("Nombre", width=150)
        self.tree_productos.column("Marca", width=100)
        self.tree_productos.column("Categoría", width=100)
        self.tree_productos.column("Cantidad", width=80)
        self.tree_productos.column("Precio", width=80)
        
        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree_productos.yview)
        self.tree_productos.configure(yscrollcommand=scrollbar.set)
        
        self.tree_productos.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        frame_botones = ctk.CTkFrame(ventana_productos)
        frame_botones.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkButton(frame_botones, text="Registrar Producto", command=self.abrir_registro_producto).pack(side="left", padx=5)
        ctk.CTkButton(frame_botones, text="Actualizar Producto", command=self.actualizar_producto).pack(side="left", padx=5)
        ctk.CTkButton(frame_botones, text="Eliminar Producto", command=self.eliminar_producto_seleccionado).pack(side="left", padx=5)
        
        self.cargar_productos(self.tree_productos)
        
        # Agregar binding para doble clic
        self.tree_productos.bind("<Double-Button-1>", self.seleccionar_producto)
        ctk.CTkButton(ventana_productos, text="Regresar", command=ventana_productos.destroy).pack(pady=10)

        
    def seleccionar_producto(self, event):
        seleccionado = self.tree_productos.selection()
        if seleccionado:
            producto_id = self.tree_productos.item(seleccionado[0])["values"][0]
            self.producto_seleccionado = producto_id
            messagebox.showinfo("Producto Seleccionado", 
                f"Producto seleccionado: {self.tree_productos.item(seleccionado[0])['values'][1]}")
            
    def eliminar_producto_seleccionado(self):
        try:
            if hasattr(self, 'producto_seleccionado'):
                respuesta = messagebox.askyesno("Confirmar Eliminación", 
                    f"¿Está seguro que desea eliminar el producto seleccionado?")
                if respuesta:
                    from bson.objectid import ObjectId
                    self.productos.delete_one({"_id": ObjectId(self.producto_seleccionado)})
                    messagebox.showinfo("Éxito", "Producto eliminado correctamente")
                    self.cargar_productos(self.tree_productos)
                    del self.producto_seleccionado
            else:
                messagebox.showwarning("Advertencia", "Por favor seleccione un producto")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        
    def seleccionar_producto(self, event):
        seleccionado = self.tree_productos.selection()
        if seleccionado:
            datos = self.tree_productos.item(seleccionado[0])["values"]
            self.producto_seleccionado = datos[0]  # ID
            messagebox.showinfo("Producto Seleccionado", f"Seleccionado: {datos[1]}")

            
    def eliminar_producto_seleccionado(self):
        try:
            if hasattr(self, 'producto_seleccionado'):
                respuesta = messagebox.askyesno("Confirmar Eliminación", 
                    "¿Estás seguro de eliminar este producto?")
                if respuesta:
                    from bson.objectid import ObjectId
                    self.productos.delete_one({"_id": ObjectId(self.producto_seleccionado)})
                    messagebox.showinfo("Éxito", "Producto eliminado correctamente")
                    self.cargar_productos(self.tree_productos)
                    del self.producto_seleccionado
            else:
                messagebox.showwarning("Advertencia", "Selecciona un producto primero")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def cargar_ajustes_stock(self, tree):
            tree.delete(*tree.get_children())
            for ajuste in self.ajustes_stock.find().sort("fecha", -1):
                tree.insert("", "end", values=(
                    ajuste["producto_nombre"],
                    ajuste["tipo_ajuste"],
                    ajuste["cantidad"],
                    ajuste["motivo"],
                    ajuste["fecha"]
                ))

    def cargar_productos_filtrados(self, tree, filtros):
        tree.delete(*tree.get_children())
        productos = self.productos.find(filtros)
        for prod in productos:
            tree.insert("", "end", values=(
                prod.get("nombre", ""),
                prod.get("marca", ""),
                prod.get("categoria", ""),
                prod.get("cantidad", 0),
                prod.get("precio", 0),
                prod.get("fecha_caducidad", "N/A"),
                prod.get("proveedor", "N/A")
            ))

    def exportar_excel(self, tree):
        filas = tree.get_children()
        if not filas:
            messagebox.showinfo("Sin datos", "No hay productos para exportar")
            return

        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        nombre_sugerido = f"inventario_{fecha_actual}.xlsx"

        archivo = filedialog.asksaveasfilename(
            initialfile=nombre_sugerido,
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Guardar reporte de inventario"
        )
        if not archivo:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Inventario"

        # Agregar fecha de exportación
        ws.append([f"Reporte generado el {fecha_actual}"])
        ws.append([])  # Fila en blanco

        # Cabeceras
        columnas = [tree.heading(col)["text"] for col in tree["columns"]]
        ws.append(columnas)

        # Datos
        for fila in filas:
            valores = tree.item(fila)["values"]
            ws.append(valores)

        try:
            wb.save(archivo)
            messagebox.showinfo("Éxito", f"Reporte guardado correctamente:\n{archivo}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{str(e)}")



    def cargar_productos(self, tree):
        tree.delete(*tree.get_children())
        productos = self.productos.find()
        for prod in productos:
            tree.insert("", "end", values=(
                str(prod["_id"]),
                prod["nombre"],
                prod["marca"],
                prod["categoria"],
                prod["cantidad"],
                prod["precio"]
            ))
            
    def abrir_registro_producto(self):
        proveedores_directos = list(self.proveedores.find())
        usuarios_proveedores = list(self.usuarios.find({"rol": "proveedor"}))
        nombres_proveedores = list(set([p["nombre"] for p in proveedores_directos] +
                                    [u["nombre"] for u in usuarios_proveedores]))

        ventana_registro = ctk.CTkToplevel(self.app)
        ventana_registro.geometry("400x600")
        ventana_registro.title("Registrar Producto")
        
        ctk.CTkLabel(ventana_registro, text="Registrar Producto", font=("Arial", 18)).pack(pady=10)
        
        entry_nombre = ctk.CTkEntry(ventana_registro, placeholder_text="Nombre del producto")
        entry_nombre.pack(pady=5)
        entry_marca = ctk.CTkEntry(ventana_registro, placeholder_text="Marca")
        entry_marca.pack(pady=5)
        entry_categoria = ctk.CTkEntry(ventana_registro, placeholder_text="Categoría")
        entry_categoria.pack(pady=5)
        entry_cantidad = ctk.CTkEntry(ventana_registro, placeholder_text="Cantidad")
        entry_cantidad.pack(pady=5)
        entry_precio = ctk.CTkEntry(ventana_registro, placeholder_text="Precio")
        entry_precio.pack(pady=5)

        # Checkbox y campo opcional para fecha de caducidad
        tiene_caducidad_var = tk.BooleanVar()
        check_caducidad = ctk.CTkCheckBox(ventana_registro, text="¿Tiene fecha de caducidad?", variable=tiene_caducidad_var)
        check_caducidad.pack(pady=5)

        entry_caducidad = ctk.CTkEntry(ventana_registro, placeholder_text="Fecha de caducidad (YYYY-MM-DD)")
        entry_caducidad.pack(pady=5)
        entry_caducidad.configure(state="disabled")

        def toggle_fecha():
            if tiene_caducidad_var.get():
                entry_caducidad.configure(state="normal")
            else:
                entry_caducidad.delete(0, "end")
                entry_caducidad.configure(state="disabled")

        check_caducidad.configure(command=toggle_fecha)

        ctk.CTkLabel(ventana_registro, text="Selecciona proveedor").pack(pady=5)
        combo_proveedor = ctk.CTkComboBox(ventana_registro, values=nombres_proveedores)
        combo_proveedor.pack(pady=5)
        
        def guardar_producto():
            nombre = entry_nombre.get()
            marca = entry_marca.get()
            categoria = entry_categoria.get()
            proveedor_nombre = combo_proveedor.get()
            fecha_caducidad = entry_caducidad.get().strip() if tiene_caducidad_var.get() else None

            try:
                cantidad = int(entry_cantidad.get())
                precio = float(entry_precio.get())
            except ValueError:
                messagebox.showerror("Error", "Cantidad debe ser entero y precio decimal")
                return

            if not all([nombre, marca, categoria]):
                messagebox.showwarning("Campos vacíos", "Llena todos los campos obligatorios")
                return

            if not proveedor_nombre:
                messagebox.showwarning("Proveedor", "Selecciona un proveedor")
                return

            producto = {
                "nombre": nombre,
                "marca": marca,
                "categoria": categoria,
                "cantidad": cantidad,
                "precio": precio,
                "proveedor": proveedor_nombre,
                "estado": "activo"
            }

            if fecha_caducidad:
                producto["fecha_caducidad"] = fecha_caducidad

            self.productos.insert_one(producto)
            messagebox.showinfo("Éxito", "Producto registrado correctamente")
            ventana_registro.destroy()
        
        ctk.CTkButton(ventana_registro, text="Guardar Producto", command=guardar_producto).pack(pady=20)

    def actualizar_producto(self):
        if not hasattr(self, "producto_seleccionado"):
            messagebox.showwarning("Advertencia", "Selecciona un producto desde la tabla primero")
            return

        producto = self.productos.find_one({"_id": ObjectId(self.producto_seleccionado)})
        if not producto:
            messagebox.showerror("Error", "Producto no encontrado")
            return

        ventana_actualizar = ctk.CTkToplevel(self.app)
        ventana_actualizar.geometry("400x600")
        ventana_actualizar.title("Actualizar Producto")

        ctk.CTkLabel(ventana_actualizar, text="Actualizar Producto", font=("Arial", 18)).pack(pady=10)

        entry_nombre = ctk.CTkEntry(ventana_actualizar, placeholder_text="Nuevo nombre")
        entry_nombre.insert(0, producto["nombre"])
        entry_nombre.pack(pady=5)

        entry_marca = ctk.CTkEntry(ventana_actualizar, placeholder_text="Nueva marca")
        entry_marca.insert(0, producto["marca"])
        entry_marca.pack(pady=5)

        entry_categoria = ctk.CTkEntry(ventana_actualizar, placeholder_text="Nueva categoría")
        entry_categoria.insert(0, producto["categoria"])
        entry_categoria.pack(pady=5)

        entry_cantidad = ctk.CTkEntry(ventana_actualizar, placeholder_text="Nueva cantidad")
        entry_cantidad.insert(0, str(producto["cantidad"]))
        entry_cantidad.pack(pady=5)

        entry_precio = ctk.CTkEntry(ventana_actualizar, placeholder_text="Nuevo precio")
        entry_precio.insert(0, str(producto["precio"]))
        entry_precio.pack(pady=5)

        entry_fecha_cad = ctk.CTkEntry(ventana_actualizar, placeholder_text="Fecha de caducidad (YYYY-MM-DD)")
        entry_fecha_cad.insert(0, producto.get("fecha_caducidad", ""))
        entry_fecha_cad.pack(pady=5)

        def actualizar():
            actualizaciones = {
                "nombre": entry_nombre.get(),
                "marca": entry_marca.get(),
                "categoria": entry_categoria.get(),
                "cantidad": int(entry_cantidad.get()),
                "precio": float(entry_precio.get()),
            }

            fecha = entry_fecha_cad.get().strip()
            if fecha:
                actualizaciones["fecha_caducidad"] = fecha
            else:
                actualizaciones.pop("fecha_caducidad", None)

            self.productos.update_one(
                {"_id": ObjectId(self.producto_seleccionado)},
                {"$set": actualizaciones}
            )

            messagebox.showinfo("Éxito", "Producto actualizado correctamente")
            ventana_actualizar.destroy()
            self.cargar_productos(self.tree_productos)

        ctk.CTkButton(ventana_actualizar, text="Actualizar", command=actualizar).pack(pady=20)

    def eliminar_producto(self):
        ventana_eliminar = ctk.CTkToplevel(self.app)
        ventana_eliminar.geometry("400x200")
        ventana_eliminar.title("Eliminar Producto")
        
        ctk.CTkLabel(ventana_eliminar, text="Eliminar Producto", font=("Arial", 18)).pack(pady=10)
        
        entry_id = ctk.CTkEntry(ventana_eliminar, placeholder_text="ID del producto")
        entry_id.pack(pady=5)
        
        def eliminar():
            try:
                from bson.objectid import ObjectId
                producto_id = ObjectId(entry_id.get())
                
                self.productos.delete_one({"_id": producto_id})
                messagebox.showinfo("Éxito", "Producto eliminado correctamente")
                ventana_eliminar.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                
        ctk.CTkButton(ventana_eliminar, text="Eliminar", command=eliminar).pack(pady=20)
        
    def abrir_gestion_proveedores(self):
        ventana_menu = ctk.CTkToplevel(self.app)
        ventana_menu.geometry("800x600")  # Ventana más grande
        ventana_menu.title("Menú de Proveedores")
        
        ctk.CTkLabel(ventana_menu, text="¿Qué deseas hacer?", font=("Arial", 18)).pack(pady=20)
        ctk.CTkButton(ventana_menu, text="Registrar Proveedor", command=self.abrir_registro_proveedor).pack(pady=10)
        ctk.CTkButton(ventana_menu, text="Consultar / Eliminar Proveedor", command=self.abrir_tabla_proveedores).pack(pady=10)
        
    def abrir_registro_proveedor(self):
        ventana_registro = ctk.CTkToplevel(self.app)
        ventana_registro.geometry("400x600")
        ventana_registro.title("Registrar Proveedor")

        ctk.CTkLabel(ventana_registro, text="Registrar Proveedor", font=("Arial", 18)).pack(pady=10)

        entry_nombre = ctk.CTkEntry(ventana_registro, placeholder_text="Nombre del proveedor")
        entry_nombre.pack(pady=5)
        entry_empresa = ctk.CTkEntry(ventana_registro, placeholder_text="Empresa")
        entry_empresa.pack(pady=5)
        entry_telefono = ctk.CTkEntry(ventana_registro, placeholder_text="Teléfono")
        entry_telefono.pack(pady=5)
        entry_correo = ctk.CTkEntry(ventana_registro, placeholder_text="Correo electrónico")
        entry_correo.pack(pady=5)

        ctk.CTkLabel(ventana_registro, text="Asignar contraseña de inicio de sesión").pack(pady=5)
        entry_password = ctk.CTkEntry(ventana_registro, placeholder_text="Contraseña para iniciar sesión", show="*")
        entry_password.pack(pady=5)

        def guardar_proveedor():
            nombre = entry_nombre.get()
            empresa = entry_empresa.get()
            telefono = entry_telefono.get()
            correo = entry_correo.get()
            contrasena = entry_password.get()

            if not all([nombre, empresa, telefono, correo, contrasena]):
                messagebox.showwarning("Campos vacíos", "Por favor completa todos los campos")
                return

            # Insertar en colección proveedores
            self.proveedores.insert_one({
                "nombre": nombre,
                "empresa": empresa,
                "telefono": telefono,
                "correo": correo
            })

            # Insertar también como usuario del sistema
            self.usuarios.insert_one({
                "usuario": nombre.lower().replace(" ", "_"),
                "password": contrasena,
                "nombre": nombre,
                "rol": "proveedor"
            })

            messagebox.showinfo("Éxito", "Proveedor registrado correctamente y puede iniciar sesión.")
            ventana_registro.destroy()

        ctk.CTkButton(ventana_registro, text="Guardar Proveedor", command=guardar_proveedor).pack(pady=20)

        
    
    def abrir_tabla_proveedores(self):
        ventana_tabla = self.abrir_nueva_ventana("Gestión de Proveedores")

        frame_tree = ctk.CTkFrame(ventana_tabla)
        frame_tree.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Guardar el Treeview como atributo de la clase
        self.tree_proveedores = ttk.Treeview(frame_tree, columns=("ID", "Nombre", "Empresa", "Teléfono", "Correo"), show="headings")
        self.tree_proveedores.heading("ID", text="ID")
        self.tree_proveedores.heading("Nombre", text="Nombre")
        self.tree_proveedores.heading("Empresa", text="Empresa")
        self.tree_proveedores.heading("Teléfono", text="Teléfono")
        self.tree_proveedores.heading("Correo", text="Correo")
        
        self.tree_proveedores.column("ID", width=100)
        self.tree_proveedores.column("Nombre", width=150)
        self.tree_proveedores.column("Empresa", width=150)
        self.tree_proveedores.column("Teléfono", width=100)
        self.tree_proveedores.column("Correo", width=200)
        
        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree_proveedores.yview)
        self.tree_proveedores.configure(yscrollcommand=scrollbar.set)
        
        self.tree_proveedores.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        frame_botones = ctk.CTkFrame(ventana_tabla)
        frame_botones.pack(pady=10)

        ctk.CTkButton(frame_botones, text="Registrar Proveedor", command=self.abrir_registro_proveedor).pack(side="left", padx=10)
        ctk.CTkButton(frame_botones, text="Actualizar Proveedor", command=self.actualizar_proveedor).pack(side="left", padx=10)
        ctk.CTkButton(frame_botones, text="Eliminar Proveedor", command=self.eliminar_proveedor_seleccionado).pack(side="left", padx=10)

        self.cargar_proveedores(self.tree_proveedores)
        
        # Agregar binding para doble clic
        self.tree_proveedores.bind("<Double-Button-1>", self.seleccionar_proveedor)
        ctk.CTkButton(ventana_tabla, text="Regresar", command=ventana_tabla.destroy).pack(pady=10)

        
    def seleccionar_proveedor(self, event):
        seleccionado = self.tree_proveedores.selection()
        if seleccionado:
            proveedor_id = self.tree_proveedores.item(seleccionado[0])["values"][0]
            self.proveedor_seleccionado = proveedor_id
            messagebox.showinfo("Proveedor Seleccionado", 
                f"Proveedor seleccionado: {self.tree_proveedores.item(seleccionado[0])['values'][1]}")
            
    def eliminar_proveedor_seleccionado(self):
        try:
            if hasattr(self, 'proveedor_seleccionado'):
                respuesta = messagebox.askyesno("Confirmar Eliminación", 
                    f"¿Está seguro que desea eliminar el proveedor seleccionado?")
                if respuesta:
                    from bson.objectid import ObjectId
                    self.proveedores.delete_one({"_id": ObjectId(self.proveedor_seleccionado)})
                    messagebox.showinfo("Éxito", "Proveedor eliminado correctamente")
                    self.cargar_proveedores(self.tree_proveedores)
                    del self.proveedor_seleccionado
            else:
                messagebox.showwarning("Advertencia", "Por favor seleccione un proveedor")
        except Exception as e:
            messagebox.showerror("Error", str(e))

        
    def cargar_proveedores(self, tree):
        tree.delete(*tree.get_children())
        proveedores = self.proveedores.find()
        for prov in proveedores:
            tree.insert("", "end", values=(
                str(prov["_id"]),
                prov["nombre"],
                prov["empresa"],
                prov["telefono"],
                prov["correo"]
            ))

    def cargar_recepciones(self, tree):
        tree.delete(*tree.get_children())
        for recepcion in self.recepciones.find():
            tree.insert("", "end", values=(
                recepcion["producto_nombre"],
                recepcion["proveedor"],
                recepcion["cantidad"],
                recepcion["fecha_caducidad"],
                recepcion["estado_fisico"]
            ))


    def actualizar_proveedor(self):
        ventana_actualizar = ctk.CTkToplevel(self.app)
        ventana_actualizar.geometry("400x500")
        ventana_actualizar.title("Actualizar Proveedor")
        
        ctk.CTkLabel(ventana_actualizar, text="Actualizar Proveedor", font=("Arial", 18)).pack(pady=10)
        
        entry_id = ctk.CTkEntry(ventana_actualizar, placeholder_text="ID del proveedor")
        entry_id.pack(pady=5)
        
        entry_nombre = ctk.CTkEntry(ventana_actualizar, placeholder_text="Nuevo nombre")
        entry_nombre.pack(pady=5)
        entry_empresa = ctk.CTkEntry(ventana_actualizar, placeholder_text="Nueva empresa")
        entry_empresa.pack(pady=5)
        entry_telefono = ctk.CTkEntry(ventana_actualizar, placeholder_text="Nuevo teléfono")
        entry_telefono.pack(pady=5)
        entry_correo = ctk.CTkEntry(ventana_actualizar, placeholder_text="Nuevo correo")
        entry_correo.pack(pady=5)
        
        def actualizar():
            try:
                from bson.objectid import ObjectId
                proveedor_id = ObjectId(entry_id.get())
                
                actualizaciones = {}
                if entry_nombre.get():
                    actualizaciones["nombre"] = entry_nombre.get()
                if entry_empresa.get():
                    actualizaciones["empresa"] = entry_empresa.get()
                if entry_telefono.get():
                    actualizaciones["telefono"] = entry_telefono.get()
                if entry_correo.get():
                    actualizaciones["correo"] = entry_correo.get()
                    
                if actualizaciones:
                    self.proveedores.update_one({"_id": proveedor_id}, {"$set": actualizaciones})
                    messagebox.showinfo("Éxito", "Proveedor actualizado correctamente")
                    ventana_actualizar.destroy()
                else:
                    messagebox.showwarning("Advertencia", "No hay campos para actualizar")
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                
        ctk.CTkButton(ventana_actualizar, text="Actualizar", command=actualizar).pack(pady=20)
        
    def eliminar_proveedor(self):
        ventana_eliminar = ctk.CTkToplevel(self.app)
        ventana_eliminar.geometry("400x200")
        ventana_eliminar.title("Eliminar Proveedor")
        
        ctk.CTkLabel(ventana_eliminar, text="Eliminar Proveedor", font=("Arial", 18)).pack(pady=10)
        
        entry_id = ctk.CTkEntry(ventana_eliminar, placeholder_text="ID del proveedor")
        entry_id.pack(pady=5)
        
        def eliminar():
            try:
                from bson.objectid import ObjectId
                proveedor_id = ObjectId(entry_id.get())
                
                self.proveedores.delete_one({"_id": proveedor_id})
                messagebox.showinfo("Éxito", "Proveedor eliminado correctamente")
                ventana_eliminar.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                
        ctk.CTkButton(ventana_eliminar, text="Eliminar", command=eliminar).pack(pady=20)
        
    def run(self):
        self.app.mainloop()


    def abrir_gestion_usuarios(self):
        ventana_usuarios = self.abrir_nueva_ventana("Gestión de Usuarios")

        ctk.CTkLabel(ventana_usuarios, text="Usuarios Registrados", font=("Arial", 18)).pack(pady=10)

        frame_tree = ctk.CTkFrame(ventana_usuarios)
        frame_tree.pack(pady=10, padx=10, fill="both", expand=True)

        self.tree_usuarios = ttk.Treeview(frame_tree, columns=("ID", "Nombre", "Usuario", "Contraseña", "Rol"), show="headings")
        for col in ("ID", "Nombre", "Usuario", "Contraseña", "Rol"):
            self.tree_usuarios.heading(col, text=col)
            self.tree_usuarios.column(col, width=150)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree_usuarios.yview)
        self.tree_usuarios.configure(yscrollcommand=scrollbar.set)
        self.tree_usuarios.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame_botones = ctk.CTkFrame(ventana_usuarios)
        frame_botones.pack(pady=10)

        ctk.CTkButton(frame_botones, text="Actualizar Usuario", command=self.actualizar_usuario).pack(side="left", padx=10)
        ctk.CTkButton(frame_botones, text="Eliminar Usuario", command=self.eliminar_usuario).pack(side="left", padx=10)

        self.cargar_usuarios(self.tree_usuarios)
        ctk.CTkButton(ventana_usuarios, text="Regresar", command=ventana_usuarios.destroy).pack(pady=10)

    def abrir_registro_recepcion(self):
        ventana = self.abrir_nueva_ventana("Recepción de Productos", "800x600")
        ctk.CTkLabel(ventana, text="Registrar Recepción de Productos", font=("Arial", 18)).pack(pady=10)

        frame_form = ctk.CTkFrame(ventana)
        frame_form.pack(pady=10)

        entry_proveedor = ctk.CTkEntry(frame_form, placeholder_text="Nombre del proveedor")
        entry_proveedor.pack(pady=5)

        entry_producto = ctk.CTkEntry(frame_form, placeholder_text="Nombre del producto")
        entry_producto.pack(pady=5)

        entry_cantidad = ctk.CTkEntry(frame_form, placeholder_text="Cantidad recibida")
        entry_cantidad.pack(pady=5)

        entry_fecha = ctk.CTkEntry(frame_form, placeholder_text="Fecha de caducidad (YYYY-MM-DD)")
        entry_fecha.pack(pady=5)

        entry_estado = ctk.CTkEntry(frame_form, placeholder_text="Estado físico del producto")
        entry_estado.pack(pady=5)

        def guardar_recepcion():
            proveedor = entry_proveedor.get().strip()
            producto = entry_producto.get().strip()
            estado = entry_estado.get().strip()
            fecha = entry_fecha.get().strip()
            try:
                cantidad = int(entry_cantidad.get())
            except:
                messagebox.showerror("Error", "Cantidad debe ser un número")
                return

            if not all([proveedor, producto, estado, fecha]):
                messagebox.showwarning("Campos incompletos", "Por favor llena todos los campos")
                return

            # Buscar proveedor
            prov = self.proveedores.find_one({"nombre": proveedor})
            if not prov:
                messagebox.showerror("Error", "Proveedor no encontrado")
                return

            # Buscar producto
            prod = self.productos.find_one({"nombre": producto})
            if not prod:
                messagebox.showerror("Error", "Producto no encontrado")
                return

            # Guardar recepción
            self.recepciones.insert_one({
                "producto_id": str(prod["_id"]),
                "producto_nombre": producto,
                "proveedor": proveedor,
                "cantidad": cantidad,
                "fecha_caducidad": fecha,
                "estado_fisico": estado
            })

            # Actualizar stock
            nueva_cantidad = prod["cantidad"] + cantidad
            self.productos.update_one({"_id": prod["_id"]}, {"$set": {"cantidad": nueva_cantidad}})

            messagebox.showinfo("Éxito", f"Recepción registrada y stock actualizado a {nueva_cantidad}")
            self.cargar_recepciones(tree)  # Recarga la tabla con lo nuevo

        ctk.CTkButton(frame_form, text="Guardar Recepción", command=guardar_recepcion).pack(pady=10)

        # Tabla de historial de recepciones
        ctk.CTkLabel(ventana, text="Historial de Recepciones", font=("Arial", 16)).pack(pady=10)
        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(pady=10, padx=10, fill="both", expand=True)

        tree = ttk.Treeview(frame_tabla, columns=("Producto", "Proveedor", "Cantidad", "Fecha", "Estado"), show="headings")
        for col in ("Producto", "Proveedor", "Cantidad", "Fecha", "Estado"):
            tree.heading(col, text=col)
            tree.column(col, width=120)

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.cargar_recepciones(tree)

        # Botón regresar
        ctk.CTkButton(ventana, text="Regresar", command=ventana.destroy).pack(pady=10)


    def cargar_usuarios(self, tree):
        tree.delete(*tree.get_children())
        for user in self.usuarios.find():
            tree.insert("", "end", values=(str(user["_id"]), user["nombre"], user["usuario"], user["password"], user["rol"]))

    def actualizar_usuario(self):
        seleccionado = self.tree_usuarios.selection()
        if not seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un usuario para actualizar")
            return

        valores = self.tree_usuarios.item(seleccionado[0])["values"]
        user_id = valores[0]

        ventana = ctk.CTkToplevel(self.app)
        ventana.geometry("400x400")
        ventana.title("Actualizar Usuario")

        ctk.CTkLabel(ventana, text="Actualizar Usuario", font=("Arial", 16)).pack(pady=10)
        entry_nombre = ctk.CTkEntry(ventana, placeholder_text="Nuevo nombre")
        entry_nombre.pack(pady=5)
        entry_usuario = ctk.CTkEntry(ventana, placeholder_text="Nuevo usuario")
        entry_usuario.pack(pady=5)
        entry_password = ctk.CTkEntry(ventana, placeholder_text="Nueva contraseña", show="*")
        entry_password.pack(pady=5)
        entry_rol = ctk.CTkEntry(ventana, placeholder_text="Nuevo rol (administrador/gerente/encargado/proveedor)")
        entry_rol.pack(pady=5)

        def guardar():
            from bson.objectid import ObjectId
            cambios = {}
            if entry_nombre.get(): cambios["nombre"] = entry_nombre.get()
            if entry_usuario.get(): cambios["usuario"] = entry_usuario.get()
            if entry_password.get(): cambios["password"] = entry_password.get()
            if entry_rol.get(): cambios["rol"] = entry_rol.get()

            if cambios:
                self.usuarios.update_one({"_id": ObjectId(user_id)}, {"$set": cambios})
                messagebox.showinfo("Éxito", "Usuario actualizado")
                ventana.destroy()
                self.cargar_usuarios(self.tree_usuarios)

        ctk.CTkButton(ventana, text="Guardar Cambios", command=guardar).pack(pady=20)

    def eliminar_usuario(self):
        seleccionado = self.tree_usuarios.selection()
        if not seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un usuario para eliminar")
            return

        valores = self.tree_usuarios.item(seleccionado[0])["values"]
        user_id = valores[0]

        respuesta = messagebox.askyesno("Confirmar", "¿Seguro que quieres eliminar este usuario?")
        if respuesta:
            from bson.objectid import ObjectId
            self.usuarios.delete_one({"_id": ObjectId(user_id)})
            messagebox.showinfo("Éxito", "Usuario eliminado correctamente")
            self.cargar_usuarios(self.tree_usuarios)

    def abrir_actualizacion_stock(self):
        ventana = self.abrir_nueva_ventana("Actualización de Stock Manual", "700x600")
        ctk.CTkLabel(ventana, text="Actualizar Stock Manualmente", font=("Arial", 18)).pack(pady=10)

        entry_producto = ctk.CTkEntry(ventana, placeholder_text="Nombre del producto")
        entry_producto.pack(pady=5)

        entry_cantidad = ctk.CTkEntry(ventana, placeholder_text="Cantidad a ajustar")
        entry_cantidad.pack(pady=5)

        entry_tipo = ctk.CTkEntry(ventana, placeholder_text="Tipo de ajuste (entrada/salida)")
        entry_tipo.pack(pady=5)

        entry_motivo = ctk.CTkEntry(ventana, placeholder_text="Motivo del ajuste")
        entry_motivo.pack(pady=5)

        def guardar_ajuste():
            producto = entry_producto.get().strip()
            tipo = entry_tipo.get().strip().lower()
            motivo = entry_motivo.get().strip()
            try:
                cantidad = int(entry_cantidad.get())
            except:
                messagebox.showerror("Error", "Cantidad debe ser numérica")
                return

            if tipo not in ["entrada", "salida"]:
                messagebox.showerror("Error", "Tipo debe ser 'entrada' o 'salida'")
                return

            if not all([producto, motivo]):
                messagebox.showwarning("Campos incompletos", "Por favor llena todos los campos")
                return

            prod = self.productos.find_one({"nombre": producto})
            if not prod:
                messagebox.showerror("Error", "Producto no encontrado")
                return

            cantidad_actual = prod["cantidad"]
            nueva_cantidad = cantidad_actual + cantidad if tipo == "entrada" else cantidad_actual - cantidad

            if nueva_cantidad < 0:
                messagebox.showwarning("Cantidad inválida", "El stock no puede ser negativo")
                return

            # Actualizar en MongoDB
            self.productos.update_one(
                {"_id": prod["_id"]},
                 {"$set": {"cantidad": nueva_cantidad}}
            )


            # Guardar en historial
            self.historial_cambios.insert_one({
                "producto_id": str(producto["_id"]),
                "nombre": producto["nombre"],
                "cantidad_anterior": cantidad_actual,
                "cantidad_nueva": nueva_cantidad,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "usuario": self.usuario_actual["nombre"]
            })

            # Guardar en historial
            from datetime import datetime
            self.ajustes_stock.insert_one({
                "producto_id": str(prod["_id"]),
                "producto_nombre": producto,
                "tipo_ajuste": tipo,
                "cantidad": cantidad,
                "motivo": motivo,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            messagebox.showinfo("Éxito", f"Ajuste guardado. Nuevo stock: {nueva_cantidad}")
            self.cargar_ajustes_stock(tree)

        ctk.CTkButton(ventana, text="Guardar Ajuste", command=guardar_ajuste).pack(pady=10)

        # Tabla de historial
        ctk.CTkLabel(ventana, text="Historial de Ajustes", font=("Arial", 16)).pack(pady=10)
        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(pady=10, padx=10, fill="both", expand=True)

        tree = ttk.Treeview(frame_tabla, columns=("Producto", "Tipo", "Cantidad", "Motivo", "Fecha"), show="headings")
        for col in ("Producto", "Tipo", "Cantidad", "Motivo", "Fecha"):
            tree.heading(col, text=col)
            tree.column(col, width=130)

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.cargar_ajustes_stock(tree)
        ctk.CTkButton(ventana, text="Regresar", command=ventana.destroy).pack(pady=10)

    def abrir_consulta_inventario(self):
        from datetime import datetime, timedelta

        ventana = self.abrir_nueva_ventana("Consulta de Inventario", "950x650")
        ctk.CTkLabel(ventana, text="Consulta de Inventario", font=("Arial", 18)).pack(pady=10)

        frame_filtros = ctk.CTkFrame(ventana)
        frame_filtros.pack(pady=10)

        entry_nombre = ctk.CTkEntry(frame_filtros, placeholder_text="Filtrar por nombre")
        entry_nombre.pack(side="left", padx=5)

        entry_categoria = ctk.CTkEntry(frame_filtros, placeholder_text="Filtrar por categoría")
        entry_categoria.pack(side="left", padx=5)

        entry_proveedor = ctk.CTkEntry(frame_filtros, placeholder_text="Filtrar por proveedor")
        entry_proveedor.pack(side="left", padx=5)

        def aplicar_filtros():
            filtros = {}
            if entry_nombre.get():
                filtros["nombre"] = {"$regex": entry_nombre.get(), "$options": "i"}
            if entry_categoria.get():
                filtros["categoria"] = {"$regex": entry_categoria.get(), "$options": "i"}
            if entry_proveedor.get():
                filtros["proveedor"] = {"$regex": entry_proveedor.get(), "$options": "i"}
            self.cargar_productos_filtrados(tree, filtros)

        def limpiar():
            entry_nombre.delete(0, "end")
            entry_categoria.delete(0, "end")
            entry_proveedor.delete(0, "end")
            self.cargar_productos_filtrados(tree, {})

        def filtrar_stock_bajo():
            self.cargar_productos_filtrados(tree, {"cantidad": {"$lt": 10}})

        def filtrar_proximos_a_caducar():
            try:
                hoy = datetime.now()
                limite = hoy + timedelta(days=15)
                self.cargar_productos_filtrados(tree, {
                    "fecha_caducidad": {
                        "$gte": hoy.strftime("%Y-%m-%d"),
                        "$lte": limite.strftime("%Y-%m-%d")
                    }
                })
            except:
                messagebox.showinfo("Aviso", "Algunos productos no tienen fecha de caducidad válida.")

        ctk.CTkButton(frame_filtros, text="Buscar", command=aplicar_filtros).pack(side="left", padx=5)
        ctk.CTkButton(frame_filtros, text="Limpiar", command=limpiar).pack(side="left", padx=5)
        ctk.CTkButton(frame_filtros, text="Stock bajo (<10)", command=filtrar_stock_bajo).pack(side="left", padx=5)
        ctk.CTkButton(frame_filtros, text="Próximos a caducar", command=filtrar_proximos_a_caducar).pack(side="left", padx=5)

        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(pady=10, padx=10, fill="both", expand=True)

        tree = ttk.Treeview(frame_tabla, columns=("Nombre", "Marca", "Categoría", "Cantidad", "Precio", "Caducidad", "Proveedor"), show="headings")
        for col in ("Nombre", "Marca", "Categoría", "Cantidad", "Precio", "Caducidad", "Proveedor"):
            tree.heading(col, text=col)
            tree.column(col, width=120)

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.cargar_productos_filtrados(tree, {})

        ctk.CTkButton(ventana, text="Regresar", command=ventana.destroy).pack(pady=10)
        ctk.CTkButton(ventana, text="Exportar a Excel", command=lambda: self.exportar_excel(tree)).pack(pady=5)

    def abrir_gestion_promociones(self):
        ventana = self.abrir_nueva_ventana("Registrar Promoción", "700x600")
        ctk.CTkLabel(ventana, text="Registrar Nueva Promoción", font=("Arial", 18)).pack(pady=10)

        frame = ctk.CTkFrame(ventana)
        frame.pack(pady=10)

        entry_nombre = ctk.CTkEntry(frame, placeholder_text="Nombre de la promoción")
        entry_nombre.pack(pady=5)

        combo_tipo = ctk.CTkComboBox(frame, values=["Temporada", "Especial", "Liquidación", "Otro"])
        combo_tipo.set("Temporada")
        combo_tipo.pack(pady=5)

        entry_inicio = ctk.CTkEntry(frame, placeholder_text="Fecha inicio (YYYY-MM-DD)")
        entry_inicio.pack(pady=5)

        entry_fin = ctk.CTkEntry(frame, placeholder_text="Fecha fin (YYYY-MM-DD)")
        entry_fin.pack(pady=5)

        entry_descuento = ctk.CTkEntry(frame, placeholder_text="Descuento (%)")
        entry_descuento.pack(pady=5)

        ctk.CTkLabel(frame, text="Selecciona productos asociados:").pack(pady=5)

        listbox_productos = tk.Listbox(frame, selectmode="multiple", height=10)
        listbox_productos.pack(pady=5, fill="x")

        productos = list(self.productos.find())
        for prod in productos:
            listbox_productos.insert("end", f"{prod['_id']} | {prod['nombre']}")

        def guardar_promocion():
            try:
                nombre = entry_nombre.get()
                tipo = combo_tipo.get()
                inicio = entry_inicio.get()
                fin = entry_fin.get()
                descuento = float(entry_descuento.get())
                seleccionados = listbox_productos.curselection()

                if not nombre or not tipo or not inicio or not fin or not seleccionados:
                    messagebox.showwarning("Campos incompletos", "Por favor completa todos los campos")
                    return

                productos_ids = [productos[i]["_id"] for i in seleccionados]

                self.promociones.insert_one({
                    "nombre": nombre,
                    "tipo": tipo,
                    "fecha_inicio": inicio,
                    "fecha_fin": fin,
                    "descuento": descuento,
                    "productos": productos_ids
                })

                messagebox.showinfo("Éxito", "Promoción registrada correctamente")
                ventana.destroy()

            except Exception as e:
                messagebox.showerror("Error", str(e))

        ctk.CTkButton(frame, text="Guardar Promoción", command=guardar_promocion).pack(pady=10)
        ctk.CTkButton(ventana, text="Quitar Promociones", command=self.abrir_tabla_promociones).pack(pady=5)
        ctk.CTkButton(ventana, text="Cerrar", command=ventana.destroy).pack(pady=10)



    
    def abrir_tabla_promociones(self):
        ventana = self.abrir_nueva_ventana("Promociones Activas", "750x500")
        ctk.CTkLabel(ventana, text="Listado de Promociones", font=("Arial", 18)).pack(pady=10)

        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(pady=10, padx=10, fill="both", expand=True)

        tree_promos = ttk.Treeview(frame_tabla, columns=("ID", "Nombre", "Tipo", "Inicio", "Fin", "Descuento"), show="headings")
        for col in ("ID", "Nombre", "Tipo", "Inicio", "Fin", "Descuento"):
            tree_promos.heading(col, text=col)
            tree_promos.column(col, width=100)

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree_promos.yview)
        tree_promos.configure(yscrollcommand=scrollbar.set)
        tree_promos.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def cargar_promociones():
            tree_promos.delete(*tree_promos.get_children())
            for promo in self.promociones.find():
                tree_promos.insert("", "end", values=(
                    str(promo["_id"]),
                    promo["nombre"],
                    promo["tipo"],
                    promo["fecha_inicio"],
                    promo["fecha_fin"],
                    f"{promo['descuento']}%"
                ))

        def eliminar_promocion():
            seleccion = tree_promos.selection()
            if not seleccion:
                messagebox.showwarning("Advertencia", "Selecciona una promoción para eliminar")
                return

            promo_id = tree_promos.item(seleccion[0])["values"][0]
            confirm = messagebox.askyesno("Confirmar", "¿Estás seguro de eliminar esta promoción?")
            if confirm:
                self.promociones.delete_one({"_id": ObjectId(promo_id)})
                messagebox.showinfo("Éxito", "Promoción eliminada correctamente")
                cargar_promociones()

        # Botones
        frame_botones = ctk.CTkFrame(ventana)
        frame_botones.pack(pady=10)

        ctk.CTkButton(frame_botones, text="Eliminar Promoción Seleccionada", command=eliminar_promocion).pack(side="left", padx=10)
        ctk.CTkButton(frame_botones, text="Cerrar", command=ventana.destroy).pack(side="left", padx=10)

        cargar_promociones()


    def abrir_generar_factura(self):
        ventana = self.abrir_nueva_ventana("Generar Factura", "800x600")
        ctk.CTkLabel(ventana, text="Órdenes sin facturar", font=("Arial", 18)).pack(pady=10)

        frame = ctk.CTkFrame(ventana)
        frame.pack(pady=10, fill="both", expand=True)

        tree = ttk.Treeview(frame, columns=("ID", "Proveedor", "Fecha", "Productos", "Estado"), show="headings")
        for col in ("ID", "Proveedor", "Fecha", "Productos", "Estado"):
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        def cargar_ordenes():
            tree.delete(*tree.get_children())
            ordenes = self.ordenes_compra.find({
                "estado": "confirmada",
                "proveedor": self.usuario_actual["nombre"]
            })
            for orden in ordenes:
                productos = ", ".join([f"{p['producto_nombre']} x{p['cantidad']}" for p in orden["productos"]])
                tree.insert("", "end", values=(str(orden["_id"]), orden["proveedor"], orden["fecha_entrega"], productos, orden["estado"]))

        def facturar():
            seleccionado = tree.selection()
            if not seleccionado:
                messagebox.showwarning("Advertencia", "Selecciona una orden")
                return

            orden_id = tree.item(seleccionado[0])["values"][0]
            from bson.objectid import ObjectId
            orden = self.ordenes_compra.find_one({"_id": ObjectId(orden_id)})

            productos = orden["productos"]

            # Ventana para ingresar precios
            ventana_factura = ctk.CTkToplevel(ventana)
            ventana_factura.geometry("500x600")
            ventana_factura.title("Detalle de Factura")

            precios = {}

            for prod in productos:
                frame_linea = ctk.CTkFrame(ventana_factura)
                frame_linea.pack(pady=5)
                ctk.CTkLabel(frame_linea, text=f"{prod['producto_nombre']} (x{prod['cantidad']}):").pack(side="left")
                entry_precio = ctk.CTkEntry(frame_linea, placeholder_text="Precio unitario")
                entry_precio.pack(side="right", padx=10)
                precios[prod['producto_nombre']] = (prod['cantidad'], entry_precio)

            def guardar_factura():
                total = 0
                detalles = []
                for nombre, (cantidad, entry_precio) in precios.items():
                    try:
                        precio_unitario = float(entry_precio.get())
                    except:
                        messagebox.showerror("Error", f"Precio inválido para {nombre}")
                        return
                    subtotal = cantidad * precio_unitario
                    total += subtotal
                    detalles.append({
                        "producto": nombre,
                        "cantidad": cantidad,
                        "precio_unitario": precio_unitario,
                        "subtotal": subtotal
                    })

                self.facturas.insert_one({
                    "orden_id": str(orden["_id"]),
                    "proveedor": orden["proveedor"],
                    "productos": detalles,
                    "precio_total": total,
                    "fecha_emision": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                messagebox.showinfo("Éxito", f"Factura generada. Total: ${total:.2f}")
                ventana_factura.destroy()

            ctk.CTkButton(ventana_factura, text="Guardar Factura", command=guardar_factura).pack(pady=20)

        cargar_ordenes()

        ctk.CTkButton(ventana, text="Facturar Orden Seleccionada", command=facturar).pack(pady=10)
        ctk.CTkButton(ventana, text="Regresar", command=ventana.destroy).pack(pady=5)



    def abrir_consulta_facturas(self):
        ventana = self.abrir_nueva_ventana("Consulta de Facturas", "900x600")
        ctk.CTkLabel(ventana, text="Facturas Recibidas", font=("Arial", 20)).pack(pady=10)

        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(pady=10, padx=10, fill="both", expand=True)

        tree = ttk.Treeview(frame_tabla, columns=("Orden ID", "Proveedor", "Total", "Fecha", "Detalles"), show="headings")
        for col in ("Orden ID", "Proveedor", "Total", "Fecha", "Detalles"):
            tree.heading(col, text=col)
            tree.column(col, width=150)

        tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        def cargar_facturas():
            tree.delete(*tree.get_children())
            facturas = self.facturas.find()
            for f in facturas:
                detalles = ", ".join([f"{p['producto']} x{p['cantidad']} = ${p['subtotal']:.2f}" for p in f["productos"]])
                tree.insert("", "end", values=(
                    f.get("orden_id", "N/A"),
                    f.get("proveedor", "N/A"),
                    f.get("precio_total", 0),
                    f.get("fecha_emision", ""),
                    detalles
                ))

        cargar_facturas()

        ctk.CTkButton(ventana, text="Regresar", command=ventana.destroy).pack(pady=10)


    def abrir_alertas_productos(self):
        from datetime import datetime, timedelta

        ventana = self.abrir_nueva_ventana("Alertas de Inventario", "800x500")
        ctk.CTkLabel(ventana, text="Alertas de Inventario", font=("Arial", 18)).pack(pady=10)

        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(padx=10, pady=10, fill="both", expand=True)

        tree = ttk.Treeview(frame_tabla, columns=("Nombre", "Stock", "Caducidad", "Motivo"), show="headings")
        for col in ("Nombre", "Stock", "Caducidad", "Motivo"):
            tree.heading(col, text=col)
            tree.column(col, width=150)

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Estilos de colores
        tree.tag_configure("caducado", background="#FF9999")        # rojo claro
        tree.tag_configure("proximo", background="#FFF89A")         # amarillo claro

        hoy = datetime.now()
        quince_dias = hoy + timedelta(days=15)

        productos = self.productos.find()
        for prod in productos:
            nombre = prod["nombre"]
            cantidad = prod["cantidad"]
            cad = prod.get("fecha_caducidad", "N/A")

            if cantidad < 10:
                tree.insert("", "end", values=(nombre, cantidad, cad, "⚠ Stock bajo"))

            if cad and cad != "N/A":
                try:
                    fecha_cad = datetime.strptime(cad, "%Y-%m-%d")

                    if fecha_cad < hoy:
                        tree.insert("", "end", values=(nombre, cantidad, cad, "❌ Caducado"), tags=("caducado",))

                    elif hoy <= fecha_cad <= quince_dias:
                        tree.insert("", "end", values=(nombre, cantidad, cad, "⏰ Próximo a caducar"), tags=("proximo",))
                except:
                    pass  # fecha inválida, no hacer nada

        ctk.CTkButton(ventana, text="Regresar", command=ventana.destroy).pack(pady=10)



    def abrir_actualizacion_stock_gerente(self):
        from bson.objectid import ObjectId

        ventana = self.abrir_nueva_ventana("Actualizar Stock - Gerente", "900x600")
        ctk.CTkLabel(ventana, text="Actualizar Stock de Productos", font=("Arial", 20)).pack(pady=10)

        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(pady=10, padx=10, fill="both", expand=True)

        columnas = ("ID", "Nombre", "Categoría", "Cantidad Actual", "Nueva Cantidad")
        tree = ttk.Treeview(frame_tabla, columns=columnas, show="headings")
        for col in columnas:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Cargar productos
        productos = list(self.productos.find())
        for prod in productos:
            tree.insert("", "end", values=(
                str(prod["_id"]),
                prod.get("nombre", ""),
                prod.get("categoria", ""),
                prod.get("cantidad", 0),
                prod.get("cantidad", 0)
            ))

        # Doble clic para editar cantidad
        def editar_celda(event):
            item = tree.identify_row(event.y)
            col = tree.identify_column(event.x)
            if not item or col != "#5":
                return

            x, y, width, height = tree.bbox(item, col)
            valor_actual = tree.set(item, col)
            entry = tk.Entry(tree)
            entry.insert(0, valor_actual)
            entry.place(x=x, y=y, width=width, height=height)
            entry.focus()

            def guardar_valor(event):
                nuevo_valor = entry.get()
                tree.set(item, col, nuevo_valor)
                entry.destroy()

            entry.bind("<Return>", guardar_valor)
            entry.bind("<FocusOut>", lambda e: entry.destroy())

        tree.bind("<Double-1>", editar_celda)

        def guardar_actualizaciones():
            cambios = []
            for item in tree.get_children():
                valores = tree.item(item)["values"]
                prod_id, nombre, categoria, actual, nuevo = valores

                try:
                    nuevo_valor = int(nuevo)
                    actual_valor = int(actual)
                except:
                    messagebox.showerror("Error", f"Cantidad inválida para {nombre}")
                    return

                if nuevo_valor != actual_valor:
                    cambios.append((prod_id, nuevo_valor, nombre))

            if not cambios:
                messagebox.showinfo("Sin cambios", "No se realizaron cambios en el stock.")
                return

            for prod_id, nuevo_stock, nombre in cambios:
                self.productos.update_one(
                    {"_id": ObjectId(prod_id)},
                    {"$set": {"cantidad": nuevo_stock}}
                )
                self.ajustes_stock.insert_one({
                    "producto_id": prod_id,
                    "producto_nombre": nombre,
                    "tipo_ajuste": "modificación directa",
                    "cantidad": abs(nuevo_stock),
                    "motivo": "Ajuste manual del gerente",
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            messagebox.showinfo("Éxito", "Stock actualizado correctamente.")
            ventana.destroy()

        ctk.CTkButton(ventana, text="Guardar Cambios", command=guardar_actualizaciones).pack(pady=10)
        ctk.CTkButton(ventana, text="Cerrar", command=ventana.destroy).pack()

    def abrir_asignar_proveedor_producto(self):
        ventana = self.abrir_nueva_ventana("Asignar Proveedor a Producto", "800x500")
        ctk.CTkLabel(ventana, text="Selecciona un Producto para Asignarle Proveedor", font=("Arial", 18)).pack(pady=10)

        # Tabla con productos
        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(pady=10, padx=10, fill="both", expand=True)

        tree = ttk.Treeview(frame_tabla, columns=("ID", "Nombre", "Marca", "Categoría", "Cantidad", "Proveedor"), show="headings")
        for col in ("ID", "Nombre", "Marca", "Categoría", "Cantidad", "Proveedor"):
            tree.heading(col, text=col)
            tree.column(col, width=120)
        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Cargar productos
        productos = list(self.productos.find())
        for prod in productos:
            tree.insert("", "end", values=(
                str(prod["_id"]),
                prod.get("nombre", ""),
                prod.get("marca", ""),
                prod.get("categoria", ""),
                prod.get("cantidad", 0),
                prod.get("proveedor", "Sin asignar")
            ))

        # Lista de proveedores
        proveedores = list(self.proveedores.find())
        nombres_proveedores = [prov["nombre"] for prov in proveedores]

        ctk.CTkLabel(ventana, text="Selecciona proveedor:").pack(pady=5)
        combo_proveedor = ctk.CTkComboBox(ventana, values=nombres_proveedores)
        combo_proveedor.pack(pady=5)

        def asignar_proveedor():
            seleccionado = tree.selection()
            if not seleccionado:
                messagebox.showwarning("Selección requerida", "Selecciona un producto de la tabla.")
                return

            producto_id = tree.item(seleccionado[0])["values"][0]
            proveedor = combo_proveedor.get()

            if not proveedor:
                messagebox.showwarning("Faltan datos", "Selecciona un proveedor.")
                return

            from bson.objectid import ObjectId
            self.productos.update_one(
                {"_id": ObjectId(producto_id)},
                {"$set": {"proveedor": proveedor}}
            )
            messagebox.showinfo("Éxito", "Proveedor asignado correctamente.")

            # Recargar tabla
            tree.delete(*tree.get_children())
            productos_actualizados = list(self.productos.find())
            for prod in productos_actualizados:
                tree.insert("", "end", values=(
                    str(prod["_id"]),
                    prod.get("nombre", ""),
                    prod.get("marca", ""),
                    prod.get("categoria", ""),
                    prod.get("cantidad", 0),
                    prod.get("proveedor", "Sin asignar")
                ))

        ctk.CTkButton(ventana, text="Asignar Proveedor", command=asignar_proveedor).pack(pady=10)
        ctk.CTkButton(ventana, text="Cerrar", command=ventana.destroy).pack(pady=5)

    def abrir_actualizar_proveedor_producto(self):
        ventana = self.abrir_nueva_ventana("Actualizar Proveedor de Producto", "800x500")
        ctk.CTkLabel(ventana, text="Actualizar Proveedor del Producto", font=("Arial", 18)).pack(pady=10)

        # Tabla de productos
        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(pady=10, padx=10, fill="both", expand=True)

        tree = ttk.Treeview(frame_tabla, columns=("ID", "Nombre", "Marca", "Categoría", "Cantidad", "Proveedor"), show="headings")
        for col in ("ID", "Nombre", "Marca", "Categoría", "Cantidad", "Proveedor"):
            tree.heading(col, text=col)
            tree.column(col, width=120)
        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def cargar_productos():
            tree.delete(*tree.get_children())
            productos = list(self.productos.find())
            for prod in productos:
                tree.insert("", "end", values=(
                    str(prod["_id"]),
                    prod.get("nombre", ""),
                    prod.get("marca", ""),
                    prod.get("categoria", ""),
                    prod.get("cantidad", 0),
                    prod.get("proveedor", "Sin asignar")
                ))

        cargar_productos()

        # Selección de nuevo proveedor
        ctk.CTkLabel(ventana, text="Selecciona nuevo proveedor:").pack(pady=5)
        proveedores = list(self.proveedores.find())
        nombres_proveedores = [prov["nombre"] for prov in proveedores]
        combo_proveedor = ctk.CTkComboBox(ventana, values=nombres_proveedores)
        combo_proveedor.pack(pady=5)

        def actualizar_proveedor():
            seleccionado = tree.selection()
            if not seleccionado:
                messagebox.showwarning("Selección requerida", "Selecciona un producto.")
                return

            proveedor = combo_proveedor.get()
            if not proveedor:
                messagebox.showwarning("Falta proveedor", "Selecciona un proveedor.")
                return

            from bson.objectid import ObjectId
            producto_id = tree.item(seleccionado[0])["values"][0]

            resultado = self.productos.update_one(
                {"_id": ObjectId(producto_id)},
                {"$set": {"proveedor": proveedor}}
            )

            if resultado.modified_count > 0:
                messagebox.showinfo("Éxito", "Proveedor actualizado correctamente.")
            else:
                messagebox.showwarning("Sin cambios", "No se modificó ningún registro.")

            cargar_productos()

        ctk.CTkButton(ventana, text="Actualizar Proveedor", command=actualizar_proveedor).pack(pady=10)
        ctk.CTkButton(ventana, text="Cerrar", command=ventana.destroy).pack(pady=5)

    def abrir_crear_orden(self):
        ventana = self.abrir_nueva_ventana("Crear Orden de Compra", "700x600")
        ctk.CTkLabel(ventana, text="Crear Orden de Compra", font=("Arial", 20)).pack(pady=10)

        # Selección de proveedor
        proveedores = list(self.proveedores.find())
        nombres_proveedores = [p["nombre"] for p in proveedores]

        ctk.CTkLabel(ventana, text="Selecciona Proveedor").pack()
        combo_proveedor = ctk.CTkComboBox(ventana, values=nombres_proveedores)
        combo_proveedor.pack(pady=5)

        # Tabla de productos con checkbox de selección
        productos = list(self.productos.find())
        productos_var = []
        cantidades_var = []

        frame_scroll = ctk.CTkScrollableFrame(ventana, height=300)
        frame_scroll.pack(pady=10, fill="both", expand=True)

        for prod in productos:
            var = tk.BooleanVar()
            cant_var = tk.StringVar()
            frame = ctk.CTkFrame(frame_scroll)
            frame.pack(fill="x", pady=2)
            tk.Checkbutton(frame, text=f"{prod['nombre']} | Stock: {prod['cantidad']}", variable=var).pack(side="left", padx=5)
            tk.Entry(frame, textvariable=cant_var, width=5).pack(side="right", padx=5)
            productos_var.append((prod, var, cant_var))

        ctk.CTkLabel(ventana, text="Fecha estimada de entrega (YYYY-MM-DD)").pack()
        entry_fecha = ctk.CTkEntry(ventana)
        entry_fecha.pack(pady=5)

        def guardar_orden():
            proveedor = combo_proveedor.get()
            fecha_entrega = entry_fecha.get()
            seleccionados = []

            for prod, var, cant_var in productos_var:
                if var.get():
                    try:
                        cantidad = int(cant_var.get())
                        if cantidad <= 0:
                            raise ValueError
                    except:
                        messagebox.showerror("Error", f"Cantidad inválida para {prod['nombre']}")
                        return
                    seleccionados.append({
                        "producto_id": str(prod["_id"]),
                        "producto_nombre": prod["nombre"],
                        "cantidad": cantidad
                    })

            if not proveedor or not seleccionados or not fecha_entrega:
                messagebox.showwarning("Campos incompletos", "Completa todos los campos")
                return

            self.ordenes_compra.insert_one({
                "proveedor": proveedor,
                "productos": seleccionados,
                "fecha_entrega": fecha_entrega,
                "estado": "pendiente"
            })

            messagebox.showinfo("Éxito", "Orden de compra creada correctamente")
            ventana.destroy()

        ctk.CTkButton(ventana, text="Guardar Orden", command=guardar_orden).pack(pady=10)

    def abrir_ordenes_proveedor(self):
        ventana = self.abrir_nueva_ventana("Órdenes de Compra", "800x600")
        ctk.CTkLabel(ventana, text="Órdenes Pendientes", font=("Arial", 18)).pack(pady=10)

        frame_tabla = ctk.CTkFrame(ventana)
        frame_tabla.pack(pady=10, padx=10, fill="both", expand=True)

        tree = ttk.Treeview(frame_tabla, columns=("ID", "Proveedor", "Fecha", "Estado", "Productos"), show="headings")
        for col in ("ID", "Proveedor", "Fecha", "Estado", "Productos"):
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        def cargar_ordenes():
            tree.delete(*tree.get_children())
            ordenes = self.ordenes_compra.find({"estado": "pendiente"})
            for orden in ordenes:
                productos = ", ".join([f"{p['producto_nombre']} (x{p['cantidad']})" for p in orden["productos"]])
                tree.insert("", "end", values=(str(orden["_id"]), orden["proveedor"], orden["fecha_entrega"], orden["estado"], productos))

        def confirmar_orden():
            seleccionado = tree.selection()
            if not seleccionado:
                messagebox.showwarning("Advertencia", "Selecciona una orden para confirmar")
                return
            orden_id = tree.item(seleccionado[0])["values"][0]
            from bson.objectid import ObjectId
            self.ordenes_compra.update_one({"_id": ObjectId(orden_id)}, {"$set": {"estado": "confirmada"}})
            messagebox.showinfo("Confirmada", "Orden confirmada correctamente")
            cargar_ordenes()

        cargar_ordenes()

        ctk.CTkButton(ventana, text="Confirmar Orden Seleccionada", command=confirmar_orden).pack(pady=10)
        
        ctk.CTkButton(ventana, text="Regresar", command=ventana.destroy).pack(pady=5)

    def mostrar_soporte(self):
            ventana = ctk.CTkToplevel(self.app)
            ventana.geometry("400x300")
            ventana.title("🛠 Soporte Técnico")

            ctk.CTkLabel(ventana, text="🛠 Soporte Técnico", font=("Arial", 20)).pack(pady=20)

            ctk.CTkLabel(ventana, text="Nombre: Edgar Espinosa", font=("Arial", 14)).pack(pady=5)
            ctk.CTkLabel(ventana, text="Correo: edgar.espinosa@lasallistas.org.mx", font=("Arial", 14)).pack(pady=5)
            ctk.CTkLabel(ventana, text="Teléfono: 5536977657", font=("Arial", 14)).pack(pady=5)

            def copiar_correo():
                ventana.clipboard_clear()
                ventana.clipboard_append("edgar.espinosa@lasallistas.org.mx")
                messagebox.showinfo("Copiado", "Correo copiado al portapapeles.")

            ctk.CTkButton(ventana, text="💌 Copiar Correo", command=copiar_correo).pack(pady=10)
            ctk.CTkButton(ventana, text="Cerrar", command=ventana.destroy).pack(pady=10)


if __name__ == "__main__":
    app = SistemaInventario()
    app.run()



