# Meraki Template Manager

A web-based dashboard for managing Cisco Meraki configuration template bindings, built with [PyWebIO](https://pywebio.readthedocs.io/). Designed for multi-vendor environments where each vendor should only see and manage their own networks.

---

## Features

- **Multi-org support** — automatically detects all organizations accessible via your API key; prompts selection if more than one is found
- **Tag-based vendor login** — vendors log in by selecting their network tag and entering a password; access is scoped to their tagged networks only
- **Templates tab** — view all configuration templates in the organization (name, ID, product types, timezone)
- **Networks tab** — view all networks scoped to the logged-in vendor's tag, with bound/unbound status
- **Bind / Unbind tab** — bind a network to a configuration template or unbind it, with confirmation prompts
- **Analytics tab** — donut charts and stat cards showing network binding rates, template usage breakdown, and unused templates — scoped to the vendor's tag
- **Changelog tab** — audit log of all bind/unbind actions (timestamp, action, network, template, org, IP address), filtered to the vendor's own networks
- **Session controls** — Refresh, Switch Org, and Logout buttons available on every page

---

## Requirements

- Python 3.8+
- A Cisco Meraki API key with access to your organization(s)

Install dependencies:

```bash
pip install pywebio requests
```

---

## Configuration

Open `TemplateManager.py` and update the following near the top of the file:

### 1. API Key

```python
API_KEY = "your_api_key_here"
```

### 2. Tag → Password Mapping

Map each Meraki network tag to a vendor password. Vendors will only see networks tagged with their assigned tag.

```python
TAG_PASSWORDS = {
    "Vendor1": "password1",
    "Vendor2": "password2",
    "Vendor3": "password3",
}
```

Set `TAG_PASSWORDS = {}` to run in open/dev mode where any password is accepted.

---

## Running the Dashboard

```bash
python3 TemplateManager.py.py
```

The dashboard will start on `http://localhost:8080` and is accessible from any browser on your network.

---

## How It Works

### Login Flow

1. On launch the app connects to the Meraki API and loads your organizations
2. If multiple orgs exist, the user selects one
3. The vendor selects their tag from a dropdown and enters their password
4. On success, all tabs are scoped exclusively to networks carrying that tag — other networks are never visible

### Changelog

Every bind and unbind action is appended to a local `meraki_changelog.json` file stored in the same directory as the script. Each entry records:

| Field | Description |
|---|---|
| Timestamp | UTC time of the action |
| Action | `BIND` or `UNBIND` |
| Network | Name of the affected network |
| Template | Template that was bound (or `—` for unbind) |
| Organization | Org name |
| IP Address | IP of the user who performed the action |

Vendors can only see changelog entries for their own networks. The changelog can be cleared from the UI (with confirmation).

---

## File Structure

```
TemplateManager.py.py     # Main application
meraki_changelog.json     # Auto-created on first bind/unbind action
README.md
```

---

## Security Notes

- **Never commit your API key** — use an environment variable or secrets manager in production
- Passwords in `TAG_PASSWORDS` are stored in plaintext in the script; treat accordingly
- The app binds to `0.0.0.0:8080` by default — restrict access at the network/firewall level as needed
- The changelog stores user IPs as a basic audit trail

---

## License

MIT
