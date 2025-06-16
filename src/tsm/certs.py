import shutil
import sys
from pathlib import Path
import os
import pwd
import grp

from loguru import logger


def generate_certs(
    type, name, common_name, hosts, output_dir, cert_config_dir, profile, domain, console, source_file=None
):
    """
    Generate CA or service certificates using cfssl/cfssljson (replaces gen-certs.sh).
    Arguments:
        type: 'ca', 'server', 'client', or 'peer'
        name: Name for the certificate files
        common_name: Common Name (CN) for the certificate
        hosts: Comma-separated list of hosts for the cert
        output_dir: Directory to write certs to
        cert_config_dir: Directory containing ca-csr.json, ca-config.json, csr-template.json
        profile: cfssl profile to use
        domain: Domain for wildcard certs
        console: rich.console.Console instance for output
        source_file: Optional path to existing certificate file to use instead of generating new one
    """
    import json
    import subprocess

    output_dir = Path(output_dir)
    cert_config_dir = Path(cert_config_dir)
    
    # Ensure the output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create certificate-specific directory
    cert_dir = output_dir / name
    cert_dir.mkdir(parents=True, exist_ok=True)

    # If source_file is provided, try to use it
    if source_file:
        source_path = Path(source_file)
        # Get the basename without extension
        base_name = source_path.stem
        # Construct paths for both .pem and .key files
        source_pem_path = source_path.parent / f"{base_name}.pem"
        source_key_path = source_path.parent / f"{base_name}.key"
        target_path = cert_dir / f"{name}.pem"
        target_key_path = cert_dir / f"{name}-key.pem"

        # Check if both cert and key exist
        if source_pem_path.exists() and source_key_path.exists():
            shutil.copy(source_pem_path, target_path)
            shutil.copy(source_key_path, target_key_path)
            console.print(f"[green]✓ Copied existing certificate and key from {base_name} to {target_path}[/green]")
            return
        # If only cert exists but no key
        elif source_pem_path.exists():
            shutil.copy(source_pem_path, target_path)
            console.print(f"[yellow]Warning: Certificate exists but key file {source_key_path} not found. Generating new key...[/yellow]")
        # If only key exists but no cert
        elif source_key_path.exists():
            shutil.copy(source_key_path, target_key_path)
            console.print(f"[yellow]Warning: Key exists but certificate file {source_pem_path} not found. Generating new certificate...[/yellow]")
        # If neither exists
        else:
            console.print(f"[yellow]Warning: Source files for {base_name} not found. Generating new certificate and key...[/yellow]")

    cfssl = shutil.which("cfssl")
    cfssljson = shutil.which("cfssljson")
    if not cfssl or not cfssljson:
        console.print("[red]cfssl and cfssljson must be installed and in PATH[/red]")
        sys.exit(1)

    # Default template contents
    ca_config_content = '{\n  "signing": {\n    "default": {\n      "expiry": "8760h"\n    },\n    "profiles": {\n      "server": {\n        "usages": [\n          "signing",\n          "key encipherment",\n          "server auth",\n          "client auth"\n        ],\n        "expiry": "8760h"\n      },\n      "client": {\n        "usages": [\n          "signing",\n          "key encipherment",\n          "client auth"\n        ],\n        "expiry": "8760h"\n      },\n      "peer": {\n        "usages": [\n          "signing",\n          "key encipherment",\n          "server auth",\n          "client auth"\n        ],\n        "expiry": "8760h"\n      }\n    }\n  }\n}\n'
    ca_csr_content = '{\n  "CN": "FinancialPayments CA",\n  "key": {\n    "algo": "rsa",\n    "size": 2048\n  },\n  "names": [\n    {\n      "C": "US",\n      "L": "San Francisco",\n      "O": "FinancialPayments",\n      "OU": "CA",\n      "ST": "California"\n    }\n  ]\n}\n'
    csr_template_content = '{\n  "CN": "COMMON_NAME",\n  "hosts": [\n    "HOSTS"\n  ],\n  "key": {\n    "algo": "ecdsa",\n    "size": 256\n  },\n  "names": [\n    {\n      "C": "US",\n      "L": "Texas",\n      "O": "etcd",\n      "ST": "California"\n    }\n  ]\n}\n'

    if type == "ca":
        ca_csr = cert_config_dir / "ca-csr.json"
        if not ca_csr.exists():
            console.print(f"[yellow]Missing {ca_csr}, generating default template...[/yellow]")
            ca_csr.parent.mkdir(parents=True, exist_ok=True)
            with open(ca_csr, "w") as f:
                f.write(ca_csr_content)
        console.print(f"[blue]Generating CA in {cert_dir}...[/blue]")
        with (cert_dir / "ca-csr.json").open("w") as f:
            f.write(ca_csr.read_text())
        p1 = subprocess.run(
            [cfssl, "gencert", "-initca", str(ca_csr)], capture_output=True, text=True
        )
        if p1.returncode != 0:
            console.print(f"[red]cfssl gencert failed: {p1.stderr}[/red]")
            sys.exit(1)
        p2 = subprocess.run(
            [cfssljson, "-bare", str(cert_dir / "ca")],
            input=p1.stdout,
            capture_output=True,
            text=True,
        )
        if p2.returncode != 0:
            console.print(f"[red]cfssljson failed: {p2.stderr}[/red]")
            sys.exit(1)
        # Copy CA files to the root certs directory for other certs to use
        ca_pem = cert_dir / "ca.pem"
        ca_key = cert_dir / "ca-key.pem"
        if ca_pem.exists() and ca_key.exists():
            shutil.copy(ca_pem, output_dir / "ca.pem")
            shutil.copy(ca_key, output_dir / "ca-key.pem")
        console.print(f"[green]✓ CA generated in {cert_dir}[/green]")
        return

    # For service certs: create a CSR JSON from template
    csr_template = cert_config_dir / "csr-template.json"
    if not csr_template.exists():
        console.print(f"[yellow]Missing {csr_template}, generating default template...[/yellow]")
        csr_template.parent.mkdir(parents=True, exist_ok=True)
        with open(csr_template, "w") as f:
            f.write(csr_template_content)
    hosts_list = [h.strip() for h in hosts.split(",") if h.strip()]
    with csr_template.open() as f:
        csr_data = json.load(f)
    csr_data["CN"] = common_name
    csr_data["hosts"] = hosts_list
    csr_path = cert_dir / f"{name}-csr.json"
    with csr_path.open("w") as f:
        json.dump(csr_data, f, indent=2)

    # Look for CA files in both the root certs directory and the CA directory
    ca_pem = None
    ca_key = None
    for search_dir in [
        output_dir,
        output_dir / "ca",
        cert_config_dir,
        cert_config_dir.parent,
        Path(output_dir).parent,
    ]:
        src_pem = search_dir / "ca.pem"
        src_key = search_dir / "ca-key.pem"
        if src_pem.exists() and src_key.exists():
            ca_pem = src_pem
            ca_key = src_key
            break

    if not ca_pem or not ca_key:
        ca_config = cert_config_dir / "ca-config.json"
        if not ca_config.exists():
            console.print(f"[yellow]Missing {ca_config}, generating default template...[/yellow]")
            ca_config.parent.mkdir(parents=True, exist_ok=True)
            with open(ca_config, "w") as f:
                f.write(ca_config_content)
        console.print("[red]CA files not found. Generate CA first with --type ca.[/red]")
        sys.exit(1)

    ca_config = cert_config_dir / "ca-config.json"
    if not ca_config.exists():
        console.print(f"[yellow]Missing {ca_config}, generating default template...[/yellow]")
        ca_config.parent.mkdir(parents=True, exist_ok=True)
        with open(ca_config, "w") as f:
            f.write(ca_config_content)
    console.print(f"[blue]Generating {type} certificate for {name} in {cert_dir}...[/blue]")
    p1 = subprocess.run(
        [
            cfssl,
            "gencert",
            f"-ca={ca_pem}",
            f"-ca-key={ca_key}",
            f"-config={ca_config}",
            f"-profile={profile}",
            str(csr_path),
        ],
        capture_output=True,
        text=True,
    )
    if p1.returncode != 0:
        console.print(f"[red]cfssl gencert failed: {p1.stderr}[/red]")
        sys.exit(1)
    p2 = subprocess.run(
        [cfssljson, "-bare", str(cert_dir / name)],
        input=p1.stdout,
        capture_output=True,
        text=True,
    )
    if p2.returncode != 0:
        console.print(f"[red]cfssljson failed: {p2.stderr}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ {type} certificate for {name} generated in {cert_dir}[/green]")


def copy_certs(from_dir, to_dir, console):
    """
    Copy certificates from one directory to another if they exist.
    Arguments:
        from_dir: Source directory
        to_dir: Destination directory
        console: rich.console.Console instance for output
    """
    from_dir = Path(from_dir)
    to_dir = Path(to_dir)
    to_dir.mkdir(parents=True, exist_ok=True)
    files = (
        list(from_dir.glob("*.pem")) + list(from_dir.glob("*.crt")) + list(from_dir.glob("*.key"))
    )
    if not files:
        console.print(f"[yellow]No cert files found in {from_dir}[/yellow]")
        return
    for f in files:
        shutil.copy(f, to_dir / f.name)
        console.print(f"[green]Copied {f.name} to {to_dir}[/green]")


def generate_bundle(bundle, output_dir, cert_config_dir, hosts, domain, common_name, console):
    """
    Generate a bundle of certs for a specific use case (e.g., traefik).
    Currently supports: traefik
    """
    import shutil
    from pathlib import Path

    from .certs import generate_certs as generate_certs_func

    if bundle == "traefik":
        traefik_dir = Path(output_dir) / "traefik"
        traefik_dir.mkdir(parents=True, exist_ok=True)
        base_cert_dir = Path(output_dir)
        ca_pem = base_cert_dir / "ca.pem"
        ca_key = base_cert_dir / "ca-key.pem"
        # Debug print for CA file locations
        print(f"[DEBUG] Looking for CA at {ca_pem} and {ca_key}")
        # Generate CA if missing
        if not ca_pem.exists() or not ca_key.exists():
            generate_certs_func(
                "ca",
                "ca",
                common_name,
                hosts,
                str(base_cert_dir),
                cert_config_dir,
                "server",
                domain,
                console,
            )
        # traefik-server
        generate_certs_func(
            "server",
            "traefik-server",
            "traefik",
            f"localhost,127.0.0.1,traefik,{domain},*.{domain}",
            str(traefik_dir),
            cert_config_dir,
            "server",
            domain,
            console,
        )
        # asterisk
        generate_certs_func(
            "server",
            "asterisk",
            "asterisk",
            f"localhost,127.0.0.1,traefik,asterisk,{domain},*.{domain}",
            str(traefik_dir),
            cert_config_dir,
            "server",
            domain,
            console,
        )
        # Copy/rename asterisk.pem to asterisk_fp.pem and asterisk-key.pem to asterisk_fp-key.pem
        asterisk_pem = traefik_dir / "asterisk.pem"
        asterisk_key = traefik_dir / "asterisk-key.pem"
        asterisk_fp_pem = traefik_dir / "asterisk_fp.pem"
        asterisk_fp_key = traefik_dir / "asterisk_fp-key.pem"
        if asterisk_pem.exists():
            shutil.copy(asterisk_pem, asterisk_fp_pem)
        if asterisk_key.exists():
            shutil.copy(asterisk_key, asterisk_fp_key)
        # wildcard_herringbank
        generate_certs_func(
            "server",
            "wildcard_herringbank",
            "wildcard_herringbank",
            f"localhost,127.0.0.1,traefik,herringbank,{domain},*.{domain}",
            str(traefik_dir),
            cert_config_dir,
            "server",
            domain,
            console,
        )
        console.print("[green]✓ Traefik cert bundle generated in proxy/certs/traefik[green]")


def generate_certs_cli(
    type, name, common_name, hosts, output_dir, cert_config_dir, profile, domain, bundle, console
):
    """
    Main entry for CLI cert generation. Handles --type, --bundle, and all CA file logic.
    """
    import shutil
    from pathlib import Path

    if bundle == "traefik":
        generate_bundle(
            bundle,
            output_dir,
            cert_config_dir,
            hosts,
            domain,
            common_name,
            console,
        )
        return
    cert_types = ["ca", "server", "client", "peer"]
    if type == "all" or not type:
        # Generate CA in the base cert directory
        ca_name = name if name else "ca"
        ca_dir = Path(output_dir)
        ca_dir.mkdir(parents=True, exist_ok=True)
        generate_certs(
            "ca",
            ca_name,
            common_name,
            hosts,
            str(ca_dir),
            cert_config_dir,
            profile,
            domain,
            console,
        )
        ca_pem = ca_dir / "ca.pem"
        ca_key = ca_dir / "ca-key.pem"
        for t in ["server", "client", "peer"]:
            cert_name = name if name else t
            out_dir = Path(output_dir) / t
            out_dir.mkdir(parents=True, exist_ok=True)
            # Copy CA files in
            ca_pem_target = out_dir / "ca.pem"
            ca_key_target = out_dir / "ca-key.pem"
            shutil.copy(ca_pem, ca_pem_target)
            shutil.copy(ca_key, ca_key_target)
            try:
                generate_certs(
                    t,
                    cert_name,
                    common_name,
                    hosts,
                    str(out_dir),
                    cert_config_dir,
                    profile,
                    domain,
                    console,
                )
            finally:
                # Remove CA files from subdir
                if ca_pem_target.exists():
                    ca_pem_target.unlink()
                if ca_key_target.exists():
                    ca_key_target.unlink()
    else:
        cert_name = name if name else type
        if type == "ca":
            out_dir = Path(output_dir)
        else:
            out_dir = Path(output_dir) / type
        out_dir.mkdir(parents=True, exist_ok=True)
        # If not CA, copy CA files in, generate, then remove
        if type != "ca":
            ca_dir = Path(output_dir)
            ca_pem = ca_dir / "ca.pem"
            ca_key = ca_dir / "ca-key.pem"
            ca_pem_target = out_dir / "ca.pem"
            ca_key_target = out_dir / "ca-key.pem"
            if not ca_pem.exists() or not ca_key.exists():
                console.print("[red]CA files not found. Generate CA first with --type ca.[/red]")
                sys.exit(1)
            shutil.copy(ca_pem, ca_pem_target)
            shutil.copy(ca_key, ca_key_target)
            try:
                generate_certs(
                    type,
                    cert_name,
                    common_name,
                    hosts,
                    str(out_dir),
                    cert_config_dir,
                    profile,
                    domain,
                    console,
                )
            finally:
                if ca_pem_target.exists():
                    ca_pem_target.unlink()
                if ca_key_target.exists():
                    ca_key_target.unlink()
        else:
            generate_certs(
                type,
                cert_name,
                common_name,
                hosts,
                str(out_dir),
                cert_config_dir,
                profile,
                domain,
                console,
            )


def copy_prod_certs_if_present():
    """
    Copy production certs from /usr/local/certs to local cert locations if present.
    Overwrites generated certs, skips if not present.
    """
    mappings = [
        ("/usr/local/certs/ca.key", "proxy/certs/ca-key.pem"),
        ("/usr/local/certs/ca.pem", "proxy/certs/ca.pem"),
        ("/usr/local/certs/traefik-server.pem", "proxy/certs/traefik/traefik-server.pem"),
        ("/usr/local/certs/traefik-server-key.pem", "proxy/certs/traefik/traefik-server-key.pem"),
        ("/usr/local/certs/traefik-server.pem", "proxy/certs/traefik/herringbank_com.pem"),
        ("/usr/local/certs/traefik-server-key.pem", "proxy/certs/traefik/herringbank_com-key.pem"),
        ("/usr/local/certs/asterisk_fp_com.crt", "proxy/certs/traefik/asterisk_fp.pem"),
        ("/usr/local/certs/asterisk_fp_com.key", "proxy/certs/traefik/asterisk_fp-key.pem"),
        (
            "/usr/local/certs/wildcard_herringbank_com.crt",
            "proxy/certs/traefik/wildcard_herringbank_com.pem",
        ),
        (
            "/usr/local/certs/wildcard_herringbank_com.key",
            "proxy/certs/traefik/wildcard_herringbank_com-key.pem",
        ),
    ]
    for src, dst in mappings:
        src_path = Path(src)
        dst_path = Path(dst)
        try:
            if src_path.exists():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src_path, dst_path)
                logger.info(f"Copied {src_path} -> {dst_path}")
        except Exception as e:
            logger.warning(f"Could not copy {src_path} -> {dst_path}: {e}")


def set_file_permissions(file_path: Path, permissions: dict | None) -> None:
    """
    Set file permissions, owner, and group.
    
    Args:
        file_path: Path to the file
        permissions: Dictionary containing:
            - mode: File permissions (octal, can be string or int)
            - owner: File owner
            - group: File group
            
    If permissions is None, no changes are made.
    If mode is not specified, defaults to 0o644.
    If owner is specified but group is not, group defaults to root.
    If group is specified but owner is not, owner defaults to root.
    If specified owner/group don't exist, falls back to current user/group.
    """
    if not permissions:
        return

    import os
    import pwd
    import grp

    try:
        # Convert mode to integer if it's a string
        mode = permissions.get('mode')
        if mode is not None:
            if isinstance(mode, str):
                # Handle string octal values (e.g., "644" or "0o644")
                if mode.startswith('0o'):
                    mode = int(mode, 8)
                else:
                    mode = int(mode, 8) if mode.isdigit() else int(mode)
            else:
                mode = int(mode)
        else:
            mode = 0o644  # Default mode if not specified

        # Set file permissions
        os.chmod(file_path, mode)

        # Set ownership if either owner or group is specified
        owner = permissions.get('owner')
        group = permissions.get('group')
        if owner is not None or group is not None:
            # Get current user/group as fallback
            current_uid = os.getuid()
            current_gid = os.getgid()
            current_user = pwd.getpwuid(current_uid).pw_name
            current_group = grp.getgrgid(current_gid).gr_name

            # Try to get specified owner/group, fall back to current if not found
            try:
                uid = pwd.getpwnam(owner).pw_uid if owner else current_uid
            except KeyError:
                logger.warning(f"User '{owner}' not found, using current user '{current_user}'")
                uid = current_uid

            try:
                gid = grp.getgrnam(group).gr_gid if group else current_gid
            except KeyError:
                logger.warning(f"Group '{group}' not found, using current group '{current_group}'")
                gid = current_gid

            os.chown(file_path, uid, gid)

    except Exception as e:
        logger.warning(f"Could not set permissions for {file_path}: {e}")


def get_config_value(config: dict, key: str, cli_value: str | None, env_key: str | None) -> str:
    """Get value from config, CLI, or environment in that order."""
    if cli_value:
        return cli_value
    if env_key and os.environ.get(env_key):
        return os.environ[env_key]
    return config.get(key, "")


def generate_certs_from_config(config_path: str, output_dir: str, cert_config_dir: str, console, cli_args: dict = None) -> None:
    """
    Generate certificates based on configuration file.
    """
    import yaml

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Get values from config, CLI args, or environment variables
    common_name = get_config_value(config.get("defaults", {}), "common_name", cli_args.get("common_name") if cli_args else None, "COMMON_NAME")
    hosts = get_config_value(config.get("defaults", {}), "hosts", cli_args.get("hosts") if cli_args else None, "HOSTS")
    domain = get_config_value(config.get("defaults", {}), "domain", cli_args.get("domain") if cli_args else None, "DOMAIN")
    profile = get_config_value(config.get("defaults", {}), "profile", cli_args.get("profile") if cli_args else None, "PROFILE")

    # Generate CA if configured
    if config.get("ca", {}).get("generate", True):
        ca_config = config["ca"]
        generate_certs(
            "ca",
            ca_config["name"],
            ca_config["common_name"],
            ca_config["hosts"],
            output_dir,
            cert_config_dir,
            profile,
            ca_config["domain"],
            console
        )

    # Generate individual certificates
    for cert in config.get("certificates", []):
        cert_name = cert["name"]
        cert_type = cert["type"]
        cert_common_name = cert.get("common_name", common_name)
        cert_hosts = cert.get("hosts", hosts)
        cert_profile = cert.get("profile", profile)
        cert_domain = cert.get("domain", domain)
        source_file = cert.get("source_file")

        # Set permissions if specified
        permissions = cert.get("permissions")
        if permissions:
            cert_dir = Path(output_dir) / cert_name
            cert_dir.mkdir(parents=True, exist_ok=True)
            for file in cert_dir.glob("*"):
                set_file_permissions(file, permissions)

        generate_certs(
            cert_type,
            cert_name,
            cert_common_name,
            cert_hosts,
            output_dir,
            cert_config_dir,
            cert_profile,
            cert_domain,
            console,
            source_file
        )
