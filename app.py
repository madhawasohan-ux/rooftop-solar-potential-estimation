import os
import tempfile
from io import BytesIO

import streamlit as st
import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from shapely.geometry import shape, Polygon
from folium.plugins import Draw
from streamlit_folium import st_folium


# ============================================================
# PATHS
# ============================================================

LOGO_PATH = os.path.join(
    "assets",
    "cinec engineering faculty logo.jpg"
)

BUILDINGS_PATH = "Malabe_Buildings_Final.gpkg"
IRRADIANCE_PATH = os.path.join(
    "data",
    "monthly_irradiance.csv"
)


# ============================================================
# CREATE SELECTED AREA MAP IMAGE
# ============================================================

def create_selected_area_image(
    buildings_gdf,
    selected_buildings,
    user_polygon
):

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".png"
    )

    map_image_path = temp_file.name
    temp_file.close()

    # Convert buildings to projected CRS
    buildings_projected = buildings_gdf.to_crs(
        epsg=32644
    )

    selected_projected = selected_buildings.to_crs(
        epsg=32644
    )

    # Polygon from GeoJSON is WGS84
    polygon_gdf = gpd.GeoDataFrame(
        geometry=[user_polygon],
        crs="EPSG:4326"
    )

    polygon_projected = polygon_gdf.to_crs(
        epsg=32644
    )

    fig, ax = plt.subplots(
        figsize=(10, 7)
    )

    # Background buildings
    buildings_projected.plot(
        ax=ax,
        facecolor="none",
        edgecolor="lightgray",
        linewidth=0.4
    )

    # Selected buildings
    if not selected_projected.empty:
        selected_projected.plot(
            ax=ax,
            facecolor="none",
            edgecolor="blue",
            linewidth=0.4
        )

    # Selected polygon
    polygon_projected.plot(
        ax=ax,
        facecolor="none",
        edgecolor="red",
        linewidth=0.8
    )

    ax.set_title(
        "Selected Area for Rooftop Solar Potential Estimation",
        fontsize=14,
        fontweight="bold"
    )

    ax.set_xlabel(
        "Easting (m)"
    )

    ax.set_ylabel(
        "Northing (m)"
    )

    ax.grid(
        True,
        alpha=0.25
    )

    plt.tight_layout()

    plt.savefig(
        map_image_path,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close(fig)

    return map_image_path



# ============================================================
# CLIENT REPORT HELPERS
# ============================================================

def create_client_energy_utilisation_data(annual_energy):
    """
    Planning scenarios only.
    These are NOT actual measured building consumption values.
    """
    scenarios = [0.60, 0.70, 0.80]

    rows = []

    for share in scenarios:
        direct_use = annual_energy * share
        surplus = annual_energy - direct_use

        rows.append([
            f"{int(share * 100)}%",
            f"{direct_use:,.0f}",
            f"{surplus:,.0f}"
        ])

    return rows


def add_client_report_sections(
    content,
    annual_energy,
    installed_capacity,
    usable_roof_area,
    buildings_found,
    monthly_df,
    actual_usage_kwh=None
):
    """Add client-focused interpretation without changing existing calculations."""

    styles_local = getSampleStyleSheet()

    normal = styles_local["Normal"]
    normal.leading = normal.fontSize * 1.5

    client_heading = ParagraphStyle(
        "ClientHeading",
        parent=styles_local["Heading1"],
        alignment=TA_CENTER,
        fontSize=17,
        leading=21
    )

    # ========================================================
    # EXECUTIVE SUMMARY
    # ========================================================
    content.append(Spacer(1, 40))
    content.append(
        Paragraph(
            "Executive Summary",
            client_heading
        )
    )

    content.append(Spacer(1, 15))

    average_daily = annual_energy / 365

    executive_text = (
        f"This preliminary rooftop solar assessment evaluates "
        f"{buildings_found:,} buildings within the selected study area. "
        f"The assessment identifies approximately "
        f"{usable_roof_area:,.2f} m² of usable rooftop area and an "
        f"estimated photovoltaic capacity of {installed_capacity:,.2f} kW. "
        f"The estimated annual solar electricity generation is "
        f"{annual_energy:,.0f} kWh/year, equivalent to an average "
        f"daily generation of approximately {average_daily:,.0f} kWh/day. "
        f"The results are intended to support preliminary planning, "
        f"design and energy-management decisions."
    )

    content.append(Paragraph(executive_text, normal))

    # ========================================================
    # ENERGY UTILISATION & SURPLUS
    # ========================================================
    content.append(Spacer(1, 40))
    content.append(
        Paragraph(
            "Energy Utilisation & Surplus Energy Assessment",
            client_heading
        )
    )

    content.append(Spacer(1, 30))

    if actual_usage_kwh is not None:

        content.append(
            Paragraph(
                "Customer-provided annual electricity consumption data "
                "are available for the selected study area. The reported "
                "consumption is compared directly with the estimated annual "
                "PV generation to determine the potential annual surplus "
                "or remaining energy requirement.",
                normal
            )
        )

        content.append(Spacer(1, 12))

        potential_surplus = max(
            annual_energy - actual_usage_kwh,
            0
        )

        residual_energy_requirement = max(
            actual_usage_kwh - annual_energy,
            0
        )

        scenario_data = [
            [
                "Energy Item",
                "Value (kWh/year)",
                "Basis"
            ],
            [
                "Customer Annual Consumption",
                f"{actual_usage_kwh:,.0f}",
                "Customer-provided actual value"
            ],
            [
                "Estimated Annual PV Generation",
                f"{annual_energy:,.0f}",
                "Solar assessment result"
            ],
            [
                "Potential Annual PV Surplus",
                f"{potential_surplus:,.0f}",
                "PV generation above reported consumption"
            ],
            [
                "Residual Energy Requirement",
                f"{residual_energy_requirement:,.0f}",
                "Consumption above PV generation"
            ]
        ]

        scenario_table = Table(
            scenario_data,
            colWidths=[180, 125, 210]
        )

    else:

        content.append(
            Paragraph(
                "Actual building electricity consumption data were not "
                "provided for this assessment. Therefore, the following "
                "values are planning scenarios and must not be interpreted "
                "as measured building demand.",
                normal
            )
        )
        content.append(Spacer(1, 30))

        scenario_data = [
            [
                "Self-consumption",
                "Potential Direct Building Use (kWh/year)",
                "Potential Surplus (kWh/year)"
            ]
        ]

        scenario_data.extend(
            create_client_energy_utilisation_data(annual_energy)
        )

        scenario_table = Table(
            scenario_data,
            colWidths=[120, 205, 190]
        )

    scenario_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)
        ])
    )

    content.append(scenario_table)
    content.append(Spacer(1, 30))

    content.append(
        Paragraph(
            "Potential applications for surplus solar electricity include "
            "battery energy storage systems (BESS), electric-vehicle "
            "charging, water pumping, grid export and, where technically "
            "and geographically feasible, larger-scale energy-storage "
            "systems such as pumped-storage hydropower (PSH). "
            "Each option requires a separate technical and economic "
            "feasibility assessment.",
            normal
        )
    )

    content.append(PageBreak())

    # ========================================================
    # KEY FINDINGS
    # ========================================================

    content.append(
        Paragraph(
            "Key Findings",
            client_heading
        )
    )

    content.append(Spacer(1, 15))

    highest = monthly_df.loc[
        monthly_df["Estimated Energy (kWh)"].idxmax()
    ]

    lowest = monthly_df.loc[
        monthly_df["Estimated Energy (kWh)"].idxmin()
    ]

    findings = [
        f"• Estimated annual PV generation: <b>{annual_energy:,.0f} kWh/year</b>.",
        f"• Average estimated daily generation: <b>{average_daily:,.0f} kWh/day</b>.",
        f"• Highest estimated monthly generation: <b>{highest['Month']}</b> "
        f"({highest['Estimated Energy (kWh)']:,.0f} kWh).",
        f"• Lowest estimated monthly generation: <b>{lowest['Month']}</b> "
        f"({lowest['Estimated Energy (kWh)']:,.0f} kWh).",
        f"• Estimated PV capacity: <b>{installed_capacity:,.2f} kW</b>.",
        f"• Buildings assessed: <b>{buildings_found:,}</b>.",
        f"• Usable rooftop area: <b>{usable_roof_area:,.2f} m²</b>."
    ]

    for finding in findings:
        content.append(Paragraph(finding, normal))
        content.append(Spacer(1, 7))

    # ========================================================
    # SURPLUS ENERGY OPTIONS
    # ========================================================
    content.append(Spacer(1, 40))
    content.append(
        Paragraph(
            "Potential Surplus-Energy Utilisation Options",
            client_heading
        )
    )

    content.append(Spacer(1, 15))

    options = [
        ["Option", "Potential Application"],
        [
            "Battery Energy Storage (BESS)",
            "Store excess daytime PV generation for later use."
        ],
        [
            "EV Charging",
            "Use surplus generation to support electric-vehicle charging."
        ],
        [
            "Water Pumping",
            "Shift pumping loads toward periods of high solar generation."
        ],
        [
            "Grid Export",
            "Export excess generation subject to applicable grid rules."
        ],
        [
            "Pumped-Storage Hydropower (PSH)",
            "Potential larger-scale storage option where suitable "
            "water resources, elevation difference and infrastructure "
            "are available."
        ]
    ]

    header_style = ParagraphStyle(
        "TableHeader",
        parent=styles_local["Normal"],
        fontName="Helvetica-Bold",
        textColor=colors.white
    )

    option_table = Table(
         [
            [
                Paragraph(str(options[0][0]), header_style),
                Paragraph(str(options[0][1]), header_style)
            ]
        ]
        +
        [
            [
                Paragraph(str(row[0]), styles_local["Normal"]),
                Paragraph(str(row[1]), styles_local["Normal"])
            ]
            for row in options[1:]
        ],
        colWidths=[190, 325]
    )

    option_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
        ])
    )

    content.append(option_table)

    content.append(Spacer(1, 15))

    content.append(
        Paragraph(
            "<b>Important:</b> These are potential applications only. "
            "Final selection should consider actual load profiles, "
            "grid capacity, storage requirements, site conditions, "
            "capital cost, operating requirements and applicable regulations.",
            normal
        )
    )

    content.append(PageBreak())
# ============================================================
# CREATE PDF REPORT
# ============================================================

def create_pdf_report(
    buildings_found,
    roof_area,
    usable_roof_area,
    panel_name,
    panel_power,
    panel_area,
    panel_efficiency,
    num_panels,
    installed_capacity,
    annual_energy,
    monthly_df,
    graph_image,
    selected_area_image,
    actual_usage_kwh=None
):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    center_title = ParagraphStyle(
        "CenterTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        leading=25
    )

    center_heading = ParagraphStyle(
        "CenterHeading",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=15,
        leading=20
    )

    normal = styles["Normal"]

    content = []

    # ========================================================
    # COVER PAGE
    # ========================================================

    if os.path.exists(LOGO_PATH):

        content.append(
            Image(
                LOGO_PATH,
                width=260,
                height=260
            )
        )

        # Center image using table
        logo_table = Table(
            [[Image(
                LOGO_PATH,
                width=260,
                height=260
            )]],
            colWidths=[515]
        )

        logo_table.setStyle(
            TableStyle([
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                )
            ])
        )

        # Remove the image already added
        content.pop()

        content.append(
            logo_table
        )

    else:

        content.append(
            Paragraph(
                "CINEC Campus",
                center_title
            )
        )

    content.append(
        Spacer(1, 25)
    )

    content.append(
        Paragraph(
            "CINEC Campus",
            center_heading
        )
    )

    content.append(
        Spacer(1, 15)
    )

    content.append(
        Paragraph(
            "BSc (Hons) Mechatronics Engineering",
            center_heading
        )
    )

    content.append(
        Spacer(1, 30)
    )

    content.append(
        Paragraph(
            "Rooftop Solar Potential Estimation Using Satellite Image Analysis",
            center_title
        )
    )

    content.append(
        Spacer(1, 210)
    )

    cover_details = [
        ["Student", "Sohan Madhawa"],
        ["Study Area", "Malabe, Sri Lanka"],
        ["Year", "2026"]
    ]

    cover_table = Table(
        cover_details,
        colWidths=[150, 300]
    )

    cover_table.setStyle(
        TableStyle([
            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),
            (
                "FONTNAME",
                (1, 0),
                (1, -1),
                "Helvetica"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )

    content.append(
        cover_table
    )

    content.append(
        PageBreak()
    )


    # ========================================================
    # REPORT SUMMARY
    # ========================================================

    content.append(

        Paragraph(
            "Rooftop Solar Potential Estimation Report",
            center_title
        )
    )

    content.append(
        Spacer(1, 20)
    )

    summary_data = [
        ["Parameter", "Value"],

        [
            "Buildings Found",
            f"{buildings_found}"
        ],

        [
            "Roof Area (m²)",
            f"{roof_area:,.2f}"
        ],

        [
            "Usable Roof Area (m²)",
            f"{usable_roof_area:,.2f}"
        ],

        [
            "Selected Panel",
            panel_name
        ],

        [
            "Panel Power (W)",
            f"{panel_power}"
        ],

        [
            "Panel Area (m²)",
            f"{panel_area:.2f}"
        ],

        [
            "Panel Efficiency",
            f"{panel_efficiency * 100:.1f}%"
        ],

        [
            "Number of Panels",
            f"{num_panels:,}"
        ],

        [
            "Installed Capacity (kW)",
            f"{installed_capacity:,.2f}"
        ],

        [
            "Estimated Annual Energy (kWh/year)",
            f"{annual_energy:,.2f}"
        ]
    ]

    summary_table = Table(
        summary_data,
        colWidths=[260, 245]
    )

    summary_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#1F4E78")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "FONTNAME",
                (0, 1),
                (0, -1),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                3
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                3
            )
        ])
    )

    content.append(
        summary_table
    )

    

    # ========================================================
    # SELECTED AREA MAP
    # ========================================================
    content.append(
            Spacer(1, 60)
        )
    content.append(
        Paragraph(
            "Selected Study Area",
            center_title
        )
    )

    content.append(
        Spacer(1, 15)
    )

    content.append(
        Paragraph(
            "The following map shows the selected area used for the rooftop "
            "solar potential calculation. The selected boundary is shown "
            "together with the building footprints considered in the analysis.",
            normal
        )
    )

    content.append(
        Spacer(1, 15)
    )

    content.append(
        Image(
            selected_area_image,
            width=450,
            height=300
        )
    )

    content.append(
        Spacer(1, 10)
    )

    content.append(
        Paragraph(
            f"<b>Buildings included in selected area:</b> "
            f"{buildings_found}",
            normal
        )
    )

    content.append(
        PageBreak()
    )


    # ========================================================
    # MONTHLY TABLE
    # ========================================================

    content.append(
        Paragraph(
            "Monthly Solar Energy Generation",
            center_title
        )
    )

    content.append(
        Spacer(1, 20)
    )

    table_data = [
        [
            "Month",
            "Irradiance\n(kWh/m²/day)",
            "Energy\n(kWh)"
        ]
    ]

    for _, row in monthly_df.iterrows():

        table_data.append([
            str(row["Month"]),

            f"{row['Solar Irradiance (kWh/m²/day)']:.3f}",

            f"{row['Estimated Energy (kWh)']:,.2f}"
        ])

    monthly_table = Table(
        table_data,
        colWidths=[160, 170, 185]
    )

    monthly_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#1F4E78")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "ALIGN",
                (1, 1),
                (-1, -1),
                "RIGHT"
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                3
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                3
            )
        ])
    )

    content.append(
        monthly_table
    )

    content.append(
            Spacer(1, 40)
        )
   

    # ========================================================
    # GRAPH
    # ========================================================

    content.append(
        Paragraph(
            "Monthly Solar Energy Generation Graph",
            center_title
        )
    )

    content.append(
        Spacer(1, 20)
    )

    content.append(
        Image(
            graph_image,
            width=500,
            height=290
        )
    )

    content.append(
        PageBreak()
    )


    # ========================================================
    # ASSUMPTIONS
    # ========================================================

    content.append(
        Paragraph(
            "Assumptions",
            center_title
        )
    )

    content.append(
        Spacer(1, 20)
    )

    assumptions = [

        "• Usable Roof Area = 80% of total roof area",

        "• Performance Ratio = 80%",

        "• Solar Irradiance Data Source = NASA POWER",

        "• PV Module Specifications obtained from manufacturer datasheets",

        "• Building selection is based on building centroids falling within "
        "the user-defined polygon."
    ]

    for assumption in assumptions:

        content.append(
            Paragraph(
                assumption,
                normal
            )
        )

        content.append(
            Spacer(1, 8)
        )


    # ========================================================
    # CLIENT-FOCUSED REPORT SECTIONS
    # ========================================================

    add_client_report_sections(
        content=content,
        annual_energy=annual_energy,
        installed_capacity=installed_capacity,
        usable_roof_area=usable_roof_area,
        buildings_found=buildings_found,
        monthly_df=monthly_df,
        actual_usage_kwh=actual_usage_kwh
    )

    content.append(
        Paragraph(
            "Monthly Solar Irradiance",
            center_title
        )
    )

    content.append(Spacer(1, 20))

    content.append(
        Image(
            irradiance_graph_path,
            width=500,
            height=290
        )
    )

    content.append(PageBreak())


    # ========================================================
    # BUILD PDF
    # ========================================================

    doc.build(
        content
    )

    pdf = buffer.getvalue()

    buffer.close()

    return pdf


# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Rooftop Solar Potential Estimation",
    layout="wide"
)

st.title(
    "🏠 Rooftop Solar Potential Estimation"
)


# ============================================================
# SESSION STATES
# ============================================================

if "map_key" not in st.session_state:

    st.session_state.map_key = 0


# ============================================================
# PANEL DATABASE
# ============================================================

panel_database = {

    "LONGi Hi-MO X6 (550W)": {

        "power": 550,
        "area": 2.58,
        "efficiency": 0.221

    },

    "Jinko Tiger Neo (580W)": {

        "power": 580,
        "area": 2.79,
        "efficiency": 0.225

    },

    "Trina Vertex (600W)": {

        "power": 600,
        "area": 3.10,
        "efficiency": 0.231

    }

}


# ============================================================
# LOAD BUILDINGS
# ============================================================

buildings = gpd.read_file(
    BUILDINGS_PATH
)


# ============================================================
# LOAD IRRADIANCE DATA
# ============================================================

irradiance_df = pd.read_csv(
    IRRADIANCE_PATH
)

monthly_irradiance = dict(
    zip(
        irradiance_df["Month"],
        irradiance_df["Irradiance"]
    )
)


# ============================================================
# PANEL SELECTION
# ============================================================

st.subheader(
    "🔋 Solar Panel Selection"
)

panel_type = st.selectbox(

    "Select Solar Panel",

    list(panel_database.keys())

)

panel_power = panel_database[panel_type]["power"]

panel_area = panel_database[panel_type]["area"]

panel_efficiency = panel_database[panel_type]["efficiency"]


# ============================================================
# CUSTOMER ELECTRICITY CONSUMPTION
# ============================================================

st.subheader(
    "🏢 Customer Electricity Consumption"
)

usage_option = st.radio(
    "Does the customer have actual electricity consumption data?",
    ["No", "Yes"],
    horizontal=True
)

actual_usage_kwh = None

if usage_option == "Yes":

    actual_usage_kwh = st.number_input(
        "Enter Annual Electricity Consumption (kWh/year)",
        min_value=0.0,
        step=1000.0,
        value=0.0
    )

else:

    st.info(
        "No actual consumption data provided. "
        "The existing 60%, 70% and 80% planning scenarios "
        "will be used."
    )


# ============================================================
# BUTTONS
# ============================================================

c1, c2, c3 = st.columns(3)

with c1:

    calculate = st.button(
        "🔄 Calculate Solar Potential"
    )

with c2:

    clear_results = st.button(
        "🗑 Clear Results"
    )

with c3:

    clear_polygon = st.button(
        "🗺 Clear Polygon"
    )


if clear_polygon:

    st.session_state.map_key += 1

    st.rerun()


if clear_results:

    st.rerun()


# ============================================================
# CREATE MAP
# ============================================================

m = folium.Map(

    location=[
        6.9061,
        79.9696
    ],

    zoom_start=17

)


Draw(

    export=True,

    draw_options={

        "polyline": False,

        "rectangle": True,

        "polygon": True,

        "circle": False,

        "circlemarker": False,

        "marker": False

    }

).add_to(m)


output = st_folium(

    m,

    width=1500,

    height=550,

    key=f"map_{st.session_state.map_key}"

)


# ============================================================
# CALCULATIONS
# ============================================================

if (
    output["last_active_drawing"] is not None
    and calculate
):

    # --------------------------------------------------------
    # GET USER POLYGON
    # --------------------------------------------------------

    user_polygon = shape(
        output["last_active_drawing"]["geometry"]
    )


    # --------------------------------------------------------
    # SELECT BUILDINGS
    # --------------------------------------------------------

    selected_buildings = buildings[
        buildings.centroid.within(
            user_polygon
        )
    ]


    # --------------------------------------------------------
    # PROJECT BUILDINGS
    # --------------------------------------------------------

    selected_buildings_projected = (
        selected_buildings.to_crs(
            epsg=32644
        )
    )


    # --------------------------------------------------------
    # ROOF AREA
    # --------------------------------------------------------

    roof_area = (
        selected_buildings_projected.geometry.area.sum()
    )


    # --------------------------------------------------------
    # USABLE ROOF AREA
    # --------------------------------------------------------

    usable_roof_area = (
        roof_area * 0.80
    )


    # --------------------------------------------------------
    # NUMBER OF PANELS
    # --------------------------------------------------------

    number_of_panels = int(
        usable_roof_area /
        panel_area
    )


    # Actual area occupied by calculated panels
    actual_panel_area = (
           number_of_panels * panel_area
       )
   

    # --------------------------------------------------------
    # INSTALLED CAPACITY
    # --------------------------------------------------------

    installed_capacity = (

        number_of_panels *
        panel_power

    ) / 1000


    # --------------------------------------------------------
    # PERFORMANCE RATIO
    # --------------------------------------------------------

    performance_ratio = 0.80


    # --------------------------------------------------------
    # DAYS PER MONTH
    # --------------------------------------------------------

    month_days = {

        "January": 31,
        "February": 28,
        "March": 31,
        "April": 30,
        "May": 31,
        "June": 30,
        "July": 31,
        "August": 31,
        "September": 30,
        "October": 31,
        "November": 30,
        "December": 31

    }


    # --------------------------------------------------------
    # MONTHLY CALCULATION
    # --------------------------------------------------------

    monthly_results = []

    annual_energy = 0


    for month, irradiance in monthly_irradiance.items():

        days = month_days[month]

        monthly_energy = (

            actual_panel_area
            *
            irradiance
            *
            panel_efficiency
            *
            performance_ratio
            *
            days

        )

        annual_energy += monthly_energy


        monthly_results.append({

            "Month": month,

            "Solar Irradiance (kWh/m²/day)": round(
                irradiance,
                3
            ),

            "Estimated Energy (kWh)": round(
                monthly_energy,
                2
            )

        })


    monthly_df = pd.DataFrame(
        monthly_results
    )


    # ========================================================
    # SELECTED AREA MAP IMAGE
    # ========================================================

    selected_area_image_path = (
        create_selected_area_image(
            buildings,
            selected_buildings,
            user_polygon
        )
    )


    # ========================================================
    # RESULTS
    # ========================================================

    st.subheader(
        "📊 Results"
    )


    r1, r2, r3, r4, r5 = st.columns(5)


    r1.metric(
        "Buildings Found",
        len(selected_buildings)
    )


    r2.metric(
        "Roof Area (m²)",
        round(
            roof_area,
            2
        )
    )


    r3.metric(
        "Usable Roof Area (m²)",
        round(
            usable_roof_area,
            2
        )
    )


    r4.metric(
        "Number of Panels",
        number_of_panels
    )


    r5.metric(
        "Installed Capacity (kW)",
        round(
            installed_capacity,
            2
        )
    )


    st.success(
        f"Selected Panel : {panel_type}"
    )


    # ========================================================
    # PANEL SPECIFICATIONS
    # ========================================================

    st.subheader(
        "🔍 Selected Panel Specifications"
    )


    p1, p2, p3 = st.columns(3)


    p1.metric(
        "Panel Power (W)",
        panel_power
    )


    p2.metric(
        "Panel Area (m²)",
        panel_area
    )


    p3.metric(
        "Panel Efficiency",
        f"{panel_efficiency * 100:.1f}%"
    )


    # ========================================================
    # ANNUAL ENERGY
    # ========================================================

    st.subheader(
        "⚡ Annual Energy Generation"
    )


    st.metric(

        "Estimated Annual Energy",

        f"{annual_energy:,.0f} kWh/year"

    )


    # ========================================================
    # MONTHLY TABLE
    # ========================================================

    st.subheader(
        "📅 Monthly Solar Energy Generation"
    )


    st.dataframe(

        monthly_df,

        use_container_width=True,

        hide_index=True,

        height=500

    )


       # ========================================================
    # MONTHLY GRAPH
    # ========================================================

    fig = px.line(
        monthly_df,
        x="Month",
        y="Estimated Energy (kWh)",
        markers=True,
        title="Monthly Solar Energy Generation"
    )

    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Energy (kWh)",
        template="plotly_white"
    )

    # Show graph on Streamlit
    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ========================================================
    # SAVE MONTHLY ENERGY GRAPH FOR PDF
    # Using Matplotlib instead of Kaleido
    # ========================================================

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".png"
    ) as tmp:

        graph_path = tmp.name

    plt.figure(figsize=(12, 7))

    plt.plot(
        monthly_df["Month"],
        monthly_df["Estimated Energy (kWh)"],
        marker="o"
    )

    plt.title(
        "Monthly Solar Energy Generation",
        fontsize=18,
        fontweight="bold"
    )

    plt.xlabel(
        "Month",
        fontsize=13
    )

    plt.ylabel(
        "Energy (kWh)",
        fontsize=13
    )

    plt.xticks(
        rotation=45
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        graph_path,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()


    # ========================================================
    # MONTHLY SOLAR IRRADIANCE GRAPH
    # ========================================================

    irradiance_fig = px.bar(
        monthly_df,
        x="Month",
        y="Solar Irradiance (kWh/m²/day)",
        title="Monthly Solar Irradiance",
        text="Solar Irradiance (kWh/m²/day)"
    )

    irradiance_fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside"
    )

    irradiance_fig.update_layout(
        template="plotly_white",
        xaxis_title="Month",
        yaxis_title="Solar Irradiance (kWh/m²/day)"
    )

    # Show irradiance graph on Streamlit
    st.plotly_chart(
        irradiance_fig,
        use_container_width=True
    )


    # ========================================================
    # SAVE IRRADIANCE GRAPH FOR PDF
    # Using Matplotlib instead of Kaleido
    # ========================================================

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".png"
    ) as irradiance_tmp:

        irradiance_graph_path = irradiance_tmp.name

    plt.figure(figsize=(12, 7))

    bars = plt.bar(
        monthly_df["Month"],
        monthly_df["Solar Irradiance (kWh/m²/day)"]
    )

    plt.title(
        "Monthly Solar Irradiance",
        fontsize=18,
        fontweight="bold"
    )

    plt.xlabel(
        "Month",
        fontsize=13
    )

    plt.ylabel(
        "Solar Irradiance (kWh/m²/day)",
        fontsize=13
    )

    plt.xticks(
        rotation=45
    )

    plt.grid(
        axis="y",
        alpha=0.3
    )

    # Add irradiance values above bars
    for bar in bars:

        height = bar.get_height()

        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{height:.2f}",
            ha="center",
            va="bottom",
            fontsize=9
        )

    plt.tight_layout()

    plt.savefig(
        irradiance_graph_path,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()


    # ========================================================
    # PDF REPORT
    # ========================================================

    pdf_file = create_pdf_report(

        buildings_found=len(
            selected_buildings
        ),

        roof_area=roof_area,

        usable_roof_area=usable_roof_area,

        panel_name=panel_type,

        panel_power=panel_power,

        panel_area=panel_area,

        panel_efficiency=panel_efficiency,

        num_panels=number_of_panels,

        installed_capacity=installed_capacity,

        annual_energy=annual_energy,

        monthly_df=monthly_df,

        graph_image=graph_path,

        selected_area_image=selected_area_image_path,

        actual_usage_kwh=actual_usage_kwh

    )


    # ========================================================
    # DOWNLOAD PDF
    # ========================================================

    st.download_button(

        label="📄 Download PDF Report",

        data=pdf_file,

        file_name="Solar_Potential_Report.pdf",

        mime="application/pdf"

    )
    # ========================================================
    # PDF REPORT
    # ========================================================

    pdf_file = create_pdf_report(

        buildings_found=len(
            selected_buildings
        ),

        roof_area=roof_area,

        usable_roof_area=usable_roof_area,

        panel_name=panel_type,

        panel_power=panel_power,

        panel_area=panel_area,

        panel_efficiency=panel_efficiency,

        num_panels=number_of_panels,

        installed_capacity=installed_capacity,

        annual_energy=annual_energy,

        monthly_df=monthly_df,

        graph_image=graph_path,

        selected_area_image=selected_area_image_path,

        actual_usage_kwh=actual_usage_kwh

    )


    # ========================================================
    # DOWNLOAD PDF
    # ========================================================

    st.download_button(

        label="📄 Download PDF Report",

        data=pdf_file,

        file_name="Solar_Potential_Report.pdf",

        mime="application/pdf"

    )


    # ========================================================
    # SHOW GRAPH
    # ========================================================

    st.plotly_chart(

        fig,

        use_container_width=True

    )
