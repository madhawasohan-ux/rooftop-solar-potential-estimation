import streamlit as st
import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.io as pio
import tempfile


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
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

from shapely.geometry import shape
from folium.plugins import Draw
from streamlit_folium import st_folium

def create_pdf_report(
    buildings_found,
    roof_area,
    usable_roof_area,
    panel_name,
    panel_power,
    num_panels,
    installed_capacity,
    annual_energy,
    monthly_df,
    graph_image

):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            "CINEC Campus",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 30))

    content.append(
        Paragraph(
            "BSc (Hons) Mechatronics Engineering",
            styles["Heading1"]
        )
    )

    content.append(Spacer(1, 30))

    content.append(
        Paragraph(
            "Rooftop Solar Potential Estimation Using Satellite Image Analysis",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 350))

    content.append(
        Paragraph(
            "Student: Sohan Madhawa",
            styles["Heading2"]
        )
    )

    content.append(
        Paragraph(
            "Study Area: Malabe, Sri Lanka",
            styles["Heading2"]
        )
    )

    content.append(
        Paragraph(
            "Year: 2026",
            styles["Heading2"]
        )
    )

    content.append(PageBreak())

    content.append(
        Paragraph(
            "Rooftop Solar Potential Estimation Report",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 20))

    content.append(
        Paragraph(
            f"<b>Buildings Found:</b> {buildings_found}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Roof Area (m²):</b> {roof_area:.2f}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Usable Roof Area (m²):</b> {usable_roof_area:.2f}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Selected Panel:</b> {panel_name}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Panel Power (W):</b> {panel_power}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Number of Panels:</b> {num_panels}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Installed Capacity (kW):</b> {installed_capacity:.2f}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"<b>Estimated Annual Energy (kWh/year):</b> {annual_energy:,.2f}",
            styles["Normal"]
        )
    )
    content.append(Spacer(1, 50))

    content.append(
        Paragraph(
            "Monthly Solar Energy Generation",
            styles["Heading2"]
        )
    )

    table_data = [
        [
            "Month",
            "Irradiance",
            "Energy (kWh)"
        ]
    ]

    for _, row in monthly_df.iterrows():

        table_data.append([

            str(row["Month"]),

            f"{row['Solar Irradiance (kWh/m²/day)']:.3f}",

            f"{row['Estimated Energy (kWh)']:,.2f}"

        ])

    table = Table(table_data)

    table.setStyle(

        TableStyle([

            ('BACKGROUND',(0,0),(-1,0),colors.grey),

            ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),

            ('GRID',(0,0),(-1,-1),1,colors.black),

            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')

        ])

    )

    content.append(table)
    content.append(PageBreak())

    content.append(
        Paragraph(
            "Monthly Solar Energy Generation Graph",
            styles["Heading2"]
        )
    )

    content.append(
        Image(
            graph_image,
            width=450,
            height=250
        )
    )
    content.append(PageBreak())

    content.append(
        Paragraph(
            "Assumptions",
            styles["Title"]
        )
    )

    content.append(Spacer(1,20))

    content.append(
        Paragraph(
            "• Usable Roof Area = 80% of total roof area",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            "• Performance Ratio = 80%",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            "• Solar Irradiance Data Source = NASA POWER",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            "• PV Module Specifications obtained from manufacturer datasheets",
            styles["Normal"]
        )
    )

    doc.build(content)

    pdf = buffer.getvalue()
    buffer.close()

    return pdf

# --------------------------------------------------
# PAGE SETTINGS
# --------------------------------------------------
st.set_page_config(
    page_title="Rooftop Solar Potential Estimation",
    layout="wide"
)

st.title("🏠 Rooftop Solar Potential Estimation")

# --------------------------------------------------
# SESSION STATES
# --------------------------------------------------
if "map_key" not in st.session_state:
    st.session_state.map_key = 0

# --------------------------------------------------
# PANEL DATABASE
# --------------------------------------------------
panel_database = {

    "LONGi Hi-MO X6 (550W)":{

        "power":550,
        "area":2.58,
        "efficiency":0.221

    },

    "Jinko Tiger Neo (580W)":{

        "power":580,
        "area":2.79,
        "efficiency":0.225

    },

    "Trina Vertex (600W)":{

        "power":600,
        "area":3.10,
        "efficiency":0.231

    }

}

# --------------------------------------------------
# LOAD BUILDINGS
# --------------------------------------------------

buildings = gpd.read_file(
    "Malabe_Buildings_Final.gpkg"
)

# --------------------------------------------------
# LOAD NASA IRRADIANCE DATA
# --------------------------------------------------

irradiance_df = pd.read_csv(
    "data/monthly_irradiance.csv"
)

monthly_irradiance = dict(

    zip(

        irradiance_df["Month"],

        irradiance_df["Irradiance"]

    )

)

# --------------------------------------------------
# PANEL SELECTION
# --------------------------------------------------

st.subheader("🔋 Solar Panel Selection")

panel_type = st.selectbox(

    "Select Solar Panel",

    list(panel_database.keys())

)

panel_power = panel_database[panel_type]["power"]

panel_area = panel_database[panel_type]["area"]

panel_efficiency = panel_database[panel_type]["efficiency"]

# --------------------------------------------------
# BUTTONS
# --------------------------------------------------

c1,c2,c3 = st.columns(3)

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

# --------------------------------------------------
# CREATE MAP
# --------------------------------------------------

m = folium.Map(

    location=[6.9061,79.9696],

    zoom_start=17

)

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

    width=1500,

    height=550,

    key=f"map_{st.session_state.map_key}"

)

# --------------------------------------------------
# CALCULATIONS
# --------------------------------------------------

if output["last_active_drawing"] is not None and calculate:

    user_polygon = shape(

        output["last_active_drawing"]["geometry"]

    )

    selected_buildings = buildings[

        buildings.centroid.within(

            user_polygon

        )

    ]

    selected_buildings_projected = (

        selected_buildings.to_crs(

            epsg=32644

        )

    )

    roof_area = (

        selected_buildings_projected.geometry.area.sum()

    )

    usable_roof_area = roof_area * 0.80

    number_of_panels = int(

        usable_roof_area /

        panel_area

    )

    installed_capacity = (

        number_of_panels *

        panel_power

    ) / 1000

    performance_ratio = 0.80

    month_days = {

        "January":31,
        "February":28,
        "March":31,
        "April":30,
        "May":31,
        "June":30,
        "July":31,
        "August":31,
        "September":30,
        "October":31,
        "November":30,
        "December":31

    }

    monthly_results = []

    annual_energy = 0

    for month,irradiance in monthly_irradiance.items():

        days = month_days[month]

        monthly_energy = (
                        usable_roof_area
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

    # --------------------------------------------------
    # RESULTS
    # --------------------------------------------------

    st.subheader("📊 Results")

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

    # --------------------------------------------------
    # PANEL SPECIFICATIONS
    # --------------------------------------------------

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
        f"{panel_efficiency*100:.1f}%"
    )

    # --------------------------------------------------
    # ANNUAL ENERGY
    # --------------------------------------------------

    st.subheader(
        "⚡ Annual Energy Generation"
    )

    st.metric(

        "Estimated Annual Energy",

        f"{annual_energy:,.0f} kWh/year"
    )
    # --------------------------------------------------
    # MONTHLY TABLE
    # --------------------------------------------------

    st.subheader(
            "📅 Monthly Solar Energy Generation"
        )

    st.dataframe(

            monthly_df,

            use_container_width=True,

            hide_index=True

        )

        # --------------------------------------------------
        # MONTHLY GRAPH
        # --------------------------------------------------

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
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".png"
    ) as tmp:

        graph_path = tmp.name

    fig.write_image(
        graph_path,
        width=1200,
        height=700
    )
    pdf_file = create_pdf_report(
        buildings_found=len(selected_buildings),
        roof_area=roof_area,
        usable_roof_area=usable_roof_area,
        panel_name=panel_type,
        panel_power=panel_power,
        num_panels=number_of_panels,
        installed_capacity=installed_capacity,
        annual_energy=annual_energy,
        monthly_df=monthly_df,
        graph_image=graph_path
    )

    st.download_button(
        label="📄 Download PDF Report",
        data=pdf_file,
        file_name="Solar_Potential_Report.pdf",
        mime="application/pdf"
    )    

    st.plotly_chart(

            fig,

            use_container_width=True

        )