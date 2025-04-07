# ESP32 Ultra Flasher

---

<div style="text-align:center;" align="center">
    <a href="https://github.com/DefinetlyNotAI/ESP32_FlashMate/issues"><img src="https://img.shields.io/github/issues/DefinetlyNotAI/ESP32_FlashMate" alt="GitHub Issues"></a>
    <a href="https://github.com/DefinetlyNotAI/ESP32_FlashMate/tags"><img src="https://img.shields.io/github/v/tag/DefinetlyNotAI/ESP32_FlashMate" alt="GitHub Tag"></a>
    <a href="https://github.com/DefinetlyNotAI/ESP32_FlashMate/graphs/commit-activity"><img src="https://img.shields.io/github/commit-activity/t/DefinetlyNotAI/ESP32_FlashMate" alt="GitHub Commit Activity"></a>
    <a href="https://github.com/DefinetlyNotAI/ESP32_FlashMate/languages"><img src="https://img.shields.io/github/languages/count/DefinetlyNotAI/ESP32_FlashMate" alt="GitHub Language Count"></a>
    <a href="https://github.com/DefinetlyNotAI/ESP32_FlashMate/actions"><img src="https://img.shields.io/github/check-runs/DefinetlyNotAI/ESP32_FlashMate/main" alt="GitHub Branch Check Runs"></a>
    <a href="https://github.com/DefinetlyNotAI/ESP32_FlashMate"><img src="https://img.shields.io/github/repo-size/DefinetlyNotAI/ESP32_FlashMate" alt="GitHub Repo Size"></a>
</div>

---

**ESP32 Ultra Flasher** is a terminal-based tool to easily flash ESP32 devices. It supports project validation, COM port detection, configuration auto-generation, and flashing of firmware using `esptool`. This project is designed to streamline flashing ESP32 devices, ensuring that configuration files and memory addresses are correctly set up before flashing.

## Features

- **Menu-based interface** for selecting and flashing ESP32 projects.
- **Semi-Automatic generation of `config.ini`** based on `.bin` files in the project folder.
- **Memory address validation** to prevent conflicts when flashing multiple `.bin` files.
- **COM port detection** to list available serial devices and auto-select the correct port for flashing.
- **Error handling** with detailed messages, highlighting issues such as missing files or incorrect settings.
- **Interactive flashing process**, allowing the user to choose whether to erase the flash before writing.
  
## Requirements

- Tested on Python 3.11.
- The following Python packages:
  - `esptool`: for flashing the ESP32.
  - `serial`: for serial communication with the ESP32.
  - `tprint`: for colorful terminal outputs and logging.

### Installation

1. Clone the repository or download the script.
2. Install required dependencies:
   ```bash
   pip install esptool pyserial tprint
   ```

## Usage

1. **Folder Setup:**
   - Place your ESP32 project in the `esp32/` folder, make sure the project is in a folder as well, example `esp32/marauder/`.
   - Each project folder should contain:
     - `.bin` files (firmware binaries).
     - `config.ini` (it will be auto-generated if missing with your help).

2. **Run the Tool:**
   - Navigate to the folder containing the script.
   - Execute the script:
     ```bash
     python esp32_flasher.py
     ```

3. **Select a Project:**
   - The tool will display a list of projects found in the `esp32/` folder. You can select a project to flash or choose options to fix issues with the project.
   - If a project is missing a `config.ini`, you can choose to autogenerate it.

4. **Flashing the ESP32:**
   - After selecting a project, the tool will prompt you to select a COM port and whether you want to erase the flash before flashing the new firmware.
   - Once the correct settings are chosen, the flashing process will begin.

5. **Handle Issues:**
   - If any project has missing or misconfigured files, the tool will display a warning and allow you to fix issues before proceeding.

## Menu Breakdown

- **1. Open folder to fix manually:** Opens the project folder to allow the user to manually edit the files.
- **2. Autogenerate config.ini:** Automatically generates a new `config.ini` based on the `.bin` files found in the project.
- **3. Recheck this project:** Re-checks the project for errors after making manual changes or generating a new config file.
- **4. Return to menu:** Returns to the main project menu.

## Configuration

If you need to generate or edit the `config.ini` manually, it should be placed in the project folder with the following format:

```ini
[Settings]
Baud_Rate = 115200
firmware.bin = 0x1000
...
```

- `Baud_Rate`: The baud rate used for flashing (e.g., `115200`).
- Each `.bin` file listed in the `config.ini` must have an associated memory address (in hexadecimal, e.g., `0x1000`).

## Troubleshooting

- **Missing `config.ini`:**
  If a project doesn't have a `config.ini`, the tool will offer to generate it semi-automatically.
  
- **Memory Address Conflicts:**
  The tool will check for conflicting memory addresses and warn you if two `.bin` files are configured to use the same address.

- **COM Port Detection Issues:**
  If the tool cannot detect any available COM ports, ensure your ESP32 device is properly connected and try again.

- **Flashing Fails:**
  If flashing fails, ensure the ESP32 is in bootloader mode and retry.

## Future Ideas

- [ ] Add communication to the tool for already flashed files

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

If you have any suggestions or issues, feel free to contribute or open an issue on the GitHub repository.
