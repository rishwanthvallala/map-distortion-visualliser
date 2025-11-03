import geopandas as gpd
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
import numpy as np
import warnings
import os
import sys
import argparse 

parser = argparse.ArgumentParser(
    description="Generate maps of various geographic projections."
)
parser.add_argument(
    '--show',
    action='store_true',  # This makes it a boolean flag
    help="Display plots interactively instead of saving them to files."
)
args = parser.parse_args()

try:
    from scraped_projections import projections as all_projections
except ImportError:
    print("Error: 'scraped_projections.py' not found.")
    print("Please run 'scrape_projections.py' first to generate the list.")
    sys.exit(1)

warnings.filterwarnings("ignore", category=RuntimeWarning, message="invalid value encountered in normalize")

# --- GEODESIC DOME GENERATION ---
t = (1.0 + np.sqrt(5.0)) / 2.0
icosahedron_vertices = np.array([[-1,t,0],[1,t,0],[-1,-t,0],[1,-t,0],[0,-1,t],[0,1,t],[0,-1,-t],[0,1,-t],[t,0,-1],[t,0,1],[-t,0,-1],[-t,0,1]])
icosahedron_vertices /= np.linalg.norm(icosahedron_vertices, axis=1)[:, np.newaxis]
icosahedron_faces = np.array([[0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],[1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],[3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],[4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1]])

def subdivide(vertices, faces):
    new_faces = []; midpoint_cache = {}; new_vertices_list = []
    def get_midpoint_index(idx1, idx2):
        key = tuple(sorted((idx1, idx2)))
        if key in midpoint_cache: return midpoint_cache[key]
        mid = (vertices[idx1] + vertices[idx2]) / 2.0
        mid_normalized = mid / np.linalg.norm(mid)
        new_vertices_list.append(mid_normalized)
        new_idx = len(vertices) + len(new_vertices_list) - 1
        midpoint_cache[key] = new_idx
        return new_idx
    for face in faces:
        v1_idx, v2_idx, v3_idx = face
        m1_idx = get_midpoint_index(v1_idx, v2_idx); m2_idx = get_midpoint_index(v2_idx, v3_idx); m3_idx = get_midpoint_index(v3_idx, v1_idx)
        new_faces.extend([[v1_idx, m1_idx, m3_idx], [v2_idx, m2_idx, m1_idx], [v3_idx, m3_idx, m2_idx], [m1_idx, m2_idx, m3_idx]])
    new_vertices = np.vstack([vertices, np.array(new_vertices_list)])
    return new_vertices, np.array(new_faces)

vertices, faces = icosahedron_vertices, icosahedron_faces
subdivisions = 3
for _ in range(subdivisions): vertices, faces = subdivide(vertices, faces)
lons = np.rad2deg(np.arctan2(vertices[:, 1], vertices[:, 0])); lats = np.rad2deg(np.arcsin(vertices[:, 2]))
triangles_for_gdf = []
for face in faces:
    face_lons = [lons[i] for i in face]
    if max(face_lons) - min(face_lons) > 270: continue
    coords = [(lons[i], lats[i]) for i in face]
    triangles_for_gdf.append(Polygon(coords))
grid_gdf = gpd.GeoDataFrame(geometry=triangles_for_gdf, crs="EPSG:4326")
world = gpd.read_file("map.zip")

# --- PLOTTING FUNCTION ---
def plot_projection(world_gdf, grid_gdf, crs_code, title):
    fig, ax = plt.subplots(1, 1, figsize=(15, 10))
    ax.set_aspect('equal')
    world_proj = world_gdf.to_crs(crs_code)
    grid_proj = grid_gdf.to_crs(crs_code)
    grid_bounds = grid_proj.total_bounds
    is_finite = all(np.isfinite(grid_bounds))
    if is_finite:
        clip_mask = grid_proj.union_all()
    else:
        world_proj_valid = world_proj[~world_proj.is_empty]
        clip_mask = world_proj_valid.union_all()
    try:
        grid_clipped = gpd.clip(grid_proj, clip_mask)
    except Exception:
        grid_clipped = grid_proj
    minx, miny, maxx, maxy = clip_mask.bounds
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    world_proj.plot(ax=ax, color='lightgray', edgecolor='white', linewidth=0.5)
    grid_clipped.plot(ax=ax, facecolor='none', edgecolor='blue', linewidth=0.5)
    ax.set_title(title, fontsize=20)
    ax.set_axis_off()
    return fig, ax

# --- LOOP AND SAVE / SHOW ---
if not args.show:
    output_dir = "projection_maps_svg"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Preparing to save maps in the '{output_dir}/' directory...")
else:
    print("Running in interactive display mode. Close each plot window to continue...")

print(f"Loaded {len(all_projections)} projections from scraped_projections.py")

for title, crs_string in all_projections.items():
    print(f"Generating plot for: {title}")
    fig = None
    try:
        fig, ax = plot_projection(world, grid_gdf, crs_string, title)
        
        if args.show:
            plt.show()  # Display the plot and wait for it to be closed
        else:
            # This is the original saving logic
            filename = "".join(c for c in title if c.isalnum() or c in (' ','_')).rstrip()
            filepath = os.path.join(output_dir, f"{filename}.svg")
            plt.savefig(filepath, bbox_inches='tight', pad_inches=0.05)
            print(f"--> Successfully saved to {filepath}")

    except Exception as e:
        print(f"--> SKIPPING '{title}' due to an error: {e}\n")
    finally:
        if fig:
            plt.close(fig) # Important to close figure in both modes

# --- NEW: Final message depends on the mode ---
if not args.show:
    print(f"\nProcessing complete. All plots saved in the '{output_dir}' folder.")
else:
    print("\nFinished displaying all plots.")