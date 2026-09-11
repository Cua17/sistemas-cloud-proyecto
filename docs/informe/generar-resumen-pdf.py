# -*- coding: utf-8 -*-
"""Genera la guia del proyecto NubeUltima para el grupo (PDF)."""
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle, ListFlowable, ListItem,
                                KeepTogether, Flowable)

OUT = r"C:\Users\jdcua\OneDrive\Universidad\2026 - Ciclo 2\Sistemas Cloud\docs\informe\Resumen-NubeUltima.pdf"

AZUL   = colors.HexColor("#1f4e79")
AZULC  = colors.HexColor("#eef3f9")
GRIS   = colors.HexColor("#555555")
LINEA  = colors.HexColor("#c9d4df")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                    fontSize=15, textColor=AZUL, spaceBefore=16, spaceAfter=7)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                    fontSize=11.5, textColor=colors.HexColor("#2c3e50"),
                    spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("BODY", parent=ss["BodyText"], fontName="Helvetica",
                      fontSize=10, leading=15, spaceAfter=6, alignment=TA_LEFT)
SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=9, textColor=GRIS, leading=13)
CELL = ParagraphStyle("CELL", parent=BODY, fontSize=9, leading=12, spaceAfter=0)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold")
TITLE = ParagraphStyle("TITLE", parent=ss["Title"], fontName="Helvetica-Bold",
                       fontSize=24, textColor=AZUL, spaceAfter=6, alignment=TA_CENTER)
SUB = ParagraphStyle("SUB", parent=BODY, fontSize=12, textColor=GRIS,
                     alignment=TA_CENTER, spaceAfter=2)


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRIS)
    canvas.drawString(2*cm, 1.1*cm, "NubeUltima - Resumen del proyecto")
    canvas.drawRightString(A4[0]-2*cm, 1.1*cm, "Pagina %d" % doc.page)
    canvas.setStrokeColor(LINEA)
    canvas.line(2*cm, 1.4*cm, A4[0]-2*cm, 1.4*cm)
    canvas.restoreState()


class Diagrama(Flowable):
    """Diagrama simple de las 5 cajas."""
    def __init__(self, w=16*cm, h=10.8*cm):
        self.width, self.height = w, h

    def box(self, c, x, y, w, h, titulo, sub, fill=AZULC):
        c.setFillColor(fill); c.setStrokeColor(AZUL); c.setLineWidth(1)
        c.roundRect(x, y, w, h, 4, stroke=1, fill=1)
        c.setFillColor(AZUL); c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x+w/2, y+h-13, titulo)
        c.setFillColor(GRIS); c.setFont("Helvetica", 7.5)
        ty = y+h-25
        for ln in sub:
            c.drawCentredString(x+w/2, ty, ln); ty -= 9

    def arrow(self, c, x1, y1, x2, y2):
        c.setStrokeColor(AZUL); c.setLineWidth(1.2)
        c.line(x1, y1, x2, y2)
        import math
        a = math.atan2(y2-y1, x2-x1)
        c.line(x2, y2, x2-6*math.cos(a-0.4), y2-6*math.sin(a-0.4))
        c.line(x2, y2, x2-6*math.cos(a+0.4), y2-6*math.sin(a+0.4))

    def draw(self):
        c = self.canv
        W = self.width
        # Dispositivos IoT
        self.box(c, 0, 9.7*cm, 6.2*cm, 1.0*cm, "Dispositivos IoT (simulados)",
                 ["medidores luz/agua + aire  -  4 zonas"], fill=colors.HexColor("#fff4e5"))
        self.arrow(c, 3.1*cm, 9.7*cm, 3.1*cm, 9.05*cm)
        c.setFont("Helvetica-Oblique", 7.5); c.setFillColor(GRIS)
        c.drawString(3.35*cm, 9.25*cm, "MQTT (ultima milla)")
        # Caja grande: la Raspberry Pi
        c.setFillColor(colors.HexColor("#f7f9fb")); c.setStrokeColor(GRIS)
        c.setLineWidth(1); c.roundRect(0, 0.2*cm, W, 8.6*cm, 5, stroke=1, fill=1)
        c.setFillColor(colors.HexColor("#2c3e50")); c.setFont("Helvetica-Bold", 9.5)
        c.drawString(0.35*cm, 8.35*cm, "Raspberry Pi 4   -   KVM (crea las maquinas virtuales)")
        # 3 VMs
        self.box(c, 0.4*cm, 5.15*cm, 4.9*cm, 2.85*cm, "VM control",
                 ["Kubernetes (server)", "publica el panel web"])
        self.box(c, 5.55*cm, 5.15*cm, 4.9*cm, 2.85*cm, "VM worker",
                 ["Kubernetes (worker)", "corre los", "microservicios"])
        self.box(c, 10.7*cm, 5.15*cm, 4.9*cm, 2.85*cm, "VM storage",
                 ["MinIO", "(almacen de respaldos)"])
        c.setFont("Helvetica-Oblique", 8); c.setFillColor(GRIS)
        c.drawString(0.4*cm, 4.75*cm, "IaaS = las 3 maquinas virtuales      PaaS = Kubernetes, que las une")
        # microservicios + monitoreo
        self.box(c, 0.4*cm, 2.9*cm, 10.05*cm, 1.55*cm, "Microservicios (dentro de Kubernetes)",
                 ["simulador  ->  broker MQTT  ->", "ingestion + base de datos  ->  deteccion de anomalias"])
        self.box(c, 10.7*cm, 2.9*cm, 4.9*cm, 1.55*cm, "Monitoreo",
                 ["Prometheus", "(CPU, RAM, temperatura)"])
        self.arrow(c, 5.4*cm, 2.9*cm, 5.4*cm, 2.35*cm)
        self.box(c, 0.4*cm, 0.9*cm, 10.05*cm, 1.35*cm, "Panel del operador   (SaaS)",
                 ["el usuario abre el navegador y lo usa"], fill=colors.HexColor("#e8f5e9"))
        self.box(c, 10.7*cm, 0.9*cm, 4.9*cm, 1.35*cm, "Respaldo   (BaaS)",
                 ["restic  ->  MinIO,", "con verificacion"], fill=colors.HexColor("#e8f5e9"))


def tabla(data, col_widths, header=True):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0,0), (-1,-1), 0.5, LINEA),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]
    if header:
        style += [("BACKGROUND", (0,0), (-1,0), AZUL),
                  ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                  ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                  ("FONTSIZE", (0,0), (-1,0), 9)]
    t.setStyle(TableStyle(style))
    return t


def P(txt, st=CELL):
    return Paragraph(txt, st)


story = []

# ---------- PORTADA ----------
story += [Spacer(1, 4*cm),
          Paragraph("NubeUltima", TITLE),
          Paragraph("Plataforma Cloud para Telemetria IoT de Ultima Milla", SUB),
          Spacer(1, 0.6*cm),
          Paragraph("Resumen del proyecto", ParagraphStyle(
              "x", parent=SUB, fontSize=13, textColor=AZUL, fontName="Helvetica-Bold")),
          Spacer(1, 2.5*cm)]
port = tabla([
    [P("Curso", CELLB), P("Sistemas Cloud y Tecnologias de Ultima Milla (EHP 1)")],
    [P("Catedratico", CELLB), P("Sergio Saenz")],
    [P("Hardware", CELLB), P("Raspberry Pi 4 (4 GB) + microSD 128 GB")],
], [3*cm, 12*cm], header=False)
story += [port, Spacer(1, 1*cm)]
story.append(Flowable())  # dummy
from reportlab.platypus import PageBreak
story.append(PageBreak())

# ---------- 1 ----------
story += [Paragraph("1. Que hicimos", H1),
          Paragraph(
    "Construimos, dentro de una <b>Raspberry Pi</b>, una version en miniatura del sistema "
    "en la nube que usaria una empresa de telecomunicaciones para ofrecer un servicio de "
    "<b>ciudad inteligente</b>.", BODY),
          Paragraph(
    "El escenario: una ciudad con <b>medidores de luz y agua</b> y <b>sensores de calidad "
    "de aire</b> repartidos en 4 zonas. Esos dispositivos (simulados por un programa, "
    "porque no tenemos sensores fisicos) envian sus lecturas por la <b>ultima milla</b> "
    "usando MQTT (el protocolo real de las redes IoT). Las lecturas llegan a un "
    "<b>centro de datos de 3 maquinas virtuales</b>, donde una plataforma de microservicios "
    "las procesa, detecta problemas (fugas, picos de consumo, aire contaminado) y los "
    "muestra en un <b>panel web</b> para un operador municipal.", BODY),
          Paragraph(
    "El proyecto demuestra las <b>4 capas de servicio de la nube</b>: IaaS, PaaS, SaaS y "
    "BaaS, mas monitoreo del hardware.", BODY)]

# ---------- 2 diagrama ----------
story += [Paragraph("2. El diagrama", H1),
          Paragraph("Este es el dibujo que va en la diapositiva principal:", BODY),
          Spacer(1, 3*mm), Diagrama(), Spacer(1, 2*mm)]
story.append(PageBreak())

# ---------- 3 capas ----------
story += [Paragraph("3. Las capas, explicadas facil", H1)]
capas = [
    [P("Capa", CELLB), P("Que es (en una frase)", CELLB), P("En el proyecto es...", CELLB), P("Herramienta", CELLB)],
    [P("IaaS", CELLB), P("Infraestructura como servicio: te dan maquinas / servidores pelados."),
     P("Las 3 maquinas virtuales creadas dentro de la Pi, cada una con su IP fija."),
     P("KVM (el virtualizador de Linux)")],
    [P("PaaS", CELLB), P("Plataforma como servicio: te dan donde \"enchufar\" tus apps sin administrar servidores."),
     P("Un cluster de Kubernetes que reparte los microservicios entre las VMs y los reinicia si se caen."),
     P("K3s (Kubernetes ligero)")],
    [P("SaaS", CELLB), P("Software como servicio: abris una pagina y la usas, como Gmail."),
     P("El panel del operador: mapa de zonas, medidores y alertas en vivo."),
     P("App web propia (Python)")],
    [P("BaaS", CELLB), P("Backup como servicio: contratar \"que alguien me haga las copias\"."),
     P("Respaldos automaticos y cifrados, con una prueba que verifica que se pueden restaurar."),
     P("MinIO + restic")],
    [P("Monitoreo", CELLB), P("Vigilar cuanto consume el hardware."),
     P("CPU, RAM, disco y temperatura de la Pi y las 3 VMs, visibles en el panel."),
     P("Prometheus")],
]
story += [tabla(capas, [1.7*cm, 4.6*cm, 5.3*cm, 3.4*cm]),
          Spacer(1, 2*mm),
          Paragraph("<b>Kubernetes</b> es un \"orquestador\": vos le decis \"quiero esta app "
                    "corriendo siempre\" y el se encarga de mantenerla viva, distribuirla y "
                    "reiniciarla. Es el tema central de la presentacion 3 del curso.", SMALL)]

# ---------- 4 recorrido ----------
story += [Paragraph("4. Como funciona: el recorrido de un dato", H1)]
pasos = [
    "Un <b>medidor</b> (simulado) genera una lectura: por ejemplo \"agua, zona 3, 5 L/min\".",
    "La manda por <b>MQTT</b> a un servidor de mensajes (Mosquitto) dentro del centro de datos.",
    "El microservicio de <b>ingestion</b> la recibe, la valida y la guarda en una base de datos (SQLite).",
    "Las <b>reglas de anomalia</b> revisan la lectura: si el flujo de agua es alto y sostenido, "
    "genera una alerta de \"posible fuga\".",
    "El <b>panel web</b> consulta la base y muestra las zonas, los medidores y las alertas, "
    "actualizandose cada 10 segundos.",
    "En paralelo: <b>Prometheus</b> vigila el hardware y <b>restic</b> respalda todo cada 30 minutos.",
]
story += [ListFlowable([ListItem(Paragraph(p, BODY), value=i+1) for i, p in enumerate(pasos)],
                       bulletType="1", leftIndent=14)]

story.append(PageBreak())

# ---------- 5 como se construyo ----------
story += [Paragraph("5. Como lo construimos (las 3 fases)", H1)]
fases = [
    [P("Fase", CELLB), P("Que se hizo", CELLB)],
    [P("1. IaaS", CELLB), P("Preparar la Raspberry Pi, instalar KVM, y crear las 3 maquinas "
        "virtuales con Debian, IPs fijas y comunicacion entre ellas. Todo desde archivos "
        "de texto (se puede destruir y recrear con un comando).")],
    [P("2. PaaS + SaaS", CELLB), P("Instalar el cluster de Kubernetes (K3s) sobre 2 de las VMs. "
        "Programar los 3 microservicios en Python, empaquetarlos como contenedores y "
        "desplegarlos. Publicar el panel para verlo desde la laptop.")],
    [P("3. Monitoreo + BaaS", CELLB), P("Instalar Prometheus para vigilar el hardware. "
        "Montar MinIO como almacen de respaldos. Configurar restic para respaldar "
        "automaticamente y verificar que las copias se restauran. Reglas de seguridad de red.")],
]
story += [tabla(fases, [3*cm, 12*cm]),
          Spacer(1, 2*mm),
          Paragraph("Todo el codigo, los scripts y la documentacion estan en GitHub "
                    "(45 versiones guardadas).", SMALL)]

# ---------- 6 resumen ----------
story += [Paragraph("6. Resumen del proyecto en 5 puntos", H1),
          Paragraph("Sintetizando, el proyecto se explica en <b>5 puntos</b>, uno por "
                    "cada capa del diagrama:", BODY)]
frases = [
    "<b>KVM</b> crea 3 maquinas virtuales sobre la Raspberry Pi. Eso es <b>IaaS</b>.",
    "<b>Kubernetes</b> une esas maquinas en una plataforma donde se despliegan los "
    "servicios sin administrar servidores. Eso es <b>PaaS</b>.",
    "Un <b>simulador</b> manda datos de medidores IoT por <b>MQTT</b>, el protocolo real "
    "de la ultima milla. Un microservicio en Python los recibe, los guarda y detecta "
    "anomalias.",
    "El operador municipal abre un <b>panel web</b> y ve las zonas y las alertas en vivo. "
    "Eso es <b>SaaS</b>.",
    "<b>restic</b> respalda todo a un almacenamiento <b>MinIO</b>, con una prueba que "
    "verifica la restauracion. Eso es <b>BaaS</b>. Y <b>Prometheus</b> vigila el hardware.",
]
story += [ListFlowable([ListItem(Paragraph(p, BODY), value=i+1) for i, p in enumerate(frases)],
                       bulletType="1", leftIndent=14)]
story += [Spacer(1, 3*mm),
          Table([[Paragraph("<b>En resumen:</b> \"Demostramos las 4 capas de servicio "
                            "de la nube -IaaS, PaaS, SaaS y BaaS- sobre una sola Raspberry Pi, "
                            "con el caso de uso real de un operador de telecomunicaciones: "
                            "conectividad IoT de ultima milla mas una plataforma de datos para "
                            "una ciudad inteligente.\"", BODY)]],
                colWidths=[15*cm],
                style=TableStyle([("BACKGROUND", (0,0), (-1,-1), AZULC),
                                  ("BOX", (0,0), (-1,-1), 1, AZUL),
                                  ("LEFTPADDING",(0,0),(-1,-1),10),
                                  ("RIGHTPADDING",(0,0),(-1,-1),10),
                                  ("TOPPADDING",(0,0),(-1,-1),8),
                                  ("BOTTOMPADDING",(0,0),(-1,-1),8)]))]

story.append(PageBreak())

# ---------- 7 herramientas ----------
story += [Paragraph("7. Herramientas principales (para el informe escrito)", H1)]
herr = [
    [P("Herramienta", CELLB), P("Para que", CELLB)],
    [P("Raspberry Pi OS (Debian)"), P("Sistema operativo de la Pi")],
    [P("KVM + libvirt"), P("Hipervisor: crea y gestiona las 3 maquinas virtuales")],
    [P("Debian (ARM64)"), P("Sistema operativo de las 3 VMs")],
    [P("Ansible"), P("Configura las VMs de forma automatica y repetible")],
    [P("K3s (Kubernetes)"), P("Orquestador de contenedores (PaaS)")],
    [P("Eclipse Mosquitto"), P("Servidor de mensajes MQTT")],
    [P("Python + FastAPI"), P("Los 3 microservicios propios y el panel")],
    [P("SQLite"), P("Base de datos de la telemetria y las alertas")],
    [P("Prometheus"), P("Monitoreo del hardware")],
    [P("MinIO + restic"), P("Servicio de respaldo (BaaS)")],
    [P("Git + GitHub"), P("Control de versiones del proyecto")],
]
story += [tabla(herr, [5*cm, 10*cm])]

# ---------- 8 rubrica ----------
story += [Paragraph("8. Cumplimiento de la rubrica", H1)]
rub = [
    [P("Lo que pide", CELLB), P("Como lo cumplimos", CELLB)],
    [P("Las VMs deben \"compilar\""), P("Se crean desde codigo en ~85 segundos con un comando")],
    [P("IPs estaticas en la red local"), P("192.168.100.11 / .12 / .13, fijas")],
    [P("Comunicacion bidireccional estable"), P("0% de perdida en las 6 direcciones, latencia < 1 ms")],
    [P("Los 4 tipos de servicio funcionales"), P("IaaS, PaaS, SaaS y BaaS, los 4 corriendo")],
    [P("Monitorizar el HW utilizado"), P("Prometheus mide CPU/RAM/disco/temperatura de las 4 maquinas")],
    [P("Acceso exitoso a los servicios"), P("El panel se abre desde la laptop; demo en vivo")],
    [P("Verificacion de los respaldos"), P("Prueba automatica que restaura y valida la base de datos")],
    [P("BaaS (puntos extra)"), P("MinIO + restic con respaldos programados y verificables")],
]
story += [tabla(rub, [6*cm, 9*cm])]

# ---------- build ----------
doc = BaseDocTemplate(OUT, pagesize=A4,
                      leftMargin=2*cm, rightMargin=2*cm,
                      topMargin=2*cm, bottomMargin=1.8*cm,
                      title="NubeUltima - Resumen del proyecto",
                      author="Grupo NubeUltima", creator="")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
doc.build([s for s in story if not (isinstance(s, Flowable) and type(s) is Flowable)])
print("OK ->", OUT)
