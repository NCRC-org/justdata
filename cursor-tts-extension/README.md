# Cursor Chat Reader Extension

A VS Code/Cursor extension that adds text-to-speech functionality to read chat responses aloud.

## Features

- 🎤 **Read Last Chat Response** - Reads the most recent chat response
- 📝 **Read Selected Text** - Reads any selected text in the editor
- ⏹️ **Stop Reading** - Stops the current speech
- 🔄 **Auto-Read Mode** - Automatically reads chat responses when they complete
- ⚙️ **Customizable** - Adjust voice, rate, pitch, and volume

## Installation

### From Source

1. Clone or download this extension folder
2. Open a terminal in the `cursor-tts-extension` directory
3. Run:
   ```bash
   npm install
   npm run compile
   ```
4. In Cursor/VS Code, press `F5` to open a new Extension Development Host window
5. Or package it: `npm run package` and install the `.vsix` file

### Manual Installation

1. Build the extension:
   ```bash
   cd cursor-tts-extension
   npm install
   npm run compile
   npm run package
   ```
2. In Cursor, go to Extensions view (`Ctrl+Shift+X`)
3. Click the `...` menu and select "Install from VSIX..."
4. Select the generated `.vsix` file

## Usage

### Keyboard Shortcuts

- `Ctrl+Alt+R` (Mac: `Cmd+Alt+R`) - Read last chat response
- `Ctrl+Alt+S` (Mac: `Cmd+Alt+S`) - Read selected text
- `Ctrl+Alt+X` (Mac: `Cmd+Alt+X`) - Stop reading

### Commands

Open Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and type:
- `Cursor Chat Reader: Read Last Chat Response`
- `Cursor Chat Reader: Read Selected Text`
- `Cursor Chat Reader: Stop Reading`
- `Cursor Chat Reader: Toggle Auto-Read`

### Configuration

Open Settings (`Ctrl+,` / `Cmd+,`) and search for "Cursor Chat Reader":

- **Voice**: Preferred voice name (leave empty for default)
- **Rate**: Speech rate (0.1 to 10.0, default: 1.0)
- **Pitch**: Speech pitch (0 to 2, default: 1.0)
- **Volume**: Speech volume (0 to 1, default: 1.0)
- **Auto-Read**: Automatically read chat responses (default: false)

## How It Works

The extension uses:
- **Web Speech API** (when available in web context) - Browser-based TTS
- **System TTS** (fallback) - Uses platform-specific commands:
  - Windows: PowerShell SpeechSynthesizer
  - macOS: `say` command
  - Linux: `espeak` or `festival`

## Limitations

- Chat response detection relies on heuristics and may need adjustment based on Cursor's UI structure
- Web Speech API may not be available in all contexts
- System TTS fallback requires appropriate TTS engines installed on Linux

## Troubleshooting

### No sound / TTS not working

1. **Check system volume** - Ensure your system volume is up
2. **Try system TTS** - The extension will automatically fall back to system TTS if Web Speech API isn't available
3. **Linux users** - Install a TTS engine:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install espeak
   # or
   sudo apt-get install festival
   ```

### Can't find chat responses

- Use "Read Selected Text" command and manually select the chat response
- Copy the chat response to clipboard, then use "Read Last Chat Response"

## Development

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch for changes
npm run watch

# Package extension
npm run package
```

## License

MIT

## Contributing

Feel free to submit issues and enhancement requests!





