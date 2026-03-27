"""
Cisco Meraki Configuration Template Dashboard
Built with PyWebIO for vendor access
Requirements: pip install pywebio requests
"""

import math
import json
import os
from datetime import datetime, timezone
import requests
from pywebio import start_server
from pywebio.input import select, actions, input, PASSWORD
from pywebio.output import (
    put_html, put_table, put_buttons, put_success,
    put_error, put_warning, clear, toast, use_scope, put_row
)
from pywebio.session import set_env, info as session_info

# -------------------------------------------------------------------
# Changelog file — stored next to this script on the server
# -------------------------------------------------------------------
CHANGELOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meraki_changelog.json")

def log_action(action, network_name, template_name, org_name, user_ip="unknown"):
    """Append an action to the changelog JSON file."""
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "action":    action,
        "network":   network_name,
        "template":  template_name,
        "org":       org_name,
        "ip":        user_ip,
    }
    entries = []
    if os.path.exists(CHANGELOG_FILE):
        try:
            with open(CHANGELOG_FILE, "r") as f:
                entries = json.load(f)
        except Exception:
            entries = []
    entries.insert(0, entry)   # newest first
    with open(CHANGELOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)

def get_user_ip():
    """Best-effort IP from PyWebIO session info."""
    try:
        return session_info.user_ip or "unknown"
    except Exception:
        return "unknown"

# -------------------------------------------------------------------
# SET YOUR API KEY HERE
# -------------------------------------------------------------------
API_KEY = "API_KEY_HERE"

BASE_URL = "https://api.meraki.com/api/v1"

LOGIN_ICON = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="52" height="52">
  <!-- Outer circle -->
  <circle cx="32" cy="32" r="28" fill="none" stroke="#1a2f45" stroke-width="2.5"/>
  <!-- Vertical center line -->
  <line x1="32" y1="4" x2="32" y2="60" stroke="#1a2f45" stroke-width="2"/>
  <!-- Horizontal center line -->
  <line x1="4" y1="32" x2="60" y2="32" stroke="#1a2f45" stroke-width="2"/>
  <!-- Top arc -->
  <path d="M 10 18 Q 32 10 54 18" fill="none" stroke="#1a2f45" stroke-width="2"/>
  <!-- Bottom arc -->
  <path d="M 10 46 Q 32 54 54 46" fill="none" stroke="#1a2f45" stroke-width="2"/>
  <!-- Left ellipse -->
  <path d="M 32 4 Q 12 20 12 32 Q 12 44 32 60" fill="none" stroke="#1a2f45" stroke-width="2"/>
  <!-- Right ellipse -->
  <path d="M 32 4 Q 52 20 52 32 Q 52 44 32 60" fill="none" stroke="#1a2f45" stroke-width="2"/>
  <!-- Network nodes -->
  <circle cx="32" cy="32" r="3.5" fill="#1a2f45"/>
  <circle cx="32" cy="8"  r="3"   fill="#1a2f45"/>
  <circle cx="32" cy="56" r="3"   fill="#1a2f45"/>
  <circle cx="8"  cy="32" r="3"   fill="#1a2f45"/>
  <circle cx="56" cy="32" r="3"   fill="#1a2f45"/>
  <!-- Connector lines from center to nodes -->
  <line x1="32" y1="28.5" x2="32" y2="11"  stroke="#1a2f45" stroke-width="1.5" stroke-dasharray="2,2"/>
  <line x1="32" y1="35.5" x2="32" y2="53"  stroke="#1a2f45" stroke-width="1.5" stroke-dasharray="2,2"/>
  <line x1="28.5" y1="32" x2="11"  y2="32" stroke="#1a2f45" stroke-width="1.5" stroke-dasharray="2,2"/>
  <line x1="35.5" y1="32" x2="53"  y2="32" stroke="#1a2f45" stroke-width="1.5" stroke-dasharray="2,2"/>
</svg>'''


# -------------------------------------------------------------------
# Tag -> Password mapping.  Key = Meraki network tag, Value = password.
# Example:
TAG_PASSWORDS = {
     "Vendor1": "Vendor1",
     "Vendor2": "Vendor2",
     "Vendor3": "Vendor3",
     "Vendor4": "Vendor4",
     "Vendor5": "Vendor5",

   }
# Set to {} for dev/open mode (any password accepted).
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Meraki API Helpers
# -------------------------------------------------------------------

def meraki_headers():
    return {
        "X-Cisco-Meraki-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

def meraki_get(endpoint):
    r = requests.get(f"{BASE_URL}{endpoint}", headers=meraki_headers(), timeout=15)
    r.raise_for_status()
    return r.json()

def meraki_post(endpoint, payload=None):
    r = requests.post(f"{BASE_URL}{endpoint}", headers=meraki_headers(),
                      json=payload or {}, timeout=15)
    r.raise_for_status()
    return r.json()

def api_get_organizations():
    return meraki_get("/organizations")

def api_get_templates(org_id):
    return meraki_get(f"/organizations/{org_id}/configTemplates")

def api_get_networks(org_id):
    return meraki_get(f"/organizations/{org_id}/networks")

def api_bind_network(network_id, template_id):
    return meraki_post(f"/networks/{network_id}/bind",
                       {"configTemplateId": template_id, "autoBind": False})

def api_unbind_network(network_id):
    return meraki_post(f"/networks/{network_id}/unbind")

def parse_api_error(e):
    try:
        return "; ".join(e.response.json().get("errors", [str(e)]))
    except Exception:
        return str(e)


# -------------------------------------------------------------------
# UI Helpers
# -------------------------------------------------------------------

def render_header(org_name=None, active_tag=None):
    subtitle = f"Organization: <strong>{org_name}</strong>" if org_name else "Loading..."
    tag_pill = (
        f'<span style="background:rgba(255,255,255,0.18);border:1px solid rgba(255,255,255,0.45);border-radius:20px;padding:3px 14px;font-size:0.78rem;font-weight:600;white-space:nowrap;">&#127991;&nbsp;{active_tag}</span>'
    ) if active_tag else ""
    put_html(f"""
    <div style="background:linear-gradient(135deg,#00bceb 0%,#005073 100%);
                padding:20px 28px;border-radius:10px;margin-bottom:20px;color:white;
                box-shadow:0 4px 15px rgba(0,0,0,0.15);
                display:flex;align-items:center;justify-content:space-between;gap:16px;">
        <div style="display:flex;align-items:center;gap:16px;">
            <div style="font-size:2rem;">&#128193;</div>
            <div>
                <div style="font-size:1.4rem;font-weight:700;">Meraki Template Manager</div>
                <div style="font-size:0.9rem;opacity:0.9;margin-top:3px;">{subtitle}</div>
            </div>
        </div>
        <div>{tag_pill}</div>
    </div>
    """)

def render_nav(current, org_id, org_name, active_tag=None):
    put_buttons(
        [
            {"label": "Templates",  "value": "t",
             "color": "primary" if current == "templates" else "secondary"},
            {"label": "Networks",   "value": "n",
             "color": "primary" if current == "networks" else "secondary"},
            {"label": "Bind",       "value": "b",
             "color": "primary" if current == "bind" else "secondary"},
            {"label": "Analytics",  "value": "a",
             "color": "primary" if current == "analytics" else "secondary"},
            {"label": "Changelog",  "value": "c",
             "color": "primary" if current == "changelog" else "secondary"},
            {"label": "Refresh",    "value": "r", "color": "light"},
            {"label": "Switch Org", "value": "s", "color": "light"},
            {"label": "Logout",     "value": "lo", "color": "danger"},
        ],
        onclick=lambda v: {
            "t":  lambda: page_templates(org_id, org_name, active_tag),
            "n":  lambda: page_networks(org_id, org_name, active_tag),
            "b":  lambda: page_bind(org_id, org_name, active_tag),
            "a":  lambda: page_analytics(org_id, org_name, active_tag),
            "c":  lambda: page_changelog(org_id, org_name, active_tag),
            "r":  lambda: {
                "templates": page_templates,
                "networks":  page_networks,
                "bind":      page_bind,
                "analytics": page_analytics,
                "changelog": page_changelog,
            }[current](org_id, org_name, active_tag),
            "s":  lambda: page_select_org(),
            "lo": lambda: app(),
        }[v]()
    )
    put_html("<hr style='border:none;border-top:1px solid #e2e8f0;margin:14px 0 18px;'>")

def badge(text, color="#00bceb"):
    return (f'<span style="background:{color};color:white;padding:2px 10px;'
            f'border-radius:12px;font-size:0.78rem;font-weight:600;">{text}</span>')

def info_box(text, bg="#e0f2fe", border="#7dd3fc"):
    put_html(f"""
    <div style="background:{bg};border:1px solid {border};border-radius:8px;
                padding:12px 16px;margin-bottom:16px;font-size:0.9rem;">{text}</div>""")

def section_title(text):
    put_html(f"""
    <div style="border-left:4px solid #00bceb;padding:6px 14px;background:#f8fafc;
                border-radius:0 6px 6px 0;margin:0 0 14px;">
        <strong style="color:#1a2f45;">{text}</strong>
    </div>""")

def status_text(text):
    put_html(f"<p style='color:#64748b;font-style:italic;'>{text}</p>")

def svg_pie(slices, size=220):
    total = sum(v for _, v, _ in slices)
    if total == 0:
        return (f"<svg width='{size}' height='{size}'>"
                f"<text x='50%' y='50%' text-anchor='middle' fill='#94a3b8'>No data</text></svg>")
    cx = cy = size / 2
    r_outer = size / 2 - 10
    r_inner = r_outer * 0.55
    angle = -math.pi / 2
    paths = []
    for label, value, color in slices:
        sweep = (value / total) * 2 * math.pi
        end_angle = angle + sweep
        x1o = cx + r_outer * math.cos(angle)
        y1o = cy + r_outer * math.sin(angle)
        x2o = cx + r_outer * math.cos(end_angle)
        y2o = cy + r_outer * math.sin(end_angle)
        x1i = cx + r_inner * math.cos(end_angle)
        y1i = cy + r_inner * math.sin(end_angle)
        x2i = cx + r_inner * math.cos(angle)
        y2i = cy + r_inner * math.sin(angle)
        large = 1 if sweep > math.pi else 0
        pct = round((value / total) * 100)
        paths.append(
            f'<path d="M {x1o:.2f} {y1o:.2f} A {r_outer:.2f} {r_outer:.2f} 0 {large} 1 '
            f'{x2o:.2f} {y2o:.2f} L {x1i:.2f} {y1i:.2f} A {r_inner:.2f} {r_inner:.2f} 0 '
            f'{large} 0 {x2i:.2f} {y2i:.2f} Z" fill="{color}" stroke="white" stroke-width="2">'
            f'<title>{label}: {value} ({pct}%)</title></path>'
        )
        angle = end_angle
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
            f'style="display:block;margin:0 auto;">{"".join(paths)}</svg>')


# -------------------------------------------------------------------
# App Entry Point
# -------------------------------------------------------------------

def app():
    clear()
    set_env(title="Meraki Template Manager")
    render_header()
    status_text("Connecting to Meraki...")
    try:
        orgs = api_get_organizations()
    except requests.exceptions.HTTPError as e:
        put_error(f"API authentication failed ({e.response.status_code}). "
                  f"Please contact your administrator.")
        return
    except Exception as e:
        put_error(f"Connection error: {e}")
        put_buttons(["Retry"], onclick=lambda _: app())
        return
    if not orgs:
        put_warning("No organizations found for the configured API key.")
        return
    if len(orgs) == 1:
        page_login(orgs[0]["id"], orgs[0]["name"])
    else:
        page_select_org(orgs)


# -------------------------------------------------------------------
# Page: Select Organization
# -------------------------------------------------------------------

def page_select_org(orgs=None):
    clear()
    render_header()
    if orgs is None:
        status_text("Loading organizations...")
        try:
            orgs = api_get_organizations()
        except Exception as e:
            put_error(f"Failed to load organizations: {e}")
            put_buttons(["Retry"], onclick=lambda _: page_select_org())
            return
    org_names = [o["name"] for o in orgs]
    org_map   = {o["name"]: o["id"] for o in orgs}
    section_title(f"Select Organization ({len(orgs)} available)")
    chosen = select("Choose an organization", options=org_names,
                    help_text="Select which Meraki organization to manage")
    page_login(org_map[chosen], chosen)


# -------------------------------------------------------------------
# Page: Login
# -------------------------------------------------------------------

def page_login(org_id, org_name):
    """
    Login gate.
    - Fetches all network tags live from the Meraki API.
    - Uses select() for the tag dropdown and input(type=PASSWORD) for
      the password — both are valid PyWebIO widgets.
    - FIX 1: Wrong password → shows an error banner and loops; the user
      cannot proceed until the correct password is entered.
    - active_tag is passed through every page so analytics (FIX 2) and
      all other tabs only show data for that tag's networks.
    """
    try:
        all_networks = api_get_networks(org_id)
    except Exception as e:
        clear()
        render_header(org_name)
        put_error(f"Failed to load networks for tag list: {e}")
        put_buttons(["Retry"], onclick=lambda _: page_login(org_id, org_name))
        return

    all_tags = sorted({tag for n in all_networks for tag in n.get("tags", [])})

    if not all_tags:
        clear()
        render_header(org_name)
        put_warning(
            "No network tags found in this organisation. "
            "Please add tags to your networks in the Meraki Dashboard first."
        )
        put_buttons(
            [
                {"label": "Retry",   "value": "retry", "color": "primary"},
                {"label": "Go Back", "value": "back",  "color": "secondary"},
            ],
            onclick=lambda v: page_login(org_id, org_name) if v == "retry" else page_select_org()
        )
        return

    if TAG_PASSWORDS:
        available_tags = [t for t in all_tags if t in TAG_PASSWORDS]
        if not available_tags:
            clear()
            render_header(org_name)
            put_warning(
                "No network tags match the TAG_PASSWORDS configuration. "
                "Please update TAG_PASSWORDS in the script."
            )
            return
    else:
        available_tags = all_tags   # dev/open mode

    show_error = False  # set True after a failed attempt to display the banner

    while True:   # keep looping until correct credentials are entered
        clear()
        render_header(org_name)

        # Error banner — only shown after at least one failed attempt
        if show_error:
            put_html("""
            <div style="max-width:460px;margin:0 auto 16px;">
              <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;
                          padding:12px 18px;display:flex;align-items:center;gap:12px;">
                <span style="font-size:1.3rem;">&#10060;</span>
                <div>
                  <div style="font-weight:700;color:#b91c1c;font-size:0.9rem;">
                    Unable to login</div>
                  <div style="color:#64748b;font-size:0.82rem;margin-top:2px;">
                    The password you entered is incorrect. Please try again.</div>
                </div>
              </div>
            </div>""")

        # Card shell
        put_html(f"""
        <div style="max-width:460px;margin:0 auto;">
          <div style="background:white;border-radius:14px;
                      box-shadow:0 4px 24px rgba(0,0,0,0.10);
                      border:1px solid #e2e8f0;overflow:hidden;">
            <div style="padding:28px 32px 28px;">
              <div style="display:flex;align-items:center;gap:14px;margin-bottom:4px;">
                <div style="flex-shrink:0;">{LOGIN_ICON}</div>
                <div>
                  <div style="font-size:1.2rem;font-weight:700;color:#1a2f45;">
                    Vendor Portal Login</div>
                  <div style="color:#64748b;font-size:0.85rem;margin-top:3px;">
                    Select your vendor and enter your password to continue.</div>
                </div>
              </div>
              <div style="margin-top:16px;"></div>
        """)

        # Tag dropdown — select() is the correct PyWebIO widget for this
        chosen_tag = select(
            "Select Your Vendor",
            options=available_tags,
            help_text="Select the network tag assigned to your account",
        )

        # Password field — input(type=PASSWORD) is valid
        entered_pw = input(
            "Password",
            type=PASSWORD,
            placeholder="Enter your password",
        )

        put_html("</div></div></div>")  # close card

        # ── FIX 1: validate password — loop back on failure, never let through ──
        if TAG_PASSWORDS:
            if entered_pw != TAG_PASSWORDS.get(chosen_tag, ""):
                show_error = True
                continue    # re-render login form with error banner; do NOT proceed

        # Correct credentials (or open/dev mode) — enter the dashboard
        toast(f"Logged in — tag: {chosen_tag}", color="success", duration=3)
        page_templates(org_id, org_name, active_tag=chosen_tag)
        return


# -------------------------------------------------------------------
# Page: Templates
# -------------------------------------------------------------------

def page_templates(org_id, org_name, active_tag=None):
    clear()
    render_header(org_name, active_tag)
    render_nav("templates", org_id, org_name, active_tag)
    section_title("Configuration Templates")
    info_box("<strong>Configuration Templates</strong> define shared settings applied across "
             "multiple networks. Use the <strong>Bind</strong> tab to attach networks to a template.")
    status_text("Fetching templates...")
    try:
        templates = api_get_templates(org_id)
    except Exception as e:
        put_error(f"Failed to load templates: {e}")
        return
    if not templates:
        put_warning("No configuration templates found. Create one in the Meraki Dashboard first.")
        return
    put_html(f"<p style='color:#64748b;margin-bottom:12px;'>Showing <strong>{len(templates)}</strong> template(s)</p>")
    rows = [["Template Name", "Template ID", "Product Types", "Timezone"]]
    for t in templates:
        product_types = ", ".join(t.get("productTypes", [])) or "N/A"
        rows.append([
            put_html(f"<strong style='color:#1a2f45;'>{t.get('name','Unnamed')}</strong>"),
            put_html(f"<code style='font-size:0.8rem;background:#f1f5f9;padding:2px 6px;"
                     f"border-radius:4px;'>{t['id']}</code>"),
            put_html(f'<span style="background:#B9D9EB;color:#2d4a5a;padding:2px 10px;border-radius:3px;font-size:0.78rem;font-weight:600;">{product_types}</span>'),
            t.get("timeZone", "N/A"),
        ])
    put_table(rows)


# -------------------------------------------------------------------
# Page: Networks
# -------------------------------------------------------------------

def page_networks(org_id, org_name, active_tag=None):
    clear()
    render_header(org_name, active_tag)
    render_nav("networks", org_id, org_name, active_tag)
    section_title("Networks")
    if active_tag:
        info_box(
            f"Showing networks tagged <strong>{active_tag}</strong>. "
            "Networks bound to a template show a <strong style='color:#16a34a;'>green badge</strong>. "
            "Unbound networks can be linked from the <strong>Bind</strong> tab.",
            "#f0fdf4", "#86efac"
        )
    else:
        info_box("Networks bound to a template show a <strong style='color:#16a34a;'>green badge</strong>. "
                 "Unbound networks can be linked from the <strong>Bind</strong> tab.",
                 "#f0fdf4", "#86efac")
    status_text("Fetching networks...")
    try:
        networks  = api_get_networks(org_id)
        templates = api_get_templates(org_id)
    except Exception as e:
        put_error(f"Failed to load data: {e}")
        return
    if active_tag:
        networks = [n for n in networks if active_tag in n.get("tags", [])]
    if not networks:
        put_warning(
            f"No networks found for tag '{active_tag}'." if active_tag
            else "No networks found for this organization."
        )
        return
    template_map = {t["id"]: t["name"] for t in templates}
    bound_count  = sum(1 for n in networks if n.get("configTemplateId"))
    put_html(f"""
    <div style="display:flex;gap:14px;margin-bottom:16px;flex-wrap:wrap;">
        <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;
                    padding:10px 20px;text-align:center;min-width:90px;">
            <div style="font-size:1.4rem;font-weight:700;color:#0369a1;">{len(networks)}</div>
            <div style="font-size:0.8rem;color:#64748b;">Total</div>
        </div>
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                    padding:10px 20px;text-align:center;min-width:90px;">
            <div style="font-size:1.4rem;font-weight:700;color:#16a34a;">{bound_count}</div>
            <div style="font-size:0.8rem;color:#64748b;">Bound</div>
        </div>
        <div style="background:#fafafa;border:1px solid #e2e8f0;border-radius:8px;
                    padding:10px 20px;text-align:center;min-width:90px;">
            <div style="font-size:1.4rem;font-weight:700;color:#94a3b8;">{len(networks)-bound_count}</div>
            <div style="font-size:0.8rem;color:#64748b;">Unbound</div>
        </div>
    </div>
    """)
    rows = [["Network Name", "Network ID", "Product Types", "Bound Template"]]
    for n in networks:
        product_types = ", ".join(n.get("productTypes", [])) or "N/A"
        bound_id = n.get("configTemplateId")
        if bound_id:
            tname_display = template_map.get(bound_id, bound_id)
            bound_cell = put_html(f'<span style="background:#16a34a;color:white;padding:2px 10px;'
                                  f'border-radius:3px;font-size:0.78rem;font-weight:600;">{tname_display}</span>')
        else:
            bound_cell = put_html(badge("Unbound", "#94a3b8"))
        rows.append([
            put_html(f"<strong>{n.get('name','Unnamed')}</strong>"),
            put_html(f"<code style='font-size:0.78rem;background:#f1f5f9;padding:2px 6px;"
                     f"border-radius:4px;'>{n['id']}</code>"),
            put_html(f'<span style="background:#B9D9EB;color:#2d4a5a;padding:2px 10px;border-radius:3px;font-size:0.78rem;font-weight:600;">{product_types}</span>'),
            bound_cell,
        ])
    put_table(rows)


# -------------------------------------------------------------------
# Page: Bind Networks
# -------------------------------------------------------------------

def page_bind(org_id, org_name, active_tag=None):
    clear()
    render_header(org_name, active_tag)
    render_nav("bind", org_id, org_name, active_tag)
    section_title("Bind / Unbind Networks")
    info_box("Binding a network to a template overwrites conflicting network-level settings. "
             "Unbinding detaches the network but retains its last configuration.",
             "#fffbeb", "#fde68a")
    status_text("Loading networks and templates...")
    try:
        networks  = api_get_networks(org_id)
        templates = api_get_templates(org_id)
    except Exception as e:
        put_error(f"Failed to load data: {e}")
        return
    if not templates:
        put_error("No configuration templates available. Create one in the Meraki Dashboard first.")
        return
    if active_tag:
        networks = [n for n in networks if active_tag in n.get("tags", [])]
    if not networks:
        put_error(
            f"No networks found for tag '{active_tag}'." if active_tag
            else "No networks found for this organization."
        )
        return

    template_map    = {t["id"]: t["name"] for t in templates}
    template_opts   = [t["name"] for t in templates]
    template_id_map = {t["name"]: t["id"] for t in templates}

    # Render all networks as a single styled table with put_table
    # Each action column contains a put_buttons widget
    rows = [["Network", "Tags", "Status", "Action"]]
    for n in networks:
        bound_id = n.get("configTemplateId")
        net_id   = n["id"]
        net_name = n.get("name", "Unnamed")

        if bound_id:
            tname       = template_map.get(bound_id, bound_id)
            status_cell = put_html(badge(f"Bound: {tname}", "#16a34a"))
            action_cell = put_buttons(
                [{"label": "Unbind", "value": "u", "color": "warning"}],
                onclick=lambda _, nid=net_id, nname=net_name: _unbind_action(
                    nid, nname, org_id, org_name, active_tag)
            )
        else:
            status_cell = put_html(badge("Unbound", "#94a3b8"))
            action_cell = put_buttons(
                [{"label": "Bind to Template", "value": "b", "color": "info"}],
                onclick=lambda _, nid=net_id, nname=net_name: _bind_action(
                    nid, nname, template_opts, template_id_map, org_id, org_name, active_tag)
            )

        tags = ", ".join(n.get("tags", [])) or "-"
        rows.append([
            put_html(f"<strong style='color:#1a2f45;'>{net_name}</strong>"),
            put_html(f"<span style='color:#64748b;font-size:0.85rem;'>{tags}</span>"),
            status_cell,
            action_cell,
        ])

    put_table(rows)


# -------------------------------------------------------------------
# Bind Action — triggered per row
# -------------------------------------------------------------------

def _bind_action(network_id, network_name, template_opts, template_id_map, org_id, org_name, active_tag=None):
    # Show inline form with red X cancel
    put_html(f"""
    <div style="background:white;border:1px solid #e2e8f0;border-radius:10px;
                padding:20px 24px;margin:8px 0 16px;box-shadow:0 2px 8px rgba(0,0,0,0.08);
                border-left:4px solid #00bceb;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <strong style="color:#1a2f45;font-size:1rem;">Bind: {network_name}</strong>
        </div>
        <p style="margin:0 0 4px;color:#64748b;font-size:0.85rem;">
            Select a configuration template to apply to this network.
        </p>
    </div>
    """)

    chosen_tmpl_name = select(
        f'Select a template to bind to "{network_name}"',
        options=template_opts,
        help_text="Choose the configuration template to apply"
    )
    chosen_tmpl_id = template_id_map[chosen_tmpl_name]

    confirmed = actions(
        f'Bind "{network_name}" to "{chosen_tmpl_name}"?',
        [
            {"label": "Confirm Bind", "value": "confirm", "color": "success"},
            {"label": "Cancel",       "value": "cancel",  "color": "danger"},
        ]
    )
    if confirmed in ("cancel", "exit"):
        toast("Bind cancelled.", color="info")
        page_bind(org_id, org_name, active_tag)
        return

    status_text(f"Binding {network_name}...")
    try:
        api_bind_network(network_id, chosen_tmpl_id)
    except requests.exceptions.HTTPError as e:
        put_error(f"Bind failed: {parse_api_error(e)}")
        put_buttons(["Try Again"], onclick=lambda _: page_bind(org_id, org_name, active_tag))
        return
    except Exception as e:
        put_error(f"Unexpected error: {e}")
        return

    log_action("BIND", network_name, chosen_tmpl_name, org_name, get_user_ip())
    toast(f"'{network_name}' bound to '{chosen_tmpl_name}'!", color="success", duration=4)
    page_bind(org_id, org_name, active_tag)


# -------------------------------------------------------------------
# Unbind Action — triggered per row
# -------------------------------------------------------------------

def _unbind_action(network_id, network_name, org_id, org_name, active_tag=None):
    confirmed = actions(
        f'Unbind "{network_name}" from its current template?',
        [
            {"label": "Yes, Unbind", "value": "confirm", "color": "warning"},
            {"label": "Cancel",      "value": "cancel",  "color": "danger"},
        ]
    )
    if confirmed in ("cancel", "exit"):
        toast("Unbind cancelled.", color="info")
        page_bind(org_id, org_name, active_tag)
        return

    status_text(f"Unbinding {network_name}...")
    try:
        api_unbind_network(network_id)
    except requests.exceptions.HTTPError as e:
        put_error(f"Unbind failed: {parse_api_error(e)}")
        return
    except Exception as e:
        put_error(f"Unexpected error: {e}")
        return

    log_action("UNBIND", network_name, "—", org_name, get_user_ip())
    toast(f"'{network_name}' has been unbound.", color="success", duration=4)
    page_bind(org_id, org_name, active_tag)


# -------------------------------------------------------------------
# Page: Analytics
# -------------------------------------------------------------------

def page_analytics(org_id, org_name, active_tag=None):
    clear()
    render_header(org_name, active_tag)
    render_nav("analytics", org_id, org_name, active_tag)
    section_title("Analytics")

    status_text("Loading analytics data...")
    try:
        networks  = api_get_networks(org_id)
        templates = api_get_templates(org_id)
    except Exception as e:
        put_error(f"Failed to load data: {e}")
        return
    # FIX 2: scope analytics to the logged-in tag's networks only
    if active_tag:
        networks = [n for n in networks if active_tag in n.get("tags", [])]
    if not networks:
        put_warning(
            f"No networks found for tag '{active_tag}'." if active_tag
            else "No networks found for this organization."
        )
        return

    total   = len(networks)
    bound   = sum(1 for n in networks if n.get("configTemplateId"))
    unbound = total - bound

    usage = {}
    for n in networks:
        tid = n.get("configTemplateId")
        if tid:
            usage[tid] = usage.get(tid, 0) + 1

    template_name_map = {t["id"]: t["name"] for t in templates}
    total_templates   = len(templates)
    used_template_ids = set(usage.keys())
    unused_templates  = [t for t in templates if t["id"] not in used_template_ids]
    unused_tmpl_count = len(unused_templates)
    used_tmpl_count   = total_templates - unused_tmpl_count
    unused_tmpl_pct   = round((unused_tmpl_count / total_templates) * 100) if total_templates else 0
    binding_rate      = round((bound / total) * 100) if total else 0

    palette = ["#00bceb","#005073","#0ea5e9","#6366f1","#8b5cf6",
               "#ec4899","#f59e0b","#10b981","#ef4444","#14b8a6"]

    usage_by_name = [
        (template_name_map.get(tid, tid), count, palette[i % len(palette)])
        for i, (tid, count) in enumerate(sorted(usage.items(), key=lambda x: -x[1]))
    ]

    # Pie 1: Bound vs Unbound networks
    pie1_slices = [("Bound", bound, "#00bceb"), ("Unbound", unbound, "#e2e8f0")]
    pie1_svg    = svg_pie(pie1_slices)
    legend1 = "".join(
        f'<span style="font-size:0.82rem;color:#555;margin:4px 8px;display:inline-flex;'
        f'align-items:center;gap:5px;">'
        f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
        f'background:{c};flex-shrink:0;"></span>{l} ({v})</span>'
        for l, v, c in pie1_slices
    )

    # Pie 2: Template usage breakdown
    if usage_by_name:
        pie2_svg = svg_pie(usage_by_name)
        legend2  = "".join(
            f'<span style="font-size:0.82rem;color:#555;margin:4px 8px;display:inline-flex;'
            f'align-items:center;gap:5px;">'
            f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
            f'background:{c};flex-shrink:0;"></span>{l} ({v})</span>'
            for l, v, c in usage_by_name
        )
    else:
        pie2_svg = "<div style='text-align:center;color:#94a3b8;padding:80px 0;font-size:0.9rem;'>No networks bound yet</div>"
        legend2  = ""

    # Pie 3: Template utilisation
    pie3_slices = [("In Use", used_tmpl_count, "#10b981"), ("Unused", unused_tmpl_count, "#fca5a5")]
    pie3_svg    = svg_pie(pie3_slices)
    legend3 = "".join(
        f'<span style="font-size:0.82rem;color:#555;margin:4px 8px;display:inline-flex;'
        f'align-items:center;gap:5px;">'
        f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
        f'background:{c};flex-shrink:0;"></span>{l} ({v})</span>'
        for l, v, c in pie3_slices
    )

    # Template detail table rows
    table_rows = ""
    for i, (name, count, color) in enumerate(usage_by_name):
        pct = round((count / bound) * 100) if bound else 0
        table_rows += f"""
        <tr style="border-bottom:1px solid #f1f5f9;">
            <td style="padding:9px 12px;color:#94a3b8;font-size:0.85rem;">{i+1}</td>
            <td style="padding:9px 12px;">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;
                             background:{color};margin-right:7px;vertical-align:middle;"></span>
                <strong>{name}</strong>
            </td>
            <td style="padding:9px 12px;font-weight:600;color:#1a2f45;">{count}</td>
            <td style="padding:9px 12px;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <div style="background:#f1f5f9;border-radius:99px;height:8px;width:120px;overflow:hidden;">
                        <div style="background:{color};height:100%;width:{pct}%;border-radius:99px;"></div>
                    </div>
                    <span style="font-size:0.82rem;color:#64748b;">{pct}%</span>
                </div>
            </td>
        </tr>"""

    # Unused templates rows
    unused_rows = "".join(
        f'<tr style="border-bottom:1px solid #f1f5f9;">'
        f'<td style="padding:8px 12px;font-size:0.85rem;color:#94a3b8;">{i+1}</td>'
        f'<td style="padding:8px 12px;"><strong>{t["name"]}</strong></td>'
        f'<td style="padding:8px 12px;">'
        f'<span style="background:#fca5a5;color:#7f1d1d;padding:2px 10px;'
        f'border-radius:12px;font-size:0.78rem;font-weight:600;">Unused</span></td>'
        f'</tr>'
        for i, t in enumerate(unused_templates)
    )

    put_html(f"""
    <!-- Stat cards -->
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:24px;">
        <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;
                    padding:14px 20px;text-align:center;flex:1;min-width:100px;">
            <div style="font-size:1.6rem;font-weight:700;color:#0369a1;">{total}</div>
            <div style="font-size:0.8rem;color:#64748b;">Total Networks</div>
        </div>
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                    padding:14px 20px;text-align:center;flex:1;min-width:100px;">
            <div style="font-size:1.6rem;font-weight:700;color:#16a34a;">{bound}</div>
            <div style="font-size:0.8rem;color:#64748b;">Bound Networks</div>
        </div>
        <div style="background:#fafafa;border:1px solid #e2e8f0;border-radius:8px;
                    padding:14px 20px;text-align:center;flex:1;min-width:100px;">
            <div style="font-size:1.6rem;font-weight:700;color:#94a3b8;">{unbound}</div>
            <div style="font-size:0.8rem;color:#64748b;">Unbound Networks</div>
        </div>
        <div style="background:#faf5ff;border:1px solid #ddd6fe;border-radius:8px;
                    padding:14px 20px;text-align:center;flex:1;min-width:100px;">
            <div style="font-size:1.6rem;font-weight:700;color:#7c3aed;">{total_templates}</div>
            <div style="font-size:0.8rem;color:#64748b;">Total Templates</div>
        </div>
        <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;
                    padding:14px 20px;text-align:center;flex:1;min-width:100px;">
            <div style="font-size:1.6rem;font-weight:700;color:#ea580c;">{used_tmpl_count}</div>
            <div style="font-size:0.8rem;color:#64748b;">Templates In Use</div>
        </div>
        <div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:8px;
                    padding:14px 20px;text-align:center;flex:1;min-width:100px;">
            <div style="font-size:1.6rem;font-weight:700;color:#e11d48;">{unused_tmpl_pct}%</div>
            <div style="font-size:0.8rem;color:#64748b;">Templates Unused</div>
        </div>
        <div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;
                    padding:14px 20px;text-align:center;flex:1;min-width:100px;">
            <div style="font-size:1.6rem;font-weight:700;color:#059669;">{binding_rate}%</div>
            <div style="font-size:0.8rem;color:#64748b;">Network Binding Rate</div>
        </div>
    </div>

    <!-- Pie charts -->
    <div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:24px;">
        <div style="background:white;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.07);
                    padding:24px;flex:1;min-width:260px;">
            <h3 style="margin:0 0 4px;color:#1a2f45;font-size:1rem;">Network Binding Status</h3>
            <p style="margin:0 0 16px;color:#64748b;font-size:0.83rem;">
                {bound} of {total} networks bound to a template</p>
            {pie1_svg}
            <div style="display:flex;flex-wrap:wrap;justify-content:center;margin-top:14px;">{legend1}</div>
        </div>
        <div style="background:white;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.07);
                    padding:24px;flex:1;min-width:260px;">
            <h3 style="margin:0 0 4px;color:#1a2f45;font-size:1rem;">Template Usage Breakdown</h3>
            <p style="margin:0 0 16px;color:#64748b;font-size:0.83rem;">
                Distribution across {len(usage_by_name)} active template(s)</p>
            {pie2_svg}
            <div style="display:flex;flex-wrap:wrap;justify-content:center;margin-top:14px;">{legend2}</div>
        </div>
        <div style="background:white;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.07);
                    padding:24px;flex:1;min-width:260px;">
            <h3 style="margin:0 0 4px;color:#1a2f45;font-size:1rem;">Template Utilisation</h3>
            <p style="margin:0 0 16px;color:#64748b;font-size:0.83rem;">
                {unused_tmpl_pct}% of templates ({unused_tmpl_count} of {total_templates}) not bound to any network</p>
            {pie3_svg}
            <div style="display:flex;flex-wrap:wrap;justify-content:center;margin-top:14px;">{legend3}</div>
        </div>
    </div>

    <!-- Template usage detail + Unused templates side by side -->
    <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start;">

        {"" if not usage_by_name else f"""
        <div style="background:white;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.07);
                    padding:20px;flex:1;min-width:280px;">
            <h3 style="margin:0 0 14px;color:#1a2f45;font-size:1rem;">Template Usage Detail</h3>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
                        <th style="padding:9px 12px;text-align:left;color:#475569;font-size:0.83rem;">#</th>
                        <th style="padding:9px 12px;text-align:left;color:#475569;font-size:0.83rem;">Template</th>
                        <th style="padding:9px 12px;text-align:left;color:#475569;font-size:0.83rem;">Networks Bound</th>
                        <th style="padding:9px 12px;text-align:left;color:#475569;font-size:0.83rem;">Share</th>
                    </tr>
                </thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
        """}

        {"" if not unused_templates else f"""
        <div style="background:white;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.07);
                    padding:20px;flex:1;min-width:280px;">
            <h3 style="margin:0 0 6px;color:#1a2f45;font-size:1rem;">Unused Templates</h3>
            <p style="margin:0 0 14px;color:#64748b;font-size:0.83rem;">
                These templates have no networks currently bound to them.</p>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#fff1f2;border-bottom:2px solid #fecdd3;">
                        <th style="padding:9px 12px;text-align:left;color:#475569;font-size:0.83rem;">#</th>
                        <th style="padding:9px 12px;text-align:left;color:#475569;font-size:0.83rem;">Template Name</th>
                        <th style="padding:9px 12px;text-align:left;color:#475569;font-size:0.83rem;">Status</th>
                    </tr>
                </thead>
                <tbody>{unused_rows}</tbody>
            </table>
        </div>
        """}

    </div>
    """)



# -------------------------------------------------------------------
# Page: Changelog
# -------------------------------------------------------------------

def page_changelog(org_id, org_name, active_tag=None):
    clear()
    render_header(org_name, active_tag)
    render_nav("changelog", org_id, org_name, active_tag)
    section_title("Changelog")

    info_box("A record of all bind and unbind actions taken through this dashboard. "
             "Each entry includes the time, action, network, template, and the IP address "
             "of the user who performed it.", "#e0f2fe", "#7dd3fc")

    # Load entries
    entries = []
    if os.path.exists(CHANGELOG_FILE):
        try:
            with open(CHANGELOG_FILE, "r") as f:
                entries = json.load(f)
        except Exception as e:
            put_error(f"Failed to read changelog: {e}")
            return

    # Filter entries to only show networks belonging to the logged-in tag
    if active_tag:
        try:
            all_networks = api_get_networks(org_id)
            tag_network_names = {
                n["name"] for n in all_networks
                if active_tag in n.get("tags", [])
            }
            entries = [e for e in entries if e.get("network") in tag_network_names]
        except Exception as e:
            put_error(f"Failed to filter changelog by tag: {e}")
            return

    put_buttons(
        [{"label": "Clear Changelog", "value": "clear", "color": "danger"}],
        onclick=lambda _: _confirm_clear_changelog(org_id, org_name, active_tag)
    )
    put_html("<div style='margin-bottom:14px;'></div>")

    if not entries:
        put_html("""
        <div style="text-align:center;padding:60px 20px;color:#94a3b8;">
            <div style="font-size:2.5rem;margin-bottom:10px;">&#128203;</div>
            <div style="font-size:1rem;font-weight:600;">No actions recorded yet</div>
            <div style="font-size:0.85rem;margin-top:6px;">
                Bind or unbind a network to see entries here.</div>
        </div>
        """)
        return

    put_html(f"<p style='color:#64748b;margin-bottom:12px;'>"
             f"Showing <strong>{len(entries)}</strong> recorded action(s) — newest first</p>")

    rows = [["Timestamp", "Action", "Network", "Template", "Organization", "IP Address"]]
    for e in entries:
        action      = e.get("action", "?")
        action_color = "#16a34a" if action == "BIND" else "#f59e0b"
        rows.append([
            put_html(f"<span style='font-size:0.82rem;color:#64748b;'>{e.get('timestamp','?')}</span>"),
            put_html(f"<span style='background:{action_color};color:white;padding:2px 10px;"
                     f"border-radius:12px;font-size:0.78rem;font-weight:600;'>{action}</span>"),
            put_html(f"<strong>{e.get('network','?')}</strong>"),
            e.get("template", "?"),
            e.get("org", "?"),
            put_html(f"<code style='font-size:0.78rem;background:#f1f5f9;padding:2px 6px;"
                     f"border-radius:4px;'>{e.get('ip','?')}</code>"),
        ])
    put_table(rows)


def _confirm_clear_changelog(org_id, org_name, active_tag=None):
    confirmed = actions(
        "Clear the entire changelog? This cannot be undone.",
        [
            {"label": "Yes, Clear All", "value": True,  "color": "danger"},
            {"label": "Cancel",         "value": False, "color": "secondary"},
        ]
    )
    if not confirmed:
        toast("Cancelled.", color="info")
        return
    try:
        with open(CHANGELOG_FILE, "w") as f:
            json.dump([], f)
        toast("Changelog cleared.", color="success", duration=3)
    except Exception as e:
        put_error(f"Failed to clear changelog: {e}")
        return
    page_changelog(org_id, org_name, active_tag)

# -------------------------------------------------------------------
# Entry Point
# -------------------------------------------------------------------

if __name__ == "__main__":
    print("Meraki Dashboard running at http://localhost:8080")
    start_server(app, port=8080, host="0.0.0.0", debug=False, auto_open_webbrowser=False)
