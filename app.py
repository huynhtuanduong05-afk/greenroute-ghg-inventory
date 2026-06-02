
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="GreenRoute GHG Inventory System",
    page_icon="🌱",
    layout="wide"
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown(
    """
    <style>
    .main-title {
        font-size: 38px;
        font-weight: 800;
        color: #14532d;
        margin-bottom: 0px;
    }
    .subtitle {
        font-size: 17px;
        color: #4b5563;
        margin-top: 0px;
        margin-bottom: 25px;
    }
    .card {
        padding: 18px 20px;
        border-radius: 16px;
        background: linear-gradient(135deg, #ecfdf5 0%, #f8fafc 100%);
        border: 1px solid #d1fae5;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 12px;
    }
    .card-red {
        padding: 16px 18px;
        border-radius: 16px;
        background: linear-gradient(135deg, #fef2f2 0%, #fff7ed 100%);
        border: 1px solid #fecaca;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 12px;
    }
    .card-blue {
        padding: 16px 18px;
        border-radius: 16px;
        background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%);
        border: 1px solid #bfdbfe;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 12px;
    }
    .big-number {
        font-size: 28px;
        font-weight: 800;
        color: #064e3b;
    }
    .small-label {
        font-size: 14px;
        color: #6b7280;
    }
    .warning-text {
        color: #991b1b;
        font-weight: 700;
    }
    .success-text {
        color: #166534;
        font-weight: 700;
    }
    .section-header {
        font-size: 24px;
        font-weight: 750;
        color: #14532d;
        margin-top: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def classify_scope(ownership, fuel_type):
    ownership = str(ownership).lower()
    fuel_type = str(fuel_type).lower()

    if "subcontract" in ownership or "3pl" in ownership or "carrier" in ownership:
        return "Scope 3 - Subcontracted transport"
    elif fuel_type in ["electricity", "ev", "electric"]:
        return "Scope 2 - Purchased electricity"
    else:
        return "Scope 1 - Owned fleet fuel combustion"


def calculate_emission(row, emission_factors):
    fuel_type = str(row["fuel_type"])
    distance_km = float(row["distance_km"])
    fuel_consumption = float(row["fuel_consumption"])
    payload_ton = float(row["payload_ton"])
    orders = max(float(row["orders"]), 1)

    # Fuel-based method if fuel/electricity consumption is available.
    if fuel_consumption > 0:
        factor = emission_factors.get(fuel_type, 0)
        total_kgco2e = fuel_consumption * factor
        method = "Fuel-based method"
    else:
        # Fallback method when actual fuel/kWh is missing.
        # These are demo intensity values and can be replaced with company-specific factors.
        default_intensity = {
            "Diesel": 0.85,
            "Gasoline": 0.75,
            "Electricity": 0.25,
            "Hybrid": 0.55
        }
        total_kgco2e = distance_km * default_intensity.get(fuel_type, 0.85)
        method = "Distance-based estimation"

    tonne_km = distance_km * max(payload_ton, 0)

    return pd.Series({
        "total_kgco2e": round(total_kgco2e, 3),
        "total_tonco2e": round(total_kgco2e / 1000, 5),
        "kgco2e_per_km": round(total_kgco2e / distance_km, 4) if distance_km > 0 else 0,
        "kgco2e_per_order": round(total_kgco2e / orders, 4),
        "kgco2e_per_ton_km": round(total_kgco2e / tonne_km, 6) if tonne_km > 0 else 0,
        "tonne_km": round(tonne_km, 3),
        "calculation_method": method
    })


def validate_columns(df):
    required_cols = [
        "trip_id", "date", "route", "vehicle_id", "vehicle_type",
        "fuel_type", "ownership", "distance_km", "empty_km",
        "fuel_consumption", "payload_ton", "orders"
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    return missing_cols


def calculate_dataset(df, emission_factors):
    df = df.copy()
    numeric_cols = ["distance_km", "empty_km", "fuel_consumption", "payload_ton", "orders"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    calc = df.apply(lambda row: calculate_emission(row, emission_factors), axis=1)
    calculated_df = pd.concat([df, calc], axis=1)
    calculated_df["scope"] = calculated_df.apply(
        lambda row: classify_scope(row["ownership"], row["fuel_type"]),
        axis=1
    )
    calculated_df["empty_km_rate"] = np.where(
        calculated_df["distance_km"] > 0,
        calculated_df["empty_km"] / calculated_df["distance_km"],
        0
    )
    calculated_df["empty_km_rate"] = calculated_df["empty_km_rate"].round(4)
    return calculated_df


def generate_demo_data():
    rows = [
        ["TRIP-001", "2026-06-01", "Hanoi - Hai Phong", "VH-01", "Medium Truck", "Diesel", "Owned fleet", 120, 10, 30, 4.5, 80],
        ["TRIP-002", "2026-06-01", "Hanoi - Bac Ninh", "VH-02", "Small Truck", "Diesel", "Owned fleet", 45, 5, 9, 2.0, 50],
        ["TRIP-003", "2026-06-01", "Hanoi - Hung Yen", "VH-03", "Van", "Gasoline", "Owned fleet", 38, 4, 7, 0.8, 65],
        ["TRIP-004", "2026-06-02", "Hanoi - Thai Nguyen", "VH-04", "Medium Truck", "Diesel", "Subcontracted carrier", 85, 15, 22, 3.8, 70],
        ["TRIP-005", "2026-06-02", "Hanoi - Ninh Binh", "VH-05", "Heavy Truck", "Diesel", "Owned fleet", 100, 8, 32, 8.0, 110],
        ["TRIP-006", "2026-06-02", "Hanoi Urban Route 1", "VH-06", "Van", "Electricity", "Owned fleet", 28, 2, 20, 0.6, 95],
        ["TRIP-007", "2026-06-03", "Hanoi - Hai Duong", "VH-07", "Small Truck", "Hybrid", "Owned fleet", 62, 6, 8, 1.7, 75],
        ["TRIP-008", "2026-06-03", "Hanoi - Vinh Phuc", "VH-08", "Medium Truck", "Diesel", "Owned fleet", 55, 12, 16, 3.0, 60],
        ["TRIP-009", "2026-06-03", "Hanoi Urban Route 2", "VH-09", "Van", "Electricity", "Owned fleet", 32, 3, 24, 0.7, 120],
        ["TRIP-010", "2026-06-04", "Hanoi - Hai Phong", "VH-01", "Medium Truck", "Diesel", "Owned fleet", 122, 18, 34, 4.2, 78],
        ["TRIP-011", "2026-06-04", "Hanoi - Bac Giang", "VH-10", "Small Truck", "Gasoline", "Subcontracted carrier", 58, 20, 11, 1.4, 40],
        ["TRIP-012", "2026-06-04", "Hanoi - Nam Dinh", "VH-11", "Heavy Truck", "Diesel", "Owned fleet", 92, 6, 27, 7.5, 100],
        ["TRIP-013", "2026-06-05", "Hanoi Urban Route 3", "VH-12", "Van", "Electricity", "Owned fleet", 25, 1, 18, 0.5, 105],
        ["TRIP-014", "2026-06-05", "Hanoi - Quang Ninh", "VH-13", "Heavy Truck", "Diesel", "Subcontracted carrier", 165, 25, 52, 9.0, 130],
        ["TRIP-015", "2026-06-05", "Hanoi - Hai Duong", "VH-07", "Small Truck", "Hybrid", "Owned fleet", 60, 4, 7, 1.9, 82],
        ["TRIP-016", "2026-06-06", "Hanoi - Thai Nguyen", "VH-04", "Medium Truck", "Diesel", "Subcontracted carrier", 84, 9, 21, 4.0, 72],
        ["TRIP-017", "2026-06-06", "Hanoi - Hung Yen", "VH-03", "Van", "Gasoline", "Owned fleet", 40, 6, 8, 0.9, 68],
        ["TRIP-018", "2026-06-06", "Hanoi - Ninh Binh", "VH-05", "Heavy Truck", "Diesel", "Owned fleet", 102, 14, 35, 8.2, 115],
        ["TRIP-019", "2026-06-07", "Hanoi Urban Route 1", "VH-06", "Van", "Electricity", "Owned fleet", 30, 2, 22, 0.6, 98],
        ["TRIP-020", "2026-06-07", "Hanoi - Bac Ninh", "VH-02", "Small Truck", "Diesel", "Owned fleet", 46, 7, 10, 2.2, 55],
        ["TRIP-021", "2026-06-07", "Hanoi - Vinh Phuc", "VH-08", "Medium Truck", "Diesel", "Owned fleet", 57, 18, 18, 2.8, 58],
        ["TRIP-022", "2026-06-08", "Hanoi - Quang Ninh", "VH-13", "Heavy Truck", "Diesel", "Subcontracted carrier", 168, 30, 55, 9.5, 135],
        ["TRIP-023", "2026-06-08", "Hanoi Urban Route 2", "VH-09", "Van", "Electricity", "Owned fleet", 31, 4, 23, 0.7, 118],
        ["TRIP-024", "2026-06-08", "Hanoi - Nam Dinh", "VH-11", "Heavy Truck", "Diesel", "Owned fleet", 95, 10, 29, 7.8, 104],
        ["TRIP-025", "2026-06-09", "Hanoi - Bac Giang", "VH-10", "Small Truck", "Gasoline", "Subcontracted carrier", 60, 22, 12, 1.5, 42],
    ]

    header = [
        "trip_id", "date", "route", "vehicle_id", "vehicle_type", "fuel_type",
        "ownership", "distance_km", "empty_km", "fuel_consumption", "payload_ton", "orders"
    ]
    return pd.DataFrame(rows, columns=header)


def kpi_card(label, value, note="", kind="green"):
    css_class = "card"
    if kind == "red":
        css_class = "card-red"
    elif kind == "blue":
        css_class = "card-blue"

    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="small-label">{label}</div>
            <div class="big-number">{value}</div>
            <div class="small-label">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def make_gradient_bar(df, x, y, title, labels=None):
    if df.empty:
        st.warning("No data available for this chart.")
        return

    fig = px.bar(
        df,
        x=x,
        y=y,
        color=x,
        color_continuous_scale="Reds",
        text=x,
        title=title,
        labels=labels
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        height=430,
        showlegend=False,
        coloraxis_showscale=False,
        title_font_size=20,
        xaxis_title="",
        yaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)


def style_emission_table(df):
    display_cols = [
        "trip_id", "route", "vehicle_id", "fuel_type", "ownership",
        "distance_km", "empty_km_rate", "total_kgco2e",
        "kgco2e_per_km", "kgco2e_per_order", "kgco2e_per_ton_km", "scope"
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    styled = (
        df[display_cols]
        .style
        .background_gradient(cmap="Reds", subset=["total_kgco2e"])
        .background_gradient(cmap="YlOrRd", subset=["empty_km_rate"])
        .format({
            "distance_km": "{:,.0f}",
            "empty_km_rate": "{:.1%}",
            "total_kgco2e": "{:,.2f}",
            "kgco2e_per_km": "{:.3f}",
            "kgco2e_per_order": "{:.3f}",
            "kgco2e_per_ton_km": "{:.5f}",
        })
    )
    return styled


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.header("⚙️ Emission Factors")
st.sidebar.caption("Demo factors. You can adjust them to match the source used in your report.")

diesel_factor = st.sidebar.number_input("Diesel factor: kgCO₂e / liter", value=2.68, min_value=0.0, step=0.01)
gasoline_factor = st.sidebar.number_input("Gasoline factor: kgCO₂e / liter", value=2.31, min_value=0.0, step=0.01)
electricity_factor = st.sidebar.number_input("Electricity factor: kgCO₂e / kWh", value=0.45, min_value=0.0, step=0.01)
hybrid_factor = st.sidebar.number_input("Hybrid factor: kgCO₂e / liter", value=1.80, min_value=0.0, step=0.01)

emission_factors = {
    "Diesel": diesel_factor,
    "Gasoline": gasoline_factor,
    "Electricity": electricity_factor,
    "Hybrid": hybrid_factor
}

# ============================================================
# SESSION STATE
# ============================================================
if "calculated_df" not in st.session_state:
    st.session_state.calculated_df = pd.DataFrame()

if "activity_df" not in st.session_state:
    st.session_state.activity_df = pd.DataFrame()

# ============================================================
# TITLE
# ============================================================
st.markdown('<div class="main-title">🌱 GreenRoute GHG Inventory System</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">A mini information system for calculating, visualizing, and managing greenhouse gas emissions in transportation.</div>',
    unsafe_allow_html=True
)

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Single Trip",
    "2. Upload & Data",
    "3. Trip Explorer",
    "4. Dashboard",
    "5. Reduction Scenario",
    "6. System Design"
])

# ============================================================
# TAB 1: SINGLE TRIP
# ============================================================
with tab1:
    st.markdown('<div class="section-header">🚚 Single Trip Emission Calculator</div>', unsafe_allow_html=True)
    st.caption("Use this tab when you want to calculate emissions for one transport trip.")

    col1, col2, col3 = st.columns(3)

    with col1:
        trip_id = st.text_input("Trip ID", value="TRIP-001")
        trip_date = st.date_input("Trip date", value=date.today())
        route = st.text_input("Route", value="Hanoi - Hai Phong")
        vehicle_id = st.text_input("Vehicle ID", value="VH-01")

    with col2:
        vehicle_type = st.selectbox("Vehicle type", ["Van", "Small Truck", "Medium Truck", "Heavy Truck"])
        fuel_type = st.selectbox("Fuel type", ["Diesel", "Gasoline", "Electricity", "Hybrid"])
        ownership = st.selectbox("Ownership", ["Owned fleet", "Subcontracted carrier"])
        distance_km = st.number_input("Distance km", value=120.0, min_value=0.0, step=1.0)

    with col3:
        empty_km = st.number_input("Empty km", value=10.0, min_value=0.0, step=1.0)
        fuel_consumption = st.number_input(
            "Fuel / electricity consumption",
            value=30.0,
            min_value=0.0,
            step=1.0,
            help="Diesel/Gasoline/Hybrid: liters. Electricity: kWh."
        )
        payload_ton = st.number_input("Payload ton", value=4.5, min_value=0.0, step=0.1)
        orders = st.number_input("Number of orders", value=80, min_value=1, step=1)

    single_row = pd.DataFrame([{
        "trip_id": trip_id,
        "date": str(trip_date),
        "route": route,
        "vehicle_id": vehicle_id,
        "vehicle_type": vehicle_type,
        "fuel_type": fuel_type,
        "ownership": ownership,
        "distance_km": distance_km,
        "empty_km": empty_km,
        "fuel_consumption": fuel_consumption,
        "payload_ton": payload_ton,
        "orders": orders
    }])

    output = calculate_dataset(single_row, emission_factors)

    st.markdown("### Result")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_card("Total emissions", f"{output.loc[0, 'total_kgco2e']:.2f} kgCO₂e", "Main result")
    with k2:
        kpi_card("CO₂e per km", f"{output.loc[0, 'kgco2e_per_km']:.2f} kg/km", "Transport efficiency", kind="blue")
    with k3:
        kpi_card("CO₂e per order", f"{output.loc[0, 'kgco2e_per_order']:.2f} kg/order", "Customer-level KPI", kind="blue")
    with k4:
        kpi_card("Empty km rate", f"{output.loc[0, 'empty_km_rate']:.1%}", "Wasted distance", kind="red" if output.loc[0, "empty_km_rate"] > 0.2 else "green")

    st.info(f"Scope classification: **{output.loc[0, 'scope']}**")
    st.dataframe(style_emission_table(output), use_container_width=True)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("➕ Add this trip to dataset", use_container_width=True):
            st.session_state.calculated_df = pd.concat(
                [st.session_state.calculated_df, output],
                ignore_index=True
            )
            st.success("Trip added. Open the Dashboard tab to see updated charts.")

    with col_b:
        st.download_button(
            label="⬇️ Download this trip result",
            data=output.to_csv(index=False).encode("utf-8"),
            file_name=f"{trip_id}_calculated_result.csv",
            mime="text/csv",
            use_container_width=True
        )

# ============================================================
# TAB 2: UPLOAD & DATA
# ============================================================
with tab2:
    st.markdown('<div class="section-header">📤 Upload & Data Manager</div>', unsafe_allow_html=True)
    st.caption("Upload a CSV file, use demo data, view the dataset, or clear data.")

    sample_df = generate_demo_data()

    st.markdown("#### Required CSV columns")
    st.code(
        "trip_id, date, route, vehicle_id, vehicle_type, fuel_type, ownership, distance_km, empty_km, fuel_consumption, payload_ton, orders",
        language="text"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.download_button(
            label="⬇️ Download sample CSV",
            data=sample_df.to_csv(index=False).encode("utf-8"),
            file_name="greenroute_sample_upload.csv",
            mime="text/csv",
            use_container_width=True
        )

    with c2:
        if st.button("📌 Load demo dataset", use_container_width=True):
            st.session_state.calculated_df = calculate_dataset(sample_df, emission_factors)
            st.success("Demo dataset loaded. Open Dashboard to view charts.")

    with c3:
        if st.button("🗑️ Clear current dataset", use_container_width=True):
            st.session_state.calculated_df = pd.DataFrame()
            st.success("Dataset cleared.")

    uploaded_file = st.file_uploader("Upload your transport activity CSV", type=["csv"])

    if uploaded_file is not None:
        uploaded_df = pd.read_csv(uploaded_file)
        missing_cols = validate_columns(uploaded_df)

        if missing_cols:
            st.error(f"Missing columns: {missing_cols}")
        else:
            calculated_df = calculate_dataset(uploaded_df, emission_factors)
            st.session_state.calculated_df = calculated_df
            st.success("Upload completed and emissions calculated.")

    df_current = st.session_state.calculated_df.copy()

    if df_current.empty:
        st.warning("No dataset yet. Upload a CSV or click Load demo dataset.")
    else:
        st.markdown("### Current calculated dataset")
        st.dataframe(style_emission_table(df_current), use_container_width=True)

        st.download_button(
            label="⬇️ Download calculated dataset",
            data=df_current.to_csv(index=False).encode("utf-8"),
            file_name="greenroute_calculated_ghg_inventory.csv",
            mime="text/csv",
            use_container_width=True
        )

# ============================================================
# TAB 3: TRIP EXPLORER
# ============================================================
with tab3:
    st.markdown('<div class="section-header">🔎 Trip Explorer</div>', unsafe_allow_html=True)
    st.caption("Select one trip to inspect its emission details.")

    df = st.session_state.calculated_df.copy()

    if df.empty:
        st.warning("No data available. Load demo data or upload a CSV first.")
    else:
        trip_options = df["trip_id"].astype(str).tolist()
        selected_trip = st.selectbox("Choose a trip", trip_options)

        selected = df[df["trip_id"].astype(str) == selected_trip].iloc[0]
        avg_emission = df["total_kgco2e"].mean()
        avg_empty_rate = df["empty_km_rate"].mean()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("Selected trip CO₂e", f"{selected['total_kgco2e']:.2f} kg", selected["route"])
        with c2:
            diff = selected["total_kgco2e"] - avg_emission
            note = f"{diff:+.2f} kg vs dataset avg"
            kpi_card("Compared with average", note, "Positive means higher than average", kind="red" if diff > 0 else "green")
        with c3:
            kpi_card("Empty km rate", f"{selected['empty_km_rate']:.1%}", "Operational waste", kind="red" if selected["empty_km_rate"] > avg_empty_rate else "green")
        with c4:
            kpi_card("Scope", selected["scope"], "GHG Protocol classification", kind="blue")

        st.markdown("### Trip detail")
        detail_df = pd.DataFrame(selected).reset_index()
        detail_df.columns = ["Field", "Value"]
        st.dataframe(detail_df, use_container_width=True, hide_index=True)

        st.markdown("### Management interpretation")
        messages = []
        if selected["fuel_type"] == "Diesel":
            messages.append("This trip uses diesel. It may be a priority candidate for fuel efficiency improvement or EV replacement if the route is short.")
        if selected["empty_km_rate"] > 0.2:
            messages.append("This trip has high empty-km rate. Consider backhaul matching, route consolidation, or better dispatch planning.")
        if selected["total_kgco2e"] > avg_emission:
            messages.append("This trip emits more than the average trip in the dataset. It should be reviewed before lower-emission trips.")
        if selected["scope"].startswith("Scope 3"):
            messages.append("This trip is subcontracted transport. The company needs carrier data-sharing rules to improve Scope 3 accuracy.")

        if not messages:
            messages.append("This trip does not show a major emission warning compared with the current dataset.")

        for m in messages:
            st.write(f"- {m}")

# ============================================================
# TAB 4: DASHBOARD
# ============================================================
with tab4:
    st.markdown('<div class="section-header">📊 GHG Inventory Dashboard</div>', unsafe_allow_html=True)
    st.caption("Charts use darker color for higher emissions and lighter color for lower emissions.")

    df = st.session_state.calculated_df.copy()

    if df.empty:
        st.warning("No data yet. Load demo data in Upload & Data tab or add a trip from Single Trip tab.")
    else:
        st.markdown("### Filters")
        f1, f2, f3 = st.columns(3)

        with f1:
            route_filter = st.multiselect("Route", sorted(df["route"].unique()), default=sorted(df["route"].unique()))
        with f2:
            fuel_filter = st.multiselect("Fuel type", sorted(df["fuel_type"].unique()), default=sorted(df["fuel_type"].unique()))
        with f3:
            scope_filter = st.multiselect("Scope", sorted(df["scope"].unique()), default=sorted(df["scope"].unique()))

        df_f = df[
            df["route"].isin(route_filter)
            & df["fuel_type"].isin(fuel_filter)
            & df["scope"].isin(scope_filter)
        ].copy()

        if df_f.empty:
            st.error("No data after filtering. Please change filters.")
        else:
            total_emission = df_f["total_kgco2e"].sum()
            total_distance = df_f["distance_km"].sum()
            total_orders = df_f["orders"].sum()
            total_tonne_km = df_f["tonne_km"].sum()
            avg_empty_rate = df_f["empty_km"].sum() / total_distance if total_distance > 0 else 0

            k1, k2, k3, k4, k5 = st.columns(5)
            with k1:
                kpi_card("Total CO₂e", f"{total_emission/1000:.2f} tons", "Filtered dataset")
            with k2:
                kpi_card("Total distance", f"{total_distance:,.0f} km", "Transport activity", kind="blue")
            with k3:
                kpi_card("CO₂e/km", f"{total_emission/total_distance:.2f} kg/km", "Intensity KPI", kind="blue")
            with k4:
                kpi_card("CO₂e/order", f"{total_emission/total_orders:.2f} kg/order", "Customer KPI", kind="blue")
            with k5:
                kpi_card("Empty km rate", f"{avg_empty_rate:.1%}", "Operational waste", kind="red" if avg_empty_rate > 0.2 else "green")

            st.markdown("### Emission hotspot charts")

            route_data = (
                df_f.groupby("route", as_index=False)["total_kgco2e"]
                .sum()
                .sort_values("total_kgco2e", ascending=False)
            )
            route_data["total_tonco2e"] = route_data["total_kgco2e"] / 1000

            vehicle_data = (
                df_f.groupby("vehicle_type", as_index=False)["total_kgco2e"]
                .sum()
                .sort_values("total_kgco2e", ascending=False)
            )

            fuel_data = (
                df_f.groupby("fuel_type", as_index=False)["total_kgco2e"]
                .sum()
                .sort_values("total_kgco2e", ascending=False)
            )

            scope_data = (
                df_f.groupby("scope", as_index=False)["total_kgco2e"]
                .sum()
                .sort_values("total_kgco2e", ascending=False)
            )

            chart1, chart2 = st.columns(2)
            with chart1:
                make_gradient_bar(
                    route_data,
                    x="total_kgco2e",
                    y="route",
                    title="Emissions by route: darker = higher",
                    labels={"total_kgco2e": "kgCO₂e", "route": "Route"}
                )
            with chart2:
                make_gradient_bar(
                    vehicle_data,
                    x="total_kgco2e",
                    y="vehicle_type",
                    title="Emissions by vehicle type",
                    labels={"total_kgco2e": "kgCO₂e", "vehicle_type": "Vehicle type"}
                )

            chart3, chart4 = st.columns(2)
            with chart3:
                make_gradient_bar(
                    fuel_data,
                    x="total_kgco2e",
                    y="fuel_type",
                    title="Emissions by fuel type",
                    labels={"total_kgco2e": "kgCO₂e", "fuel_type": "Fuel type"}
                )
            with chart4:
                fig_pie = px.pie(
                    scope_data,
                    values="total_kgco2e",
                    names="scope",
                    title="Emission share by scope",
                    hole=0.45
                )
                fig_pie.update_layout(height=430)
                st.plotly_chart(fig_pie, use_container_width=True)

            st.markdown("### High-emission trip table")
            top10 = df_f.sort_values("total_kgco2e", ascending=False).head(10)
            st.dataframe(style_emission_table(top10), use_container_width=True)

            st.markdown("### Automatic management suggestions")
            dirty_routes = route_data.head(3)["route"].tolist()
            high_empty = df_f[df_f["empty_km_rate"] > 0.2]
            diesel_share = df_f[df_f["fuel_type"] == "Diesel"]["total_kgco2e"].sum() / total_emission if total_emission > 0 else 0

            suggestions = []
            if dirty_routes:
                suggestions.append(f"Focus first on these high-emission routes: **{', '.join(dirty_routes)}**.")
            if len(high_empty) > 0:
                suggestions.append(f"**{len(high_empty)} trips** have empty-km rate above 20%. Consider backhaul matching or route consolidation.")
            if diesel_share > 0.5:
                suggestions.append(f"Diesel accounts for **{diesel_share:.1%}** of filtered emissions. Prioritize fuel efficiency improvement or EV transition on short routes.")
            if total_tonne_km > 0:
                intensity = total_emission / total_tonne_km
                suggestions.append(f"Current freight carbon intensity is **{intensity:.4f} kgCO₂e/ton-km**. Use this as a baseline KPI.")

            for s in suggestions:
                st.markdown(f"- {s}")

# ============================================================
# TAB 5: REDUCTION SCENARIO
# ============================================================
with tab5:
    st.markdown('<div class="section-header">🌿 Reduction Scenario Simulator</div>', unsafe_allow_html=True)
    st.caption("Estimate potential CO₂e reduction from practical green transport actions.")

    df = st.session_state.calculated_df.copy()

    if df.empty:
        st.warning("No data available. Load demo data or upload a CSV first.")
    else:
        baseline = df["total_kgco2e"].sum()

        st.markdown("### Choose improvement actions")
        s1, s2, s3 = st.columns(3)

        with s1:
            fuel_efficiency_improvement = st.slider(
                "Fuel efficiency improvement for diesel/gasoline/hybrid trips",
                min_value=0,
                max_value=30,
                value=8,
                step=1,
                help="Example: eco-driving, maintenance, better dispatching."
            )

        with s2:
            empty_km_reduction = st.slider(
                "Empty-km reduction",
                min_value=0,
                max_value=50,
                value=15,
                step=1,
                help="Example: backhaul matching and better route consolidation."
            )

        with s3:
            ev_shift_short_routes = st.slider(
                "Shift short urban fossil-fuel trips to EV",
                min_value=0,
                max_value=100,
                value=25,
                step=5,
                help="Applies to fossil-fuel trips under 60 km."
            )

        scenario_df = df.copy()
        scenario_df["scenario_kgco2e"] = scenario_df["total_kgco2e"]

        # Action 1: reduce fuel-based emissions for fossil-fuel trips.
        fossil_mask = scenario_df["fuel_type"].isin(["Diesel", "Gasoline", "Hybrid"])
        scenario_df.loc[fossil_mask, "scenario_kgco2e"] *= (1 - fuel_efficiency_improvement / 100)

        # Action 2: assume empty-km emissions are proportional to empty-km rate.
        # Only reduce the portion related to empty distance.
        scenario_df["empty_emission_part"] = scenario_df["scenario_kgco2e"] * scenario_df["empty_km_rate"]
        scenario_df["scenario_kgco2e"] -= scenario_df["empty_emission_part"] * (empty_km_reduction / 100)

        # Action 3: selected share of short fossil-fuel routes shift to EV.
        short_fossil_mask = fossil_mask & (scenario_df["distance_km"] <= 60)
        scenario_df.loc[short_fossil_mask, "scenario_kgco2e"] *= (1 - 0.65 * ev_shift_short_routes / 100)

        scenario_total = scenario_df["scenario_kgco2e"].sum()
        reduction = baseline - scenario_total
        reduction_pct = reduction / baseline if baseline > 0 else 0

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi_card("Baseline emissions", f"{baseline/1000:.2f} tons CO₂e", "Current dataset")
        with c2:
            kpi_card("Scenario emissions", f"{scenario_total/1000:.2f} tons CO₂e", "After selected actions", kind="blue")
        with c3:
            kpi_card("Estimated reduction", f"{reduction/1000:.2f} tons CO₂e", f"{reduction_pct:.1%} reduction", kind="green")

        comparison = pd.DataFrame({
            "Scenario": ["Baseline", "After improvement"],
            "kgCO₂e": [baseline, scenario_total]
        })

        fig = px.bar(
            comparison,
            x="Scenario",
            y="kgCO₂e",
            color="kgCO₂e",
            color_continuous_scale="Greens_r",
            text="kgCO₂e",
            title="Before vs after reduction scenario"
        )
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig.update_layout(coloraxis_showscale=False, height=430)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Trip-level scenario result")
        scenario_view = scenario_df.copy()
        scenario_view["reduction_kgco2e"] = scenario_view["total_kgco2e"] - scenario_view["scenario_kgco2e"]
        scenario_view["reduction_pct"] = np.where(
            scenario_view["total_kgco2e"] > 0,
            scenario_view["reduction_kgco2e"] / scenario_view["total_kgco2e"],
            0
        )
        display_cols = ["trip_id", "route", "fuel_type", "distance_km", "total_kgco2e", "scenario_kgco2e", "reduction_kgco2e", "reduction_pct"]
        styled_scenario = (
            scenario_view[display_cols]
            .sort_values("reduction_kgco2e", ascending=False)
            .style
            .background_gradient(cmap="Greens", subset=["reduction_kgco2e"])
            .format({
                "distance_km": "{:,.0f}",
                "total_kgco2e": "{:,.2f}",
                "scenario_kgco2e": "{:,.2f}",
                "reduction_kgco2e": "{:,.2f}",
                "reduction_pct": "{:.1%}"
            })
        )
        st.dataframe(styled_scenario, use_container_width=True)

# ============================================================
# TAB 6: SYSTEM DESIGN
# ============================================================
with tab6:
    st.markdown('<div class="section-header">🧩 Information System Design</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown(
            """
            ### System components

            **1. Data input layer**
            - GPS / odometer data
            - Fuel invoices
            - Driver mobile form
            - Order management system
            - Vehicle master data

            **2. Database layer**
            - Fleet table
            - Trip table
            - Shipment table
            - Fuel table
            - Emission factor table

            **3. Calculation engine**
            - Fuel-based method
            - Distance-based method
            - Ton-km intensity calculation
            - Scope 1 / Scope 2 / Scope 3 classification

            **4. Dashboard layer**
            - Total CO₂e
            - CO₂e per km
            - CO₂e per order
            - CO₂e per ton-km
            - Emission by route, vehicle, fuel, and scope

            **5. Management decision layer**
            - Identify high-emission routes
            - Detect high empty-km rate
            - Support EV transition decisions
            - Support customer ESG reporting
            """
        )

    with col2:
        st.markdown(
            """
            ### Data flow

            ```
            Transport activity data
                    ↓
            Data cleaning and validation
                    ↓
            Emission calculation engine
                    ↓
            GHG inventory database
                    ↓
            Dashboard and report
                    ↓
            Management actions
            ```

            ### What is new in this version?

            - Select and inspect individual trips
            - Filter dashboard by route, fuel, and scope
            - Dark-to-light color dashboard for emission hotspots
            - Color-highlighted table cells
            - Reduction scenario simulator
            - Downloadable CSV results
            """
        )

    st.success(
        "This prototype shows how a transportation company can transform GHG inventory from a static report into a practical decision-support system."
    )
