"""
generate_chart.py
Module for fetching ChurchTools group data and rendering the SVG/PNG org-chart.
"""

import os
import math
import logging
import requests
from typing import Any, Optional, Dict, List, Tuple, Set, cast

try:
    import cairosvg # type: ignore
except ImportError:
    cairosvg = None

logger = logging.getLogger(__name__)

# --- Configuration for Generation ---
GENERATE_PNG: bool = os.getenv("CT_GENERATE_PNG", "false").lower() in ("true", "1", "yes")
SPLIT_DEPTH: int = int(os.getenv("CT_SPLIT_DEPTH", "2"))

ALLOWED_STATUS_IDS_ENV: str = os.getenv("CT_ALLOWED_STATUS_IDS", "")
ALLOWED_STATUS_IDS: Set[int] = {int(s.strip()) for s in ALLOWED_STATUS_IDS_ENV.split(",") if s.strip().isdigit()}

CT_COLORS: Dict[str, str] = {
    "lime": "#84cc16", "sky": "#0ea5e9", "amber": "#f59e0b", "teal": "#14b8a6",
    "gray": "#6b7280", "purple": "#a855f7", "emerald": "#10b981", "blue": "#3b82f6",
    "violet": "#8b5cf6", "yellow": "#eab308", "pink": "#ec4899"
}

SVG_LINK_ICON: str = "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71 M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"
SVG_STATUS_DRAFT: str = "M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.89 1.147l-2.83.911a.75.75 0 01-.93-.93l.91-2.83a4.5 4.5 0 011.147-1.89L16.862 4.487zM16.862 4.487L19.5 7.125"
SVG_STATUS_ACTIVE: str = "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
SVG_STATUS_FINISHED: str = "M3 3v1.5M3 21v-6m0 0l2.77-.693a14.45 14.45 0 014.66 0l2.14.535a14.45 14.45 0 004.66 0l2.77-.693V4.5l-2.77.693a14.45 14.45 0 01-4.66 0l-2.14-.535a14.45 14.45 0 00-4.66 0L3 4.5M8.25 12l2.25-2.25M12 9l2.25 2.25"
SVG_STATUS_ARCHIVED: str = "M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m6 4.5h4m-7.036-4.5h11.072c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"

def _fetch_paginated_api(base_url: str, endpoint: str, headers: Dict[str, str], ignore_errors: bool = False) -> List[Dict[str, Any]]:
    all_data: List[Dict[str, Any]] = []
    page: int = 1
    has_more: bool = True
    while has_more:
        url = f"{base_url}{endpoint}?page={page}&limit=100"
        res = requests.get(url, headers=headers, timeout=15)
        if not res.ok:
            if ignore_errors: return all_data
            res.raise_for_status()
        json_data = res.json()
        all_data.extend(json_data.get("data", []))
        pagination = json_data.get("meta", {}).get("pagination", {})
        if pagination:
            has_more = pagination.get("current", 1) < pagination.get("lastPage", 1)
            page += 1
        else:
            has_more = False
    return all_data

def fetch_ct_data(base_url: str, api_token: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[int, Dict[str, int]], Set[int], Set[int]]:
    auth_header = api_token if api_token.startswith("Login ") else f"Login {api_token}"
    headers = {"Authorization": auth_header, "Accept": "application/json"}

    try:
        logger.info("Fetching raw data from ChurchTools API...")
        grouptypes = _fetch_paginated_api(base_url, "/api/group/grouptypes", headers)
        groups = _fetch_paginated_api(base_url, "/api/groups", headers)
        hierarchies = _fetch_paginated_api(base_url, "/api/groups/hierarchies", headers)

        all_children_original: Set[int] = set()
        hierarchy_parents_original: Set[int] = set()
        for h in hierarchies:
            g_id = h.get("groupId")
            if g_id: hierarchy_parents_original.add(int(g_id))
            all_children_original.update(int(c) for c in h.get("children", []))

        valid_groups: List[Dict[str, Any]] = []
        for g in groups:
            s_id = int(g.get("information", {}).get("groupStatusId") or g.get("statusId") or g.get("groupStatusId") or 0)
            g["status_id"] = s_id
            if ALLOWED_STATUS_IDS and s_id not in ALLOWED_STATUS_IDS:
                continue
            valid_groups.append(g)

        groups = valid_groups
        valid_group_ids: Set[int] = {int(g["id"]) for g in groups if g.get("id")}

        valid_hierarchies: List[Dict[str, Any]] = []
        for h in hierarchies:
            h_id = h.get("groupId")
            if h_id and int(h_id) in valid_group_ids:
                h["children"] = [c for c in h.get("children", []) if int(c) in valid_group_ids]
                valid_hierarchies.append(h)
        hierarchies = valid_hierarchies

        role_maps: Dict[int, Dict[int, str]] = {}
        for g in groups:
            g_id = g.get("id")
            if g_id:
                role_maps[g_id] = {
                    int(r.get("groupTypeRoleId", 0)): str(r.get("nameTranslated") or r.get("name", ""))
                    for r in g.get("roles", []) if r.get("groupTypeRoleId") is not None
                }

        needed_ids: Set[int] = {int(h["groupId"]) for h in hierarchies if h.get("groupId")}
        needed_ids.update(valid_group_ids)

        member_counts: Dict[int, Dict[str, int]] = {}
        for g_id in needed_ids:
            members = _fetch_paginated_api(base_url, f"/api/groups/{g_id}/members", headers, ignore_errors=True)
            counts: Dict[str, int] = {}
            for m in members:
                r_id = m.get("groupTypeRoleId")
                if r_id is not None:
                    role_name = role_maps.get(g_id, {}).get(int(r_id), f"Role {r_id}")
                    counts[role_name] = counts.get(role_name, 0) + 1
            member_counts[g_id] = counts

        return grouptypes, groups, hierarchies, member_counts, all_children_original, hierarchy_parents_original
    except requests.exceptions.RequestException as e:
        logger.error(f"API Connection Error: {e}")
        return [], [], [], {}, set(), set()

def build_tree(grouptypes: List[Dict[str, Any]], groups: List[Dict[str, Any]], hierarchies: List[Dict[str, Any]], member_counts: Dict[int, Dict[str, int]], all_children_original: Set[int], hierarchy_parents_original: Set[int], base_url: str) -> List[Dict[str, Any]]:
    types_map = {t.get("id"): t for t in grouptypes if t.get("id") is not None}
    lookup: Dict[int, Dict[str, Any]] = {}
    children_map: Dict[int, List[int]] = {}
    valid_all_children: Set[int] = set()

    for h in hierarchies:
        g_id = h.get("groupId")
        if not g_id: continue
        c_ids = [int(c) for c in h.get("children", [])]
        children_map[int(g_id)] = c_ids
        valid_all_children.update(c_ids)

    for g in groups:
        g_id = int(g.get("id", 0))
        if not g_id: continue
        type_id = g.get("information", {}).get("groupTypeId")
        lookup[g_id] = {
            "id": g_id,
            "name": str(g.get("name", "Unnamed Group")),
            "url": f"{base_url.rstrip('/')}/groups/{g_id}",
            "type_name": str(types_map.get(type_id, {}).get("name", "Group")),
            "color": str(g.get("information", {}).get("color", "gray")),
            "status_id": int(g.get("status_id", 0)),
            "member_counts": dict(member_counts.get(g_id, {})),
            "is_isolated": False,
            "is_disconnected_tree": False,
            "has_detached_children": False,
            "is_layout_clone": False
        }

    def _build_node(node_id: int, current_path: Set[int]) -> Optional[Dict[str, Any]]:
        if node_id in current_path or node_id not in lookup: return None
        node: Dict[str, Any] = dict(lookup[node_id])
        node["unique_id"] = f"node_{node_id}_p{len(current_path)}"

        children_list: List[Dict[str, Any]] = []
        for child_id in children_map.get(node_id, []):
            child_node = _build_node(child_id, current_path | {node_id})
            if child_node:
                children_list.append(child_node)

        node["children"] = children_list
        return node

    tree: List[Dict[str, Any]] = []

    for g_id in lookup:
        if g_id in valid_all_children:
            continue

        root_node = _build_node(g_id, set())
        if not root_node: continue

        was_child = g_id in all_children_original
        was_parent = g_id in hierarchy_parents_original
        has_valid_children = len(root_node.get("children", [])) > 0

        if not was_child and not was_parent:
            root_node["is_isolated"] = True
            tree.append(root_node)
        elif not was_child:
            tree.append(root_node)
        elif not has_valid_children:
            root_node["is_isolated"] = True
            tree.append(root_node)
        else:
            root_node["is_disconnected_tree"] = True
            tree.append(root_node)

    return tree

def render_svg_tree(tree: List[Dict[str, Any]], output_path: str) -> bool:
    if not tree: return False

    BOX_W, BOX_H, GAP_X, GAP_Y = 240, 135, 40, 50

    def extract_subtrees(nodes: List[Dict[str, Any]], current_depth: int, parent_context_name: str = "Main Tree") -> List[Dict[str, Any]]:
        extracted: List[Dict[str, Any]] = []
        for node in nodes:
            children: List[Dict[str, Any]] = node.get("children", [])
            if current_depth == SPLIT_DEPTH and children:
                if any(bool(child.get("children")) for child in children):
                    detached_children: List[Dict[str, Any]] = list(children)
                    subtree_root: Dict[str, Any] = dict(node)
                    subtree_root["children"] = detached_children
                    subtree_root["unique_id"] = str(node.get("unique_id", "")) + "_subclone"
                    subtree_root["parent_context"] = parent_context_name
                    subtree_root["is_layout_clone"] = True
                    subtree_root["has_detached_children"] = False

                    extracted.append(subtree_root)
                    node["children"] = []
                    node["has_detached_children"] = True
            elif current_depth < SPLIT_DEPTH:
                extracted.extend(extract_subtrees(children, current_depth + 1, str(node.get("name", "Main Tree"))))
        return extracted

    main_tree = [n for n in tree if not n.get("is_isolated") and not n.get("is_disconnected_tree")]
    isolated_nodes = [n for n in tree if n.get("is_isolated")]
    sub_trees = extract_subtrees(main_tree, 0)

    disconnected_trees = [n for n in tree if n.get("is_disconnected_tree")]
    for dt in disconnected_trees:
        dt["parent_context"] = "Ignored Area"
        sub_trees.append(dt)

    group_counts: Dict[int, int] = {}
    used_types: Dict[str, str] = {}
    unique_nodes: Dict[int, Dict[str, Any]] = {}

    def _walk_tree(nodes: List[Dict[str, Any]]) -> None:
        for n in nodes:
            if not n.get("is_layout_clone"):
                n_id = int(n["id"])
                group_counts[n_id] = group_counts.get(n_id, 0) + 1
                if n_id not in unique_nodes: unique_nodes[n_id] = n
            used_types[str(n["type_name"])] = CT_COLORS.get(str(n["color"]), "#6b7280")
            _walk_tree(n.get("children", []))

    _walk_tree(main_tree)
    _walk_tree(sub_trees)
    _walk_tree(isolated_nodes)

    dup_ids = {g_id for g_id, count in group_counts.items() if count > 1}
    sorted_types = sorted(used_types.items())

    type_counts: Dict[str, int] = {}
    status_counts: Dict[int, int] = {}
    for n in unique_nodes.values():
        t_name = str(n["type_name"])
        type_counts[t_name] = type_counts.get(t_name, 0) + 1
        status_counts[int(n.get("status_id", 0))] = status_counts.get(int(n.get("status_id", 0)), 0) + 1

    L_X, L_Y, L_W = 30.0, 30.0, 580.0
    num_left_items = len(sorted_types) + int(len(dup_ids) > 0) + int(len(isolated_nodes) > 0)
    L_H = 45.0 + max(num_left_items, 4) * 28.0 + 10.0

    positions: Dict[str, Tuple[float, float]] = {}
    layout_nodes: List[Dict[str, Any]] = []
    svg_structural: List[str] = []

    def _calculate_positions_compact(nodes: List[Dict[str, Any]], start_x: float, start_y: float) -> float:
        if not nodes: return 0.0
        dummy_root: Dict[str, Any] = {"unique_id": "dummy", "children": nodes, "name": "dummy"}

        def _compute(node: Dict[str, Any], depth: int) -> Tuple[Dict[str, Any], Dict[int, Tuple[float, float]]]:
            child_layouts: List[Tuple[Dict[str, Any], Dict[int, Tuple[float, float]]]] = []
            for c in node.get("children", []):
                child_layouts.append(_compute(c, depth + 1))

            current_contour: Dict[int, Tuple[float, float]] = {}
            child_x_offsets: List[float] = []

            for i, (_, child_contour) in enumerate(child_layouts):
                shift = 0.0
                if i > 0:
                    for d in child_contour.keys():
                        if d in current_contour:
                            overlap = current_contour[d][1] + GAP_X - child_contour[d][0]
                            if overlap > shift: shift = overlap
                child_x_offsets.append(shift)

                for d, (min_x, max_x) in child_contour.items():
                    current_contour[d] = (min(current_contour.get(d, (float('inf'),))[0], min_x + shift), max(current_contour.get(d, (-float('inf'), float('-inf')))[1], max_x + shift))

            node_x = (child_x_offsets[0] + child_x_offsets[-1]) / 2.0 if child_layouts else 0.0
            for i, c in enumerate(node.get("children", [])):
                c["rel_x"] = child_x_offsets[i] - node_x

            my_contour: Dict[int, Tuple[float, float]] = {}
            if str(node.get("unique_id")) != "dummy":
                my_contour[depth] = (-BOX_W/2.0, BOX_W/2.0)

            for d, (min_x, max_x) in current_contour.items():
                my_contour[d] = (min(my_contour.get(d, (float('inf'),))[0], min_x - node_x), max(my_contour.get(d, (-float('inf'), float('-inf')))[1], max_x - node_x))

            return node, my_contour

        _, full_contour = _compute(dummy_root, -1)
        min_x_overall = min([bounds[0] for bounds in full_contour.values()]) if full_contour else 0.0
        max_x_overall = max([bounds[1] for bounds in full_contour.values()]) if full_contour else 0.0

        def _assign(node: Dict[str, Any], abs_x: float, abs_y: float):
            if str(node.get("unique_id")) != "dummy":
                node["x"], node["y"] = abs_x - BOX_W / 2.0, abs_y
                positions[str(node["unique_id"])] = (node["x"], node["y"])
                layout_nodes.append(node)
                child_y = abs_y + BOX_H + GAP_Y
            else:
                child_y = abs_y
            for c in node.get("children", []):
                _assign(c, abs_x + float(c.get("rel_x", 0.0)), child_y)

        _assign(dummy_root, start_x - min_x_overall, start_y)
        return (max_x_overall - min_x_overall)

    current_y = L_Y + L_H + 40.0
    total_width_main = _calculate_positions_compact(main_tree, 40.0, current_y)
    max_w = max(total_width_main + 100.0, L_X + L_W + 100.0)

    for st in sub_trees:
        current_y = max((float(n.get("y", 0.0)) for n in layout_nodes), default=current_y) + BOX_H + 80.0
        title, subtitle = f"Detailed View: {str(st.get('name', ''))}", f"(Continuation of branch from: {str(st.get('parent_context', 'Main Tree'))})"
        svg_structural.extend([
            f'<line x1="40" y1="{current_y}" x2="{max_w - 40}" y2="{current_y}" stroke="#e5e7eb" stroke-width="2" />',
            f'<text x="40" y="{current_y + 35}" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#374151">{title}</text>',
            f'<text x="40" y="{current_y + 55}" font-family="Arial, sans-serif" font-size="14" fill="#6b7280">{subtitle}</text>'
        ])
        current_y += 80.0
        max_w = max(max_w, _calculate_positions_compact([st], 40.0, current_y) + 80.0)

    current_y = max((float(n.get("y", 0.0)) for n in layout_nodes), default=current_y) + BOX_H + 100.0
    if isolated_nodes:
        svg_structural.extend([
            f'<line x1="40" y1="{current_y}" x2="{max_w - 40}" y2="{current_y}" stroke="#d1d5db" stroke-width="2" stroke-dasharray="8,8" />',
            f'<text x="40" y="{current_y + 35}" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#4b5563">Isolated Groups</text>'
        ])
        iso_start_y = current_y + 60.0
        max_cols = max(4, int(max_w // (BOX_W + GAP_X)))
        for i, n in enumerate(isolated_nodes):
            nx = 40.0 + (i % max_cols) * (BOX_W + GAP_X)
            ny = iso_start_y + (i // max_cols) * (BOX_H + GAP_Y)
            node_data = dict(n)
            node_data.update({"x": nx, "y": ny})
            layout_nodes.append(node_data)
            max_w = max(max_w, nx + BOX_W + 40.0)

    canvas_h, canvas_w = max((float(n.get("y", 0.0)) for n in layout_nodes), default=0.0) + BOX_H + 40.0, max_w

    svg: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}">',
        '<rect width="100%" height="100%" fill="#fafafa" />',
        f'<rect x="{L_X}" y="{L_Y}" width="{L_W}" height="{L_H}" rx="8" fill="#ffffff" stroke="#e5e7eb" stroke-width="2"/>'
    ]

    # --- LEGEND ---
    COL1_X = L_X + 20.0
    svg.append(f'<text x="{COL1_X}" y="{L_Y+28}" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="#111827">Legend (Group Types)</text>')
    curr_ly = L_Y + 55.0
    for t_name, t_color in sorted_types:
        svg.extend([
            f'<rect x="{COL1_X}" y="{curr_ly}" width="18" height="18" rx="4" fill="{t_color}"/>',
            f'<text x="{COL1_X+30}" y="{curr_ly+14}" font-family="Arial, sans-serif" font-size="14" fill="#374151">{t_name} ({type_counts.get(t_name, 0)})</text>'
        ])
        curr_ly += 28.0
    if dup_ids:
        svg.extend([
            f'<rect x="{COL1_X}" y="{curr_ly}" width="18" height="18" rx="4" fill="#ffffff" stroke="#6b7280" stroke-width="2" stroke-dasharray="4,3" opacity="0.5" />',
            f'<text x="{COL1_X+30}" y="{curr_ly+14}" font-family="Arial, sans-serif" font-size="14" fill="#374151">Duplicate ({len(dup_ids)})</text>'
        ])
        curr_ly += 28.0
    if isolated_nodes:
        svg.extend([
            f'<rect x="{COL1_X}" y="{curr_ly}" width="18" height="18" rx="4" fill="#f9fafb" stroke="#9ca3af" stroke-width="2" stroke-dasharray="2,2" />',
            f'<text x="{COL1_X+30}" y="{curr_ly+14}" font-family="Arial, sans-serif" font-size="14" fill="#374151">Isolated ({len(isolated_nodes)})</text>'
        ])

    COL2_X = L_X + 340.0
    svg.append(f'<text x="{COL2_X}" y="{L_Y+28}" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="#111827">Status (Icons)</text>')
    curr_ry = L_Y + 55.0
    for s_name, s_path, s_id in [("Active", SVG_STATUS_ACTIVE, 1), ("Draft", SVG_STATUS_DRAFT, 2), ("Finished", SVG_STATUS_FINISHED, 4), ("Archived", SVG_STATUS_ARCHIVED, 3)]:
        svg.extend([
            f'<g transform="translate({COL2_X}, {curr_ry}) scale(0.75)" fill="none" stroke="#6b7280" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="{s_path}"/></g>',
            f'<text x="{COL2_X+30}" y="{curr_ry+14}" font-family="Arial, sans-serif" font-size="14" fill="#374151">{s_name} ({status_counts.get(s_id, 0)})</text>'
        ])
        curr_ry += 28.0

    svg.extend(svg_structural)

    def _draw_lines(nodes: List[Dict[str, Any]]):
        for n in nodes:
            px, py = positions[str(n["unique_id"])]
            for c in n.get("children", []):
                cx, cy = positions[str(c["unique_id"])]
                mid_y = py + BOX_H + (GAP_Y / 2.0)
                svg.append(f'<path d="M {px+(BOX_W/2.0)} {py+BOX_H} L {px+(BOX_W/2.0)} {mid_y} L {cx+(BOX_W/2.0)} {mid_y} L {cx+(BOX_W/2.0)} {cy}" fill="none" stroke="#a1a1aa" stroke-width="2" />')
            _draw_lines(n.get("children", []))

    _draw_lines(main_tree); _draw_lines(sub_trees)

    for n in layout_nodes:
        x, y = float(n.get("x", 0.0)), float(n.get("y", 0.0))
        hex_color = CT_COLORS.get(str(n.get("color", "gray")), "#6b7280")
        is_dup, is_iso = int(n.get("id", 0)) in dup_ids, n.get("is_isolated", False)

        box_elements: List[str] = ['<g opacity="0.5">'] if is_dup else []
        if n.get("url"): box_elements.append(f'<a href="{str(n["url"])}" target="_blank" style="text-decoration:none; cursor:pointer;">')

        dash_attr = ' stroke-dasharray="8,5"' if is_dup else (' stroke-dasharray="2,2"' if is_iso else '')
        box_elements.extend([
            f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="8" fill="{"#f9fafb" if is_iso else "#ffffff"}" stroke="{hex_color}" stroke-width="3"{dash_attr}/>',
            f'<text x="{x+(BOX_W/2.0)}" y="{y+20}" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="{hex_color}" text-anchor="middle">{str(n.get("type_name", "GROUP")).upper()}</text>'
        ])

        if n.get("url"): box_elements.append(f'<g transform="translate({x + BOX_W - 24}, {y + 10}) scale(0.65)" fill="none" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="{SVG_LINK_ICON}"/></g>')

        name = str(n.get("name", ""))
        lines = [name] if len(name) <= 24 else ([name[:24]+"-", name[24:].strip()[:21]+"..."] if name.rfind(' ', 0, 25) <= 0 else [name[:name.rfind(' ', 0, 25)].strip(), name[name.rfind(' ', 0, 25):].strip()[:21]+"..."])
        status_id = int(n.get("status_id", 0))
        icon_path = SVG_STATUS_DRAFT if status_id == 2 else SVG_STATUS_ACTIVE if status_id == 1 else SVG_STATUS_FINISHED if status_id == 4 else SVG_STATUS_ARCHIVED if status_id == 3 else ""
        icon_x = x + (BOX_W / 2.0) - (len(lines[0]) * 7.5 / 2.0) - 20

        text_y = y + 53 if len(lines) == 1 else y + 44
        box_elements.append(f'<text x="{x+(BOX_W/2.0)}" y="{text_y}" font-family="Arial, sans-serif" font-size="15" font-weight="bold" fill="#333" text-anchor="middle">{lines[0]}</text>')
        if len(lines) > 1: box_elements.append(f'<text x="{x+(BOX_W/2.0)}" y="{y+62}" font-family="Arial, sans-serif" font-size="15" font-weight="bold" fill="#333" text-anchor="middle">{lines[1]}</text>')
        if icon_path: box_elements.append(f'<g transform="translate({icon_x}, {text_y - 13}) scale(0.60)" fill="none" stroke="{hex_color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="{icon_path}"/></g>')

        if n.get("has_detached_children"): box_elements.append(f'<text x="{x+(BOX_W/2.0)}" y="{y+BOX_H-6}" font-family="Arial, sans-serif" font-size="10" font-weight="bold" fill="#9ca3af" text-anchor="middle">▼ Subgroups separate ▼</text>')

        counts: Dict[str, int] = dict(n.get("member_counts", {}))
        if counts:
            box_elements.append(f'<line x1="{x+15}" y1="{y+80}" x2="{x+BOX_W-15}" y2="{y+80}" stroke="#e5e7eb" />')
            for i, (r_name, r_count) in enumerate(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:4]):
                box_elements.append(f'<text x="{x + 15 if i % 2 == 0 else x + BOX_W - 15}" y="{y + 100 + (i // 2) * 18}" font-family="Arial, sans-serif" font-size="12" fill="#4b5563" text-anchor="{"start" if i % 2 == 0 else "end"}">{r_name if len(r_name) < 13 else r_name[:11] + "."}: {r_count}</text>')

        if n.get("url"): box_elements.append('</a>')
        if is_dup: box_elements.append('</g>')
        svg.extend(box_elements)

    svg.append('</svg>')

    try:
        with open(output_path, "w", encoding="utf-8") as f: f.write("\n".join(svg))
        logger.info(f"🎨 SVG perfectly rendered and saved to '{output_path}'.")

        if GENERATE_PNG:
            if cairosvg:
                png_path = output_path.replace(".svg", ".png")
                current_mp = canvas_w * canvas_h
                scale_factor = math.sqrt(32_000_000.0 / current_mp) if current_mp > 32_000_000.0 else 1.0
                if scale_factor < 1.0: logger.warning(f"📉 Scaling PNG down to {scale_factor:.1%} (Limit protection).")

                cast(Any, cairosvg).svg2png(bytestring="\n".join(svg).encode("utf-8"), write_to=png_path, scale=float(scale_factor))
                logger.info(f"📸 PNG fallback successfully generated at '{png_path}'.")
            else:
                logger.warning("❌ PNG generation skipped: 'cairosvg' library is missing.")
        return True
    except Exception as e:
        logger.error(f"Failed to write output files: {e}")
        return False

def create_organigram(base_url: str, api_token: str, output_path: str) -> bool:
    """Main entrypoint for generation module."""
    logger.info("Initializing Organization Chart Generation...")
    grouptypes, groups, hierarchies, member_counts, all_children_orig, hierarchy_parents_orig = fetch_ct_data(base_url, api_token)
    if not grouptypes or not groups:
        logger.warning("Aborting generation: Unable to retrieve essential base data.")
        return False
    tree = build_tree(grouptypes, groups, hierarchies, member_counts, all_children_orig, hierarchy_parents_orig, base_url)
    if not tree:
        logger.warning("Aborting generation: No valid hierarchy structure calculated.")
        return False
    return render_svg_tree(tree, output_path)
