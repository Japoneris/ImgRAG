"""Bokeh server application for interactive embedding visualization.

Run with: bokeh serve --show this_file.py
Or programmatically via run_server().
"""

import base64
import subprocess
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

from bokeh.events import Tap
from bokeh.io import curdoc
from bokeh.layouts import column
from bokeh.models import (
    ColumnDataSource,
    CustomJS,
    HoverTool,
    Slider,
    TapTool,
    Div,
)
from bokeh.plotting import figure

from .embedding_analyzer import load_analysis


def _human_size(nbytes: int | None) -> str:
    """Format byte count as human-readable string."""
    if nbytes is None:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.0f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def generate_thumbnails(
    points: list[dict],
    max_size: int = 80,
) -> dict[str, str]:
    """Generate base64-encoded thumbnails for images.

    Args:
        points: List of point dicts with 'hash' and 'filepath' keys
        max_size: Maximum thumbnail dimension in pixels

    Returns:
        Dictionary mapping hashes to base64 data-URI strings
    """
    thumbnails = {}
    for pt in points:
        fp = pt.get("filepath")
        h = pt["hash"]
        if not fp or not Path(fp).exists():
            thumbnails[h] = ""
            continue
        try:
            with Image.open(fp) as img:
                img.thumbnail((max_size, max_size))
                buf = BytesIO()
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                thumbnails[h] = f"data:image/png;base64,{b64}"
        except Exception:
            thumbnails[h] = ""
    return thumbnails


def create_visualization(data_path: str | Path):
    """Build a Bokeh document from analysis JSON.

    Args:
        data_path: Path to the analysis JSON file

    Returns:
        Bokeh document components (plot, header div)
    """
    data = load_analysis(data_path)
    points = data["points"]

    if not points:
        return column(Div(text="<h2>No data points to visualize.</h2>"))

    # Generate thumbnails
    print(f"Generating thumbnails for {len(points)} images...")
    thumbs = generate_thumbnails(points)

    # Build data source
    source = ColumnDataSource(data=dict(
        x=[pt["x"] for pt in points],
        y=[pt["y"] for pt in points],
        hash=[pt["hash"] for pt in points],
        filepath=[pt.get("filepath") or "N/A" for pt in points],
        filename=[Path(pt.get("filepath") or "N/A").name for pt in points],
        folder=[str(Path(pt.get("filepath") or "/").parent) for pt in points],
        width_px=[str(pt.get("width") or "?") for pt in points],
        height_px=[str(pt.get("height") or "?") for pt in points],
        size_hr=[_human_size(pt.get("size")) for pt in points],
        thumbnail=[thumbs.get(pt["hash"], "") for pt in points],
    ))

    # Create figure
    title = f"Embedding Map — {data['model']} ({data['method'].upper()}, {data['count']} images)"
    p = figure(
        title=title,
        width=1200,
        height=800,
        tools="pan,wheel_zoom,box_zoom,reset,tap",
        active_scroll="wheel_zoom",
    )

    # Scatter plot
    renderer = p.scatter(
        "x", "y",
        source=source,
        size=8,
        alpha=0.5,
    )

    # Slider to control point size
    size_slider = Slider(start=2, end=30, value=8, step=1, title="Point size")
    size_slider.js_on_change("value", CustomJS(
        args=dict(renderer=renderer),
        code="renderer.glyph.size = cb_obj.value;",
    ))

    # Hide grid and axes, keep border
    p.xgrid.visible = False
    p.ygrid.visible = False
    p.xaxis.visible = False
    p.yaxis.visible = False

    # Hover tooltip with thumbnail
    hover = HoverTool(tooltips="""
        <div style="max-width:350px">
            <div><img src="@thumbnail" style="max-width:160px; max-height:160px;"></div>
            <div style="margin-top:4px">
                <b>@filename</b><br>
                <span style="font-size:11px; color:#666">@folder</span><br>
                <span style="font-size:11px">@{width_px}x@{height_px} — @size_hr</span>
            </div>
        </div>
    """)
    p.add_tools(hover)

    header = Div(
        text=f"<h2>Embedding Analysis</h2>"
             f"<p>Model: <b>{data['model']}</b> | "
             f"Method: <b>{data['method'].upper()}</b> | "
             f"Images: <b>{data['count']}</b></p>"
             f"<p><i>Click on a point to open its folder.</i></p>",
    )

    return p, source, header, size_slider


def setup_tap_callback(source):
    """Register a server-side tap callback to open folders.

    Only works when running as a Bokeh server app.
    """
    def on_tap(event):
        # Find the nearest point
        indices = source.selected.indices
        if not indices:
            return
        idx = indices[0]
        folder = source.data["folder"][idx]
        if folder and folder != "/" and Path(folder).is_dir():
            try:
                if sys.platform == "linux":
                    subprocess.Popen(["xdg-open", folder])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder])
                else:
                    subprocess.Popen(["explorer", folder])
            except Exception as e:
                print(f"Could not open folder: {e}")

    source.selected.on_change("indices", lambda attr, old, new: on_tap(None))


def run_server(data_path: str | Path, port: int = 5006):
    """Launch a Bokeh server with the visualization.

    Args:
        data_path: Path to the analysis JSON file
        port: Port number for the server
    """
    from bokeh.server.server import Server
    from bokeh.application import Application
    from bokeh.application.handlers.function import FunctionHandler

    def modify_doc(doc):
        p, source, header, size_slider = create_visualization(data_path)
        setup_tap_callback(source)
        doc.add_root(column(header, size_slider, p))
        doc.title = "Embedding Visualization"

    app = Application(FunctionHandler(modify_doc))
    server = Server({"/": app}, port=port)
    server.start()

    print(f"Bokeh server running at http://localhost:{port}/")
    print("Press Ctrl+C to stop.")

    server.io_loop.add_callback(server.show, "/")
    server.io_loop.start()
