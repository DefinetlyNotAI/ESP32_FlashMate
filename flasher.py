import configparser
import msvcrt
import os
import shutil
import subprocess
from datetime import datetime

import esptool
import serial
import serial.tools.list_ports

from utils import tprint, handler, separator


class ESP32:
    def __init__(self):
        self.esp32_folder = 'esp32'
        self.menu_items = []
        self.current_item = None
        self.config = configparser.ConfigParser()
        self.check = Check(self.config)
        self.get = Get()
        self.__load_menu_items()

    def __load_menu_items(self) -> None:
        try:
            if not os.path.exists(self.esp32_folder):
                tprint.error(f"'{self.esp32_folder}' folder not found.")
                return

            self.menu_items = []
            for folder in os.listdir(self.esp32_folder):
                folder_path = os.path.join(self.esp32_folder, folder)
                if os.path.isdir(folder_path):
                    issues, warn = self.check.for_issues(folder_path)
                    self.menu_items.append(
                        (folder, True if issues else False, issues if issues else [], warn if warn else []))

        except Exception as e:
            handler.exception(msg=e)

    # ----------------------------  Menu methods -----------------------------  #

    def main_menu(self) -> None:
        try:
            while True:
                print()
                separator("ESP32 Ultra Manager - Main Menu")
                print()

                # Check update status
                update_status, update_color = self.check.update_status()

                # Check COM port availability
                ports = list(serial.tools.list_ports.comports())
                com_status_color = "\033[91m" if not ports else "\033[97m"  # Red if no ports, white otherwise

                print("  [1] Flash an ESP32 Project")
                print(f"  [2] Communicate {com_status_color}(COM Ports Available: {len(ports)})\033[0m")
                print(f"  [3] Updates {update_color}({update_status})\033[0m")
                print("  [4] Help")
                print("  [5] Exit\n")

                while msvcrt.kbhit():
                    msvcrt.getch()

                try:
                    choice = tprint.input("Select an option: > ").strip()
                except Exception:
                    tprint.warning("If you see this after serial communication automatically, its a known bug as the stdin isn't successfully cleared for some reason.")
                    choice = tprint.input("Select an option: > ").strip()

                if choice == '1':
                    self._flasher_menu()
                elif choice == '2':
                    self._communication_menu()
                elif choice == '3':
                    self._update_menu()
                elif choice == '4':
                    print()
                    tprint.info("ESP32 Ultra Manager - Help")
                    print("A tool to flash ESP32 devices from organized folders under ./esp32")
                    print("Each folder must contain .bin files and a config.ini")
                    print("The tool supports auto-generation of config.ini and update via Git.")
                elif choice == '5' or choice.lower() == 'exit':
                    break
                else:
                    tprint.warning("Invalid selection. Try again.")
        except Exception as e:
            handler.exception(msg=e)

    def _update_menu(self) -> None:
        print()
        separator("ESP32 Ultra Manager - Update")
        print()

        try:
            update_status, update_color = self.check.update_status()
            if update_status not in ["Up-to-date", "Uncommitted Changes", "Ahead of Main", "Update Available"]:
                tprint.warning(f"{update_status}. Please resolve the issues before updating.")
                return
            if update_status == "Ahead of Main":
                tprint.warning("You are ahead of the main branch.")
                tprint.warning("Please commit or stash your changes to allow updating.")
                return
            if update_status == "Uncommitted Changes":
                tprint.warning("You have uncommitted changes!! Will still update though.")

            # Fetch remote and check for updates
            subprocess.run(["git", "fetch"], stdout=subprocess.DEVNULL)
        except Exception as e:
            handler.exception(msg=e)

        try:
            branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
            local_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
            remote_commit = subprocess.check_output(["git", "rev-parse", f"origin/{branch}"]).decode().strip()
            if local_commit == remote_commit:
                date = subprocess.check_output(["git", "show", "-s", "--format=%ci", local_commit]).decode().strip()
                tprint.info("No updates available.")
                tprint.info(f"  Current commit: {local_commit[:7]} from {date}")
                return

            # Updates available
            local_date = subprocess.check_output(["git", "show", "-s", "--format=%ci", local_commit]).decode().strip()
            remote_date = subprocess.check_output(["git", "show", "-s", "--format=%ci", remote_commit]).decode().strip()
            local_dt = datetime.strptime(local_date, "%Y-%m-%d %H:%M:%S %z")
            remote_dt = datetime.strptime(remote_date, "%Y-%m-%d %H:%M:%S %z")
            delta = remote_dt - local_dt
            commit_diff = subprocess.check_output(
                ["git", "rev-list", "--count", f"{local_commit}..origin/{branch}"]).decode().strip()
            latest_message = subprocess.check_output(
                ["git", "log", "-1", "--pretty=%B", f"origin/{branch}"]).decode().strip()

            tprint.info(f"Update available!")
            print(f"  Current : {local_commit[:7]} from {local_date}")
            print(f"  Latest  : {remote_commit[:7]} from {remote_date}")
            print(f"  Behind by {commit_diff} commit(s), {delta.days} days.")
            print(f"  Latest message: {latest_message}\n")

            choice = tprint.input("Do you want to update now? (y/n): > ").strip().lower()
            if choice == 'y':
                result = subprocess.run(["git", "pull", "origin", branch], capture_output=True, text=True)
                if result.returncode == 0:
                    tprint.success("Update successful.")
                else:
                    tprint.error("Update failed.")
                    print(result.stderr)
                    tprint.warning("Possible causes: merge conflict, local changes, no permission.")
            else:
                tprint.info("Update skipped.")
        except Exception as e:
            handler.exception(msg=e)

    def _communication_menu(self) -> None:
        try:
            print()
            separator("ESP32 Ultra Manager - Serial Communication")
            print()

            # Check available COM ports
            ports = list(serial.tools.list_ports.comports())
            if not ports:
                tprint.error("No COM ports found.")
                return

            tprint.info("Select a project for communication:")
            tprint.info("   [1] Temporary (Custom Baud Rate)")
            for idx, (item, _, _, _) in enumerate(self.menu_items):
                tprint.info(f"   [{idx + 2}] {item}")

            print()
            choice = tprint.input("Enter a number to select, or 'exit' to quit: > ").strip()
            if choice.lower() == 'exit':
                return

            try:
                choice = int(choice)
                if choice == 1:
                    baud_rate = self.get.valid_baud_rate()
                    if baud_rate == 'exit':
                        return
                    self.__start_communication(None, baud_rate)
                elif 2 <= choice <= len(self.menu_items) + 1:
                    project = self.menu_items[choice - 2]
                    folder_name, _, _, _ = project
                    folder_path = os.path.join(self.esp32_folder, folder_name)
                    config_path = os.path.join(folder_path, 'config.ini')
                    self.config.read(config_path)

                    baud_rate = self.config.get('Settings', 'Baud_Rate', fallback=None)
                    if not baud_rate or not baud_rate.isdigit():
                        tprint.error("Invalid or missing Baud Rate in config.ini.")
                        return
                    self.__start_communication(folder_name, baud_rate)
                else:
                    tprint.warning("Invalid selection. Returning to menu.")
            except ValueError:
                tprint.error("Invalid input. Please enter a valid number.")
        except Exception as e:
            handler.exception(msg=e)

    def _flasher_menu(self) -> None:
        try:
            print()
            separator("ESP32 Ultra Manager - Flashing")
            print()

            if len(self.menu_items) == 0:
                tprint.warning("No projects found in the 'esp32' folder.")
                tprint.warning("Please add your projects and try again.")
                return

            tprint.info("Select a project to flash:")
            for idx, (item, error, issues, warn) in enumerate(self.menu_items):
                if error:
                    tprint.warning(f"   [{idx + 1}] {item}")
                else:
                    tprint.info(f"  [{idx + 1}] {item}")

            selection = tprint.input("Enter a number to select, or 'exit' to quit: > ").strip()

            if selection.lower() == 'exit':
                return

            while True:
                try:
                    selection = int(selection) - 1
                    tprint.debug(f"Selection of user (index): {selection}")
                    if 0 <= selection < len(self.menu_items):
                        self.current_item = self.menu_items[selection]
                        self.__handle_issues(self.current_item)
                        break
                    else:
                        tprint.warning("Invalid selection, try again.")
                except ValueError:
                    tprint.error("Invalid input, please enter a valid number or 'exit'.")
                selection = tprint.input("Enter a number to select, or 'exit' to quit: > ").strip()
                if selection.lower() == 'exit':
                    break
        except Exception as e:
            handler.exception(msg=e)

    # ----------------------------  Menu methods -----------------------------  #

    def __flash_esp32(self, folder_name: str) -> None:
        """Flash the ESP32 using the config.ini instructions."""

        def flash(flash_port: str, flash_folder_path: str, flash_bin_files: dict[str, str],
                  flash_baud_rate: str) -> None:
            """Flash the ESP32."""
            try:
                # Ask if user wants to erase flash
                erase_flash = tprint.input("Do you want to erase the flash before flashing? (y/n): > ").strip().lower()

                while erase_flash not in ['y', 'n']:
                    tprint.warning("Invalid input. Please enter 'y' or 'n'.")
                    erase_flash = tprint.input(
                        "Do you want to erase the flash before flashing? (y/n): > ").strip().lower()

                # Proceed with flashing
                tprint.debug(f"Flashing to {flash_port} at {flash_baud_rate} baud...")

                # TODO - Add custom setting support for esptool
                flash_args = [
                    '--chip', 'esp32',
                    '--port', flash_port,
                    '--baud', flash_baud_rate,
                    '--before', 'default_reset',
                    '--after', 'hard_reset',
                    'write_flash',
                    '-z',  # compress
                    '--flash_mode', 'dio',
                    '--flash_freq', '40m',
                    '--flash_size', 'detect',
                ]

                if erase_flash == 'y':
                    flash_args.append('--erase')

                # Add each bin file with its corresponding memory address
                for flash_fname, flash_addr in flash_bin_files.items():
                    if not flash_addr:
                        tprint.error(f"Address for {flash_fname} is empty.")
                        return
                    full_path = os.path.join(flash_folder_path, flash_fname)
                    flash_args.extend([flash_addr, full_path])

                # Flash the ESP32
                esptool.main(flash_args)
                print()
                tprint.success("Flashing complete.")
                print()

            except Exception as err:
                print()
                handler.exception(msg=f"Flashing failed: {err}")
                print()

        try:
            folder_path = os.path.join(self.esp32_folder, folder_name)
            config_path = os.path.join(folder_path, 'config.ini')
            self.config.read(config_path)

            baud_rate = self.config.get('Settings', 'Baud_Rate', fallback='115200')
            bin_files = {
                key: value for key, value in self.config.items('Settings')
                if key.endswith('.bin')
            }

            if not bin_files:
                tprint.error("No bin files specified in config.ini")
                return

            tprint.debug(f"Using Baud Rate: {baud_rate}")
            for f, addr in bin_files.items():
                tprint.debug(f"  {f} -> {addr}")

            # Check available COM ports
            ports = list(serial.tools.list_ports.comports())
            if not ports:
                tprint.error("No COM ports found.")
                self._flasher_menu()
                return

            selected_port = self.__com_port_menu(ports)

            if not selected_port:
                tprint.warning("No COM port selected, returning to menu.")
                self._flasher_menu()
                return

            # Flash the ESP32
            flash(selected_port, folder_path, bin_files, baud_rate)
        except Exception as e:
            handler.exception(msg=e)

    def __handle_issues(self, item: tuple[str, str, list[str], list[str]]) -> None:
        try:
            folder_name, error, issues, warn = item
            folder_path = os.path.join(self.esp32_folder, folder_name)

            print()
            tprint.info(f"Project: {folder_name}")
            if warn:
                for w in warn:
                    tprint.warning(w)

            if error:
                tprint.warning("Issues detected:")
                for idx, issue in enumerate(issues, start=1):
                    print(f"\033[91m  [{idx}] {issue}\033[0m")

                self.__suggest_fixes(issues)
                self.__show_issues(folder_path)

                self.check.project(self.menu_items, folder_name, folder_path)
                self._flasher_menu()
            else:
                self.__flash_esp32(folder_name)
        except Exception as e:
            handler.exception(msg=e)

    def __show_issues(self, folder_path):
        def delete_subdirectories(path):
            try:
                if not os.path.isdir(path):
                    raise ValueError(f"Provided path '{path}' is not a directory.")

                for entry in os.scandir(path):
                    if entry.is_dir(follow_symlinks=False):
                        try:
                            shutil.rmtree(entry.path)
                            tprint.debug(f"Deleted directory: {entry.path}")
                        except Exception as e:
                            handler.exception(msg=f"Failed {entry.path} -> {e}")
                tprint.success("Subdirectories removed.")
            except Exception as e:
                handler.exception(msg=e)

        tprint.info("Options:")
        print("  [1] Open folder to fix manually")
        print("  [2] Autogenerate config.ini (or regenerate)")
        print("  [3] Remove subdirectories (if any)")
        choice = tprint.input(" > ").strip()

        if choice == '1':
            os.system(f'explorer {folder_path}')
            tprint.input("Press enter to recheck the project: > ")
        elif choice == '2':
            self.__generate_config(folder_path)
        elif choice == '3':
            delete_subdirectories(folder_path)
        else:
            if choice.lower() != 'exit':
                tprint.warning("Invalid choice, returning to menu.")

    def __generate_config(self, folder_path: str) -> None:
        try:
            if not os.path.exists(folder_path):
                tprint.error(f"'{folder_path}' folder not found.")
            if not os.path.isdir(folder_path):
                tprint.error(f"'{folder_path}' is not a directory.")

            config_path = os.path.join(folder_path, 'config.ini')
            if os.path.exists(config_path):
                tprint.warning("'config.ini' already exists. Regenerating will overwrite it.")
                os.remove(config_path)

            bin_files = [f for f in os.listdir(folder_path) if f.endswith('.bin')]
            if not bin_files:
                tprint.error("No .bin files found in the folder to generate config.ini.")

            print()
            tprint.info(f"Found BIN files: {', '.join(bin_files)}")

            baud = self.get.valid_baud_rate()
            if baud == 'exit':
                return

            config = configparser.ConfigParser()
            config['Settings'] = {'Baud_Rate': baud}

            used_addresses = set()
            for bin_file in bin_files:
                while True:
                    address = self.get.valid_address(bin_file)
                    if address == 'exit':
                        return
                    if address in used_addresses:
                        tprint.warning(f"Address {address} is already in use. Please enter a unique address.")
                    else:
                        used_addresses.add(address)
                        break
                config['Settings'][bin_file] = address

            config_path = os.path.join(folder_path, 'config.ini')
            with open(config_path, 'w') as configfile:
                config.write(configfile)

            print()
            tprint.success("'config.ini' generated successfully!")
        except Exception as e:
            handler.exception(msg=e)

    @staticmethod
    def __suggest_fixes(issues: list[str]) -> None:
        """Provide suggestive fixes for detected issues."""
        try:
            print()
            tprint.info("Suggestive Fixes:")
            for idx, issue in enumerate(issues, start=1):
                if "Missing config.ini" in issue:
                    print("    Suggestion: Use the 'Autogenerate config.ini' option to create a new config.ini file.")
                elif "Invalid memory address" in issue:
                    print(
                        "    Suggestion: Ensure all memory addresses in config.ini are in hex format (e.g., 0x10000).")
                elif "Bin file" in issue and "not referenced" in issue:
                    print("    Suggestion: Add the missing bin file to the [Settings] section of config.ini.")
                elif "Bin file" in issue and "referenced in config.ini but not found" in issue:
                    print("    Suggestion: Ensure the referenced bin file exists in the project folder.")
                elif "Subfolders detected" in issue:
                    print("    Suggestion: Remove subfolders from the project folder to avoid conflicts.")
                elif "Invalid or missing Baud_Rate" in issue:
                    print(
                        "    Suggestion: Add a valid Baud_Rate (e.g. 115200) to the [Settings] section of config.ini.")
                elif "Memory address conflict" in issue:
                    print("    Suggestion: Ensure all memory addresses in config.ini are unique.")
                else:
                    print("    Suggestion: Review the issue manually and resolve it.")
            print()
        except Exception as e:
            handler.exception(msg=e)

    def __com_port_menu(self, ports):
        print()
        tprint.info("Available COM ports:")
        likely_port = None
        for idx, port in enumerate(ports):
            is_likely = 'esp' in port.description.lower() or 'usb' in port.description.lower()
            marker = '\033[92m <-- likely ESP32\033[0m' if is_likely else ''
            if is_likely and not likely_port:
                likely_port = port.device
            tprint.info(f"[{idx + 1}] {port.device} - {port.description}{marker}")

        choice = tprint.input("Select a COM port (or press enter to use suggested): > ").strip()
        if choice.lower() == 'exit':
            return

        return self.get.selected_com_port(choice, likely_port, ports)

    def __start_communication(self, project_name: str, baud_rate: str) -> None:
        try:
            ports = list(serial.tools.list_ports.comports())
            if not ports:
                tprint.error("No COM ports found.")
                return

            selected_port = self.__com_port_menu(ports)

            if not selected_port:
                tprint.warning("No COM port selected, returning to menu.")
                return

            print()
            tprint.info(f"Connecting to {selected_port} at {baud_rate} baud...")
            try:
                def __test_connection(port_test, baud_test):
                    try:
                        with serial.Serial(port_test, int(baud_test), timeout=1) as ser_test:
                            ser_test.write(b'\x55')  # Send a recognizable byte pattern (e.g., 0x55)
                            response = ser_test.read(100).decode(errors='ignore')
                            if "ESP" in response or "rst:" in response:
                                tprint.debug(f"Received response at baud rate {baud_test}: \n{response}")
                                return True
                    except serial.SerialException as err:
                        tprint.warning(f"Serial Exception at baud rate {baud_test}: {err}")
                    except OSError as err:
                        tprint.warning(f"OSError at baud rate {baud_test}: {err}")
                    return False

                if not __test_connection(selected_port, baud_rate):
                    tprint.warning(f"Failed to connect at {baud_rate} baud.")
                    choice = tprint.input(
                        "Do you want to auto-fix and find the correct baud rate? (y/n): > ").strip().lower()
                    if choice == 'y':
                        tprint.info("Attempting to find a working baud rate...")
                        for rate in sorted(Check.esp32_supported_baudrates, reverse=True):
                            tprint.debug(f"Trying baud rate: {rate}")
                            if __test_connection(selected_port, rate):
                                baud_rate = rate
                                tprint.success(f"Connection successful at {baud_rate} baud.")
                                self.config.set('Settings', 'Baud_Rate', str(baud_rate))
                                with open(os.path.join(self.esp32_folder, project_name, 'config.ini'), 'w') as configfile:
                                    self.config.write(configfile)
                                tprint.info(f"Baud rate {baud_rate} saved to config.ini.")
                                break
                        else:
                            tprint.warning("Unable to find a working baud rate. Returning to menu.")
                            return
                    else:
                        tprint.info("Auto-fix skipped. Connecting...")

                with serial.Serial(selected_port, int(baud_rate), timeout=1) as ser:
                    print()
                    separator(f"Session {project_name or 'Temporary'} Started")
                    print("Press Ctrl+C to exit the session.\n")
                    while True:
                        try:
                            if ser.in_waiting > 0:
                                print(ser.read(ser.in_waiting).decode(errors='ignore'), end='', flush=True)
                        except KeyboardInterrupt:
                            if ser.is_open:
                                tprint.debug("Closing serial port and resetting input buffer.")
                                ser.reset_input_buffer()  # Clear any existing data in the serial buffer
                                ser.close()
                            break
                        except Exception as e:
                            handler.exception(msg=e)
                            if ser.is_open:
                                tprint.debug("Closing serial port and resetting input buffer.")
                                ser.reset_input_buffer()  # Clear any existing data in the serial buffer
                                ser.close()
                            break
            except Exception as e:
                handler.exception(msg=e)
                return
            finally:
                print()
                separator(f"Session {project_name or 'Temporary'} Ended")
        except Exception as e:
            handler.exception(msg=e)


class Check:
    esp32_supported_baudrates = [
        50,
        75,
        110,
        134,
        150,
        200,
        300,
        600,
        1200,
        1800,
        2400,
        4800,
        9600,  # Default baudrate for many USB-UART bridges
        14400,
        19200,
        28800,
        38400,
        57600,
        74880,  # Default bootloader baudrate
        115200,  # Most common and default flashing speed
        128000,
        230400,
        256000,
        460800,  # Fast and reliable
        512000,
        921600,  # Maximum reliable speed for many USB-UART bridges (CP210x, CH340)
        1000000,
        1152000,
        1500000,
        2000000,  # Often flaky unless high-end bridge + short cable
    ]

    def __init__(self, config):
        self.config = config

    def project(self, menu_items, folder_name: str, folder_path: str) -> None:
        try:
            refreshed_issues, _ = self.for_issues(folder_path)
            for idx, (name, error, issues, warn) in enumerate(menu_items):
                if name == folder_name:
                    error = True if refreshed_issues else False
                    menu_items[idx] = (folder_name, error, refreshed_issues if error else None, warn)
                    break
        except Exception as e:
            handler.exception(msg=e)

    def for_memory_address_conflicts(self, bin_files: list[str]) -> list[str]:
        """Check if any of the bin files in the config have conflicting memory addresses."""
        try:
            addresses = {}
            mem_conflicts = []
            for bin_file in bin_files:
                address = self.config['Settings'].get(bin_file)
                if address in addresses:
                    mem_conflicts.append(
                        f"Memory address conflict: '{bin_file}' and '{addresses[address]}' are using the same address: {address}")
                addresses[address] = bin_file
            return mem_conflicts
        except Exception as e:
            handler.exception(msg=e)
            return ["Unexpected error during memory address conflict check."]

    def for_issues(self, folder_path: str) -> tuple[list[str], list[str]]:

        def validate_memory_addresses() -> list[str]:
            """Ensure all memory addresses are valid hex."""
            issues_local = []
            try:
                settings = self.config['Settings']
                for key, value in settings.items():
                    if key.endswith('.bin') and not (
                            value.startswith('0x') and all(c in '0123456789abcdefABCDEF' for c in value[2:])):
                        issues_local.append(f"Invalid memory address: {value}. Address must be in hex format.")
                return issues_local
            except Exception as err:
                handler.exception(msg=err)
                return ["Unexpected error during memory address validation."]

        try:
            issues = []
            warn = []
            config_path = os.path.join(folder_path, 'config.ini')

            if not os.path.exists(config_path):
                issues.append("Missing config.ini")
                return issues, warn

            self.config.read(config_path)
            if 'Settings' not in self.config.sections():
                issues.append("Missing [Settings] section in config.ini")
                return issues, warn

            bin_files = [f for f in os.listdir(folder_path) if f.endswith('.bin')]
            referenced_files = [key for key in self.config['Settings'] if key.endswith('.bin')]

            mem_conflicts = self.for_memory_address_conflicts(bin_files)
            if mem_conflicts:
                for conflict in mem_conflicts:
                    issues.append(conflict)

            for bin_file in bin_files:
                if bin_file not in referenced_files:
                    issues.append(f"Bin file '{bin_file}' is not referenced in config.ini")
            for ref_file in referenced_files:
                if ref_file not in bin_files:
                    issues.append(f"Bin file '{ref_file}' is referenced in config.ini but not found in the folder")

            # Check for subfolders inside the project folder
            subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
            if subfolders:
                issues.append(f"Subfolders detected in project folder: {', '.join(subfolders)}")

            issues += validate_memory_addresses()

            baud_rate = self.config.get('Settings', 'Baud_Rate', fallback=None)
            if not baud_rate or not baud_rate.isdigit():
                issues.append(f"Invalid or missing Baud_Rate in config.ini")
            else:
                baud_rate = int(baud_rate)
                if baud_rate not in self.esp32_supported_baudrates:
                    warn.append(f"Baud Rate: {baud_rate} is unusual, so take heed.")
                if baud_rate < 0:
                    issues.append(f"Invalid Baud Rate: {baud_rate}. Must be above 0.")
                if baud_rate > 2000000:
                    warn.append(
                        f"Baud Rate: {baud_rate} is unusually high, so take heed. Anything above 2000000 may not work.")

            return issues, warn
        except Exception as e:
            handler.exception(msg=e)
            return ["Unexpected error during folder check."], []

    @staticmethod
    def update_status() -> tuple[str, str]:
        """Check the update status and return the status message and color."""
        try:
            if shutil.which("git") is None:
                return "Git Not Installed", "\033[91m"  # Red

            # Check if current directory is a Git repo
            try:
                subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"], stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                return "Not a Git Repo", "\033[91m"  # Red

            # Check current branch
            try:
                branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
                if branch not in ["main", "nightly"]:
                    return f"Unsupported Branch ({branch})", "\033[91m"  # Red
            except Exception:
                return "Unknown Branch", "\033[91m"  # Red

            # Check GitHub connectivity (Windows only)
            ping_result = subprocess.run(["ping", "-n", "1", "github.com"], stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL).returncode
            if ping_result != 0:
                return "Offline", "\033[91m"  # Red

            # Fetch remote and check for updates
            subprocess.run(["git", "fetch"], stdout=subprocess.DEVNULL)
            local_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
            remote_commit = subprocess.check_output(["git", "rev-parse", f"origin/{branch}"]).decode().strip()

            if subprocess.check_output(["git", "status", "--porcelain"]).strip():
                return "Uncommitted Changes", "\033[93m"  # Yellow
            elif subprocess.check_output(["git", "rev-list", "--left-right", f"{branch}..origin/{branch}"]).strip():
                return "Ahead of Remote", "\033[93m"  # Yellow
            elif local_commit == remote_commit:
                return "Up-to-date", "\033[97m"  # White
            else:
                return "Update Available", "\033[92m"  # Green
        except Exception:
            return "Error Checking Updates", "\033[91m"  # Red


class Get:
    @staticmethod
    def valid_baud_rate() -> str:
        try:
            while True:
                baud = tprint.input("Enter Baud Rate: > ").strip()
                if baud.lower() == 'exit':
                    return 'exit'
                if baud.isdigit():
                    return baud
                tprint.warning("Invalid baud rate. Please enter numbers only.")
        except Exception as e:
            handler.exception(msg=e)

    @staticmethod
    def valid_address(bin_file: str) -> str:
        try:
            while True:
                address = tprint.input(f"Enter memory address for '{bin_file}': > ").strip()
                if address.lower() == 'exit':
                    return 'exit'
                if address.startswith('0x') and all(c in '0123456789abcdefABCDEF' for c in address[2:]):
                    return address
                tprint.warning("Invalid address format. Use hex (e.g., 0x10000).")
        except Exception as e:
            handler.exception(msg=e)

    @staticmethod
    def selected_com_port(choice: str, likely_port: str, ports: list) -> str:
        """Return the selected COM port, or None if invalid."""
        try:
            if choice == '' and likely_port:
                return likely_port
            elif choice == '' and not likely_port:
                tprint.error("No suggested port was found. Please select a port manually.")
                return None
            try:
                return ports[int(choice) - 1].device
            except (ValueError, IndexError):
                tprint.error("Invalid selection. Returning to menu.")
                return None
        except Exception as e:
            handler.exception(msg=e)
            return None


def main():
    try:
        if not os.path.exists("esp32"):
            os.mkdir("esp32")
            print()
            tprint.warning("The 'esp32' folder did not exist. It has been created. Add your projects and try again.")
            exit()
        flasher = ESP32()
        flasher.main_menu()
    except KeyboardInterrupt:
        print()
        tprint.warning("Program interrupted. Please use 'exit' instead of Ctrl+C.")
    except Exception as err:
        print()
        handler.exception(msg=err)
    finally:
        tprint.info("Exiting...")
        print()
        separator("ESP32 Ultra Flasher")


if __name__ == "__main__":
    main()
