import os
import tempfile
from io import BytesIO
import base64

import streamlit as st
import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import qrcode

from shapely.geometry import shape
from folium.plugins import Draw
from streamlit_folium import st_folium

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER


# ============================================================
# PATHS
# ============================================================

LOGO_PATH = os.path.join("assets", "cinec engineering faculty logo.jpg")
BACKGROUND_PATH = os.path.join("assets", "OIP (1).webp")  # solar panel landscape background
SIDE_IMAGE_PATH = os.path.join("assets", "OIP.webp")          # secondary solar image

BUILDINGS_PATH = "Malabe_Buildings_Final.gpkg"
IRRADIANCE_PATH = os.path.join("data", "monthly_irradiance.csv")
APP_URL = "https://rooftop-solar-potential.streamlit.app/"


# ============================================================
# QR CODE
# ============================================================

def create_qr_code(url=APP_URL):
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    path = f.name
    f.close()

    qr = qrcode.QRCode(
        version=4,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=3
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(path)

    return path


# ============================================================
# PDF MAP IMAGE
# ============================================================

def create_selected_area_image(buildings_gdf, selected_buildings, user_polygon):

    f = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    path = f.name
    f.close()

    all_b = buildings_gdf.to_crs(epsg=32644)
    sel_b = selected_buildings.to_crs(epsg=32644)

    poly = gpd.GeoDataFrame(
        geometry=[user_polygon],
        crs="EPSG:4326"
    ).to_crs(epsg=32644)

    fig, ax = plt.subplots(figsize=(10, 7), facecolor="white")

    all_b.plot(
        ax=ax,
        facecolor="none",
        edgecolor="lightgray",
        linewidth=0.35,
        zorder=1
    )

    if not sel_b.empty:
        sel_b.plot(
            ax=ax,
            facecolor="blue",
            edgecolor="blue",
            alpha=0.70,
            linewidth=0.25,
            zorder=2
        )

    poly.plot(
        ax=ax,
        facecolor="none",
        edgecolor="red",
        linewidth=1.2,
        zorder=3
    )

    # Keep the complete building extent visible in the exported PDF map.
    if not all_b.empty:
        minx, miny, maxx, maxy = all_b.total_bounds
        pad_x = max((maxx - minx) * 0.03, 1)
        pad_y = max((maxy - miny) * 0.03, 1)
        ax.set_xlim(minx - pad_x, maxx + pad_x)
        ax.set_ylim(miny - pad_y, maxy + pad_y)

    ax.set_title(
        "Selected Area for Rooftop Solar Potential Estimation",
        fontweight="bold"
    )
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.grid(True, alpha=0.25)

    fig.tight_layout()
    fig.canvas.draw()
    fig.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
        facecolor="white"
    )
    plt.close(fig)

    return path

# ============================================================
# PDF GRAPH IMAGES
# ============================================================

def create_pdf_graphs(df):

    f1 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    energy_path = f1.name
    f1.close()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(df["Month"], df["Estimated Energy (kWh)"])
    ax.set_title("Monthly Solar Energy Generation", fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Energy (kWh)")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(energy_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    f2 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    irr_path = f2.name
    f2.close()

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(
        df["Month"],
        df["Solar Irradiance (kWh/m²/day)"]
    )
    ax.set_title("Monthly Solar Irradiance", fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Solar Irradiance (kWh/m²/day)")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", alpha=0.25)

    for bar, value in zip(
        bars,
        df["Solar Irradiance (kWh/m²/day)"]
    ):
        ax.text(
            bar.get_x() + bar.get_width()/2,
            bar.get_height(),
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=8
        )

    plt.tight_layout()
    plt.savefig(irr_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    return energy_path, irr_path


# ============================================================
# CLIENT REPORT HELPERS
# ============================================================

def add_client_report_sections(content, annual_energy, installed_capacity,
                               usable_roof_area, buildings_found,
                               actual_usage_kwh=None):

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.leading = 16

    heading = ParagraphStyle(
        "ClientHeading",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=17,
        textColor=colors.HexColor("#12355B")
    )

    content.append(PageBreak())
    content.append(Paragraph("Executive Summary", heading))
    content.append(Spacer(1, 15))

    avg_daily = annual_energy / 365

    content.append(Paragraph(
        f"This preliminary rooftop solar assessment evaluates "
        f"{buildings_found:,} buildings within the selected study area. "
        f"The assessment identifies approximately {usable_roof_area:,.2f} m² "
        f"of usable rooftop area and an estimated photovoltaic capacity of "
        f"{installed_capacity:,.2f} kW. The estimated annual electricity "
        f"generation is {annual_energy:,.0f} kWh, equivalent to approximately "
        f"{avg_daily:,.0f} kWh per day.",
        normal
    ))

    content.append(Spacer(1, 20))
    content.append(Paragraph(
        "Potential Energy Utilisation Scenarios",
        heading
    ))
    content.append(Spacer(1, 12))

    if actual_usage_kwh and actual_usage_kwh > 0:
        content.append(Paragraph(
            f"The customer-provided annual electricity consumption is "
            f"{actual_usage_kwh:,.0f} kWh/year.",
            normal
        ))
    else:
        content.append(Paragraph(
            "No actual electricity consumption data was provided. ",
            normal
        ))

    data = [["Direct Solar Use", "Potential Direct Use (kWh)", "Potential Surplus (kWh)"]]

    for s in [0.60, 0.70, 0.80]:
        direct = annual_energy * s
        surplus = annual_energy - direct
        data.append([
            f"{int(s*100)}%",
            f"{direct:,.0f}",
            f"{surplus:,.0f}"
        ])

    table = Table(data, colWidths=[150, 180, 185])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#12355B")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#AAB7C4")),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7)
    ]))

    content.append(Spacer(1, 12))
    content.append(table)


# ============================================================
# PDF REPORT
# ============================================================

def create_pdf_report(buildings_found, roof_area, usable_roof_area,
                      panel_name, panel_power, panel_area,
                      panel_efficiency, num_panels, installed_capacity,
                      annual_energy, monthly_df, graph_image,
                      selected_area_image, irradiance_graph,
                      qr_image, actual_usage_kwh=None):

    # PDF REPORT ONLY: web application UI/code below remains unchanged.
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=34, leftMargin=34,
                            topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    # Professional PDF-only visual system. Content and calculations remain unchanged.
    navy = colors.HexColor("#183B5B")
    slate = colors.HexColor("#334E68")
    accent = colors.HexColor("#2F6F9F")
    pale_blue = colors.HexColor("#EAF2F8")
    soft_fill = colors.HexColor("#F7F9FB")
    border = colors.HexColor("#C7D3DD")
    body_text = colors.HexColor("#374957")
    muted = colors.HexColor("#667785")

    title = ParagraphStyle("ReportTitle", parent=styles["Heading1"],
        fontName="Helvetica-Bold", fontSize=20, leading=25,
        textColor=navy, spaceAfter=7)
    subtitle = ParagraphStyle("ReportSubtitle", parent=styles["Normal"],
        fontSize=9.5, leading=13.5, textColor=muted, spaceAfter=11)
    heading = ParagraphStyle("SectionHeading", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=14.5, leading=19,
        textColor=navy, spaceBefore=15, spaceAfter=8)
    normal = ParagraphStyle("Body", parent=styles["Normal"],
        fontSize=9.4, leading=13.8, textColor=body_text)
    small = ParagraphStyle("Small", parent=normal, fontSize=8.1, leading=11.2,
        textColor=muted)
    metric_label = ParagraphStyle("MetricLabel", parent=normal, fontSize=7.7,
        leading=9.5, alignment=TA_CENTER, textColor=muted)
    metric_value = ParagraphStyle("MetricValue", parent=normal, fontName="Helvetica-Bold",
        fontSize=15.5, leading=19, alignment=TA_CENTER, textColor=navy)

    content=[]

    # CUSTOMER-FACING REPORT HEADER (no campus/logo/student cover page)
    content.append(Paragraph("Rooftop Solar Potential Assessment", title))
    content.append(Paragraph(
        "Preliminary solar photovoltaic assessment for the selected study area in Malabe, Sri Lanka.", subtitle))

    info=Table([["Assessment Type", "Rooftop Solar Potential Estimation"],
                ["Study Area", "Malabe, Sri Lanka"]], colWidths=[145,370])
    info.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,-1),pale_blue),
        ("BACKGROUND",(1,0),(1,-1),soft_fill),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),0.45,border),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    content.append(info)

    avg_daily=annual_energy/365 if annual_energy else 0

    # KEY RESULTS - shown once
    content.append(Paragraph("Key Results", heading))
    metric_data=[[Paragraph("BUILDINGS ANALYSED",metric_label),Paragraph("USABLE ROOF AREA",metric_label),Paragraph("SYSTEM SIZE",metric_label),Paragraph("ANNUAL GENERATION",metric_label)],
                 [Paragraph(f"{buildings_found:,}",metric_value),Paragraph(f"{usable_roof_area:,.0f} m²",metric_value),Paragraph(f"{installed_capacity:,.2f} kW",metric_value),Paragraph(f"{annual_energy:,.0f} kWh",metric_value)]]
    metrics=Table(metric_data,colWidths=[128.75]*4)
    metrics.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),soft_fill),
        ("BOX",(0,0),(-1,-1),0.7,border),
        ("INNERGRID",(0,0),(-1,-1),0.4,border),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9)]))
    content.append(metrics)

    # PV CONFIGURATION - compact, no duplicate results table
    content.append(Paragraph("Selected PV Configuration", heading))
    config=[["Selected Solar Panel",panel_name],
            ["Panel Power",f"{panel_power} W"],
            ["Panel Area",f"{panel_area:.2f} m²"],
            ["Panel Efficiency",f"{panel_efficiency*100:.1f}%"],
            ["Estimated Number of Panels",f"{num_panels:,}"],
            ["Total Roof Area Identified",f"{roof_area:,.2f} m²"]]
    cfg=Table(config,colWidths=[235,280])
    cfg.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,-1),pale_blue),
        ("BACKGROUND",(1,0),(1,-1),soft_fill),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),0.45,border),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8)]))
    content.append(cfg)

    # SELECTED AREA
    content.append(Paragraph("Selected Study Area", heading))
    content.append(Paragraph("The map below shows the selected boundary and the building footprints included in the rooftop solar potential calculation.", normal))
    content.append(Spacer(1,8))
    if selected_area_image and os.path.exists(selected_area_image):
        im=Image(selected_area_image,width=420,height=220); im.hAlign="CENTER"; content.append(im)
    content.append(Paragraph(f"Buildings included in the selected area: <b>{buildings_found:,}</b>", small))
    content.append(PageBreak())

    # MONTHLY GENERATION
    content.append(Paragraph("Monthly Solar Energy Generation", title))
    content.append(Paragraph("Estimated monthly energy output based on the selected PV configuration and average solar irradiance data.", subtitle))
    if graph_image and os.path.exists(graph_image):
        gi=Image(graph_image,width=420,height=200); gi.hAlign="CENTER"; content.append(gi)
    content.append(Spacer(1,14))

    rows=[["Month","Irradiance (kWh/m²/day)","Estimated Energy (kWh)"]]
    for _,row in monthly_df.iterrows():
        rows.append([str(row["Month"]),f'{row["Solar Irradiance (kWh/m²/day)"]:.3f}',f'{row["Estimated Energy (kWh)"]:,.2f}'])
    rows.append(["Annual Total","—",f"{annual_energy:,.2f}"])
    monthly=Table(rows,colWidths=[160,175,180],repeatRows=1)
    monthly.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),navy),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#EAF0F5")),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),0.4,border),
        ("ALIGN",(1,1),(-1,-1),"RIGHT"),("ROWBACKGROUNDS",(0,1),(-1,-2),[colors.white,soft_fill]),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]))
    content.append(monthly)

    # Start the remaining assessment content on page 3
    content.append(PageBreak())

    # ENERGY UTILISATION
    content.append(Paragraph("Energy Utilisation Assessment", heading))
    if actual_usage_kwh is not None and actual_usage_kwh>0:
        surplus=max(annual_energy-actual_usage_kwh,0); deficit=max(actual_usage_kwh-annual_energy,0)
        util=[["Customer Annual Consumption",f"{actual_usage_kwh:,.0f} kWh/year"],
              ["Estimated Annual PV Generation",f"{annual_energy:,.0f} kWh/year"],
              ["Potential Annual Surplus",f"{surplus:,.0f} kWh/year"],
              ["Remaining Grid Requirement",f"{deficit:,.0f} kWh/year"]]
        content.append(Paragraph("Customer-provided annual consumption is compared with the estimated annual PV generation. This is a preliminary annual comparison and does not replace interval load-profile analysis.",normal))
    else:
        util=[["Estimated Annual PV Generation",f"{annual_energy:,.0f} kWh/year"],
              ["Average Daily PV Generation",f"{avg_daily:,.0f} kWh/day"],
              ["Customer Consumption Data","Not provided"],
              ["Assessment Scope","Generation potential only"]]
        content.append(Paragraph("Actual customer electricity consumption data were not provided; therefore, this report presents generation potential rather than claiming a specific self-consumption or export percentage.",normal))
    content.append(Spacer(1,8))
    ut=Table(util,colWidths=[270,245])
    ut.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),pale_blue),("GRID",(0,0),(-1,-1),0.45,border),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),("LEFTPADDING",(0,0),(-1,-1),8)]))
    content.append(ut)

    # POTENTIAL SURPLUS-ENERGY UTILISATION OPTIONS
    content.append(Spacer(1,12))
    content.append(Paragraph("Potential Surplus-Energy Utilisation Options", title))
    options_data = [
        [Paragraph('<font color="white"><b>Option</b></font>', normal)],
        [Paragraph('<font color="white"><b>Potential Application</b></font>', normal)],
        [Paragraph("Battery Energy Storage (BESS)", normal), Paragraph("Store excess daytime PV generation for later use.", normal)],
        [Paragraph("EV Charging", normal), Paragraph("Use surplus generation to support electric-vehicle charging.", normal)],
        [Paragraph("Water Pumping", normal), Paragraph("Shift pumping loads toward periods of high solar generation.", normal)],
        [Paragraph("Grid Export", normal), Paragraph("Export excess generation subject to applicable grid rules.", normal)],
        [Paragraph("Pumped-Storage Hydropower (PSH)", normal), Paragraph("Potential larger-scale storage option where suitable water resources, elevation difference and infrastructure are available.", normal)]
    ]
    options=Table(options_data,colWidths=[170,345])
    options.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),slate),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),0.5,border),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("RIGHTPADDING",(0,0),(-1,-1),8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,soft_fill])
    ]))
    content.append(options)
    content.append(Spacer(1,7))
    content.append(Paragraph(
        "<b>Important:</b> These are potential applications only. Final selection should consider actual load profiles, "
        "grid capacity, storage requirements, site conditions, capital cost, operating requirements and applicable regulations.",
        normal))

    # ASSUMPTIONS + NEXT STEPS
    content.append(Paragraph("Assessment Basis and Recommendations", heading))
    assumptions=[
        "Usable rooftop area was estimated as 80% of the identified roof area.",
        "A performance ratio of 0.80 was applied in the energy estimation.",
        "Solar irradiance values are based on the long-term average dataset used by the application.",
        "Building selection is based on building footprints/centroids located within the user-defined polygon.",
        "Final PV design should include site inspection, shading analysis, roof structural assessment and electrical design verification."
    ]
    for a in assumptions: content.append(Paragraph("• "+a,normal)); content.append(Spacer(1,4))

    # QR
    if qr_image and os.path.exists(qr_image):
        content.append(Spacer(1,14))
        qr=Image(qr_image,width=82,height=82)
        qrt=Table([[qr,Paragraph("<b>Interactive Assessment Access</b><br/>Scan the QR code to access the Rooftop Solar Potential Estimation web application.",normal)]],colWidths=[100,415])
        qrt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),soft_fill),("BOX",(0,0),(-1,-1),0.45,border),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
        content.append(qrt)

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(border)
        canvas.setLineWidth(0.6)
        canvas.line(34,28,A4[0]-34,28)
        canvas.setFont("Helvetica",8)
        canvas.setFillColor(muted)
        canvas.drawString(34,16,"Rooftop Solar Potential Assessment")
        canvas.drawRightString(A4[0]-34,16,f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(content,onFirstPage=footer,onLaterPages=footer)
    pdf=buffer.getvalue(); buffer.close(); return pdf



# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Rooftop Solar Potential Estimation",
    page_icon="☀️",
    layout="wide"
)


# ============================================================
# BACKGROUND + PROFESSIONAL UI
# ============================================================

if os.path.exists(BACKGROUND_PATH):
    with open(BACKGROUND_PATH, "rb") as f:
        bg = base64.b64encode(f.read()).decode()

    background = f"""
    background:
        linear-gradient(rgba(3,12,22,0.70), rgba(3,12,22,0.88)),
        url("data:image/webp;base64,{bg}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    """
else:
    background = "background: linear-gradient(135deg,#07111d,#0b1d2d);"

st.markdown(f"""
<style>
.stApp {{
    {background}
    color:#F4F7FB;
}}
[data-testid="stHeader"] {{background:rgba(0,0,0,0);}}
.block-container {{max-width:1250px;padding-top:1.5rem;padding-bottom:2rem;}}
.hero {{
    background:rgba(5,16,28,.78);
    border:1px solid rgba(130,180,220,.30);
    border-radius:18px;padding:24px 28px;
    backdrop-filter:blur(10px);
    box-shadow:0 12px 35px rgba(0,0,0,.28);
}}
.hero-title {{font-size:2.35rem;font-weight:750;color:#F5F7FA;}}
.hero-sub {{font-size:1.05rem;color:#CDD6DF;margin-top:7px;}}
.qr-card {{
    text-align:center;padding:10px;border-radius:14px;
    background:rgba(2,8,15,.90);
    border:1px solid rgba(255,255,255,.18);color:#EAF0F5;
}}
.section-card {{
    background:rgba(5,17,29,.84);
    border:1px solid rgba(117,159,194,.32);
    border-radius:15px;padding:16px 20px;margin:10px 0;
    backdrop-filter:blur(9px);
}}
.section-title {{font-size:1.15rem;font-weight:700;color:#F1F5F9;}}
.section-desc {{font-size:.92rem;color:#B9C5D0;margin-top:5px;}}
.metric-card {{
    background:rgba(8,20,34,.92);
    border-radius:12px;padding:15px;
    border:1px solid rgba(106,158,207,.38);min-height:100px;
}}
.metric-label {{color:#BAC6D2;font-size:.84rem;}}
.metric-value {{color:#FFF;font-size:1.38rem;font-weight:750;margin-top:9px;}}
div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {{
    border-radius:10px;
    min-height:46px;
    font-weight:700;
}}

/* PDF DOWNLOAD BUTTON - same visible professional button treatment */
.st-key-download_pdf_btn button {{
    width:100% !important;
    min-height:56px !important;
    border-radius:12px !important;
    border:1px solid rgba(118,150,255,.65) !important;
    background:linear-gradient(135deg,#243B86 0%,#4A3AA8 100%) !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    opacity:1 !important;
    visibility:visible !important;
    font-size:1rem !important;
    font-weight:750 !important;
    box-shadow:0 8px 20px rgba(39,55,145,.30) !important;
    transition:all .2s ease !important;
}}
.st-key-download_pdf_btn button:hover {{
    background:linear-gradient(135deg,#304BA5 0%,#5A48C0 100%) !important;
    border-color:#9AA8FF !important;
    transform:translateY(-1px) !important;
    box-shadow:0 10px 24px rgba(60,72,170,.40) !important;
}}
.st-key-download_pdf_btn button p,
.st-key-download_pdf_btn button span,
.st-key-download_pdf_btn button svg {{
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    fill:currentColor !important;
    opacity:1 !important;
    visibility:visible !important;
}}

/* SELECTED PANEL SPECIFICATIONS - make existing metric labels and values readable */
div[data-testid="stMetric"] {{
    color:#EAF0F7 !important;
}}
div[data-testid="stMetric"] label,
div[data-testid="stMetric"] label *,
div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] *,
div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricLabel"] div {{
    color:#D7E5F3 !important;
    -webkit-text-fill-color:#D7E5F3 !important;
    opacity:1 !important;
}}
div[data-testid="stMetricValue"],
div[data-testid="stMetricValue"] *,
div[data-testid="stMetricValue"] p,
div[data-testid="stMetricValue"] div {{
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    opacity:1 !important;
    font-weight:750 !important;
}}

/* Requested visibility fix: Select Solar Panel label */
div[data-testid="stSelectbox"] > label,
div[data-testid="stSelectbox"] > label *,
div[data-testid="stSelectbox"] label p {{
    color:#D7E5F3 !important;
    -webkit-text-fill-color:#D7E5F3 !important;
    opacity:1 !important;
    font-weight:500 !important;
}}

/* ============================================================
   CLEAR RESULTS + CLEAR POLYGON BUTTONS
   Same prominent style as Calculate Solar Potential
   ============================================================ */
.st-key-calculate_solar_btn button,
.st-key-clear_results_btn button,
.st-key-clear_polygon_btn button {{
    width:100% !important;
    min-height:56px !important;
    border-radius:12px !important;
    border:1px solid rgba(118,150,255,.65) !important;
    background:linear-gradient(135deg,#243B86 0%,#4A3AA8 100%) !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    opacity:1 !important;
    visibility:visible !important;
    font-size:1rem !important;
    font-weight:750 !important;
    box-shadow:0 8px 20px rgba(39,55,145,.30) !important;
    transition:all .2s ease !important;
}}

.st-key-calculate_solar_btn button p,
.st-key-calculate_solar_btn button span,
.st-key-calculate_solar_btn button svg,
.st-key-clear_results_btn button p,
.st-key-clear_results_btn button span,
.st-key-clear_results_btn button svg,
.st-key-clear_polygon_btn button p,
.st-key-clear_polygon_btn button span,
.st-key-clear_polygon_btn button svg {{
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    fill:currentColor !important;
    opacity:1 !important;
    visibility:visible !important;
}}

.st-key-calculate_solar_btn button:hover,
.st-key-clear_results_btn button:hover,
.st-key-clear_polygon_btn button:hover {{
    background:linear-gradient(135deg,#304BA5 0%,#5A48C0 100%) !important;
    border-color:#9AA8FF !important;
    transform:translateY(-1px) !important;
    box-shadow:0 10px 24px rgba(60,72,180,.42) !important;
}}
.note-box {{
    background:rgba(6,19,32,.90);
    border:1px solid rgba(102,158,211,.35);
    border-radius:12px;padding:14px 18px;color:#D4DCE5;
}}

/* Monthly Solar Energy Generation table - matches application background */
.monthly-table-wrap {{
    width:100%;
    max-height:455px;
    overflow-y:auto;
    background:rgba(6,19,32,.92);
    border:1px solid rgba(102,158,211,.38);
    border-radius:12px;
    box-shadow:0 8px 22px rgba(0,0,0,.20);
}}
.monthly-energy-table {{
    width:100%;
    border-collapse:collapse;
    font-size:14px;
    color:#E8EEF5;
}}
.monthly-energy-table thead th {{
    position:sticky;
    top:0;
    z-index:1;
    background:linear-gradient(135deg,#1D3B5A 0%,#273E61 100%);
    color:#FFFFFF !important;
    padding:13px 16px;
    text-align:left;
    font-weight:700;
    border-bottom:1px solid rgba(125,170,210,.45);
}}
.monthly-energy-table td {{
    padding:11px 16px;
    color:#E8EEF5 !important;
    background:rgba(8,25,40,.82);
    border-bottom:1px solid rgba(120,150,180,.16);
}}
.monthly-energy-table tbody tr:nth-child(even) td {{
    background:rgba(13,34,52,.82);
}}
.monthly-energy-table tbody tr:hover td {{
    background:rgba(28,57,80,.90);
}}
.monthly-energy-table .total-row td {{
    background:rgba(34,64,88,.98) !important;
    color:#FFFFFF !important;
    font-weight:700;
    border-top:1px solid rgba(130,180,220,.45);
}}
.monthly-table-wrap::-webkit-scrollbar {{
    width:8px;
}}
.monthly-table-wrap::-webkit-scrollbar-thumb {{
    background:rgba(110,150,185,.55);
    border-radius:8px;
}}

/* Previous dataframe styling retained but no longer used by the monthly table */

div[data-testid="stDataFrame"] {{
    background:rgba(7,20,33,.92) !important;
    border:1px solid rgba(102,158,211,.35) !important;
    border-radius:10px !important;
    overflow:hidden !important;
}}
div[data-testid="stDataFrame"] * {{
    color:#E8EEF5 !important;
}}
div[data-testid="stDataFrame"] [role="gridcell"],
div[data-testid="stDataFrame"] [role="columnheader"] {{
    background:rgba(12,30,47,.96) !important;
    color:#F2F6FA !important;
    border-color:rgba(120,150,180,.22) !important;
}}
div[data-testid="stDataFrame"] [role="columnheader"] {{
    background:rgba(22,48,70,.98) !important;
    color:#FFFFFF !important;
    font-weight:700 !important;
}}

/* Customer Electricity Consumption text visibility */
div[data-testid="stRadio"] label,
div[data-testid="stRadio"] label p,
div[data-testid="stNumberInput"] label,
div[data-testid="stNumberInput"] label p {{
    color:#F1F5F9 !important;
    opacity:1 !important;
}}
div[data-testid="stRadio"] {{
    color:#F1F5F9 !important;
}}
div[data-testid="stNumberInput"] input {{
    color:#F8FAFC !important;
    background:rgba(7,20,33,.88) !important;
}}
</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATES
# ============================================================

if "map_key" not in st.session_state:
    st.session_state.map_key = 0

if "result_data" not in st.session_state:
    st.session_state.result_data = None


# ============================================================
# HERO + QR
# ============================================================

qr_image_path = create_qr_code()

h1, h2 = st.columns([5.5, 1.15], vertical_alignment="center")

with h1:
    st.markdown("""
    <div class="hero">
        <div class="hero-title">☀️ Rooftop Solar Potential Estimation</div>
        <div class="hero-sub">
            Satellite Image Analysis for Rooftop Solar Potential in Malabe
        </div>
    </div>
    """, unsafe_allow_html=True)

with h2:
    st.markdown('<div class="qr-card">Scan to open<br><b>Web App</b></div>',
                unsafe_allow_html=True)
    st.image(qr_image_path, width=145)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_buildings():
    return gpd.read_file(BUILDINGS_PATH)

@st.cache_data
def load_irradiance():
    return pd.read_csv(IRRADIANCE_PATH)

buildings = load_buildings()
irradiance_df = load_irradiance()

monthly_irradiance = dict(
    zip(irradiance_df["Month"], irradiance_df["Irradiance"])
)


# ============================================================
# PANEL DATABASE
# ============================================================

panel_database = {
    "LONGi Hi-MO X6 (550W)": {"power":550, "area":2.58, "efficiency":0.221},
    "Jinko Tiger Neo (580W)": {"power":580, "area":2.79, "efficiency":0.225},
    "Trina Vertex (600W)": {"power":600, "area":3.10, "efficiency":0.231}
}


# ============================================================
# 1. MAP
# ============================================================

st.markdown("""
<div class="section-card">
<div class="section-title">1. Select Area on Map</div>
<div class="section-desc">Draw a polygon on the map to select your study area.</div>
</div>
""", unsafe_allow_html=True)

m = folium.Map(location=[6.9061,79.9696], zoom_start=17)

Draw(
    export=True,
    draw_options={
        "polyline":False,
        "rectangle":True,
        "polygon":True,
        "circle":False,
        "circlemarker":False,
        "marker":False
    }
).add_to(m)

output = st_folium(
    m,
    width=None,
    height=520,
    key=f"map_{st.session_state.map_key}"
)


# ============================================================
# CLEAR POLYGON BUTTON - IMMEDIATELY BELOW MAP
# ============================================================

b1, b2, _, _ = st.columns([1.2,1.2,1,1])

with b1:
    clear_polygon = st.button("⬡ Clear Polygon", use_container_width=True, key="clear_polygon_btn")

if clear_polygon:
    st.session_state.map_key += 1
    st.session_state.result_data = None
    st.rerun()


# ============================================================
# 2. PANEL SELECTION
# ============================================================

left, right = st.columns([4.8,2], vertical_alignment="center")

with left:
    st.markdown("""
    <div class="section-card">
    <div class="section-title">2. Select Solar Panel</div>
    <div class="section-desc">Choose the solar panel you want to use for the estimation.</div>
    </div>
    """, unsafe_allow_html=True)

    panel_type = st.selectbox(
        "Select Solar Panel",
        list(panel_database.keys())
    )

with right:
    if os.path.exists(SIDE_IMAGE_PATH):
        st.image(SIDE_IMAGE_PATH, use_container_width=True)

panel_power = panel_database[panel_type]["power"]
panel_area = panel_database[panel_type]["area"]
panel_efficiency = panel_database[panel_type]["efficiency"]


# ============================================================
# 3. CUSTOMER CONSUMPTION
# ============================================================

left, right = st.columns([4.8,2], vertical_alignment="center")

with left:
    st.markdown("""
    <div class="section-card">
    <div class="section-title">3. Customer Electricity Consumption</div>
    <div class="section-desc">Provide annual electricity consumption information.</div>
    </div>
    """, unsafe_allow_html=True)

    usage_option = st.radio(
        "Does the customer have actual electricity consumption data?",
        ["No","Yes"],
        horizontal=True
    )

    actual_usage_kwh = None

    if usage_option == "Yes":
        actual_usage_kwh = st.number_input(
            "Enter Annual Electricity Consumption (kWh/year)",
            min_value=0.0,
            value=0.0,
            step=1000.0
        )
    else:
        st.info(
            "No actual consumption data provided. The existing 60%, 70% and "
            "80% planning scenarios will be used."
        )

with right:
    if os.path.exists(BACKGROUND_PATH):
        st.image(BACKGROUND_PATH, use_container_width=True)


# ============================================================
# 4. CALCULATE
# ============================================================

c1, c2 = st.columns([3,2], vertical_alignment="center")

with c1:
    st.markdown("""
    <div class="section-card">
    <div class="section-title">4. Calculate Solar Potential</div>
    <div class="section-desc">
    Click the button below to estimate the solar potential for the selected area.
    </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    calc_btn, clear_btn = st.columns(2)

    with calc_btn:
        calculate = st.button(
            "▣ Calculate Solar Potential",
            type="primary",
            use_container_width=True,
            key="calculate_solar_btn"
        )

    with clear_btn:
        clear_results = st.button(
            "🗑 Clear Results",
            use_container_width=True,
            key="clear_results_btn"
        )


if clear_results:
    st.session_state.result_data = None
    st.rerun()


# ============================================================
# CALCULATIONS
# ============================================================

if calculate:

    if output is None or output.get("last_active_drawing") is None:
        st.warning("Please draw a polygon on the map before calculating.")

    else:
        user_polygon = shape(
            output["last_active_drawing"]["geometry"]
        )

        selected_buildings = buildings[
            buildings.centroid.within(user_polygon)
        ]

        selected_buildings_projected = selected_buildings.to_crs(
            epsg=32644
        )

        roof_area = selected_buildings_projected.geometry.area.sum()
        usable_roof_area = roof_area * 0.80

        number_of_panels = int(
            usable_roof_area / panel_area
        )

        actual_panel_area = number_of_panels * panel_area

        installed_capacity = (
            number_of_panels * panel_power
        ) / 1000

        performance_ratio = 0.80

        month_days = {
            "January":31, "February":28, "March":31,
            "April":30, "May":31, "June":30,
            "July":31, "August":31, "September":30,
            "October":31, "November":30, "December":31
        }

        monthly_results = []
        annual_energy = 0

        for month, irradiance in monthly_irradiance.items():

            monthly_energy = (
                actual_panel_area
                * irradiance
                * panel_efficiency
                * performance_ratio
                * month_days[month]
            )

            annual_energy += monthly_energy

            monthly_results.append({
                "Month":month,
                "Solar Irradiance (kWh/m²/day)":round(irradiance,3),
                "Estimated Energy (kWh)":round(monthly_energy,2)
            })

        monthly_df = pd.DataFrame(monthly_results)

        selected_area_image = create_selected_area_image(
            buildings,
            selected_buildings,
            user_polygon
        )

        energy_graph, irradiance_graph = create_pdf_graphs(monthly_df)

        pdf_file = create_pdf_report(
            len(selected_buildings),
            roof_area,
            usable_roof_area,
            panel_type,
            panel_power,
            panel_area,
            panel_efficiency,
            number_of_panels,
            installed_capacity,
            annual_energy,
            monthly_df,
            energy_graph,
            selected_area_image,
            irradiance_graph,
            qr_image_path,
            actual_usage_kwh
        )

        st.session_state.result_data = {
            "buildings_found":len(selected_buildings),
            "roof_area":roof_area,
            "usable_roof_area":usable_roof_area,
            "number_of_panels":number_of_panels,
            "installed_capacity":installed_capacity,
            "annual_energy":annual_energy,
            "monthly_df":monthly_df,
            "pdf_file":pdf_file,
            "panel_power":panel_power,
            "panel_area":panel_area,
            "panel_efficiency":panel_efficiency
        }


# ============================================================
# RESULTS
# ============================================================

if st.session_state.result_data:

    d = st.session_state.result_data

    st.markdown("""
    <div class="section-card">
    <div class="section-title" style="font-size:1.45rem;">Results</div>
    <div class="section-desc">Estimated rooftop solar potential for the selected area.</div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(4)

    metric_data = [
        ("🏢 Total Buildings Found", f"{d['buildings_found']:,}"),
        ("⌂ Usable Roof Area", f"{d['usable_roof_area']:,.2f} m²"),
        ("⚡ Estimated System Size", f"{d['installed_capacity']:,.2f} kW"),
        ("☀ Annual Energy Generation", f"{d['annual_energy']:,.0f} kWh")
    ]

    for col, (label, value) in zip(cols, metric_data):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    table_col, chart_col = st.columns([1.05,1.55])

    with table_col:
        st.markdown("""
        <div class="section-card">
        <div class="section-title">Monthly Solar Energy Generation</div>
        </div>
        """, unsafe_allow_html=True)

        show_df = d["monthly_df"].copy()
        show_df.columns = ["Month","Irradiance (kWh/m²/day)","Energy (kWh)"]

        show_df["Irradiance (kWh/m²/day)"] = show_df[
            "Irradiance (kWh/m²/day)"
        ].map(lambda x:f"{x:.3f}")

        show_df["Energy (kWh)"] = show_df[
            "Energy (kWh)"
        ].map(lambda x:f"{x:,.2f}")

        total = pd.DataFrame([{
            "Month":"Total (Year)",
            "Irradiance (kWh/m²/day)":"—",
            "Energy (kWh)":f"{d['annual_energy']:,.2f}"
        }])

        show_df = pd.concat([show_df,total],ignore_index=True)

        # Custom themed table - matches the application dark background
        table_rows = []
        for _, row in show_df.iterrows():
            row_class = "total-row" if row["Month"] == "Total (Year)" else ""
            table_rows.append(
                f'<tr class="{row_class}">'
                f'<td>{row["Month"]}</td>'
                f'<td>{row["Irradiance (kWh/m²/day)"]}</td>'
                f'<td>{row["Energy (kWh)"]}</td>'
                f'</tr>'
            )

        table_html = (
            '<div class="monthly-table-wrap">'
            '<table class="monthly-energy-table">'
            '<thead><tr>'
            '<th>Month</th>'
            '<th>Irradiance (kWh/m²/day)</th>'
            '<th>Energy (kWh)</th>'
            '</tr></thead>'
            '<tbody>'
            + ''.join(table_rows) +
            '</tbody></table></div>'
        )

        st.markdown(table_html, unsafe_allow_html=True)

    with chart_col:
        st.markdown("""
        <div class="section-card">
        <div class="section-title">Monthly Solar Energy Generation Chart</div>
        </div>
        """, unsafe_allow_html=True)

        # Two-tone blue column styling (dark blue at the base, lighter blue toward the top)
        chart_df = d["monthly_df"].copy()
        months = chart_df["Month"].tolist()
        energy = chart_df["Estimated Energy (kWh)"].tolist()

        fig = go.Figure()

        # Small stacked layers create a smooth two-tone blue transition without changing any values.
        layers = 24
        bottom_rgb = (24, 88, 150)
        top_rgb = (86, 145, 220)

        for i in range(layers):
            t = i / (layers - 1)
            r = int(bottom_rgb[0] + (top_rgb[0] - bottom_rgb[0]) * t)
            g = int(bottom_rgb[1] + (top_rgb[1] - bottom_rgb[1]) * t)
            b = int(bottom_rgb[2] + (top_rgb[2] - bottom_rgb[2]) * t)

            fig.add_trace(go.Bar(
                x=months,
                y=[value / layers for value in energy],
                marker_color=f"rgb({r},{g},{b})",
                marker_line_width=0,
                hoverinfo="skip",
                showlegend=False
            ))

        fig.update_layout(
            barmode="stack",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(7,18,30,.70)",
            margin=dict(l=20,r=20,t=20,b=20),
            height=455,
            xaxis_title="",
            yaxis_title="Energy (kWh)",
            bargap=0.18,
            hovermode=False,
            xaxis=dict(
                tickfont=dict(color="#D7E5F3", size=13),
                title_font=dict(color="#EAF0F7")
            ),
            yaxis=dict(
                tickfont=dict(color="#D7E5F3", size=13),
                title_font=dict(color="#EAF0F7")
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar":False}
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
    <div class="section-card">
    <div class="section-title">Selected Panel Specifications</div>
    </div>
    """, unsafe_allow_html=True)

    p1,p2,p3 = st.columns(3)
    p1.metric("Panel Power",f"{d['panel_power']} W")
    p2.metric("Panel Area",f"{d['panel_area']:.2f} m²")
    p3.metric("Panel Efficiency",f"{d['panel_efficiency']*100:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    note, download = st.columns([2.1,1])

    with note:
        st.markdown("""
        <div class="note-box">
        <b>ⓘ Note:</b> This is a preliminary assessment based on satellite data
        and average solar irradiance. A detailed site assessment is recommended
        for accurate final system design.
        </div>
        """, unsafe_allow_html=True)

    with download:
        st.download_button(
            "📄 Download Detailed Report (PDF)",
            data=d["pdf_file"],
            file_name="Solar_Potential_Report.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="download_pdf_btn"
        )
