# Quick Installation Guide

## Step 1: Install Dependencies

Open a terminal in the `cursor-tts-extension` folder and run:

```bash
npm install
```

## Step 2: Compile the Extension

```bash
npm run compile
```

## Step 3: Install in Cursor

### Option A: Development Mode (Recommended for testing)

1. Open Cursor
2. Press `F5` or go to `Run > Start Debugging`
3. This opens a new "Extension Development Host" window
4. The extension will be active in that window

### Option B: Package and Install

1. Package the extension:
   ```bash
   npm run package
   ```
   This creates a `.vsix` file in the folder.

2. In Cursor:
   - Open Extensions view (`Ctrl+Shift+X` or `Cmd+Shift+X`)
   - Click the `...` menu (three dots) in the Extensions view
   - Select "Install from VSIX..."
   - Choose the `.vsix` file you just created

## Step 4: Use It!

Once installed, you can:

- Press `Ctrl+Alt+R` (or `Cmd+Alt+R` on Mac) to read the last chat response
- Press `Ctrl+Alt+S` to read selected text
- Press `Ctrl+Alt+X` to stop reading
- Or use Command Palette (`Ctrl+Shift+P`) and search for "Cursor Chat Reader"

## Troubleshooting

### "Cannot find module" errors

Make sure you ran `npm install` in the extension folder.

### TTS not working on Windows

Windows should work out of the box with PowerShell's built-in TTS. If it doesn't, try running PowerShell as administrator.

### TTS not working on Linux

Install a TTS engine:
```bash
sudo apt-get install espeak
```

### Extension not loading

- Check the Output panel (`View > Output`) and select "Log (Extension Host)" to see error messages
- Make sure you compiled the extension (`npm run compile`)
- Restart Cursor after installation





