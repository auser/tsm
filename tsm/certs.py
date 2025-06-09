import shutil
import sys
from pathlib import Path
import os
import pwd
import grp

from loguru import logger


def generate_certs(
    type, name, common_name, hosts, output_dir, cert_config_dir, profile, domain, console
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
    """
    import json
    import subprocess

    output_dir = Path(output_dir)
    cert_config_dir = Path(cert_config_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

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
        console.print(f"[blue]Generating CA in {output_dir}...[/blue]")
        with (output_dir / "ca-csr.json").open("w") as f:
            f.write(ca_csr.read_text())
        p1 = subprocess.run(
            [cfssl, "gencert", "-initca", str(ca_csr)], capture_output=True, text=True
        )
        if p1.returncode != 0:
            console.print(f"[red]cfssl gencert failed: {p1.stderr}[/red]")
            sys.exit(1)
        p2 = subprocess.run(
            [cfssljson, "-bare", str(output_dir / "ca")],
            input=p1.stdout,
            capture_output=True,
            text=True,
        )
        if p2.returncode != 0:
            console.print(f"[red]cfssljson failed: {p2.stderr}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ CA generated in {output_dir}[/green]")
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
    csr_path = output_dir / f"{name}-csr.json"
    with csr_path.open("w") as f:
        json.dump(csr_data, f, indent=2)

    ca_pem = output_dir / "ca.pem"
    ca_key = output_dir / "ca-key.pem"
    # Debug prints for CA search
    logger.debug(f"generate_certs: output_dir={output_dir}")
    logger.debug(f"generate_certs: ca_pem={ca_pem}, ca_key={ca_key}")
    logger.debug(
        f"generate_certs: searching for CA in {[str(output_dir), str(cert_config_dir), str(cert_config_dir.parent), str(Path(output_dir).parent)]}"
    )
    if not ca_pem.exists() or not ca_key.exists():
        for search_dir in [
            output_dir,
            cert_config_dir,
            cert_config_dir.parent,
            Path(output_dir).parent,
        ]:
            src_pem = search_dir / "ca.pem"
            src_key = search_dir / "ca-key.pem"
            if src_pem.exists() and src_key.exists():
                try:
                    shutil.copy(src_pem, ca_pem)
                    shutil.copy(src_key, ca_key)
                    logger.debug(f"Copied CA from {src_pem} and {src_key} to {ca_pem} and {ca_key}")
                except Exception as e:
                    logger.debug(f"Failed to copy CA from {src_pem} or {src_key}: {e}")
                break
    if not ca_pem.exists() or not ca_key.exists():
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
    console.print(f"[blue]Generating {type} certificate for {name} in {output_dir}...[/blue]")
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
        [cfssljson, "-bare", str(output_dir / name)],
        input=p1.stdout,
        capture_output=True,
        text=True,
    )
    if p2.returncode != 0:
        console.print(f"[red]cfssljson failed: {p2.stderr}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ {type} certificate for {name} generated in {output_dir}[/green]")


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
    Generate certificates based on a YAML configuration file.
    
    The YAML config should have this structure:
    defaults:
      common_name: "traefik"
      hosts: "localhost,127.0.0.1"
      domain: "example.com"
      profile: "server"
      permissions:
        mode: 0o644
        owner: "traefik"
        group: "traefik"
    
    ca:
      generate: true
      name: "ca"
      common_name: "My CA"
      hosts: "localhost,127.0.0.1"
      copy:
        from: "/path/to/certs"
        files:
          - "ca.pem"
          - "ca-key.pem"
      permissions:
        mode: 0o644
        owner: "traefik"
        group: "traefik"
    
    certificates:
      - name: "traefik-server"
        type: "server"
        common_name: "traefik"
        hosts: "localhost,127.0.0.1,traefik,example.com,*.example.com"
        profile: "server"
        copy:
          from: "/path/to/certs"
          files:
            - "traefik-server.pem"
            - "traefik-server-key.pem"
        permissions:
          mode: 0o644
          owner: "traefik"
          group: "traefik"
    
    bundles:
      traefik:
        - name: "traefik-server"
          source: "traefik-server"
          copy: true
          permissions:
            mode: 0o644
            owner: "traefik"
            group: "traefik"
    """
    import yaml
    from pathlib import Path
    
    config_path = Path(config_path)
    output_dir = Path(output_dir)
    cert_config_dir = Path(cert_config_dir)
    cli_args = cli_args or {}
    
    if not config_path.exists():
        console.print(f"[red]Certificate config file not found: {config_path}[/red]")
        sys.exit(1)
        
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Get defaults
    defaults = config.get('defaults', {})
    
    # Generate or use CA
    ca_config = config.get('ca', {})
    if ca_config.get('generate', True):
        # Try to copy existing CA first
        if 'copy' in ca_config:
            copy_dir = Path(ca_config['copy']['from'])
            copied = False
            for file_name in ca_config['copy']['files']:
                src_file = copy_dir / file_name
                if src_file.exists():
                    dst_file = output_dir / file_name
                    shutil.copy(src_file, dst_file)
                    if 'permissions' in ca_config:
                        set_file_permissions(dst_file, ca_config['permissions'])
                    copied = True
                    console.print(f"[green]Copied CA file {file_name} from {copy_dir}[/green]")
            
            if not copied:
                console.print(f"[yellow]No CA files found in {copy_dir}, generating new CA...[/yellow]")
                generate_certs(
                    "ca",
                    ca_config.get('name', 'ca'),
                    get_config_value(ca_config, 'common_name', cli_args.get('common_name'), 'COMMON_NAME'),
                    get_config_value(ca_config, 'hosts', cli_args.get('hosts'), 'HOSTS'),
                    str(output_dir),
                    str(cert_config_dir),
                    "server",
                    get_config_value(ca_config, 'domain', cli_args.get('domain'), 'DOMAIN'),
                    console
                )
        else:
            generate_certs(
                "ca",
                ca_config.get('name', 'ca'),
                get_config_value(ca_config, 'common_name', cli_args.get('common_name'), 'COMMON_NAME'),
                get_config_value(ca_config, 'hosts', cli_args.get('hosts'), 'HOSTS'),
                str(output_dir),
                str(cert_config_dir),
                "server",
                get_config_value(ca_config, 'domain', cli_args.get('domain'), 'DOMAIN'),
                console
            )
    
    # Generate individual certificates
    for cert_config in config.get('certificates', []):
        cert_type = cert_config.get('type', 'server')
        cert_name = cert_config['name']
        cert_dir = output_dir / cert_type
        cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to copy existing certificate first
        if 'copy' in cert_config:
            copy_dir = Path(cert_config['copy']['from'])
            copied = False
            for file_name in cert_config['copy']['files']:
                src_file = copy_dir / file_name
                if src_file.exists():
                    dst_file = cert_dir / file_name
                    shutil.copy(src_file, dst_file)
                    if 'permissions' in cert_config:
                        set_file_permissions(dst_file, cert_config['permissions'])
                    copied = True
                    console.print(f"[green]Copied certificate {file_name} from {copy_dir}[/green]")
            
            if not copied:
                console.print(f"[yellow]No certificate files found in {copy_dir}, generating new certificate...[/yellow]")
                generate_certs(
                    cert_type,
                    cert_name,
                    get_config_value(cert_config, 'common_name', cli_args.get('common_name'), 'COMMON_NAME'),
                    get_config_value(cert_config, 'hosts', cli_args.get('hosts'), 'HOSTS'),
                    str(cert_dir),
                    str(cert_config_dir),
                    cert_config.get('profile', defaults.get('profile', 'server')),
                    get_config_value(cert_config, 'domain', cli_args.get('domain'), 'DOMAIN'),
                    console
                )
        else:
            generate_certs(
                cert_type,
                cert_name,
                get_config_value(cert_config, 'common_name', cli_args.get('common_name'), 'COMMON_NAME'),
                get_config_value(cert_config, 'hosts', cli_args.get('hosts'), 'HOSTS'),
                str(cert_dir),
                str(cert_config_dir),
                cert_config.get('profile', defaults.get('profile', 'server')),
                get_config_value(cert_config, 'domain', cli_args.get('domain'), 'DOMAIN'),
                console
            )
    
    # Handle bundles
    for bundle_name, bundle_certs in config.get('bundles', {}).items():
        bundle_dir = output_dir / bundle_name
        bundle_dir.mkdir(parents=True, exist_ok=True)
        
        for cert_config in bundle_certs:
            source_name = cert_config['source']
            target_name = cert_config['name']
            
            # Find source certificate
            source_cert = None
            for cert in config.get('certificates', []):
                if cert['name'] == source_name:
                    source_cert = cert
                    break
            
            if not source_cert:
                console.print(f"[red]Source certificate '{source_name}' not found for bundle '{bundle_name}'[/red]")
                continue
            
            if cert_config.get('copy', False):
                # Copy existing certificate
                source_dir = output_dir / source_cert['type']
                source_pem = source_dir / f"{source_name}.pem"
                source_key = source_dir / f"{source_name}-key.pem"
                target_pem = bundle_dir / f"{target_name}.pem"
                target_key = bundle_dir / f"{target_name}-key.pem"
                
                if source_pem.exists() and source_key.exists():
                    shutil.copy(source_pem, target_pem)
                    shutil.copy(source_key, target_key)
                    if 'permissions' in cert_config:
                        set_file_permissions(target_pem, cert_config['permissions'])
                        set_file_permissions(target_key, cert_config['permissions'])
                    console.print(f"[green]Copied {source_name} to {target_name} in {bundle_name} bundle[/green]")
                else:
                    console.print(f"[red]Source certificate files not found for {source_name}[/red]")
            else:
                # Generate new certificate
                generate_certs(
                    source_cert['type'],
                    target_name,
                    get_config_value(source_cert, 'common_name', cli_args.get('common_name'), 'COMMON_NAME'),
                    get_config_value(source_cert, 'hosts', cli_args.get('hosts'), 'HOSTS'),
                    str(bundle_dir),
                    str(cert_config_dir),
                    source_cert.get('profile', defaults.get('profile', 'server')),
                    get_config_value(source_cert, 'domain', cli_args.get('domain'), 'DOMAIN'),
                    console
                )
