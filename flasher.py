import configparser
import os

import esptool
import serial
import serial.tools.list_ports

from utils import tprint, handler, separator


class ESP32UltraFlasher:
    def __init__(self):
        self.esp32_folder = 'esp32'
        self.esp32_supported_baudrates = [
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
            2500000,
            3000000,
            3500000,
            4000000  # ESP32 supports it, but most bridges can't
        ]
        self.menu_items = []
        self.current_item = None
        self.config = configparser.ConfigParser()
        self.__load_menu_items()

    def display_menu(self) -> None:
        try:
            print()

            if len(self.menu_items) == 0:
                tprint.warning("No projects found in the 'esp32' folder.")
                tprint.warning("Please add your projects and try again.")
                exit()

            tprint.info("Select a project to flash:")
            for idx, (item, error, issues, warn) in enumerate(self.menu_items):
                if error:
                    tprint.warning(f"   <{idx + 1}> {item}")
                else:
                    tprint.info(f"  <{idx + 1}> {item}")

            selection = tprint.input("Enter a number to select, or 'exit' to quit: > ").strip()

            if selection.lower() == 'exit':
                exit()

            while True:
                try:
                    selection = int(selection) - 1
                    tprint.debug(f"Selection of user (index): {selection}")
                    if 0 <= selection < len(self.menu_items):
                        self.current_item = self.menu_items[selection]
                        self.__handle_selection(self.current_item)
                        break
                    else:
                        tprint.warning("Invalid selection, try again.")
                except ValueError:
                    tprint.error("Invalid input, please enter a valid number or 'exit'.")
                selection = tprint.input("Enter a number to select, or 'exit' to quit: > ").strip()
                if selection.lower() == 'exit':
                    exit()
        except Exception as e:
            handler.exception(msg=e)

    def __autogenerate_config(self, folder_path: str) -> bool:
        try:
            bin_files = [f for f in os.listdir(folder_path) if f.endswith('.bin')]
            if not bin_files:
                tprint.error("No .bin files found in the folder to generate config.ini.")
                return False

            print()
            tprint.info(f"Found BIN files: {', '.join(bin_files)}")

            baud = self.__get_valid_baud_rate()
            if baud == 'exit':
                return False

            config = configparser.ConfigParser()
            config['Settings'] = {'Baud_Rate': baud}

            for bin_file in bin_files:
                address = self.__get_valid_address(bin_file)
                if address == 'exit':
                    return False
                config['Settings'][bin_file] = address

            config_path = os.path.join(folder_path, 'config.ini')
            with open(config_path, 'w') as configfile:
                config.write(configfile)

            print()
            tprint.success("'config.ini' generated successfully!")
            return True
        except Exception as e:
            handler.exception(msg=e)
            return False

    @staticmethod
    def __get_valid_baud_rate() -> str:
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
    def __get_valid_address(bin_file: str) -> str:
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

    def __load_menu_items(self) -> None:
        try:
            if not os.path.exists(self.esp32_folder):
                tprint.error(f"'{self.esp32_folder}' folder not found.")
                return

            self.menu_items = []
            for folder in os.listdir(self.esp32_folder):
                folder_path = os.path.join(self.esp32_folder, folder)
                if os.path.isdir(folder_path):
                    issues, warn = self.__check_folder_for_issues(folder_path)
                    self.menu_items.append((folder, True if issues else False, issues if issues else [], warn if warn else []))

        except Exception as e:
            handler.exception(msg=e)

    def __check_folder_for_issues(self, folder_path: str) -> tuple[list[str], list[str]]:
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

            mem_conflicts = self.__check_for_memory_address_conflicts(bin_files)
            if mem_conflicts:
                for conflict in mem_conflicts:
                    issues.append(conflict)

            for bin_file in bin_files:
                if bin_file not in referenced_files:
                    issues.append(f"Bin file '{bin_file}' is not referenced in config.ini")
            for ref_file in referenced_files:
                if ref_file not in bin_files:
                    issues.append(f"Bin file '{ref_file}' is referenced in config.ini but not found in the folder")

            issues += self.__validate_memory_addresses()

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

    def __validate_memory_addresses(self) -> list[str]:
        """Ensure all memory addresses are valid hex."""
        issues = []
        try:
            settings = self.config['Settings']
            for key, value in settings.items():
                if key.endswith('.bin') and not (
                        value.startswith('0x') and all(c in '0123456789abcdefABCDEF' for c in value[2:])):
                    issues.append(f"Invalid memory address: {value}. Address must be in hex format.")
            return issues
        except Exception as e:
            handler.exception(msg=e)
            return ["Unexpected error during memory address validation."]

    def __handle_selection(self, item: tuple[str, str, list[str], list[str]]) -> None:
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
                for issue in issues:
                    print(f"\033[91m  - {issue}\033[0m")

                print()
                tprint.info("Options:")
                print("  [1] Open folder to fix manually")
                print("  [2] Autogenerate config.ini")
                print("  [3] Recheck this project")
                print("  [4] Return to menu")
                choice = tprint.input(" > ").strip()

                if choice == '1':
                    os.system(f'explorer {folder_path}')
                    tprint.input("Press enter to recheck the project: > ")
                    self.__check_project(folder_name, folder_path)
                elif choice == '2':
                    if self.__autogenerate_config(folder_path):
                        self.__check_project(folder_name, folder_path)
                    else:
                        tprint.error("Failed to autogenerate config.ini.")
                elif choice == '3':
                    self.__check_project(folder_name, folder_path)
                else:
                    if choice.lower() != 'exit':
                        tprint.warning("Invalid choice, returning to menu.")
                self.display_menu()
            else:
                self.__flash_esp32(folder_name)
        except Exception as e:
            handler.exception(msg=e)

    def __check_project(self, folder_name: str, folder_path: str) -> None:
        try:
            refreshed_issues, _ = self.__check_folder_for_issues(folder_path)
            for idx, (name, _, _) in enumerate(self.menu_items):
                if name == folder_name:
                    error = True if refreshed_issues else False
                    self.menu_items[idx] = (folder_name, error, refreshed_issues if error else None)
                    break
        except Exception as e:
            handler.exception(msg=e)

    def __flash_esp32(self, folder_name: str) -> None:
        """Flash the ESP32 using the config.ini instructions."""
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
                self.display_menu()
                return

            print()
            tprint.info("Available COM ports:")
            likely_port = None
            for idx, port in enumerate(ports):
                is_likely = 'esp' in port.description.lower() or 'usb' in port.description.lower()
                marker = ' <-- likely ESP32' if is_likely else ''
                if is_likely and not likely_port:
                    likely_port = port.device
                tprint.info(f"<{idx + 1}> {port.device} - {port.description}{marker}")

            choice = tprint.input("Select a COM port (or press enter to use suggested): > ").strip()
            if choice.lower() == 'exit':
                return

            selected_port = self.__get_selected_com_port(choice, likely_port, ports)
            if not selected_port:
                tprint.warning("No COM port selected, returning to menu.")
                self.display_menu()
                return

            # Flash the ESP32
            self.__flash(selected_port, folder_path, bin_files, baud_rate)
        except Exception as e:
            handler.exception(msg=e)

    @staticmethod
    def __get_selected_com_port(choice: str, likely_port: str, ports: list) -> str:
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

    @staticmethod
    def __flash(port: str, folder_path: str, bin_files: dict[str, str], baud_rate: str) -> None:
        """Flash the ESP32."""
        try:
            # Ask if user wants to erase flash
            erase_flash = tprint.input("Do you want to erase the flash before flashing? (y/n): > ").strip().lower()

            while erase_flash not in ['y', 'n']:
                tprint.warning("Invalid input. Please enter 'y' or 'n'.")
                erase_flash = tprint.input("Do you want to erase the flash before flashing? (y/n): > ").strip().lower()

            # Proceed with flashing
            tprint.debug(f"Flashing to {port} at {baud_rate} baud...")

            flash_args = [
                '--chip', 'esp32',
                '--port', port,
                '--baud', baud_rate,
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
            for fname, addr in bin_files.items():
                if not addr:
                    tprint.error(f"Address for {fname} is empty.")
                    return
                full_path = os.path.join(folder_path, fname)
                flash_args.extend([addr, full_path])

            # Flash the ESP32
            esptool.main(flash_args)
            print()
            tprint.success("Flashing complete.")
            print()

        except Exception as e:
            print()
            handler.exception(msg=f"Flashing failed: {e}")
            print()

    def __check_for_memory_address_conflicts(self, bin_files: list[str]) -> list[str]:
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


if __name__ == "__main__":
    try:
        separator("ESP32 Ultra Flasher")
        if not os.path.exists("esp32"):
            os.mkdir("esp32")
            print()
            tprint.warning("The 'esp32' folder does not exist. We have recreated it so add your projects.")
            exit()
        flasher = ESP32UltraFlasher()
        flasher.display_menu()
    except KeyboardInterrupt:
        print()
        tprint.warning("Program interrupted in a non-graceful way. May produce issues")
        tprint.warning("Please don't exit the program in this way, use 'exit' instead.")
    except Exception as err:
        print()
        handler.exception(msg=err)
    finally:
        tprint.info("Exiting...")
        print()
        separator("ESP32 Ultra Flasher")
