"""Standalone HTML viewer for embedding analysis (no server required).

Generates a self-contained HTML file with embedded thumbnails.
"""

from pathlib import Path

from bokeh.embed import file_html
from bokeh.layouts import column
from bokeh.models import (
    ColumnDataSource,
    CustomJS,
    Div,
    HoverTool,
    Slider,
    TapTool,
)
from bokeh.plotting import figure
from bokeh.resources import CDN

from .embedding_analyzer import load_analysis
from .visualizer import _human_size, generate_thumbnails


def generate_static_html(data_path: str | Path, output_path: str | Path) -> None:
    """Generate a standalone HTML file for the analysis.

    Args:
        data_path: Path to the analysis JSON file
        output_path: Path for the output HTML file
    """
    data = load_analysis(data_path)
    points = data["points"]

    if not points:
        Path(output_path).write_text("<h2>No data points to visualize.</h2>")
        return

    # Generate thumbnails
    print(f"Generating thumbnails for {len(points)} images...")
    thumbs = generate_thumbnails(points)

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

    title = f"Embedding Map — {data['model']} ({data['method'].upper()}, {data['count']} images)"
    p = figure(
        title=title,
        width=1200,
        height=800,
        tools="pan,wheel_zoom,box_zoom,reset,tap",
        active_scroll="wheel_zoom",
    )

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

    # Tap callback: copy folder path to clipboard
    tap_cb = CustomJS(args=dict(source=source), code="""
        const indices = source.selected.indices;
        if (indices.length === 0) return;
        const folder = source.data['folder'][indices[0]];
        if (folder && folder !== '/') {
            navigator.clipboard.writeText(folder).then(() => {
                // Brief visual feedback
                const el = document.getElementById('copy-feedback');
                if (el) {
                    el.textContent = 'Copied: ' + folder;
                    el.style.opacity = '1';
                    setTimeout(() => { el.style.opacity = '0'; }, 2000);
                }
            });
        }
    """)
    p.js_on_event("tap", tap_cb)

    header = Div(
        text=f"<h2>Embedding Analysis</h2>"
             f"<p>Model: <b>{data['model']}</b> | "
             f"Method: <b>{data['method'].upper()}</b> | "
             f"Images: <b>{data['count']}</b></p>"
             f"<p><i>Click on a point to copy its folder path to clipboard.</i></p>"
             f"<div id='copy-feedback' style='color:green; font-weight:bold; "
             f"transition: opacity 0.5s; opacity:0;'>&nbsp;</div>",
    )

    layout = column(header, size_slider, p)
    html = file_html(layout, resources=CDN, title="Embedding Analysis")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Static visualization saved to {output_path}")
