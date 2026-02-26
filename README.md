# Meraki Template Manager

A browser-based dashboard built with Python and PyWebIO for managing Cisco Meraki configuration template bindings — without needing direct access to the Meraki Dashboard.

---

## Overview

Meraki Template Manager gives vendor teams a clean interface to view templates, browse networks, bind/unbind networks to configuration templates, and track all changes made through the tool.

**Key capabilities:**
- View all configuration templates and their product types
- Browse all networks and see which template each is bound to
- Bind any unbound network to a template with a single click
- Unbind networks from their current template
- Analytics dashboard with pie charts and usage statistics
- Changelog that records every bind/unbind action with timestamp and user IP

---

## Technology Stack

| Component | Detail |
|-----------|--------|
| Language | Python 3.8+ |
| Web Framework | PyWebIO |
| API | Cisco Meraki REST API v1 |
| Charts | Pure SVG generated server-side (no dependencies) |
| Changelog | JSON file stored locally (`meraki_changelog.json`) |
| Dependencies | `pywebio`, `requests` |

---

## Requirements

- Python 3.8 or higher
- pip
- Network access to `api.meraki.com` on port 443
- A valid Cisco Meraki API key with read/write access to your organisation

---

## Installation

**1. Install dependencies**

```bash
pip install pywebio requests
```

**2. Set your API key**

Open `meraki_dashboard.py` and replace the placeholder near the top of the file:

```python
API_KEY = "your_meraki_api_key_here"
```

> ⚠️ Never commit your API key to version control. For production, load it from an environment variable instead:
> ```python
> import os
> API_KEY = os.environ.get("MERAKI_API_KEY")
> ```

**3. Run the dashboard**

```bash
python meraki_dashboard.py
```

Open your browser and navigate to:

```
http://localhost:8080
```

For remote access: `http://<server-ip>:8080`

---

## Navigation

| Tab | Purpose |
|-----|---------|
| Templates | Lists all configuration templates with ID, product types, and timezone |
| Networks | Shows all networks, product types, and current template binding status |
| Bind | Bind unbound networks to templates or unbind existing ones |
| Analytics | Pie charts and stat cards showing binding rates and template utilisation |
| Changelog | Log of all bind/unbind actions with timestamp, network, template, and IP |
| Refresh | Reloads data for the current tab from the Meraki API |
| Switch Org | Returns to the organisation selector (multi-org accounts only) |

---

## Usage

### Binding a Network to a Template

1. Click the **Bind** tab
2. Locate the network you want — networks showing a grey **Unbound** badge are available
3. Click **Bind to Template** in the Action column
4. Select a template from the dropdown
5. Click **Confirm Bind** to proceed or **Cancel** to abort

> The action is automatically logged in the Changelog with your IP and a UTC timestamp.

### Unbinding a Network

1. On the **Bind** tab, locate the network showing a green **Bound** badge
2. Click the **Unbind** button
3. Click **Yes, Unbind** to confirm or **Cancel** to abort

---

## Analytics

The Analytics tab provides a visual overview of your organisation's template adoption:

- **Network Binding Status** — pie chart of bound vs unbound networks
- **Template Usage Breakdown** — distribution of networks across active templates
- **Template Utilisation** — pie chart of templates in use vs unused
- **Stat cards** — total networks, bound, unbound, templates in use, unused %, and binding rate
- **Template Usage Detail** — ranked table with share progress bars
- **Unused Templates** — list of templates with no networks currently bound

---

## Changelog

Every successful bind and unbind action is written to `meraki_changelog.json` in the same directory as the script.

### Fields recorded

| Field | Description |
|-------|-------------|
| `timestamp` | Date and time of the action in UTC |
| `action` | `BIND` or `UNBIND` |
| `network` | Name of the affected network |
| `template` | Template applied (or `—` for unbind) |
| `org` | Organisation name |
| `ip` | IP address of the user session |

To clear the log, click **Clear Changelog** on the Changelog tab and confirm.

---

## Deployment

### Local
Run the script directly and access via `localhost:8080`.

### Server
The dashboard binds to `0.0.0.0:8080` by default. For a shared team deployment:

- Deploy on a Linux VM or cloud instance (AWS Lightsail, DigitalOcean, Azure, etc.)
- Run behind an Nginx reverse proxy with HTTPS via Let's Encrypt
- Use `screen` or `systemd` to keep the process running after logout

```bash
# Keep running after logout
screen -S meraki
python meraki_dashboard.py
# Detach: Ctrl+A then D
```

---

## Security

> This dashboard provides full read/write access to your Meraki organisation.

- Store the API key in an environment variable rather than hardcoded in production
- Deploy behind HTTPS — never run on plain HTTP over public networks
- Restrict access via firewall rules or Nginx basic auth
- The changelog records IP addresses but there is no built-in user authentication

---

## Troubleshooting

| Symptom | Resolution |
|---------|------------|
| API authentication failed (401/403) | Verify the API key is correct and has not expired. Regenerate in the Meraki Dashboard. |
| Connection error on startup | Check network access to `api.meraki.com` on port 443. |
| No organisations found | The API key may be scoped to a different account. |
| Bind fails with error | The template type may be incompatible with the network's product types. |
| Changelog file not created | Ensure the script has write permissions to its own directory. |
| Port 8080 already in use | Change the port in the last line: `start_server(app, port=9090, ...)` |

---

## File Reference

| File | Purpose |
|------|---------|
| `meraki_dashboard.py` | Main application — run this to start the dashboard |
| `meraki_changelog.json` | Auto-generated on first action. Stores all bind/unbind history |
| `README.md` | This file |

---

## Obtaining a Meraki API Key

1. Log in to [dashboard.meraki.com](https://dashboard.meraki.com)
2. Go to your **Profile → API access**
3. Click **Generate new API key** and copy the value
4. Ensure the key has Full access or at minimum read + configure access to your organisation

---

*Created by Ibrahim Ahmed*
