# NC–NDFC Ansible Playbooks

Automate Cisco **Nexus Dashboard Fabric Controller (NDFC)** provisioning and day‑2 operations: build a fabric, onboard switches, create VRFs and networks, define vPC peers & interfaces, run validations, and orchestrate upgrades.

> **Tested template:** Easy_Fabric (FABRIC_TYPE: `Switch_Fabric`).
>
> These playbooks assume an Easy_Fabric build with common `nvPairs` such as `BGP_AS`, `FABRIC_INTERFACE_TYPE`, and loopback definitions. Adjust as needed if you use another template.

---

## What this repository automates

* **Fabric lifecycle**: create/add fabric objects and build them end‑to‑end.
* **Device lifecycle**: pre‑provision and add switches to the fabric.
* **L3 constructs**: VRFs and routed networks (SVIs / VNIs as applicable to fabric template).
* **vPC formation**: define vPC pairs and related parameters.
* **Interfaces**: access/trunk/routed interfaces per host/role.
* **Health & validation**: sanity checks and post‑change validation reports.
* **Upgrades**: stage, run, and verify NDFC‑driven device upgrades.

---

## Repository layout

```
NC-NDFC-playbooks/
├─ add_fabric.yml              # Create a fabric object (metadata & nvPairs)
├─ build_fabric.yml            # Orchestrate full build flow (wrapper)
├─ add_switches.yml            # Discover/add switches to the fabric
├─ preprovision_switches.yml   # Pre-provision nodes and roles
├─ add_vrfs.yml                # Create VRFs
├─ add_networks.yml            # Create L2/L3 networks in VRFs
├─ add_vpc_pair.yml            # Define vPC pairs
├─ add_interfaces.yml          # Configure interfaces (access/trunk/routed)
├─ Validate_vrfs_networks.yml  # Validate VRF/network state
├─ sanity_report.yml           # Collect health & compliance data
├─ stage_upgrade.yml           # Stage images for upgrade
├─ run_upgrade.yml             # Execute upgrade
├─ verify_upgrade.yml          # Post-upgrade checks
├─ ndfc_hosts.yml              # Inventory entry for the NDFC controller
├─ ansible.cfg                 # Ansible config tuned for these playbooks
├─ collections/                # (Optional) vendored collections
├─ filter_plugins/             # Custom Jinja2 filters (if used by tasks)
├─ group_vars/                 # Global/subgroup variables (fabric, vrfs, etc.)
├─ inventories/                # Environment-specific inventories (lab/prod)
├─ tasks/                      # Shared include/task files
└─ reports/                    # Generated CSV/JSON/Markdown reports
```

---

## Prerequisites

* **Ansible** 2.15+ (or AAP equivalent)
* **Python** 3.9+
* **Cisco NDFC** reachable from your Ansible control node (API access)
* **Ansible collections** to control NDFC (installed via `collections/` vendoring or `ansible-galaxy`)
* **Credentials** for NDFC with API permissions (read/write for fabric & inventory)

> If you’re using a different NDFC template than Easy_Fabric, review the `nvPairs` in your `group_vars` and tailor examples below accordingly.

---

## Quick start

1. **Clone & enter** the repo

   ```bash
   git clone <this-repo-url>
   cd NC-NDFC-playbooks
   ```

2. **Collections**

   * If `collections/` is already populated, you can use it as vendored dependencies.
   * Otherwise, install required collections (example):

     ```bash
     ansible-galaxy collection install cisco.dcnm
     # or your internal requirements: ansible-galaxy install -r collections/requirements.yml
     ```

3. **Set inventory**

   * Minimal NDFC host inventory is provided in `ndfc_hosts.yml`. You can also maintain per‑env inventories under `inventories/`.

4. **Provide credentials** (choose one):

   * **Environment variables**

     ```bash
     export NDFC_HOST="ndfc.example.com"
     export NDFC_USERNAME="admin"
     export NDFC_PASSWORD="<secret>"
     ```
   * **Ansible Vault** (recommended for shared repos)

     ```yaml
     # group_vars/all/ndfc_auth.yml (vaulted)
     ndfc_host: ndfc.example.com
     ndfc_username: admin
     ndfc_password: !vault |
       $ANSIBLE_VAULT;1.1;AES256;...
     ```

     ```bash
     ansible-vault encrypt group_vars/all/ndfc_auth.yml
     ```

5. **Dry run** *(where supported by modules)* or run against a lab inventory.

---

## Inventories & variables

### `ndfc_hosts.yml` (single-controller example)

```yaml
all:
  children:
    ndfc:
      hosts:
        ndfc:
          ansible_host: "{{ lookup('env','NDFC_HOST') | default('ndfc.example.com', true) }}"
```

### Fabric variables (Easy_Fabric example)

Create `group_vars/all/fabric.yml`:

```yaml
fabric:
  name: NC_Fabric
  template: Easy_Fabric
  control: mgmt
  nvPairs:
    FABRIC_TYPE: Switch_Fabric
    FABRIC_INTERFACE_TYPE: p2p
    BGP_AS: 65001
    LOOPBACK0_IP_RANGE: 10.255.0.0/24
    VPC_DOMAIN_ID_START: 100
    ANYCAST_GW_MAC: 2020.00.00.00
```

### Switch onboarding

`group_vars/all/switches.yml`:

```yaml
switches:
  - hostname: leaf101
    serial: FOC1234ABC1
    mgmt_ip: 10.10.1.101
    role: leaf
  - hostname: leaf102
    serial: FOC1234ABC2
    mgmt_ip: 10.10.1.102
    role: leaf
  - hostname: spine201
    serial: FOC1234ABC9
    mgmt_ip: 10.10.1.201
    role: spine
```

### vPC pairs

`group_vars/all/vpc.yml`:

```yaml
vpc_pairs:
  - name: vpc_leaf101_102
    primary: leaf101
    secondary: leaf102
    keepalive_vrf: management
    peer_link_po: 10
```

### VRFs & networks

`group_vars/all/tenants.yml`:

```yaml
vrfs:
  - name: PROD
    vlan: 1100
    multicast: false
  - name: DEV
    vlan: 1101

networks:
  - name: app-10
    vrf: PROD
    vlan_id: 10
    gw: 10.10.10.1/24
    attach:
      - leaf101
      - leaf102
  - name: web-20
    vrf: DEV
    vlan_id: 20
    gw: 10.20.20.1/24
    attach:
      - leaf101
```

### Interfaces

`group_vars/all/interfaces.yml`:

```yaml
interfaces:
  - switch: leaf101
    name: Ethernet1/1
    mode: access
    access_vlan: 10
    description: app10-host-A
  - switch: leaf102
    name: Ethernet1/1
    mode: trunk
    trunk_vlans: [10,20]
    description: hypervisor-uplink
```

---

## How to run

> **Tip:** Most playbooks expect the variables shown above. Use `-e @file.yml` to inject ad‑hoc var files if you don’t want to keep everything in `group_vars/`.

### Create/add the fabric object

```bash
ansible-playbook -i ndfc_hosts.yml add_fabric.yml \
  -e @group_vars/all/fabric.yml \
  -e @group_vars/all/ndfc_auth.yml
```

### Build the fabric (wrapper)

```bash
ansible-playbook -i ndfc_hosts.yml build_fabric.yml
```

> This typically includes fabric creation, switch onboarding, vPC, VRFs, networks, and interfaces in a safe order. Adjust with `--tags/--skip-tags` as needed.

### Pre-provision & add switches

```bash
ansible-playbook -i ndfc_hosts.yml preprovision_switches.yml
ansible-playbook -i ndfc_hosts.yml add_switches.yml
```

### Create VRFs & networks

```bash
ansible-playbook -i ndfc_hosts.yml add_vrfs.yml -e @group_vars/all/tenants.yml
ansible-playbook -i ndfc_hosts.yml add_networks.yml -e @group_vars/all/tenants.yml
```

### Define vPC pairs

```bash
ansible-playbook -i ndfc_hosts.yml add_vpc_pair.yml -e @group_vars/all/vpc.yml
```

### Configure interfaces

```bash
ansible-playbook -i ndfc_hosts.yml add_interfaces.yml -e @group_vars/all/interfaces.yml
```

### Validate & report

```bash
ansible-playbook -i ndfc_hosts.yml Validate_vrfs_networks.yml
ansible-playbook -i ndfc_hosts.yml sanity_report.yml
# Reports will be saved under ./reports/
```

### Upgrades

```bash
ansible-playbook -i ndfc_hosts.yml stage_upgrade.yml  -e image_version=...
ansible-playbook -i ndfc_hosts.yml run_upgrade.yml    -e maintenance_window=...
ansible-playbook -i ndfc_hosts.yml verify_upgrade.yml
```

---

## ansible.cfg highlights

* Inventory defaults and callback settings tuned for NDFC workflows.
* If you rely on environment variables for auth (e.g., `NDFC_USERNAME`/`NDFC_PASSWORD`), ensure `vars_plugins` or lookup usage in playbooks matches.
* Adjust forks/timeouts to suit fabric size.

---

## Idempotency & check mode

* Most tasks are written to be idempotent based on NDFC API state. Some NDFC modules may have **limited `--check` support**; prefer a lab dry‑run or read‑only reports (`sanity_report.yml`) before production changes.

---

## Outputs

* **reports/**: CSV/JSON/Markdown artifacts from validation and sanity checks (timestamps in filenames).
* **Ansible stdout**: use `-v` or higher for detailed API responses.

---

## Troubleshooting

* Verify NDFC credentials and reachability (HTTPS/REST).
* Ensure the fabric template in variables matches NDFC (e.g., `Easy_Fabric`).
* Mismatched `nvPairs` cause 400‑level API errors—confirm names/values for your NDFC release.
* For onboarding, confirm serial numbers and mgmt IPs are correct and reachable.
* Use `-vvv` to see request/response bodies when diagnosing failures.

---

## Contributing / extending

* Keep shared logic in `tasks/` and custom filters in `filter_plugins/`.
* Add new roles/playbooks as discrete steps and expose variables in `group_vars/`.
* Prefer small, composable playbooks wired together by `build_fabric.yml`.

---

## Appendix: Variable reference (common)

| Var                                    | Meaning                                   |
| -------------------------------------- | ----------------------------------------- |
| `fabric.name`                          | Fabric display name in NDFC               |
| `fabric.template`                      | NDFC template (e.g., `Easy_Fabric`)       |
| `fabric.nvPairs.FABRIC_TYPE`           | Should be `Switch_Fabric` for Easy_Fabric |
| `fabric.nvPairs.FABRIC_INTERFACE_TYPE` | p2p or port‑channel, depends on design    |
| `fabric.nvPairs.BGP_AS`                | Underlay/global AS number                 |
| `switches[]`                           | Nodes to (pre)provision with roles        |
| `vpc_pairs[]`                          | vPC peerings and parameters               |
| `vrfs[]`                               | Tenant VRF definitions                    |
| `networks[]`                           | L2/L3 networks and attachments            |
| `interfaces[]`                         | Access/trunk/routed interface intents     |

---

### License

Internal use. Update if you plan to open source.
