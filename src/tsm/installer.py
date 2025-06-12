import subprocess
import sys

from rich.console import Console

console = Console()

def install_docker():
  """Install docker."""
  if subprocess.call(["which", "docker"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
    return
  if sys.platform == "darwin":
    subprocess.run(["brew", "install", "docker"], check=True)
    console.print("[green]✓ docker installed via Homebrew[/green]")
  elif sys.platform == "linux":
    subprocess.run(["sudo", "apt-get", "install", "-y", "docker"], check=True)
    console.print("[green]✓ docker installed via apt[/green]")
  else:
    console.print("[red]Install docker manually from https://docs.docker.com/get-docker/[/red]")
    sys.exit(1)

def install_uv():
  """Install uv."""
  if subprocess.call(["which", "uv"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
    console.print("[green]✓ uv already installed[/green]")
    return
  if sys.platform == "darwin" or sys.platform == "linux":
    subprocess.run(["curl", "-LsSf", "https://astral.sh/uv/install.sh"], check=True)
    subprocess.run(["./install.sh"], check=True)
    console.print("[green]✓ uv installed via curl[/green]")
  else:
    console.print("[red]Install uv manually from https://docs.astral.sh/uv/installation/[/red]")
    sys.exit(1)

def install_git():
  """Install git."""
  if subprocess.call(["which", "git"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
    console.print("[green]✓ git already installed[/green]")
    return
  if sys.platform == "darwin":
    subprocess.run(["brew", "install", "git"], check=True)
    console.print("[green]✓ git installed via Homebrew[/green]")
  elif sys.platform == "linux":
    subprocess.run(["sudo", "apt-get", "install", "-y", "git"], check=True)
    console.print("[green]✓ git installed via apt[/green]")
  else:
    console.print("[red]Unsupported platform[/red]")
    sys.exit(1)

def install_golang():
  """Install golang."""
  if subprocess.call(["which", "go"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
    console.print("[green]✓ go already installed[/green]")
    return
  if sys.platform == "darwin":
    subprocess.run(["brew", "install", "go"], check=True)
    console.print("[green]✓ go installed via Homebrew[/green]")
  elif sys.platform == "linux":
    subprocess.run(["curl", "-LO", "https://go.dev/dl/go1.24.4.linux-amd64.tar.gz"], check=True)
    subprocess.run(["sudo", "tar", "-C", "/usr/local", "-xzf", "go1.24.4.linux-amd64.tar.gz"], check=True)
    subprocess.run(["sudo", "mv", "/usr/local/go", "/usr/local/go1.24.4"], check=True)
    subprocess.run(["sudo", "ln", "-s", "/usr/local/go1.24.4/bin/go", "/usr/local/bin/go"], check=True)
    console.print("[green]✓ go installed via curl[/green]")
  else:
    console.print("[red]Install go manually from https://go.dev/doc/install[/red]")
    sys.exit(1)

def install_build_dependencies():
  """Install build dependencies."""
  if subprocess.call(["which", "make"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
    console.print("[green]✓ build-essential already installed[/green]")
    return
  if sys.platform == "darwin":
    subprocess.run(["brew", "install", "build-essential"], check=True)
    console.print("[green]✓ build-essential installed via Homebrew[/green]")
  elif sys.platform == "linux":
    subprocess.run(["sudo", "apt-get", "install", "-y", "build-essential"], check=True)
    console.print("[green]✓ build-essential installed via apt[/green]")
  else:
    console.print("[red]Install build-essential manually from https://packages.ubuntu.com/search?suite=all&section=all&arch=amd64&searchon=names&keywords=build-essential[/red]")
    sys.exit(1)

def install_cfssl_with_git():
    """Install cfssl with git."""
    if subprocess.call(["which", "cfssl"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
      console.print("[green]✓ cfssl already installed[/green]")
      return
    subprocess.run(["git", "clone", "https://github.com/cloudflare/cfssl.git"], check=True)
    subprocess.run(["cd", "cfssl"], check=True)
    subprocess.run(["make"], check=True)
    subprocess.run(["sudo", "install"], check=True)
    console.print("[green]✓ cfssl and cfssljson installed via git[/green]")