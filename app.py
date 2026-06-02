
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

st.set_page_config(
    page_title="GreenRoute GHG Inventory System",
    page_icon="🌱",
    layout="wide"
)

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
    fuel_type = row["fuel_type"]
    distance_km = float(row["distance_km"])
    fuel_consumption = float(row["fuel_consumption"])
    payload_ton = float(row["payload_ton"])
    orders = max(float(row["orders"]), 1)

    if fuel_consumption > 0:
        factor = emission_factors.get(fuel_type, 0)
        total_kgco2e = fuel_consumption * factor
        method = "Fuel-based method"
    else:
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
        "total_kgco2e": total_kgco2e,
        "total_tonco2e": total_kgco2e / 1000,
        "kgco2e_per_km": total_kgco2e / distance_km if distance_km > 0 else 0,
        "kgco2e_per_order": total_kgco2e / orders,
        "kgco2e_per_ton_km": total_kgco2e / tonne_km if tonne_km > 0 else 0,
        "tonne_km": tonne_km,
        "calculation_method": method
    })

def generate_demo_data():
    np.random.seed(42)
    routes = ["HN-Bac Ninh", "HN-Hai Phong", "HN-Thai Nguyen", "HN-Hung Yen", "HN-Ninh Binh"]
    vehicle_types = ["Van", "Small Truck", "Medium Truck", "Heavy Truck"]
    fuel_types = ["Diesel", "Gasoline", "Electricity", "Hybrid"]
    ownerships = ["Owned fleet", "Owned fleet", "Subcontracted carrier"]

    rows = []
    for i in range(50):
        fuel_type = np.random.choice(fuel_types, p=[0.55, 0.15, 0.15, 0.15])
        distance = np.random.randint(25, 260)
        payload = round(np.random.uniform(0.2, 12), 2)
        orders = np.random.randint(10, 220)

        if fuel_type == "Diesel":
            fuel_consumption = round(distance * np.random.uniform(0.18, 0.35), 2)
        elif fuel_type == "Gasoline":
            fuel_consumption = round(distance * np.random.uniform(0.12, 0.25), 2)
        elif fuel_type == "Electricity":
            fuel_consumption = round(distance * np.random.uniform(0.5, 1.1), 2)
        else:
            fuel_consumption = round(distance * np.random.uniform(0.08, 0.18), 2)

        rows.append({
            "trip_id": f"TRIP-{i+1:03d}",
            "date": str(date.today()),
            "route": np.random.choice(routes),
            "vehicle_id": f"VH-{np.random.randint(1, 15):02d}",
            "vehicle_type": np.random.choice(vehicle_types),
            "fuel_type": fuel_type,
            "ownership": np.random.choice(ownerships),
            "distance_km": distance,
            "empty_km": np.random.randint(0, 35),
            "fuel_consumption": fuel_consumption,
            "payload_ton": payload,
            "orders": orders
        })

    return pd.DataFrame(rows)

st.title("🌱 GreenRoute: Mini GHG Inventory System for Transportation")
st.caption("A student-level information system for calculating, tracking, and reporting greenhouse gas emissions from transport activities.")

st.sidebar.header("⚙️ Emission Factors")
st.sidebar.markdown("These are demo factors. You can edit them based on the official factor source used in your report.")

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

tab1, tab2, tab3, tab4 = st.tabs([
    "Single Trip Calculator",
    "Batch Upload",
    "Dashboard",
    "System Design"
])

if "calculated_df" not in st.session_state:
    st.session_state.calculated_df = pd.DataFrame()

with tab1:
    st.subheader("🚚 Single Trip Emission Calculator")

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

    result = single_row.apply(lambda row: calculate_emission(row, emission_factors), axis=1)
    output = pd.concat([single_row, result], axis=1)
    output["scope"] = output.apply(lambda row: classify_scope(row["ownership"], row["fuel_type"]), axis=1)
    output["empty_km_rate"] = output["empty_km"] / output["distance_km"]

    st.markdown("### Result")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total emissions", f"{output.loc[0, 'total_kgco2e']:.2f} kgCO₂e")
    kpi2.metric("CO₂e per km", f"{output.loc[0, 'kgco2e_per_km']:.2f} kg/km")
    kpi3.metric("CO₂e per order", f"{output.loc[0, 'kgco2e_per_order']:.2f} kg/order")
    kpi4.metric("CO₂e per ton-km", f"{output.loc[0, 'kgco2e_per_ton_km']:.4f} kg/ton-km")

    st.info(f"Scope classification: **{output.loc[0, 'scope']}**")
    st.dataframe(output, use_container_width=True)

    if st.button("Add this trip to dashboard"):
        st.session_state.calculated_df = pd.concat(
            [st.session_state.calculated_df, output],
            ignore_index=True
        )
        st.success("Trip added to dashboard dataset.")

with tab2:
    st.subheader("📤 Batch Upload CSV")

    st.markdown(
        """
        Upload a CSV file with these columns:

        `trip_id, date, route, vehicle_id, vehicle_type, fuel_type, ownership, distance_km, empty_km, fuel_consumption, payload_ton, orders`
        """
    )

    sample_df = generate_demo_data()

    st.download_button(
        label="Download sample CSV template",
        data=sample_df.to_csv(index=False).encode("utf-8"),
        file_name="sample_transport_ghg_data.csv",
        mime="text/csv"
    )

    uploaded_file = st.file_uploader("Upload your transport activity CSV", type=["csv"])

    use_demo = st.checkbox("Use demo dataset instead of uploading", value=False)

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    elif use_demo:
        df = sample_df
    else:
        df = pd.DataFrame()

    if not df.empty:
        required_cols = [
            "trip_id", "date", "route", "vehicle_id", "vehicle_type",
            "fuel_type", "ownership", "distance_km", "empty_km",
            "fuel_consumption", "payload_ton", "orders"
        ]

        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            st.error(f"Missing columns: {missing_cols}")
        else:
            calc = df.apply(lambda row: calculate_emission(row, emission_factors), axis=1)
            calculated_df = pd.concat([df, calc], axis=1)
            calculated_df["scope"] = calculated_df.apply(
                lambda row: classify_scope(row["ownership"], row["fuel_type"]),
                axis=1
            )
            calculated_df["empty_km_rate"] = calculated_df["empty_km"] / calculated_df["distance_km"]

            st.session_state.calculated_df = calculated_df

            st.success("Calculation completed.")
            st.dataframe(calculated_df, use_container_width=True)

            st.download_button(
                label="Download calculated result CSV",
                data=calculated_df.to_csv(index=False).encode("utf-8"),
                file_name="calculated_ghg_inventory.csv",
                mime="text/csv"
            )

with tab3:
    st.subheader("📊 GHG Inventory Dashboard")

    df_dash = st.session_state.calculated_df.copy()

    if df_dash.empty:
        st.warning("No data yet. Add one trip in Tab 1 or upload/use demo data in Tab 2.")
    else:
        total_emission = df_dash["total_kgco2e"].sum()
        total_distance = df_dash["distance_km"].sum()
        total_orders = df_dash["orders"].sum()
        total_tonne_km = df_dash["tonne_km"].sum()
        avg_empty_rate = df_dash["empty_km"].sum() / total_distance if total_distance > 0 else 0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total CO₂e", f"{total_emission/1000:.2f} tons")
        k2.metric("Total distance", f"{total_distance:,.0f} km")
        k3.metric("CO₂e/km", f"{total_emission/total_distance:.2f} kg/km")
        k4.metric("CO₂e/order", f"{total_emission/total_orders:.2f} kg/order")
        k5.metric("Empty km rate", f"{avg_empty_rate:.1%}")

        st.markdown("### Emissions by route")
        route_chart = df_dash.groupby("route")["total_kgco2e"].sum().sort_values(ascending=False)
        st.bar_chart(route_chart)

        st.markdown("### Emissions by vehicle type")
        vehicle_chart = df_dash.groupby("vehicle_type")["total_kgco2e"].sum().sort_values(ascending=False)
        st.bar_chart(vehicle_chart)

        st.markdown("### Emissions by scope")
        scope_chart = df_dash.groupby("scope")["total_kgco2e"].sum().sort_values(ascending=False)
        st.bar_chart(scope_chart)

        st.markdown("### Top 10 highest-emission trips")
        top10 = df_dash.sort_values("total_kgco2e", ascending=False).head(10)
        st.dataframe(top10, use_container_width=True)

        st.markdown("### Automatic management suggestions")

        dirty_routes = route_chart.head(3).index.tolist()
        high_empty = df_dash[df_dash["empty_km_rate"] > 0.2]

        suggestions = []

        if dirty_routes:
            suggestions.append(f"Prioritize route optimization for: {', '.join(dirty_routes)}.")
        if len(high_empty) > 0:
            suggestions.append(f"{len(high_empty)} trips have empty-km rate above 20%; consider backhaul matching or route consolidation.")
        if "Diesel" in df_dash["fuel_type"].values:
            suggestions.append("Diesel vehicles dominate emissions; evaluate EV/hybrid replacement for short urban routes.")
        if total_tonne_km > 0:
            intensity = total_emission / total_tonne_km
            suggestions.append(f"Current freight carbon intensity is {intensity:.4f} kgCO₂e/ton-km. Use this as a baseline KPI.")

        for s in suggestions:
            st.write(f"- {s}")

        st.download_button(
            label="Download dashboard data",
            data=df_dash.to_csv(index=False).encode("utf-8"),
            file_name="dashboard_ghg_inventory_data.csv",
            mime="text/csv"
        )

with tab4:
    st.subheader("🧩 Information System Design")

    st.markdown(
        """
        ### 1. System components

        **Data input layer**
        - GPS / odometer data
        - Fuel invoices
        - Driver mobile form
        - Order management system
        - Vehicle master data

        **Database layer**
        - Fleet table
        - Trip table
        - Shipment table
        - Fuel table
        - Emission factor table

        **Calculation engine**
        - Fuel-based method
        - Distance-based method
        - Ton-km intensity calculation
        - Scope 1 / Scope 2 / Scope 3 classification

        **Dashboard layer**
        - Total CO₂e
        - CO₂e per km
        - CO₂e per order
        - CO₂e per ton-km
        - Emission by route, vehicle, and scope

        **Management decision layer**
        - Identify high-emission routes
        - Detect high empty-km rate
        - Support green routing
        - Support customer ESG reporting
        """
    )

    st.markdown(
        """
        ### 2. Data flow

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
        Management actions: routing, fleet replacement, carrier evaluation
        ```
        """
    )

    st.markdown(
        """
        ### 3. Why this system is useful

        This mini-system turns GHG inventory from a static report into a decision-support tool.
        Instead of only saying how much CO₂e was emitted, it shows where the emissions come from,
        which trips are inefficient, and what actions the company can take.
        """
    )
