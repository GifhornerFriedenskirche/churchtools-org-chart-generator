import os
import sys
import logging
import requests
from typing import List, Dict, Any
import graphviz

# --- CONFIGURATION & SECURITY ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Credentials from GitHub Secrets
BASE_URL = os.getenv('CT_BASE_URL', '').rstrip('/')
API_TOKEN = os.getenv('CT_API_TOKEN')
WIKI_CATEGORY_ID = os.getenv('CT_WIKI_CATEGORY_ID')

if not all([BASE_URL, API_TOKEN, WIKI_CATEGORY_ID]):
    logger.error("Security/Config Error: Missing required environment variables (URL, Token, Wiki-ID).")
    sys.exit(1)

# Group type mapping (Keys must exactly match the group type names in your ChurchTools instance)
TYPE_COLORS = {
    'Kleingruppen': '#0284c7', 'Dienste': '#65a30d', 'Maßnahmen': '#d97706',
    'Merkmale': '#0d9488', 'Verteiler': '#b45309', 'Datenschutz-Einwilligungen': '#64748b',
    'Gemeindeorgane': '#9333ea', 'Dienstbereiche': '#0f766e', 'Veranstaltungen': '#4d7c0f',
    'default': '#f1f5f9'
}

def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({'Authorization': f'Login {API_TOKEN}'})
    return session

def fetch_meta_data(session: requests.Session) -> Dict[str, str]:
    """Fetches group type names to dynamically map IDs to names."""
    try:
        res = session.get(f"{BASE_URL}/api/grouptypes", timeout=15)
        res.raise_for_status()
        return {str(t['id']): t['name'] for t in res.json().get('data', [])}
    except Exception as e:
        logger.error(f"Failed to load group types metadata: {e}")
        sys.exit(1)

def fetch_groups(session: requests.Session) -> List[Dict[str, Any]]:
    """Fetches the group list (Zero PII logging enforced)."""
    try:
        res = session.get(f"{BASE_URL}/api/groups", timeout=15)
        res.raise_for_status()
        return res.json().get('data', [])
    except Exception as e:
        logger.error(f"Failed to load groups: {e}")
        sys.exit(1)

def build_svg(groups: List[Dict[str, Any]], type_map: Dict[str, str]) -> str:
    """Generates the graph and saves it as a temporary SVG file."""
    dot = graphviz.Digraph(format='svg')
    dot.attr(bgcolor='#ffffff', rankdir='TB', splines='ortho')
    dot.attr('node', fontname='Arial', fontsize='11', style='filled,rounded')

    for g in groups:
        gid = str(g['id'])
        name = g['name']
        pid = str(g.get('parentId')) if g.get('parentId') else None

        # Determine group type ID
        tid = str(g.get('information', {}).get('groupTypeId', g.get('groupTypeId', '')))
        t_name = type_map.get(tid, 'default')
        color = TYPE_COLORS.get(t_name, TYPE_COLORS['default'])

        url = f"{BASE_URL}/?q=churchdb#GroupView/view/{gid}"

        # Visual logic for orphan groups (no parent)
        shape = 'hexagon' if not pid or pid == "None" else 'rect'

        dot.node(gid, name, shape=shape, fillcolor=color, color='#1e293b', URL=url)
        if pid and pid != "None":
            dot.edge(pid, gid, color='#94a3b8')

    # Add Legend
    legend = '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
    legend += '<TR><TD COLSPAN="2" BGCOLOR="#cbd5e1"><B>Legend</B></TD></TR>'
    for n, c in TYPE_COLORS.items():
        if n == 'default': continue
        legend += f'<TR><TD BGCOLOR="{c}">  </TD><TD ALIGN="LEFT">{n}</TD></TR>'
    legend += '</TABLE>>'
    dot.node('legend', label=legend, shape='none')

    return dot.render('temp_organigram', cleanup=True)

def upload_file(session: requests.Session, path: str):
    """Uploads the SVG file directly to the ChurchTools Wiki category."""
    url = f"{BASE_URL}/api/files"
    payload = {'domainType': 'wikicategory', 'domainId': WIKI_CATEGORY_ID}

    try:
        with open(path, 'rb') as f:
            files = {'files[]': ('organigramm.svg', f, 'image/svg+xml')}
            res = session.post(url, data=payload, files=files, timeout=30)
            res.raise_for_status()
            logger.info("Successfully uploaded the organizational chart to ChurchTools.")
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    s = get_session()
    t_map = fetch_meta_data(s)
    g_data = fetch_groups(s)

    file_path = build_svg(g_data, t_map)
    upload_file(s, file_path)

    # Cleanup (optional, since the GitHub runner is ephemeral)
    if os.path.exists(file_path):
        os.remove(file_path)
