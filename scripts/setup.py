"""Script to setup Aegis - Install dependencies and setup configurations"""

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"📦 {description}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, check=True, shell=isinstance(cmd, str))
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Error: {e}")
        return False


def main():
    """Main setup function."""
    print("\n" + "="*60)
    print("🚀 Synexian Agent Setup")
    print("="*60)

    project_root = Path(__file__).parent.parent

    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Python 3.10 or higher is required")
        sys.exit(1)

    print(f"✅ Python version: {sys.version_info.major}.{sys.version_info.minor}")

    # Install dependencies
    if not run_command(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        "Installing Synexian Agent"
    ):
        sys.exit(1)

    # Install dev dependencies
    run_command(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        "Installing development dependencies (optional)"
    )

    # Create .env file if it doesn't exist
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    if not env_file.exists() and env_example.exists():
        print("\n📝 Creating .env file from .env.example")
        env_file.write_text(env_example.read_text())
        print("✅ .env file created")
        print("⚠️  Please edit .env and add your OpenRouter API key")
    else:
        print("\n✅ .env file already exists")

    # Create output directory
    output_dir = project_root / "synexian-reports"
    output_dir.mkdir(exist_ok=True)
    print(f"✅ Output directory created: {output_dir}")

    # Verify installation
    print("\n" + "="*60)
    print("🔍 Verifying Installation")
    print("="*60)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "synexian", "version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        print("✅ Synexian Agent is installed correctly!")
    except subprocess.CalledProcessError:
        print("❌ Installation verification failed")
        sys.exit(1)

    # Print next steps
    print("\n" + "="*60)
    print("🎉 Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Edit .env and add your OpenRouter API key")
    print("   Get one free at: https://openrouter.ai")
    print("\n2. Run your first analysis:")
    print("   synexian analyze ./your-project")
    print("\n3. View configuration:")
    print("   synexian config-show")
    print("\n4. Run tests:")
    print("   pytest")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
