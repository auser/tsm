# This file defines how PyOxidizer application building and packaging is
# performed. See PyOxidizer's documentation at
# https://gregoryszorc.com/docs/pyoxidizer/stable/pyoxidizer.html for details
# of this configuration file format.

def make_exe_for_target(target_triple=None):
    # Obtain the default PythonDistribution for our build target.
    # PyOxidizer will automatically use the target triple from --target-triple flag
    dist = default_python_distribution()

    # Create a packaging policy
    policy = dist.make_python_packaging_policy()
    
    # Enable filesystem-relative resources for better compatibility
    policy.resources_location = "filesystem-relative:prefix"
    
    # Configure the Python interpreter
    python_config = dist.make_python_interpreter_config()
    
    # Make the embedded interpreter behave like a normal Python process
    python_config.config_profile = "python"
    
    # Set up the executable name
    exe_name = "tsm"
    
    # Set up the executable
    exe = dist.to_python_executable(
        name=exe_name,
        packaging_policy=policy,
        config=python_config,
    )

    # Add the main package from src/tsm
    exe.add_python_resources(exe.read_package_root(
        path="src/tsm",
        packages=["tsm"],
    ))

    # Add templates directory
    exe.add_python_resources(exe.read_package_root(
        path="templates",
        packages=["templates"],
    ))

    # Add dependencies using pip_download
    exe.add_python_resources(exe.pip_download([
        "click>=8.1.0",
        "pydantic>=2.0.0",
        "pyyaml>=6.0",
        "docker>=7.0.0",
        "requests>=2.31.0",
        "rich>=13.0.0",
        "loguru>=0.7.0",
        "watchdog>=3.0.0",
        "jinja2>=3.1.0",
        "prometheus-client>=0.19.0",
        "python-dotenv>=1.0.0"
    ]))

    # Set the entry point to the CLI command
    python_config.run_module = "tsm.cli"

    return exe

def make_embedded_resources(exe):
    return exe.to_embedded_resources()

def make_install(exe):
    # Create an object that represents our installed application file layout.
    files = FileManifest()

    # Add the generated executable to our install layout in the root directory.
    files.add_python_resource(".", exe)

    return files

def make_msi(exe):
    # See the full docs for more. But this will convert your Python executable
    # into a `WiXMSIBuilder` Starlark type, which will be converted to a Windows
    # .msi installer when it is built.
    return exe.to_wix_msi_builder(
        # Simple identifier of your app.
        "tsm",
        # The name of your application.
        "TSM",
        # The version of your application.
        "1.0",
        # The author/manufacturer of your application.
        "Ari Lerner"
    )

# Dynamically enable automatic code signing.
def register_code_signers():
    # You will need to run with `pyoxidizer build --var ENABLE_CODE_SIGNING 1` for
    # this if block to be evaluated.
    if not VARS.get("ENABLE_CODE_SIGNING"):
        return

# Call our function to set up automatic code signers.
register_code_signers()

# Register all build targets
register_target("exe", make_exe_for_target)
register_target("resources", make_embedded_resources, depends=["exe"], default_build_script=True)
register_target("install", make_install, depends=["exe"], default=True)
register_target("msi_installer", make_msi, depends=["exe"])

# Resolve whatever targets the invoker of this configuration file is requesting
resolve_targets()