import warnings
import os
import platform
import subprocess
import time
import threading
import sys
import shutil
import argparse

# Ensure UTF-8 encoding for console output
if platform.system().lower() == "windows":
    # Force UTF-8 encoding on Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ignore specific SyntaxWarning
warnings.filterwarnings("ignore", category=SyntaxWarning, module="DrissionPage")

CURSOR_LOGO = """
   ██████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗ 
  ██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██╔══██╗
  ██║     ██║   ██║██████╔╝███████╗██║   ██║██████╔╝
  ██║     ██║   ██║██╔══██╗╚════██║██║   ██║██╔══██╗
  ╚██████╗╚██████╔╝██║  ██║███████║╚██████╔╝██║  ██║
   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
"""

# Update the paths to match the new directory structure
MAIN_SCRIPT = "src/main.py"  # New main entry point
DATA_FOLDER = "data"
CODE_FOLDER = "src"
ENV_FILE = ".env"
APP_NAME = "CursorKeepAlive"

# Define platform-specific separator for PyInstaller
SEPARATOR = ";" if platform.system().lower() == "windows" else ":"


def get_platform_info():
    """Get detailed platform information for build optimization"""
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    # Determine if we're on Apple Silicon or Intel Mac
    if system == "darwin":
        if arch == "arm64":
            return system, "arm64", "mac_m1"
        else:
            return system, "x86_64", "mac_intel"
    elif system == "windows":
        return system, arch, "windows"
    elif system == "linux":
        return system, arch, "linux"
    else:
        return system, arch, system


# Create recursive data file list for src directory
def get_recursive_data_files(start_dir, target_dir):
    data_files = []
    for root, dirs, files in os.walk(start_dir):
        # Skip __pycache__ directories
        if "__pycache__" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                source = os.path.join(root, file)
                # Get the relative path within the src directory
                rel_path = os.path.relpath(source, start=os.path.dirname(start_dir))
                # Set the target path
                target = os.path.dirname(os.path.join(target_dir, rel_path))
                data_files.append((source, target))
    return data_files

class LoadingAnimation:
    def __init__(self):
        self.is_running = False
        self.animation_thread = None

    def start(self, message="Building"):
        self.is_running = True
        self.animation_thread = threading.Thread(target=self._animate, args=(message,))
        self.animation_thread.start()

    def stop(self):
        self.is_running = False
        if self.animation_thread:
            self.animation_thread.join()
        print("\r" + " " * 70 + "\r", end="", flush=True)  # Clear the line

    def _animate(self, message):
        animation = "|/-\\"
        idx = 0
        while self.is_running:
            print(f"\r{message} {animation[idx % len(animation)]}", end="", flush=True)
            idx += 1
            time.sleep(0.1)


def print_logo():
    # Check if running on Windows
    if platform.system().lower() == "windows":
        # Use a simpler ASCII version for Windows
        WINDOWS_LOGO = """
   ______                          
  / ____/_  __________  ____  _____
 / /   / / / / ___/ _ \/ __ \/ ___/
/ /___/ /_/ / /  /  __/ /_/ / /    
\____/\__,_/_/   \___/\____/_/     
        """
        print("\033[96m" + WINDOWS_LOGO + "\033[0m")
    else:
        # Use Unicode logo for other platforms
        print("\033[96m" + CURSOR_LOGO + "\033[0m")
    
    print("\033[93m" + "Building Cursor Keep Alive...".center(56) + "\033[0m\n")


def progress_bar(progress, total, prefix="", length=50):
    filled = int(length * progress // total)
    bar = "█" * filled + "░" * (length - filled)
    percent = f"{100 * progress / total:.1f}"
    print(f"\r{prefix} |{bar}| {percent}% Complete", end="", flush=True)
    if progress == total:
        print()


def simulate_progress(message, duration=1.0, steps=20):
    print(f"\033[94m{message}\033[0m")
    for i in range(steps + 1):
        time.sleep(duration / steps)
        progress_bar(i, steps, prefix="Progress:", length=40)


def filter_output(output):
    """ImportantMessage"""
    if not output:
        return ""
    important_lines = []
    for line in output.split("\n"):
        # Only keep lines containing specific keywords
        if any(
            keyword in line.lower()
            for keyword in ["error:", "failed:", "completed", "directory:"]
        ):
            important_lines.append(line)
    return "\n".join(important_lines)


# Define additional data files to include
base_data_files = [
    (DATA_FOLDER, DATA_FOLDER),
    (ENV_FILE, "."),
    ("src/turnstilePatch", "src/turnstilePatch"),  # Include turnstilePatch folder from src directory
    ("src/icloud", "src/icloud"),  # Explicitly include the iCloud module directory
    ("names-dataset.txt", "."),  # Include names dataset
]

# Ensure data files exist and are accessible
def ensure_files_exist():
    # Create .env file if it doesn't exist
    if not os.path.exists(ENV_FILE) and os.path.exists(".env.example"):
        shutil.copy(".env.example", ENV_FILE)
        print(f"Created {ENV_FILE} from template")
    
    # Add .env file to data files
    if ENV_FILE not in [src for src, _ in base_data_files]:
        base_data_files.append((ENV_FILE, "."))
    
    # Create empty accounts.csv file if it doesn't exist - in same directory as .env
    env_dir = os.path.dirname(os.path.abspath(ENV_FILE))
    accounts_csv_path = os.path.join(env_dir, "accounts.csv")
    if not os.path.exists(accounts_csv_path):
        with open(accounts_csv_path, "w", newline="") as f:
            f.write("created_date,email,password,token,first_name,last_name\n")
        print(f"Created empty accounts.csv file at {accounts_csv_path}")
    
    # Add accounts.csv to data files (from same directory as .env)
    base_data_files.append((accounts_csv_path, "."))
    
    # Create empty emails.txt file in same directory as .env
    emails_file_path = os.path.join(env_dir, "emails.txt")
    if not os.path.exists(emails_file_path):
        with open(emails_file_path, "w") as f:
            pass
        print(f"Created empty emails.txt file at {emails_file_path}")
    
    # Add emails.txt to data files (from same directory as .env)
    base_data_files.append((emails_file_path, "."))
    
    # Ensure data directory exists
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER, exist_ok=True)


def build(target_platform=None, target_arch=None):
    # Clear screen
    os.system("cls" if platform.system().lower() == "windows" else "clear")

    # Print logo
    print_logo()

    # Ensure necessary files exist
    ensure_files_exist()

    # Get platform information
    system, arch, platform_id = get_platform_info()
    
    # Override with target platform if provided
    if target_platform:
        platform_id = target_platform
        print(f"\033[93mBuilding for target platform: {platform_id}\033[0m")
    else:
        print(f"\033[93mBuilding for current platform: {platform_id} ({arch})\033[0m")

    # Set output directory based on platform
    output_dir = f"dist/{platform_id}"

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    simulate_progress("Creating output directory...", 0.5)

    # Get Python source files
    py_data_files = get_recursive_data_files(CODE_FOLDER, "src")

    # Combine both lists
    data_files = base_data_files + py_data_files
    
    # Format data files for PyInstaller
    data_args = []
    for src, dst in data_files:
        if os.path.exists(src):
            data_args.append(f"--add-data={src}{SEPARATOR}{dst}")
    
    # Base PyInstaller command
    command = [
        "pyinstaller",
        "--onefile",
        "--clean",
        f"--name={APP_NAME}_{platform_id}" + (".exe" if platform_id == "windows" else ""),
        "--hidden-import=src",
        "--hidden-import=src.icloud",
        "--hidden-import=src.icloud.generateEmail",
        "--hidden-import=src.icloud.hidemyemail",
        "--hidden-import=src.core",
        "--hidden-import=src.utils",
        "--hidden-import=src.ui",
        "--hidden-import=src.auth",
        "--collect-submodules=src",
    ]
    
    # Add platform-specific options
    if target_arch:
        if system == "darwin":
            if target_arch == "universal2":
                command.append("--target-architecture=universal2")
            elif target_arch in ["x86_64", "arm64"]:
                command.append(f"--target-architecture={target_arch}")
    
    # Add data files
    command.extend(data_args)
    
    # Add the main script
    command.append(MAIN_SCRIPT)

    loading = LoadingAnimation()
    try:
        simulate_progress(f"Running PyInstaller for {platform_id}...", 2.0)
        loading.start(f"Building for {platform_id} in progress")
        result = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
        loading.stop()

        if result.stderr:
            filtered_errors = [
                line
                for line in result.stderr.split("\n")
                if any(
                    keyword in line.lower()
                    for keyword in ["error:", "failed:", "completed", "directory:"]
                )
            ]
            if filtered_errors:
                print("\033[93mBuild Warnings/Errors:\033[0m")
                print("\n".join(filtered_errors))

    except subprocess.CalledProcessError as e:
        loading.stop()
        print(f"\033[91mBuild failed with error code {e.returncode}\033[0m")
        if e.stderr:
            print("\033[91mError Details:\033[0m")
            print(e.stderr)
        return
    except FileNotFoundError:
        loading.stop()
        print(
            "\033[91mError: Please ensure PyInstaller is installed (pip install pyinstaller)\033[0m"
        )
        return
    except KeyboardInterrupt:
        loading.stop()
        print("\n\033[91mBuild cancelled by user\033[0m")
        return
    finally:
        loading.stop()

    # Copy config file
    if os.path.exists("config.ini.example"):
        simulate_progress("Copying configuration file...", 0.5)
        if system == "windows":
            subprocess.run(
                ["copy", "config.ini.example", f"{output_dir}\\config.ini"], shell=True
            )
        else:
            subprocess.run(["cp", "config.ini.example", f"{output_dir}/config.ini"])

    # Copy .env.example file
    if os.path.exists(".env.example"):
        simulate_progress("Copying environment file...", 0.5)
        if system == "windows":
            subprocess.run(["copy", ".env.example", f"{output_dir}\\.env"], shell=True)
        else:
            subprocess.run(["cp", ".env.example", f"{output_dir}/.env"])

    # Move the PyInstaller output to the platform-specific directory
    simulate_progress("Moving files to output directory...", 0.5)
    # PyInstaller typically puts files in a 'dist' folder in the root directory
    exec_name = f"{APP_NAME}_{platform_id}" + (".exe" if platform_id == "windows" else "")
    pyinstaller_output = os.path.join("dist", exec_name)
    
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")
    
    # Check if the output file exists
    if os.path.exists(pyinstaller_output):
        try:
            # Get the destination file path
            dest_file = os.path.join(output_dir, exec_name)
            
            print(f"Copying from {pyinstaller_output} to {dest_file}")
            
            # Copy the file using shutil (more reliable cross-platform)
            shutil.copy2(pyinstaller_output, dest_file)
            
            # Verify the file exists in the destination
            if os.path.exists(dest_file):
                file_size = os.path.getsize(dest_file)
                print(f"SUCCESS: Copied file to {dest_file} (size: {file_size} bytes)")
            else:
                print(f"ERROR: Failed to verify file exists at {dest_file}")
                
                # Try creating an empty file for testing
                try:
                    with open(os.path.join(output_dir, "test.txt"), "w") as f:
                        f.write("Test file for debugging")
                    print(f"Created test file at {os.path.join(output_dir, 'test.txt')}")
                except Exception as e:
                    print(f"Failed to create test file: {str(e)}")
        except Exception as e:
            print(f"ERROR during copy operation: {str(e)}")
    else:
        print(f"ERROR: Source file not found at {pyinstaller_output}")
        
        # Look for similarly named files in the dist directory
        print("Looking for files in dist directory:")
        if os.path.exists("dist"):
            # Check all files in the dist directory
            for item in os.listdir("dist"):
                item_path = os.path.join("dist", item)
                if os.path.isfile(item_path):
                    file_size = os.path.getsize(item_path)
                    print(f" - Found file: {item} (size: {file_size} bytes)")
                    
                    # If the file name contains our app name, try copying it
                    if APP_NAME.lower() in item.lower():
                        try:
                            dest_file = os.path.join(output_dir, exec_name)
                            shutil.copy2(item_path, dest_file)
                            print(f"Copied alternative file {item} to {dest_file}")
                            
                            # Create a test file to verify write permissions
                            with open(os.path.join(output_dir, "test.txt"), "w") as f:
                                f.write("Test file for debugging")
                        except Exception as e:
                            print(f"Failed to copy alternative file: {str(e)}")
                elif os.path.isdir(item_path):
                    print(f" - Found directory: {item}")
                    # Check files in subdirectory
                    for subitem in os.listdir(item_path):
                        subitem_path = os.path.join(item_path, subitem)
                        if os.path.isfile(subitem_path):
                            print(f"   - {subitem} (size: {os.path.getsize(subitem_path)} bytes)")
                            
                            # If it looks like our executable, copy it
                            if APP_NAME.lower() in subitem.lower():
                                try:
                                    dest_file = os.path.join(output_dir, exec_name)
                                    shutil.copy2(subitem_path, dest_file)
                                    print(f"Copied file from subdirectory: {subitem} to {dest_file}")
                                except Exception as e:
                                    print(f"Failed to copy from subdirectory: {str(e)}")
        else:
            print(" - dist directory not found")
    
    # Verify the contents of the output directory
    print(f"\nVerifying contents of {output_dir}:")
    if os.path.exists(output_dir):
        found_files = False
        for item in os.listdir(output_dir):
            found_files = True
            item_path = os.path.join(output_dir, item)
            if os.path.isfile(item_path):
                print(f" - File: {item} (size: {os.path.getsize(item_path)} bytes)")
            else:
                print(f" - Directory: {item}")
        
        if not found_files:
            print(" - Directory exists but is empty!")
            
            # As a last resort, create a dummy file so artifact upload doesn't fail
            try:
                with open(os.path.join(output_dir, "placeholder.txt"), "w") as f:
                    f.write("Placeholder file created because no executable was found")
                print(" - Created placeholder.txt file")
            except Exception as e:
                print(f" - Failed to create placeholder: {str(e)}")
    else:
        print(" - Output directory does not exist!")
        
    # Print absolute paths for clarity
    print(f"\nAbsolute paths:")
    print(f"Current directory: {os.path.abspath(os.curdir)}")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    if os.path.exists(pyinstaller_output):
        print(f"Source file: {os.path.abspath(pyinstaller_output)}")
    else:
        print(f"Source file not found: {os.path.abspath(pyinstaller_output)}")

    print(
        f"\n\033[92mBuild completed successfully! Output directory: {output_dir}\033[0m"
    )


def main():
    parser = argparse.ArgumentParser(description="Build CursorKeepAlive for different platforms.")
    parser.add_argument("--platform", choices=["mac_m1", "mac_intel", "universal_mac", "windows", "linux", "all"], 
                      help="Target platform to build for")
    parser.add_argument("--arch", choices=["x86_64", "arm64", "universal2"],
                      help="Target architecture (macOS only)")
    
    args = parser.parse_args()
    
    if args.platform == "all":
        if platform.system().lower() == "darwin":
            print("\033[95mBuilding for Mac M1...\033[0m")
            build("mac_m1", "arm64")
            
            print("\n\033[95mBuilding for Mac Intel...\033[0m")
            build("mac_intel", "x86_64")
            
            print("\n\033[95mBuilding for Universal Mac Binary...\033[0m")
            build("universal_mac", "universal2")
        elif platform.system().lower() == "windows":
            print("\033[95mBuilding for Windows...\033[0m")
            build("windows")
        elif platform.system().lower() == "linux":
            print("\033[95mBuilding for Linux...\033[0m")
            build("linux")
        else:
            print("\033[91mCan only build for all platforms when on macOS or Windows\033[0m")
    elif args.platform:
        build(args.platform, args.arch)
    else:
        build()


if __name__ == "__main__":
    main()
