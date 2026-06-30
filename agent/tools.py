# agent/tools.py — Herramientas del agente
# Generado por AgentKit

"""
Herramientas específicas de Calden Viajes.
Estas funciones extienden las capacidades de Valentina más allá de responder texto.
Cubren los casos de uso elegidos: FAQ, cotización/reservas, leads/ventas y soporte.
"""

import os
import json
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")

# Archivo simple donde se registran los leads/cotizaciones capturados
LEADS_FILE = "leads.json"


def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    """Retorna el horario de atención del negocio."""
    info = cargar_info_negocio()
    horario = info.get("negocio", {}).get("horario", "No disponible")
    # Horario: Lunes a Viernes de 10:00 a 18:00
    ahora = datetime.now()
    es_dia_habil = ahora.weekday() < 5            # 0=Lunes ... 4=Viernes
    en_horario = 10 <= ahora.hour < 18
    return {
        "horario": horario,
        "esta_abierto": es_dia_habil and en_horario,
    }


def buscar_en_knowledge(consulta: str) -> str:
    """
    Busca información relevante en los archivos de /knowledge.
    Retorna el contenido más relevante encontrado.
    """
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                # Búsqueda simple por coincidencia de texto
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en mis archivos."


# ════════════════════════════════════════════════════════════
# LEADS / VENTAS Y COTIZACIONES
# ════════════════════════════════════════════════════════════

# Datos que se necesitan para armar una cotización en Calden Viajes
CAMPOS_COTIZACION = [
    "destino",
    "fecha_salida",
    "cantidad_pasajeros",
    "tipo_habitacion",
    "presupuesto",      # opcional
    "contacto",         # nombre + WhatsApp/email
]


def _leer_leads() -> list[dict]:
    """Lee los leads guardados (lista vacía si no existe el archivo)."""
    if not os.path.exists(LEADS_FILE):
        return []
    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def registrar_lead(telefono: str, nombre: str, interes: str) -> dict:
    """
    Registra un lead/prospecto interesado en un viaje.

    Args:
        telefono: Número de WhatsApp del cliente
        nombre: Nombre del cliente
        interes: Destino o paquete de interés

    Returns:
        El lead registrado.
    """
    leads = _leer_leads()
    lead = {
        "telefono": telefono,
        "nombre": nombre,
        "interes": interes,
        "estado": "nuevo",
        "creado": datetime.now().isoformat(),
    }
    leads.append(lead)
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)
    logger.info(f"Lead registrado: {nombre} ({telefono}) — interés: {interes}")
    return lead


def registrar_cotizacion(telefono: str, datos: dict) -> dict:
    """
    Registra un pedido de cotización con los datos recopilados al cliente.

    Args:
        telefono: Número de WhatsApp del cliente
        datos: Diccionario con los campos de CAMPOS_COTIZACION

    Returns:
        Diccionario con la cotización registrada y los campos que faltan (si los hay).
    """
    faltantes = [
        campo for campo in CAMPOS_COTIZACION
        if campo != "presupuesto" and not datos.get(campo)
    ]
    leads = _leer_leads()
    cotizacion = {
        "telefono": telefono,
        "tipo": "cotizacion",
        "datos": datos,
        "estado": "pendiente_confirmacion",
        "creado": datetime.now().isoformat(),
    }
    leads.append(cotizacion)
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)
    logger.info(f"Cotización registrada para {telefono}: {datos}")
    return {"cotizacion": cotizacion, "faltantes": faltantes}


def escalar_a_vendedor(telefono: str, contexto: str) -> dict:
    """
    Marca que la conversación debe pasar a un asesor humano de Calden Viajes.

    Args:
        telefono: Número del cliente
        contexto: Resumen de lo que necesita

    Returns:
        Confirmación del escalamiento (incluye contactos de la agencia).
    """
    info = cargar_info_negocio()
    telefonos = info.get("negocio", {}).get("telefonos", [])
    logger.info(f"Escalando a vendedor — {telefono}: {contexto}")
    return {
        "escalado": True,
        "telefono_cliente": telefono,
        "contexto": contexto,
        "contactos_agencia": telefonos,
    }


# ════════════════════════════════════════════════════════════
# SOPORTE POST-VENTA
# ════════════════════════════════════════════════════════════

def crear_ticket(telefono: str, problema: str) -> dict:
    """
    Crea un ticket de soporte post-venta simple.

    Args:
        telefono: Número del cliente
        problema: Descripción del problema o consulta

    Returns:
        El ticket creado con un ID.
    """
    leads = _leer_leads()
    ticket_id = f"TICKET-{len(leads) + 1:04d}"
    ticket = {
        "telefono": telefono,
        "tipo": "soporte",
        "ticket_id": ticket_id,
        "problema": problema,
        "estado": "abierto",
        "creado": datetime.now().isoformat(),
    }
    leads.append(ticket)
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)
    logger.info(f"Ticket {ticket_id} creado para {telefono}: {problema}")
    return ticket
