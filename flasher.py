import configparser
import os
import esptool
import serial
import serial.tools.list_ports
from tprint import TPrint, TPrintColors, separator

tprint = TPrint(
    color_scheme={
        'info': TPrintColors.WHITE,
        'warning': TPrintColors.YELLOW,
        'error': TPrintColors.RED,
        'debug': TPrintColors.CYAN,
        'critical': TPrintColors.BRIGHT_RED,
        'success': TPrintColors.BRIGHT_GREEN,
        'input': TPrintColors.GREEN
    },
    debug_mode=True,
    use_timestamps=False,
    purge_old_logs=True
)


class ESP32UltraFlasher:
    def __init__(self):
        self.esp32_folder = 'esp32'
        self.menu_items = []
        self.current_item = None
        self.config = configparser.ConfigParser()
        self.__load_menu_items()

    @staticmethod
    def __autogenerate_config(folder_path: str) -> None:
        bin_files = [f for f in os.listdir(folder_path) if f.endswith('.bin')]
        if not bin_files:
            tprint.error("No .bin files found in the folder to generate config.ini.")
            return

        print()
        tprint.info(f"Found BIN files: {', '.join(bin_files)}")

        baud = tprint.input("Enter Baud Rate: > ").strip()
        while not baud.isdigit():
            tprint.warning("Invalid baud rate. Please enter numbers only.")
            baud = tprint.input("Enter Baud Rate: > ").strip()

        config = configparser.ConfigParser()
        config['Settings'] = {'Baud_Rate': baud}

        for bin_file in bin_files:
            address = tprint.input(f"Enter memory address for '{bin_file}': > ").strip()
            while not (address.startswith('0x') and all(c in '0123456789abcdefABCDEF' for c in address[2:])):
                tprint.warning("Invalid address format. Use hex (e.g., 0x10000).")
                address = tprint.input(f"Enter memory address for '{bin_file}': > ").strip()
            config['Settings'][bin_file] = address

        config_path = os.path.join(folder_path, 'config.ini')
        with open(config_path, 'w') as configfile:
            config.write(configfile)

        print()
        tprint.success("'config.ini' generated successfully!")

    def __load_menu_items(self) -> None:
        """Scan esp32/ directory and populate menu items."""
        if not os.path.exists(self.esp32_folder):
            tprint.error(f"'{self.esp32_folder}' folder not found.")
            return

        self.menu_items = []
        for folder in os.listdir(self.esp32_folder):
            folder_path = os.path.join(self.esp32_folder, folder)
            if os.path.isdir(folder_path):
                issues = self.__check_folder_for_issues(folder_path)
                if issues:
                    self.menu_items.append((folder, True, issues))
                else:
                    self.menu_items.append((folder, False, []))

    def __check_folder_for_issues(self, folder_path: str) -> list[str]:
        issues = []
        config_path = os.path.join(folder_path, 'config.ini')

        if not os.path.exists(config_path):
            issues.append("Missing config.ini")
            return issues

        try:
            self.config.read(config_path)
            if 'Settings' not in self.config.sections():
                issues.append("Missing [Settings] section in config.ini")
                return issues

            # Check if all bin files in the folder are referenced in config.ini
            bin_files = [f for f in os.listdir(folder_path) if f.endswith('.bin')]
            referenced_files = [key for key in self.config['Settings'] if key.endswith('.bin')]
            for bin_file in bin_files:
                if bin_file not in referenced_files:
                    issues.append(f"Bin file '{bin_file}' is not referenced in config.ini")
            for ref_file in referenced_files:
                if ref_file not in bin_files:
                    issues.append(f"Bin file '{ref_file}' is referenced in config.ini but not found in the folder")

            # Validate memory addresses (must be hex)
            for key, value in self.config.items('Settings'):
                if key.endswith('.bin'):
                    if not (value.startswith('0x') and all(c in '0123456789abcdefABCDEF' for c in value[2:])):
                        issues.append(f"Invalid address format for {key}. Use hex (e.g., 0x10000).")

            # Validate baud rate (must be a number)
            if not self.config.has_option('Settings', 'Baud_Rate'):
                issues.append("Missing Baud_Rate in config.ini")
            else:
                baud_rate = self.config.get('Settings', 'Baud_Rate')
                if not baud_rate.isdigit():
                    issues.append(f"Invalid Baud_Rate '{baud_rate}', must be a valid number.")

        except Exception as e:
            issues.append(f"Error reading config.ini: {e}")

        return issues

    def display_menu(self) -> None:
        """Display the main menu with index-based selection."""
        print()
        tprint.info("Select a project to flash:")
        for idx, (item, error, _) in enumerate(self.menu_items):
            if error:
                tprint.warning(f"   <{idx + 1}> {item}")
            else:
                tprint.info(f"  <{idx + 1}> {item}")

        selection = tprint.input("Enter a number to select, or 'exit' to quit: > ").strip()

        if selection.lower() == 'exit':
            tprint.debug("Exiting...")
            exit()

        try:
            selection = int(selection) - 1
            tprint.debug(f"Selection of user (index): {selection}")
            if 0 <= selection < len(self.menu_items):
                self.current_item = self.menu_items[selection]
                self.__handle_selection(self.current_item)
            elif selection == "exit":
                tprint.warning("Returning to main menu...")
                self.display_menu()
            else:
                tprint.warning("Invalid selection, try again.")
                tprint.debug(f"Reason: out of range [0 < selection <= {len(self.menu_items)}]")
                self.display_menu()
        except ValueError:
            tprint.error("Invalid input, please enter a valid number or 'exit'.")
            self.display_menu()

    def _check_project(self, folder_name: str, folder_path: str) -> None:
        refreshed_issues = self.__check_folder_for_issues(folder_path)
        for idx, (name, _, _) in enumerate(self.menu_items):
            if name == folder_name:
                error = True if refreshed_issues else False
                self.menu_items[idx] = (folder_name, error, refreshed_issues if error else None)
                break

    def __handle_selection(self, item: tuple[str, str, list[str]]) -> None:
        """Handle selected menu item."""
        folder_name, error, issues = item
        folder_path = os.path.join(self.esp32_folder, folder_name)

        if error:
            print()
            tprint.info(f"Project: {folder_name}")
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
            elif choice == '2':
                self.__autogenerate_config(folder_path)
            else:
                tprint.warning("Not valid choice, returning to menu.")
            self._check_project(folder_name, folder_path)
            self.display_menu()
        else:
            self._flash_esp32(folder_name)

    def _flash_esp32(self, folder_name: str) -> None:
        """Flash the ESP32 using the config.ini instructions."""
        folder_path = os.path.join(self.esp32_folder, folder_name)
        config_path = os.path.join(folder_path, 'config.ini')
        self.config.read(config_path)

        if 'Settings' not in self.config.sections():
            tprint.error("Missing [Settings] section in config.ini")
            return

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

        if choice == '' and likely_port:
            selected_port = likely_port
        elif choice == '' and not likely_port:
            tprint.error("No suggested port found. Please select a port.")
            self.display_menu()
            return
        elif choice.lower() == 'exit':
            tprint.info("Returning to Main Menu...")
            self.display_menu()
            return
        else:
            try:
                selected_port = ports[int(choice) - 1].device
                tprint.debug(f"Selected port (index): {selected_port}")
            except (ValueError, IndexError):
                tprint.error("Invalid selection. Returning to menu.")
                self.display_menu()
                return

        # Firmware Version Check
        self._check_firmware_version(selected_port)

        # Flash the ESP32
        self.__flash(selected_port, folder_path, bin_files, baud_rate)

    @staticmethod
    def _check_firmware_version(port: str) -> None:
        """Check the firmware version of the connected ESP32 device."""
        print()
        try:
            tprint.debug("Checking firmware version...")
            esptool.main(['--chip', 'esp32', '--port', port, 'read_mac'])
        except Exception as e:
            tprint.debug(f"Error reading firmware version: {e}")

    @staticmethod
    def __flash(port: str, folder_path: str, bin_files: dict[str, str], baud_rate: str) -> None:
        """Flash the ESP32."""
        # Ask if user wants to erase flash
        erase_flash = tprint.input("Do you want to erase the flash before flashing? (y/n): > ").strip().lower()

        while erase_flash not in ['y', 'n']:
            tprint.warning("Invalid input. Please enter 'y' or 'n'.")
            erase_flash = tprint.input("Do you want to erase the flash before flashing? (y/n): > ").strip().lower()

        tprint.debug(f"Flashing to {port} at {baud_rate} baud...")

        try:
            args = [
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
                args.append('--erase')

            for fname, addr in bin_files.items():
                if not addr:
                    tprint.error(f"Address for {fname} is empty.")
                    return
                full_path = os.path.join(folder_path, fname)
                args.extend([addr, full_path])

            esptool.main(args)
            print()
            tprint.success(f"Flashing complete.")
            print()

        except Exception as e:
            print()
            tprint.critical(f"Flashing failed: {e}")
            print()


if __name__ == "__main__":
    try:
        separator("ESP32 Ultra Flasher")
        flasher = ESP32UltraFlasher()
        flasher.display_menu()
    except KeyboardInterrupt:
        print()
        tprint.info("Exiting...")
        tprint.warning("Program interrupted in a non-graceful way. May produce issues")
        tprint.warning("Please don't exit the program in this way, use 'exit' instead.")
    finally:
        print()
        separator("ESP32 Ultra Flasher")
