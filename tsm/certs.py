import shutil
import sys
from pathlib import Path

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
        ("/usr/local/certs/traefik-server.pem", "proxy/certs/traefik/example_com.pem"),
        ("/usr/local/certs/traefik-server-key.pem", "proxy/certs/traefik/example_com-key.pem"),
        ("/usr/local/certs/asterisk_fp_com.crt", "proxy/certs/traefik/asterisk_fp.pem"),
        ("/usr/local/certs/asterisk_fp_com.key", "proxy/certs/traefik/asterisk_fp-key.pem"),
        (
            "/usr/local/certs/wildcard_example_com.crt",
            "proxy/certs/traefik/wildcard_example_com.pem",
        ),
        (
            "/usr/local/certs/wildcard_example_com.key",
            "proxy/certs/traefik/wildcard_example_com-key.pem",
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
