import streamlit as st
import sqlite3
import urllib.parse
from datetime import datetime

# CONFIGURACIÓN DE LA PÁGINA (Optimizada para celular)
st.set_page_config(page_title="SoderoApp 💧", page_icon="💧", layout="centered")

# CONFIGURACIÓN DEL NEGOCIO (Cambiá tu alias acá)
ALIAS_MERCADO_PAGO = "SODA.EL.BARRIO.MP"

# 1. CONEXIÓN Y CREACIÓN DE BASE DE DATOS (SQLite)
def conectar_db():
    conn = sqlite3.connect("sodero.db")
    return conn

def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()
    # Tabla de clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            direccion TEXT NOT NULL,
            telefono TEXT NOT NULL,
            dia_visita TEXT NOT NULL,
            envases_prestados INTEGER DEFAULT 0,
            saldo_dinero REAL DEFAULT 0.0
        )
    """)
    conn.commit()
    
    # Insertar datos de prueba si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM clientes")
    if cursor.fetchone()[0] == 0:
        usuarios_prueba = [
            ("Doña Rosa", "Calle Falsa 123", "5493412345678", "Lunes"),
            ("Don Carlos (Kiosco)", "Av. San Martín 450", "5493418765432", "Lunes"),
            ("Almacén de Pocho", "Belgrano 789", "5493415554433", "Martes"),
            ("María Laura", "Pellegrini 1212", "5493416667788", "Lunes")
        ]
        cursor.executemany("""
            INSERT INTO clientes (nombre, direccion, telefono, dia_visita, envases_prestados, saldo_dinero)
            VALUES (?, ?, ?, ?, 0, 0.0)
        """, usuarios_prueba)
        conn.commit()
    conn.close()

inicializar_db()

# 2. FUNCIONES DE LÓGICA DE NEGOCIO
def obtener_clientes_por_dia(dia):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, direccion, telefono, envases_prestados, saldo_dinero FROM clientes WHERE dia_visita = ?", (dia,))
    clientes = cursor.fetchall()
    conn.close()
    return clientes

def registrar_visita(id_cliente, entregados, retirados, total_pesos, pago):
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Buscar valores actuales
    cursor.execute("SELECT envases_prestados, saldo_dinero FROM clientes WHERE id = ?", (id_cliente,))
    actual = cursor.fetchone()
    envases_actuales = actual[0]
    saldo_actual = actual[1]
    
    # Calcular nuevos valores
    nuevos_envases = envases_actuales + (entregados - retirados)
    nuevo_saldo = saldo_actual + (total_pesos - pago)
    
    # Actualizar base de datos
    cursor.execute("""
        UPDATE clientes 
        SET envases_prestados = ?, saldo_dinero = ? 
        WHERE id = ?
    """, (nuevos_envases, nuevo_saldo, id_cliente))
    
    conn.commit()
    conn.close()
    return nuevos_envases, nuevo_saldo

def agregar_nuevo_cliente(nombre, direccion, telefono, dia):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO clientes (nombre, direccion, telefono, dia_visita)
        VALUES (?, ?, ?, ?)
    """, (nombre, direccion, telefono, dia))
    conn.commit()
    conn.close()

# 3. INTERFAZ GRÁFICA (Streamlit)
st.title("💧 SoderoApp - Gestión de Barrio")

# Selector de Modo en la barra lateral
modo = st.sidebar.radio("Menú", ["🚚 Hoja de Ruta", "👤 Agregar Cliente"])

# --- MODO: HOJA DE RUTA ---
if modo == "🚚 Hoja de Ruta":
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
    
    # Detectar día actual de forma automática para ahorrar clics (0=Lunes, 5=Sábado)
    dia_actual_num = datetime.now().weekday()
    dia_defecto = dias_semana[dia_actual_num] if dia_actual_num < 6 else "Lunes"
    
    dia_seleccionado = st.selectbox("Seleccionar Día de Reparto:", dias_semana, index=dias_semana.index(dia_defecto))
    
    clientes = obtener_clientes_por_dia(dia_seleccionado)
    
    st.subheader(f"Clientes del {dia_seleccionado} ({len(clientes)})")
    st.write("---")
    
    if not clientes:
        st.info("No hay clientes agendados para este día.")
    
    for clie in clientes:
        id_clie, nombre, direccion, telefono, envases, saldo = clie
        
        # Tarjeta visual por cada cliente
        with st.expander(f"📍 {nombre} - {direccion}"):
            st.write(f"📞 **Teléfono:** {telefono}")
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.metric("Sifones en su casa", f"{envases} u.")
            with col_info2:
                # Color rojo si debe plata, verde si está al día
                st.metric("Saldo actual (Libreta)", f"${saldo:,.2f}", delta=-saldo if saldo > 0 else None, delta_color="inverse")
            
            # Formulario de carga rápida
            st.write("**Registrar Entrega de Hoy:**")
            with st.form(key=f"form_{id_clie}"):
                col1, col2 = st.columns(2)
                with col1:
                    entregados = st.number_input("📥 Llenos entregados", min_value=0, value=2, step=1, key=f"ent_{id_clie}")
                    total_pesos = st.number_input("💰 Total a cobrar ($)", min_value=0.0, value=2000.0, step=100.0, key=f"tot_{id_clie}")
                with col2:
                    retirados = st.number_input("📤 Vacíos retirados", min_value=0, value=2, step=1, key=f"ret_{id_clie}")
                    pago = st.number_input("💵 ¿Cuánto pagó hoy? ($)", min_value=0.0, value=2000.0, step=100.0, key=f"pag_{id_clie}")
                
                boton_guardar = st.form_submit_button("💾 Guardar Visita")
                
                if boton_guardar:
                    # Guardamos en la base de datos
                    n_envases, n_saldo = registrar_visita(id_clie, entregados, retirados, total_pesos, pago)
                    st.success(f"¡Guardado! Nuevo saldo: ${n_saldo:,.2f} | Sifones: {n_envases}")
                    
                    # Generamos el texto para WhatsApp
                    texto_comprobante = f"""*💧 REPARTO DE SODA - COMPROBANTE *
----------------------------------------
*Cliente:* {nombre}
*Dirección:* {direccion}
*Fecha:* {datetime.now().strftime('%d/%m/%Y')}

*Detalle:*
• Sifones Entregados: {entregados}
• Sifones Retirados: {retirados}

*Resumen:*
• Total de hoy: ${total_pesos:,.2f}
• Pagó hoy: ${pago:,.2f}
----------------------------------------
• *SALDO ACTUAL EN LIBRETA:* ${n_saldo:,.2f}

💳 *Alias Transferencia:*
*{ALIAS_MERCADO_PAGO}*
(Podés copiar el alias y pegar en Mercado Pago)

_¡Muchas gracias!_ 😊"""
                    
                    # Crear el enlace directo a WhatsApp
                    texto_url = urllib.parse.quote(texto_comprobante)
                    url_wa = f"https://wa.me/{telefono}?text={texto_url}"
                    
                    # Botón llamativo para enviar
                    st.markdown(f"""
                        <a href="{url_wa}" target="_blank">
                            <button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:5px; font-weight:bold; cursor:pointer;">
                                📲 Enviar Comprobante por WhatsApp
                            </button>
                        </a>
                    """, unsafe_allow_html=True)

# --- MODO: AGREGAR CLIENTE ---
elif modo == "👤 Agregar Cliente":
    st.subheader("Registrar nuevo cliente en el barrio")
    
    with st.form("nuevo_cliente"):
        nombre = st.text_input("Nombre y Apellido:")
        direccion = st.text_input("Dirección (Ej: Av. Belgrano 123 o 'Portón Verde'):")
        telefono = st.text_input("Celular (Con código de área sin el 15, ej: 5493412345678):")
        dia = st.selectbox("Día de visita asignado:", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        
        enviar_alta = st.form_submit_button("➕ Dar de Alta Cliente")
        
        if enviar_alta:
            if nombre and direccion and telefono:
                agregar_nuevo_cliente(nombre, direccion, telefono, dia)
                st.success(f"¡{nombre} fue agregado correctamente para los días {dia}!")
            else:
                st.error("Por favor, completa todos los campos obligatorios.")