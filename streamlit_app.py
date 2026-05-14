#!/usr/bin/env python3
"""Streamlit dashboard for API timing analytics from conversation export files."""

from __future__ import annotations

import io
import os
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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


def _parse_timing_string(timing_str: str) -> dict[str, float]:
    timing: dict[str, float] = {}
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


def parse_dataframe(df: pd.DataFrame) -> list[dict]:
    records: list[dict] = []
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
            created_dt = datetime.fromisoformat(created_raw.replace("Z[UTC]", "+00:00"))
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


def parse_uploaded_file(uploaded_file) -> tuple[list[dict], str]:
    try:
        filename = uploaded_file.name
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("xlsx", "xls"):
            df = pd.read_excel(uploaded_file, header=0)
        else:
            df = pd.read_csv(uploaded_file, header=0)

        records = parse_dataframe(df)
        if not records:
            return [], "No 'Api Timing' entries found in the uploaded file."
        return records, ""
    except Exception as exc:
        return [], f"Failed to parse file: {exc}"


def load_default() -> list[dict]:
    if not os.path.exists(DEFAULT_CSV):
        return []
    df = pd.read_csv(DEFAULT_CSV, header=0)
    return parse_dataframe(df)


def build_frames(records: list[dict]):
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
    df_apis = df_flat[df_flat["api"] != "totalExecutionTime"].copy()

    avg_per_api = (
        df_apis.groupby("api")["ms"]
        .agg(avg_ms="mean", max_ms="max", min_ms="min", count="count")
        .reset_index()
        .sort_values("avg_ms", ascending=False)
    )

    conv_totals = []
    for r in records:
        apis_only = {k: v for k, v in r["timing"].items() if k != "totalExecutionTime"}
        total = r["timing"].get("totalExecutionTime", sum(r["timing"].values()))
        slowest = max(apis_only, key=apis_only.get) if apis_only else "N/A"
        conv_totals.append(
            {
                "conv_id": r["conv_id"],
                "date": r["date"],
                "time": r["time"],
                "total_ms": total,
                "slowest_api": slowest,
                "slowest_ms": apis_only.get(slowest, 0),
                "num_apis": len(apis_only),
            }
        )

    df_convs = pd.DataFrame(conv_totals).sort_values(["date", "time"])
    heatmap_pivot = df_apis.pivot_table(index="api", columns="conv_id", values="ms", aggfunc="mean")

    table_rows = []
    for r in records:
        apis_only = {k: v for k, v in r["timing"].items() if k != "totalExecutionTime"}
        total = r["timing"].get("totalExecutionTime", sum(r["timing"].values()))
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


def fig_bar_avg(avg_per_api: pd.DataFrame):
    colors = [COLORS["accent3"] if i == 0 else COLORS["accent1"] for i in range(len(avg_per_api))]
    fig = go.Figure(
        go.Bar(
            x=avg_per_api["api"],
            y=avg_per_api["avg_ms"],
            marker_color=colors,
            text=avg_per_api["avg_ms"].round(0).astype(int).astype(str) + " ms",
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Avg: %{y:.0f} ms<br>Max: %{customdata[0]:.0f} ms<br>Calls: %{customdata[1]}<extra></extra>",
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


def fig_scatter(df_convs: pd.DataFrame):
    fig = go.Figure()
    for _, row in df_convs.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[f"{row['date']} {row['time']}"],
                y=[row["total_ms"]],
                mode="markers+text",
                marker=dict(
                    size=14,
                    color=COLORS["accent2"] if row["total_ms"] < 5000 else COLORS["accent3"],
                    line=dict(width=2, color="white"),
                ),
                text=[row["conv_id"][-6:]],
                textposition="top center",
                textfont=dict(size=9),
                name=row["conv_id"],
                hovertemplate=(
                    f"<b>{row['conv_id']}</b><br>"
                    f"Date: {row['date']} {row['time']}<br>"
                    f"Total: {row['total_ms']:.0f} ms<br>"
                    f"Slowest: {row['slowest_api']} ({row['slowest_ms']:.0f} ms)<extra></extra>"
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


def fig_heatmap(heatmap_pivot: pd.DataFrame):
    z = heatmap_pivot.values
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[c[-8:] for c in heatmap_pivot.columns],
            y=heatmap_pivot.index.tolist(),
            colorscale=[
                [0.0, "#0f1117"],
                [0.3, "#1a3a5c"],
                [0.6, "#6c63ff"],
                [0.85, "#ffa500"],
                [1.0, "#ff6584"],
            ],
            text=[[f"{v:.0f} ms" if not pd.isna(v) else "N/A" for v in row] for row in z],
            texttemplate="%{text}",
            textfont=dict(size=9),
            hovertemplate="API: <b>%{y}</b><br>Conv: %{x}<br>Time: %{z:.0f} ms<extra></extra>",
            showscale=True,
            colorbar=dict(title="ms", tickfont=dict(color=COLORS["text"])),
        )
    )
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="API Response Time Heatmap (per Conversation)", font=dict(size=16)),
        xaxis_title="Conversation ID (last 8 chars)",
        yaxis_title="API Name",
        height=420,
    )
    return fig


def fig_pie(df_convs: pd.DataFrame):
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
            hovertemplate="<b>%{label}</b><br>Times slowest: %{value}<br>%{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="Which API Was Slowest Most Often?", font=dict(size=16)),
        showlegend=True,
        legend=dict(font=dict(color=COLORS["text"])),
    )
    return fig


def fig_stacked(df_apis: pd.DataFrame, df_convs: pd.DataFrame):
    apis_in_data = sorted(df_apis["api"].unique())
    fig = go.Figure()
    for i, api in enumerate(apis_in_data):
        sub = df_apis[df_apis["api"] == api]
        merged = df_convs[["conv_id", "date", "time"]].merge(sub[["conv_id", "ms"]], on="conv_id", how="left")
        merged["label"] = merged["conv_id"].str[-8:] + "\n" + merged["date"]
        fig.add_trace(
            go.Bar(
                name=api,
                x=merged["label"],
                y=merged["ms"],
                marker_color=API_COLORS[i % len(API_COLORS)],
                hovertemplate=f"<b>{api}</b><br>Conv: %{{x}}<br>Time: %{{y:.0f}} ms<extra></extra>",
            )
        )

    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="API Timing Breakdown per Conversation (Stacked)", font=dict(size=16)),
        barmode="stack",
        xaxis_title="Conversation (last 8 chars + date)",
        yaxis_title="Response Time (ms)",
        legend=dict(font=dict(color=COLORS["text"]), orientation="h", y=-0.25),
        height=480,
        xaxis_tickangle=-30,
    )
    return fig


def render():
    st.set_page_config(page_title="API Timing Dashboard", page_icon="📊", layout="wide")

    st.markdown(
        """
        <style>
        .stApp { background: #0f1117; color: #e0e0e0; }
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        .metric-card {
            border: 1px solid #2a2d3e;
            border-left: 4px solid #6c63ff;
            border-radius: 10px;
            background: #1a1d27;
            padding: 12px 14px;
            margin-bottom: 0.5rem;
        }
        .metric-title { color: #8888aa; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
        .metric-value { color: #e0e0e0; font-size: 24px; font-weight: 700; margin-top: 4px; }
        .metric-sub { color: #8888aa; font-size: 11px; margin-top: 4px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("API Timing Analytics")
    st.caption("Deep analysis of API response times across all conversations")

    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

    if uploaded_file is not None:
        records, err = parse_uploaded_file(uploaded_file)
        source_label = f"{uploaded_file.name} ({len(records)} conversation(s))"
        if err:
            st.error(err)
            return
    else:
        records = load_default()
        source_label = f"default file ({len(records)} conversation(s))"

    if not records:
        st.warning("No Api Timing records found. Upload a valid export file with the Custom Metrics column.")
        return

    st.caption(f"Data source: {source_label}")

    df_apis, avg_per_api, df_convs, heatmap_pivot, df_table = build_frames(records)

    slowest_api = avg_per_api.iloc[0]["api"] if not avg_per_api.empty else "N/A"
    slowest_avg = avg_per_api.iloc[0]["avg_ms"] if not avg_per_api.empty else 0
    fastest_api = avg_per_api.iloc[-1]["api"] if not avg_per_api.empty else "N/A"
    fastest_avg = avg_per_api.iloc[-1]["avg_ms"] if not avg_per_api.empty else 0
    avg_total = df_convs["total_ms"].mean()
    max_row = df_convs.loc[df_convs["total_ms"].idxmax()]

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Conversations with Timing</div><div class="metric-value">{len(records)}</div><div class="metric-sub">{df_convs["date"].nunique()} date(s)</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-card" style="border-left-color:{COLORS["accent3"]};"><div class="metric-title">Slowest API (avg)</div><div class="metric-value">{slowest_api}</div><div class="metric-sub">{slowest_avg:.0f} ms avg</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-card" style="border-left-color:{COLORS["accent2"]};"><div class="metric-title">Fastest API (avg)</div><div class="metric-value">{fastest_api}</div><div class="metric-sub">{fastest_avg:.0f} ms avg</div></div>',
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f'<div class="metric-card" style="border-left-color:{COLORS["accent4"]};"><div class="metric-title">Avg Total Exec Time</div><div class="metric-value">{avg_total:.0f} ms</div><div class="metric-sub">across all conversations</div></div>',
            unsafe_allow_html=True,
        )
    with m5:
        st.markdown(
            f'<div class="metric-card" style="border-left-color:{COLORS["accent3"]};"><div class="metric-title">Max Exec Time Conv</div><div class="metric-value">{str(max_row["conv_id"])[-10:]}</div><div class="metric-sub">{max_row["total_ms"]:.0f} ms on {max_row["date"]}</div></div>',
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns([2, 1])
    with c1:
        st.plotly_chart(fig_bar_avg(avg_per_api), use_container_width=True)
    with c2:
        st.plotly_chart(fig_pie(df_convs), use_container_width=True)

    st.plotly_chart(fig_scatter(df_convs), use_container_width=True)
    st.plotly_chart(fig_stacked(df_apis, df_convs), use_container_width=True)
    st.plotly_chart(fig_heatmap(heatmap_pivot), use_container_width=True)

    st.subheader("Detailed Breakdown by Conversation")
    st.caption("All API response times in milliseconds")
    st.dataframe(df_table, use_container_width=True, hide_index=True)

    csv_bytes = df_table.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download detailed table as CSV",
        data=csv_bytes,
        file_name="api_timing_breakdown.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    render()