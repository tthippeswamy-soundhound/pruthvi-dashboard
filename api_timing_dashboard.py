#!/usr/bin/env python3

import os
import re
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

TIMING_PATTERN = re.compile(r"Api Timing\s*:?=\s*\[([^\]]+)\]", re.IGNORECASE)
DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "conversations.csv")

COLORS = {
    "bg": "#0f1117",
    "card": "#1a1d27",
    "border": "#2a2d3e",
    "accent1": "#6c63ff",
    "accent2": "#00d4aa",
    "accent3": "#ff6584",
    "accent4": "#ffa500",
    "text": "#e0e0e0",
    "subtext": "#8888aa",
}

API_COLORS = px.colors.qualitative.Vivid

LAYOUT_BASE = dict(
    paper_bgcolor=COLORS["card"],
    plot_bgcolor=COLORS["bg"],
    font=dict(color=COLORS["text"], family="Inter, sans-serif"),
    xaxis=dict(gridcolor="#2a2d3e", zerolinecolor="#2a2d3e"),
    yaxis=dict(gridcolor="#2a2d3e", zerolinecolor="#2a2d3e"),
    margin=dict(l=40, r=20, t=50, b=40),
)


def _parse_timing_string(timing_str: str) -> dict:
    timing = {}
    for item in timing_str.split(","):
        item = item.strip()
        parts = item.split(":")
        if len(parts) < 2:
            continue

        name = parts[0].strip()
        val_str = parts[1].replace(" ms", "").replace("ms", "").strip()

        try:
            timing[name] = float(val_str)
        except ValueError:
            pass

    return timing


def parse_dataframe(df: pd.DataFrame) -> list:
    records = []

    if df.shape[1] <= 29:
        return records

    for _, row in df.iterrows():
        custom_metrics = str(row.iloc[29]) if pd.notna(row.iloc[29]) else ""
        match = TIMING_PATTERN.search(custom_metrics)

        if not match:
            continue

        conv_id = str(row.iloc[0])
        created_raw = str(row.iloc[2])

        try:
            created_dt = datetime.fromisoformat(
                created_raw.replace("Z[UTC]", "+00:00")
            )
            date_str = created_dt.strftime("%Y-%m-%d")
            time_str = created_dt.strftime("%H:%M:%S")
        except Exception:
            date_str = created_raw[:10]
            time_str = ""

        timing = _parse_timing_string(match.group(1))

        if timing:
            records.append(
                {
                    "conv_id": conv_id,
                    "date": date_str,
                    "time": time_str,
                    "timing": timing,
                }
            )

    return records


def load_default() -> list:
    if not os.path.exists(DEFAULT_CSV):
        return []

    df = pd.read_csv(DEFAULT_CSV, header=0)
    return parse_dataframe(df)


def build_frames(records: list):
    flat_rows = []

    for r in records:
        for api, ms in r["timing"].items():
            flat_rows.append(
                {
                    "conv_id": r["conv_id"],
                    "date": r["date"],
                    "time": r["time"],
                    "api": api,
                    "ms": ms,
                }
            )

    df_flat = pd.DataFrame(flat_rows)

    if df_flat.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )

    df_apis = df_flat[df_flat["api"] != "totalExecutionTime"].copy()

    avg_per_api = (
        df_apis.groupby("api")["ms"]
        .agg(avg_ms="mean", max_ms="max", min_ms="min", count="count")
        .reset_index()
        .sort_values("avg_ms", ascending=False)
    )

    conv_totals = []

    for r in records:
        apis_only = {
            k: v for k, v in r["timing"].items()
            if k != "totalExecutionTime"
        }

        total = r["timing"].get("totalExecutionTime", sum(apis_only.values()))

        if apis_only:
            slowest_name = max(apis_only, key=apis_only.get)
            slowest_ms = apis_only.get(slowest_name, 0)
        else:
            slowest_name = "N/A"
            slowest_ms = 0

        conv_totals.append(
            {
                "conv_id": r["conv_id"],
                "date": r["date"],
                "time": r["time"],
                "total_ms": total,
                "slowest_api": slowest_name,
                "slowest_ms": slowest_ms,
                "num_apis": len(apis_only),
            }
        )

    df_convs = pd.DataFrame(conv_totals).sort_values(["date", "time"])

    heatmap_pivot = df_apis.pivot_table(
        index="api",
        columns="conv_id",
        values="ms",
        aggfunc="mean",
    )

    table_rows = []

    for r in records:
        apis_only = {
            k: v for k, v in r["timing"].items()
            if k != "totalExecutionTime"
        }

        total = r["timing"].get("totalExecutionTime", sum(apis_only.values()))

        slowest = max(apis_only, key=apis_only.get) if apis_only else "N/A"

        row = {
            "Conversation ID": r["conv_id"],
            "Date": r["date"],
            "Time": r["time"],
            "# APIs": len(apis_only),
            "Slowest API": slowest,
            "Slowest (ms)": apis_only.get(slowest, 0),
            "Total Exec (ms)": total,
        }

        for api in sorted(apis_only):
            row[api] = apis_only[api]

        table_rows.append(row)

    df_table = pd.DataFrame(table_rows)

    return df_apis, avg_per_api, df_convs, heatmap_pivot, df_table


def empty_fig(msg="No data"):
    fig = go.Figure()
    fig.update_layout(
        **LAYOUT_BASE,
        annotations=[
            dict(
                text=msg,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(color=COLORS["subtext"], size=16),
            )
        ],
    )
    return fig


def fig_bar_avg(avg_per_api):
    if avg_per_api.empty:
        return empty_fig("No API data")

    colors = [
        COLORS["accent3"] if i == 0 else COLORS["accent1"]
        for i in range(len(avg_per_api))
    ]

    fig = go.Figure(
        go.Bar(
            x=avg_per_api["api"],
            y=avg_per_api["avg_ms"],
            marker_color=colors,
            text=avg_per_api["avg_ms"].round(0).astype(int).astype(str) + " ms",
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Avg: %{y:.0f} ms<br>"
                "Max: %{customdata[0]:.0f} ms<br>"
                "Calls: %{customdata[1]}"
                "<extra></extra>"
            ),
            customdata=avg_per_api[["max_ms", "count"]].values,
        )
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="Average Response Time per API", font=dict(size=16)),
        xaxis_title="API",
        yaxis_title="Avg Response Time (ms)",
        xaxis_tickangle=-35,
        showlegend=False,
    )

    return fig


def fig_scatter(df_convs):
    if df_convs.empty:
        return empty_fig("No conversation data")

    fig = go.Figure()

    for _, row in df_convs.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[f"{row['date']} {row['time']}"],
                y=[row["total_ms"]],
                mode="markers+text",
                marker=dict(
                    size=14,
                    color=(
                        COLORS["accent2"]
                        if row["total_ms"] < 5000
                        else COLORS["accent3"]
                    ),
                    line=dict(width=2, color="white"),
                ),
                text=[row["conv_id"][-6:]],
                textposition="top center",
                textfont=dict(size=9),
                customdata=[row["conv_id"]],
                name=row["conv_id"],
                hovertemplate=(
                    f"<b>{row['conv_id']}</b><br>"
                    f"Date: {row['date']} {row['time']}<br>"
                    f"Total: {row['total_ms']:.0f} ms<br>"
                    f"Slowest: {row['slowest_api']} "
                    f"({row['slowest_ms']:.0f} ms)"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="Total Execution Time per Conversation", font=dict(size=16)),
        xaxis_title="Date & Time",
        yaxis_title="Total Execution Time (ms)",
        xaxis_tickangle=-30,
    )

    return fig


def fig_heatmap(heatmap_pivot):
    if heatmap_pivot.empty:
        return empty_fig("No heatmap data")

    z = heatmap_pivot.values

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[str(c)[-8:] for c in heatmap_pivot.columns],
            y=heatmap_pivot.index.tolist(),
            colorscale=[
                [0.0, "#0f1117"],
                [0.3, "#1a3a5c"],
                [0.6, "#6c63ff"],
                [0.85, "#ffa500"],
                [1.0, "#ff6584"],
            ],
            text=[
                [
                    f"{v:.0f} ms" if not pd.isna(v) else "N/A"
                    for v in row
                ]
                for row in z
            ],
            texttemplate="%{text}",
            textfont=dict(size=9),
            hovertemplate=(
                "API: <b>%{y}</b><br>"
                "Conv: %{x}<br>"
                "Time: %{z:.0f} ms"
                "<extra></extra>"
            ),
            showscale=True,
            colorbar=dict(title="ms", tickfont=dict(color=COLORS["text"])),
        )
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(
            text="API Response Time Heatmap per Conversation",
            font=dict(size=16),
        ),
        xaxis_title="Conversation ID last 8 chars",
        yaxis_title="API Name",
        height=420,
    )

    return fig


def fig_pie(df_convs):
    if df_convs.empty:
        return empty_fig("No slowest API data")

    counts = df_convs["slowest_api"].value_counts().reset_index()
    counts.columns = ["api", "count"]

    fig = go.Figure(
        go.Pie(
            labels=counts["api"],
            values=counts["count"],
            hole=0.55,
            marker=dict(colors=API_COLORS),
            textinfo="label+percent",
            textfont=dict(size=12),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Times slowest: %{value}<br>"
                "%{percent}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(
            text="Which API Was Slowest Most Often?",
            font=dict(size=16),
        ),
        showlegend=True,
        legend=dict(font=dict(color=COLORS["text"])),
    )

    return fig


def fig_stacked(df_apis, df_convs):
    if df_apis.empty or df_convs.empty:
        return empty_fig("No stacked chart data")

    apis_in_data = sorted(df_apis["api"].unique())

    fig = go.Figure()

    for i, api in enumerate(apis_in_data):
        sub = df_apis[df_apis["api"] == api]

        merged = df_convs[["conv_id", "date", "time"]].merge(
            sub[["conv_id", "ms"]],
            on="conv_id",
            how="left",
        )

        merged["label"] = merged["conv_id"].str[-8:] + "<br>" + merged["date"]

        fig.add_trace(
            go.Bar(
                name=api,
                x=merged["label"],
                y=merged["ms"],
                marker_color=API_COLORS[i % len(API_COLORS)],
                hovertemplate=(
                    f"<b>{api}</b><br>"
                    "Conv: %{x}<br>"
                    "Time: %{y:.0f} ms"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(
            text="API Timing Breakdown per Conversation",
            font=dict(size=16),
        ),
        barmode="stack",
        xaxis_title="Conversation",
        yaxis_title="Response Time (ms)",
        legend=dict(
            font=dict(color=COLORS["text"]),
            orientation="h",
            y=-0.25,
        ),
        height=480,
        xaxis_tickangle=-30,
    )

    return fig


def fig_conversation_breakdown(record):
    apis_only = {
        k: v for k, v in record["timing"].items()
        if k != "totalExecutionTime"
    }

    if not apis_only:
        return empty_fig("No API timing data for selected conversation")

    items = sorted(apis_only.items(), key=lambda x: x[1], reverse=True)
    apis = [k for k, _ in items]
    ms_values = [v for _, v in items]

    fig = go.Figure(
        go.Bar(
            x=apis,
            y=ms_values,
            marker_color=[
                API_COLORS[i % len(API_COLORS)]
                for i in range(len(apis))
            ],
            text=[f"{v:.0f} ms" for v in ms_values],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Execution: %{y:.0f} ms<extra></extra>",
        )
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(
            text="API Execution Time for Selected Conversation",
            font=dict(size=16),
        ),
        xaxis_title="API",
        yaxis_title="Execution Time (ms)",
        xaxis_tickangle=-35,
        showlegend=False,
    )

    return fig


def read_uploaded_file(uploaded_file):
    if uploaded_file.name.lower().endswith(("xlsx", "xls")):
        return pd.read_excel(uploaded_file)

    return pd.read_csv(uploaded_file)


def main():
    st.set_page_config(
        page_title="API Timing Dashboard",
        layout="wide",
    )

    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0f1117;
            color: #e0e0e0;
        }
        div[data-testid="stMetric"] {
            background-color: #1a1d27;
            border: 1px solid #2a2d3e;
            border-radius: 12px;
            padding: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("API Timing Analytics")
    st.caption("Deep analysis of API response times across all conversations")

    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file is not None:
        try:
            df = read_uploaded_file(uploaded_file)
            source_label = uploaded_file.name
        except Exception as exc:
            st.error(f"Failed to read uploaded file: {exc}")
            st.stop()
    else:
        if os.path.exists(DEFAULT_CSV):
            df = pd.read_csv(DEFAULT_CSV)
            source_label = "conversations.csv"
        else:
            st.info("Upload a CSV or Excel file to get started.")
            st.stop()

    records = parse_dataframe(df)

    if not records:
        st.error("No 'Api Timing' entries found in the file.")
        st.stop()

    df_apis, avg_per_api, df_convs, heatmap_pivot, df_table = build_frames(records)

    st.success(f"Loaded {len(records)} conversation(s) from {source_label}")

    if avg_per_api.empty or df_convs.empty:
        st.error("Timing data was found, but no API timing rows could be built.")
        st.stop()

    slowest_api = avg_per_api.iloc[0]["api"]
    slowest_avg = avg_per_api.iloc[0]["avg_ms"]
    fastest_api = avg_per_api.iloc[-1]["api"]
    fastest_avg = avg_per_api.iloc[-1]["avg_ms"]
    avg_total = df_convs["total_ms"].mean()
    max_row = df_convs.loc[df_convs["total_ms"].idxmax()]

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Conversations", len(records))
    c2.metric("Slowest API Avg", slowest_api, f"{slowest_avg:.0f} ms")
    c3.metric("Fastest API Avg", fastest_api, f"{fastest_avg:.0f} ms")
    c4.metric("Avg Total Exec", f"{avg_total:.0f} ms")
    c5.metric("Max Exec Conv", max_row["conv_id"][-8:], f"{max_row['total_ms']:.0f} ms")

    tab_overview, tab_drilldown = st.tabs(
        ["Overview", "Conversation Drilldown"]
    )

    with tab_overview:
        left, right = st.columns([2, 1])

        with left:
            st.plotly_chart(fig_bar_avg(avg_per_api), use_container_width=True)

        with right:
            st.plotly_chart(fig_pie(df_convs), use_container_width=True)

        st.plotly_chart(fig_scatter(df_convs), use_container_width=True)
        st.plotly_chart(fig_stacked(df_apis, df_convs), use_container_width=True)
        st.plotly_chart(fig_heatmap(heatmap_pivot), use_container_width=True)

        st.subheader("Detailed Breakdown by Conversation")
        st.dataframe(df_table, use_container_width=True, hide_index=True)

    with tab_drilldown:
        search = st.text_input("Find Conversation ID")

        filtered_records = records
        if search.strip():
            filtered_records = [
                r for r in records
                if search.lower().strip() in r["conv_id"].lower()
            ]

        if not filtered_records:
            st.warning("No conversation IDs match your search.")
            st.stop()

        selected_conv_id = st.selectbox(
            "Select conversation ID",
            [r["conv_id"] for r in filtered_records],
        )

        selected = next(
            r for r in records
            if r["conv_id"] == selected_conv_id
        )

        total_ms = selected["timing"].get(
            "totalExecutionTime",
            sum(
                v for k, v in selected["timing"].items()
                if k != "totalExecutionTime"
            ),
        )

        st.markdown(f"**Conversation ID:** `{selected_conv_id}`")
        st.markdown(
            f"**Date:** {selected.get('date', '')} "
            f"{selected.get('time', '')} &nbsp;&nbsp; "
            f"**Total:** {total_ms:.0f} ms",
            unsafe_allow_html=True,
        )

        st.plotly_chart(
            fig_conversation_breakdown(selected),
            use_container_width=True,
        )

        apis_only = {
            k: v for k, v in selected["timing"].items()
            if k != "totalExecutionTime"
        }

        drill_df = pd.DataFrame(
            sorted(apis_only.items(), key=lambda x: x[1], reverse=True),
            columns=["API", "Execution Time (ms)"],
        )

        st.subheader("Selected Conversation API Timing")
        st.dataframe(drill_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()