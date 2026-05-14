#!/usr/bin/env python3
"""
API Timing Dashboard
Upload any CSV or Excel conversation export and get an instant visual
breakdown of API response times. Runs at http://localhost:8050
"""

import base64
import io
import re
import sys
import os
from datetime import datetime

import dash
from dash import dcc, html, dash_table, Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ── Constants ─────────────────────────────────────────────────────────────────

TIMING_PATTERN = re.compile(r"Api Timing\s*:?=\s*\[([^\]]+)\]", re.IGNORECASE)
DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "conversations.csv")

COLORS = {
    "bg":      "#0f1117",
    "card":    "#1a1d27",
    "border":  "#2a2d3e",
    "accent1": "#6c63ff",
    "accent2": "#00d4aa",
    "accent3": "#ff6584",
    "accent4": "#ffa500",
    "text":    "#e0e0e0",
    "subtext": "#8888aa",
    "upload":  "#1e2235",
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

# ── Parsing helpers ───────────────────────────────────────────────────────────


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
    """Extract Api Timing records from a dataframe (col index 29 = Custom Metrics)."""
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
            records.append({
                "conv_id": conv_id,
                "date": date_str,
                "time": time_str,
                "timing": timing,
            })
    return records


def parse_file_content(content: str, filename: str) -> tuple[list, str]:
    """Decode a base64 upload payload and return (records, error_msg)."""
    try:
        _header, encoded = content.split(",", 1)
        decoded = base64.b64decode(encoded)
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(decoded), header=0)
        else:
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")), header=0)
        records = parse_dataframe(df)
        if not records:
            return [], "No 'Api Timing' entries found in the uploaded file."
        return records, ""
    except Exception as exc:
        return [], f"Failed to parse file: {exc}"


def load_default() -> list:
    if not os.path.exists(DEFAULT_CSV):
        return []
    df = pd.read_csv(DEFAULT_CSV, header=0)
    return parse_dataframe(df)


# ── DataFrame builders ────────────────────────────────────────────────────────


def build_frames(records: list):
    flat_rows = []
    for r in records:
        for api, ms in r["timing"].items():
            flat_rows.append({
                "conv_id": r["conv_id"],
                "date":    r["date"],
                "time":    r["time"],
                "api":     api,
                "ms":      ms,
            })

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
        slowest = max(apis_only, key=apis_only.get) if apis_only else ("N/A", 0)
        slowest_name = slowest if isinstance(slowest, str) else slowest[0]
        conv_totals.append({
            "conv_id":    r["conv_id"],
            "date":       r["date"],
            "time":       r["time"],
            "total_ms":   total,
            "slowest_api": slowest_name,
            "slowest_ms":  apis_only.get(slowest_name, 0),
            "num_apis":   len(apis_only),
        })

    df_convs = pd.DataFrame(conv_totals).sort_values(["date", "time"])

    heatmap_pivot = df_apis.pivot_table(
        index="api", columns="conv_id", values="ms", aggfunc="mean"
    )

    table_rows = []
    for r in records:
        apis_only = {k: v for k, v in r["timing"].items() if k != "totalExecutionTime"}
        total = r["timing"].get("totalExecutionTime", sum(r["timing"].values()))
        slowest = max(apis_only, key=apis_only.get) if apis_only else "N/A"
        row = {
            "Conversation ID": r["conv_id"],
            "Date":            r["date"],
            "Time":            r["time"],
            "# APIs":          len(apis_only),
            "Slowest API":     slowest,
            "Slowest (ms)":    apis_only.get(slowest, 0),
            "Total Exec (ms)": total,
        }
        for api in sorted(apis_only):
            row[api] = apis_only[api]
        table_rows.append(row)

    df_table = pd.DataFrame(table_rows)

    return df_apis, avg_per_api, df_convs, heatmap_pivot, df_table


# ── Chart builders ────────────────────────────────────────────────────────────


def fig_bar_avg(avg_per_api):
    colors = [COLORS["accent3"] if i == 0 else COLORS["accent1"]
              for i in range(len(avg_per_api))]
    fig = go.Figure(go.Bar(
        x=avg_per_api["api"],
        y=avg_per_api["avg_ms"],
        marker_color=colors,
        text=avg_per_api["avg_ms"].round(0).astype(int).astype(str) + " ms",
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Avg: %{y:.0f} ms<br>Max: %{customdata[0]:.0f} ms<br>Calls: %{customdata[1]}<extra></extra>",
        customdata=avg_per_api[["max_ms", "count"]].values,
    ))
    fig.update_layout(**LAYOUT_BASE,
                      title=dict(text="Average Response Time per API", font=dict(size=16)),
                      xaxis_title="API", yaxis_title="Avg Response Time (ms)",
                      xaxis_tickangle=-35, showlegend=False)
    return fig


def fig_scatter(df_convs):
    fig = go.Figure()
    for _, row in df_convs.iterrows():
        fig.add_trace(go.Scatter(
            x=[f"{row['date']} {row['time']}"],
            y=[row["total_ms"]],
            mode="markers+text",
            marker=dict(size=14,
                        color=COLORS["accent2"] if row["total_ms"] < 5000 else COLORS["accent3"],
                        line=dict(width=2, color="white")),
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
        ))
    fig.update_layout(**LAYOUT_BASE,
                      title=dict(text="Total Execution Time per Conversation", font=dict(size=16)),
                      xaxis_title="Date & Time", yaxis_title="Total Execution Time (ms)",
                      xaxis_tickangle=-30)
    return fig


def fig_heatmap(heatmap_pivot):
    z = heatmap_pivot.values
    fig = go.Figure(go.Heatmap(
        z=z,
        x=[c[-8:] for c in heatmap_pivot.columns],
        y=heatmap_pivot.index.tolist(),
        colorscale=[[0.0,"#0f1117"],[0.3,"#1a3a5c"],[0.6,"#6c63ff"],[0.85,"#ffa500"],[1.0,"#ff6584"]],
        text=[[f"{v:.0f} ms" if not pd.isna(v) else "N/A" for v in row] for row in z],
        texttemplate="%{text}",
        textfont=dict(size=9),
        hovertemplate="API: <b>%{y}</b><br>Conv: %{x}<br>Time: %{z:.0f} ms<extra></extra>",
        showscale=True,
        colorbar=dict(title="ms", tickfont=dict(color=COLORS["text"])),
    ))
    fig.update_layout(**LAYOUT_BASE,
                      title=dict(text="API Response Time Heatmap (per Conversation)", font=dict(size=16)),
                      xaxis_title="Conversation ID (last 8 chars)",
                      yaxis_title="API Name", height=420)
    return fig


def fig_pie(df_convs):
    counts = df_convs["slowest_api"].value_counts().reset_index()
    counts.columns = ["api", "count"]
    fig = go.Figure(go.Pie(
        labels=counts["api"], values=counts["count"], hole=0.55,
        marker=dict(colors=API_COLORS),
        textinfo="label+percent", textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>Times slowest: %{value}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE,
                      title=dict(text="Which API Was Slowest Most Often?", font=dict(size=16)),
                      showlegend=True, legend=dict(font=dict(color=COLORS["text"])))
    return fig


def fig_stacked(df_apis, df_convs):
    apis_in_data = sorted(df_apis["api"].unique())
    fig = go.Figure()
    for i, api in enumerate(apis_in_data):
        sub = df_apis[df_apis["api"] == api]
        merged = df_convs[["conv_id","date","time"]].merge(sub[["conv_id","ms"]], on="conv_id", how="left")
        merged["label"] = merged["conv_id"].str[-8:] + "\n" + merged["date"]
        fig.add_trace(go.Bar(
            name=api, x=merged["label"], y=merged["ms"],
            marker_color=API_COLORS[i % len(API_COLORS)],
            hovertemplate=f"<b>{api}</b><br>Conv: %{{x}}<br>Time: %{{y:.0f}} ms<extra></extra>",
        ))
    fig.update_layout(**LAYOUT_BASE,
                      title=dict(text="API Timing Breakdown per Conversation (Stacked)", font=dict(size=16)),
                      barmode="stack",
                      xaxis_title="Conversation (last 8 chars + date)",
                      yaxis_title="Response Time (ms)",
                      legend=dict(font=dict(color=COLORS["text"]), orientation="h", y=-0.25),
                      height=480, xaxis_tickangle=-30)
    return fig


# ── UI helpers ────────────────────────────────────────────────────────────────


def stat_card(title, value, sub="", color=COLORS["accent1"], card_id=None):
    kwargs = {"id": card_id} if card_id else {}
    return html.Div([
        html.P(title, style={"color": COLORS["subtext"], "fontSize": "12px",
                              "margin": "0 0 4px 0", "textTransform": "uppercase",
                              "letterSpacing": "1px"}),
        html.H3(value, style={"color": color, "margin": "0", "fontSize": "26px", "fontWeight": "700"}),
        html.P(sub,  style={"color": COLORS["subtext"], "fontSize": "11px", "margin": "4px 0 0 0"}),
    ], style={
        "background": COLORS["card"],
        "border": f"1px solid {COLORS['border']}",
        "borderLeft": f"4px solid {color}",
        "borderRadius": "10px",
        "padding": "18px 22px",
        "flex": "1",
        "minWidth": "190px",
    }, **kwargs)


def empty_fig(msg="No data"):
    fig = go.Figure()
    fig.update_layout(**LAYOUT_BASE,
                      annotations=[dict(text=msg, xref="paper", yref="paper",
                                        x=0.5, y=0.5, showarrow=False,
                                        font=dict(color=COLORS["subtext"], size=16))])
    return fig


# ── App layout ────────────────────────────────────────────────────────────────

app = dash.Dash(__name__, title="API Timing Dashboard")
app.layout = html.Div(
    id="root",
    style={"background": COLORS["bg"], "minHeight": "100vh",
           "fontFamily": "Inter, Segoe UI, sans-serif",
           "color": COLORS["text"], "padding": "24px 32px"},
    children=[

        # Hidden store for parsed records (JSON)
        dcc.Store(id="store-records"),

        # ── Header ──────────────────────────────────────────────────────────
        html.Div([
            html.Div([
                html.H1("API Timing Analytics",
                        style={"margin": "0", "fontSize": "28px",
                               "fontWeight": "800", "color": "white"}),
                html.P("Deep analysis of API response times across all conversations",
                       style={"color": COLORS["subtext"], "margin": "4px 0 0 0", "fontSize": "14px"}),
            ]),
            html.Div(id="header-meta", style={"textAlign": "right"}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "flex-start", "marginBottom": "24px"}),

        # ── Upload zone ──────────────────────────────────────────────────────
        html.Div([
            dcc.Upload(
                id="upload-data",
                children=html.Div([
                    html.Div("⬆", style={"fontSize": "32px", "lineHeight": "1", "marginBottom": "8px"}),
                    html.Div([
                        html.Span("Drop a CSV or Excel file here", style={"color": COLORS["text"], "fontWeight": "600"}),
                        html.Span("  or  ", style={"color": COLORS["subtext"]}),
                        html.Span("click to browse", style={"color": COLORS["accent1"],
                                                              "textDecoration": "underline",
                                                              "cursor": "pointer"}),
                    ]),
                    html.Div("Supports .csv · .xlsx · .xls",
                             style={"color": COLORS["subtext"], "fontSize": "12px", "marginTop": "6px"}),
                ], style={"textAlign": "center"}),
                style={
                    "background": COLORS["upload"],
                    "border": f"2px dashed {COLORS['accent1']}",
                    "borderRadius": "12px",
                    "padding": "28px",
                    "cursor": "pointer",
                    "transition": "border-color .2s",
                },
                multiple=False,
            ),
            html.Div(id="upload-status",
                     style={"marginTop": "10px", "fontSize": "13px", "textAlign": "center"}),
        ], style={"marginBottom": "28px"}),

        # ── Summary cards ────────────────────────────────────────────────────
        html.Div(id="summary-cards",
                 style={"display": "flex", "gap": "16px", "flexWrap": "wrap",
                        "marginBottom": "28px"}),

        # ── Row 1: Bar avg + Pie ─────────────────────────────────────────────
        html.Div([
            html.Div(dcc.Graph(id="chart-bar-avg", config={"displayModeBar": False}),
                     style={"flex": "2", "background": COLORS["card"], "borderRadius": "12px",
                            "padding": "16px", "border": f"1px solid {COLORS['border']}"}),
            html.Div(dcc.Graph(id="chart-pie", config={"displayModeBar": False}),
                     style={"flex": "1", "background": COLORS["card"], "borderRadius": "12px",
                            "padding": "16px", "border": f"1px solid {COLORS['border']}"}),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "20px"}),

        # ── Row 2: Scatter ───────────────────────────────────────────────────
        html.Div(
            dcc.Graph(id="chart-scatter", config={"displayModeBar": False}),
            style={"background": COLORS["card"], "borderRadius": "12px",
                   "padding": "16px", "border": f"1px solid {COLORS['border']}",
                   "marginBottom": "20px"},
        ),

        # ── Row 3: Stacked bar ───────────────────────────────────────────────
        html.Div(
            dcc.Graph(id="chart-stacked", config={"displayModeBar": False}),
            style={"background": COLORS["card"], "borderRadius": "12px",
                   "padding": "16px", "border": f"1px solid {COLORS['border']}",
                   "marginBottom": "20px"},
        ),

        # ── Row 4: Heatmap ───────────────────────────────────────────────────
        html.Div(
            dcc.Graph(id="chart-heatmap", config={"displayModeBar": False}),
            style={"background": COLORS["card"], "borderRadius": "12px",
                   "padding": "16px", "border": f"1px solid {COLORS['border']}",
                   "marginBottom": "20px"},
        ),

        # ── Row 5: Table ─────────────────────────────────────────────────────
        html.Div([
            html.H3("Detailed Breakdown by Conversation",
                    style={"color": "white", "marginTop": "0", "fontSize": "16px"}),
            html.P("All API response times in milliseconds · Sortable & filterable",
                   style={"color": COLORS["subtext"], "fontSize": "12px", "margin": "0 0 14px 0"}),
            dash_table.DataTable(
                id="detail-table",
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "#252836",
                    "color": COLORS["accent1"],
                    "fontWeight": "700",
                    "fontSize": "12px",
                    "border": f"1px solid {COLORS['border']}",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.5px",
                },
                style_cell={
                    "backgroundColor": COLORS["card"],
                    "color": COLORS["text"],
                    "border": f"1px solid {COLORS['border']}",
                    "fontSize": "12px",
                    "padding": "10px 12px",
                    "textAlign": "center",
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#1e2130"},
                    {"if": {"column_id": "Slowest API"},
                     "color": COLORS["accent3"], "fontWeight": "600"},
                    {"if": {"column_id": "Total Exec (ms)"},
                     "color": COLORS["accent4"], "fontWeight": "600"},
                    {"if": {"column_id": "Conversation ID"},
                     "color": COLORS["accent2"], "fontWeight": "600", "textAlign": "left"},
                ],
                sort_action="native",
                filter_action="native",
                page_size=20,
            ),
        ], style={"background": COLORS["card"], "borderRadius": "12px",
                  "padding": "20px", "border": f"1px solid {COLORS['border']}"}),

        # ── Footer ───────────────────────────────────────────────────────────
        html.Div(
            html.P("API Timing Dashboard · All times in milliseconds",
                   style={"color": COLORS["subtext"], "fontSize": "11px",
                          "textAlign": "center", "margin": "0"}),
            style={"marginTop": "28px", "paddingTop": "16px",
                   "borderTop": f"1px solid {COLORS['border']}"},
        ),
    ],
)


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("store-records", "data"),
    Output("upload-status", "children"),
    Output("upload-status", "style"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True,
)
def on_upload(contents, filename):
    if contents is None:
        return dash.no_update, dash.no_update, dash.no_update

    records, err = parse_file_content(contents, filename)
    if err:
        return (
            dash.no_update,
            f"✗  {err}",
            {"marginTop": "10px", "fontSize": "13px", "textAlign": "center",
             "color": COLORS["accent3"]},
        )

    import json
    serialisable = [
        {"conv_id": r["conv_id"], "date": r["date"],
         "time": r["time"], "timing": r["timing"]}
        for r in records
    ]
    return (
        serialisable,
        f"✓  Loaded {filename}  ·  {len(records)} conversation(s) with Api Timing data",
        {"marginTop": "10px", "fontSize": "13px", "textAlign": "center",
         "color": COLORS["accent2"]},
    )


@app.callback(
    Output("header-meta", "children"),
    Output("summary-cards", "children"),
    Output("chart-bar-avg", "figure"),
    Output("chart-pie", "figure"),
    Output("chart-scatter", "figure"),
    Output("chart-stacked", "figure"),
    Output("chart-heatmap", "figure"),
    Output("detail-table", "data"),
    Output("detail-table", "columns"),
    Input("store-records", "data"),
)
def refresh_dashboard(store_data):
    # Load from store if available, otherwise fall back to default CSV
    if store_data:
        records = store_data
        source_label = f"{len(records)} conversation(s) · uploaded file"
    else:
        records = load_default()
        source_label = f"{len(records)} conversation(s) · default file"

    if not records:
        blank = empty_fig("Upload a file to get started")
        no_cards = [html.P("No data loaded yet.",
                           style={"color": COLORS["subtext"], "fontSize": "13px"})]
        return (
            html.Span("No data", style={"color": COLORS["subtext"], "fontSize": "12px"}),
            no_cards,
            blank, blank, blank, blank, blank,
            [], [],
        )

    df_apis, avg_per_api, df_convs, heatmap_pivot, df_table = build_frames(records)

    # Stats
    slowest_api   = avg_per_api.iloc[0]["api"]   if not avg_per_api.empty else "N/A"
    slowest_avg   = avg_per_api.iloc[0]["avg_ms"] if not avg_per_api.empty else 0
    fastest_api   = avg_per_api.iloc[-1]["api"]   if not avg_per_api.empty else "N/A"
    fastest_avg   = avg_per_api.iloc[-1]["avg_ms"] if not avg_per_api.empty else 0
    avg_total     = df_convs["total_ms"].mean()
    max_row       = df_convs.loc[df_convs["total_ms"].idxmax()]

    header_meta = html.Div([
        html.Span("● LIVE DATA",
                  style={"color": COLORS["accent2"], "fontSize": "12px",
                         "fontWeight": "600", "letterSpacing": "1px"}),
        html.Br(),
        html.Span(source_label,
                  style={"color": COLORS["subtext"], "fontSize": "11px"}),
    ], style={"textAlign": "right"})

    cards = [
        stat_card("Conversations with Timing", str(len(records)),
                  f"{df_convs['date'].nunique()} date(s)", COLORS["accent1"]),
        stat_card("Slowest API (avg)", slowest_api,
                  f"{slowest_avg:.0f} ms avg", COLORS["accent3"]),
        stat_card("Fastest API (avg)", fastest_api,
                  f"{fastest_avg:.0f} ms avg", COLORS["accent2"]),
        stat_card("Avg Total Exec Time", f"{avg_total:.0f} ms",
                  "across all conversations", COLORS["accent4"]),
        stat_card("Max Exec Time Conv", max_row["conv_id"][-10:],
                  f"{max_row['total_ms']:.0f} ms on {max_row['date']}", COLORS["accent3"]),
    ]

    table_data    = df_table.to_dict("records")
    table_columns = [{"name": c, "id": c} for c in df_table.columns]

    return (
        header_meta,
        cards,
        fig_bar_avg(avg_per_api),
        fig_pie(df_convs),
        fig_scatter(df_convs),
        fig_stacked(df_apis, df_convs),
        fig_heatmap(heatmap_pivot),
        table_data,
        table_columns,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # port = int(sys.argv[1]) if len(sys.argv) > 1 else 8050
    port = 8501
    print(f"\n  API Timing Dashboard  →  http://localhost:{port}\n")
    app.run(debug=False, host="0.0.0.0", port=port)
