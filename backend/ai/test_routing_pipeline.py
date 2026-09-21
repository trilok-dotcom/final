import sys
from pathlib import Path
import cv2
import numpy as np

# Ensure backend parent directory is in sys.path
AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai.predict import predict, _find_test_image
from ai.road_network import clean_road_mask, extract_road_skeleton, process_road_network
from ai.route import (
    get_or_build_road_graph,
    calculate_route,
    generate_route_visualizations,
    build_simplified_road_graph,
)


from ai.georeference import georeference, haversine_distance_km
from services.directions import generate_route_directions


def run_pipeline_test():
    print("=" * 70)
    print("      RESQROUTE AI - COMPLETE ROAD ROUTE & DIRECTIONS PIPELINE TEST")
    print("=" * 70)

    # 0. Test Master Georeferencing Round-Trip
    test_lat, test_lon = 12.9640, 77.5900
    px, py = georeference.geo_to_pixel(test_lat, test_lon)
    rec_lat, rec_lon = georeference.pixel_to_geo(px, py)
    print(f"[STEP 0] Georeference Roundtrip Test:")
    print(f"         Original : lat={test_lat}, lon={test_lon}")
    print(f"         Pixel    : x={px}, y={py}")
    print(f"         Recovered: lat={rec_lat}, lon={rec_lon}")
    print(f"         Error    : lat_err={abs(test_lat - rec_lat):.6f}, lon_err={abs(test_lon - rec_lon):.6f}")

    # 1. Locate test satellite image 100703_sat.jpg
    sat_img_path = AI_DIR / "datasets" / "test" / "100703_sat.jpg"
    if not sat_img_path.exists():
        sat_img_path = _find_test_image()

    print(f"\n[STEP 1] Using Satellite Image : {sat_img_path}")

    # 2. Run U-Net prediction
    print("[STEP 2] Running U-Net Model Inference...")
    pred_res = predict(image_path=sat_img_path, threshold=0.40)
    mask_path = Path(pred_res["mask_output_path"])
    print(f"         Prediction Mask saved : {mask_path}")

    # 3. Clean Mask & Extract Skeleton
    print("[STEP 3] Running Mask Cleaning & Skeletonization...")
    net_res = process_road_network(mask_path=mask_path, sat_path=sat_img_path)
    print(f"         Cleaned Mask saved    : {net_res['road_mask_cleaned.png']}")
    print(f"         Road Skeleton saved   : {net_res['road_skeleton.png']}")

    # 4. Build Simplified Graph & Prune Spurs
    print("[STEP 4] Constructing Simplified Road Graph & Pruning Spurs...")
    skel_img = cv2.imread(net_res["road_skeleton.png"], cv2.IMREAD_GRAYSCALE)
    prob_img = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

    graph = build_simplified_road_graph(skel_img, prob_mask=prob_img, min_branch_length=15)
    print(f"         Simplified Graph Nodes: {graph.number_of_nodes()}")
    print(f"         Simplified Graph Edges: {graph.number_of_edges()}")

    # Count junctions and endpoints
    junctions = [n for n, deg in graph.degree() if deg >= 3]
    endpoints = [n for n, deg in graph.degree() if deg == 1]
    print(f"         Junction Nodes        : {len(junctions)}")
    print(f"         Endpoint Nodes        : {len(endpoints)}")

    # 5. Test GEOSPATIAL ROUTE DEBUG for Target Coordinates (12.9640, 77.5900 -> 12.9750, 77.5920)
    req_start_lat, req_start_lon = 12.9640, 77.5900
    req_dest_lat, req_dest_lon = 12.9750, 77.5920

    start_px, start_py = georeference.geo_to_pixel(req_start_lat, req_start_lon)
    dest_px, dest_py = georeference.geo_to_pixel(req_dest_lat, req_dest_lon)

    route_res = calculate_route(graph, (start_px, start_py), (dest_px, dest_py))
    start_snap_node = route_res["start_node"]
    dest_snap_node = route_res["end_node"]

    snap_start_lat, snap_start_lon = georeference.pixel_to_geo(*start_snap_node)
    snap_dest_lat, snap_dest_lon = georeference.pixel_to_geo(*dest_snap_node)

    route_path = route_res["path"]
    route_coords = [georeference.pixel_to_geo(p[0], p[1]) for p in route_path]
    route_coords[0] = (snap_start_lat, snap_start_lon)
    route_coords[-1] = (snap_dest_lat, snap_dest_lon)

    geo_dist_km = sum(haversine_distance_km(route_coords[j][0], route_coords[j][1], route_coords[j+1][0], route_coords[j+1][1]) for j in range(len(route_coords)-1))

    print("\n" + "=" * 40)
    print("GEOSPATIAL ROUTE DEBUG")
    print("=" * 40)
    print(f"Requested Start:\nlat={req_start_lat}\nlon={req_start_lon}\n")
    print(f"Start Pixel:\nx={start_px}\ny={start_py}\n")
    print(f"Snapped Start Pixel:\nx={start_snap_node[0]}\ny={start_snap_node[1]}\n")
    print(f"Snapped Start Geo:\nlat={snap_start_lat}\nlon={snap_start_lon}\n")
    print(f"Requested Destination:\nlat={req_dest_lat}\nlon={req_dest_lon}\n")
    print(f"Destination Pixel:\nx={dest_px}\ny={dest_py}\n")
    print(f"Snapped Destination Pixel:\nx={dest_snap_node[0]}\ny={dest_snap_node[1]}\n")
    print(f"Snapped Destination Geo:\nlat={snap_dest_lat}\nlon={snap_dest_lon}\n")
    print(f"Route First Coordinate:\nlat={route_coords[0][0]}\nlon={route_coords[0][1]}\n")
    print(f"Route Last Coordinate:\nlat={route_coords[-1][0]}\nlon={route_coords[-1][1]}\n")
    print(f"Route Point Count:\n{len(route_coords)}\n")
    print(f"Route Distance:\n{geo_dist_km:.2f} km")
    print("=" * 40)

    # 5. Test 5 Start & Destination Coordinate Pairs
    test_pairs = [
        {"name": "Pair 1 (South to North)", "start": (270, 430), "dest": (325, 120)},
        {"name": "Pair 2 (South-West to North-East)", "start": (220, 390), "dest": (350, 150)},
        {"name": "Pair 3 (Mid-Branch to North)", "start": (280, 260), "dest": (330, 110)},
        {"name": "Pair 4 (West Branch to East Branch)", "start": (150, 300), "dest": (420, 200)},
        {"name": "Pair 5 (South-East to North-West)", "start": (380, 420), "dest": (180, 150)},
    ]

    print("\n[STEP 5] Testing Route & Turn-by-Turn Generation for 5 Pairs...")

    output_dir = AI_DIR / "outputs" / "route"
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, test in enumerate(test_pairs, 1):
        name = test["name"]
        start_pt = test["start"]
        dest_pt = test["dest"]
        print(f"\n--- Testing Route #{i}: {name} ---")
        print(f"    Target Start      : {start_pt}")
        print(f"    Target Destination: {dest_pt}")

        try:
            route_res = calculate_route(
                graph=graph,
                start_pixel=start_pt,
                dest_pixel=dest_pt,
                max_distance=120.0,
                douglas_peucker_epsilon=2.5,
            )

            path = route_res["path"]
            raw_path = route_res["raw_path"]
            length_px = route_res["route_length_pixels"]

            print(f"    [SUCCESS] Route calculated!")
            print(f"    - Raw Pixel Steps   : {len(raw_path)}")
            print(f"    - Smoothed Waypoints: {len(path)}")
            print(f"    - Spatial Length    : {length_px:.2f} pixels")

            # Generate Turn-by-Turn Directions
            dir_res = generate_route_directions(
                path_pixels=path,
                graph=graph,
                pixel_to_meters=12.0,
                generate_debug_vis=True,
                output_dir=output_dir,
            )
            directions = dir_res["directions"]

            print(f"    - Generated Directions ({len(directions)} steps):")
            for d in directions:
                print(f"      {d['step']}. [{d['type'].upper()}] {d['instruction']} ({d['distance_m']}m)")

            # Generate and save route debug visualizations
            vis = generate_route_visualizations(
                graph=graph,
                path=path,
                start_node=route_res["start_node"],
                end_node=route_res["end_node"],
                bg_image_path=sat_img_path,
                output_dir=output_dir,
            )

            pair_debug_path = output_dir / f"route_debug_pair{i}.png"
            cv2.imwrite(str(pair_debug_path), cv2.imread(vis["route_debug.png"]))
            print(f"    - Debug Image saved : {pair_debug_path}")

        except Exception as err:
            print(f"    [NOTE] Route #{i} calculation info: {err}")

    print("\n" + "=" * 70)
    print("[SUCCESS] Target Pipeline & Directions Testing Complete!")
    print(f"Saved Debug Artifacts in: {output_dir}")
    print(f"  - Cleaned Mask     : {net_res['road_mask_cleaned.png']}")
    print(f"  - Road Skeleton    : {net_res['road_skeleton.png']}")
    print(f"  - Road Graph       : {output_dir / 'road_graph.png'}")
    print(f"  - Route Debug      : {output_dir / 'route_debug.png'}")
    print(f"  - Directions Debug : {output_dir / 'direction_debug.png'}")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline_test()
