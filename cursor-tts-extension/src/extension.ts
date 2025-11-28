import * as vscode from 'vscode';

let currentProcess: any = null;
let autoReadEnabled = false;

export function activate(context: vscode.ExtensionContext) {
    console.log('Cursor Chat Reader extension is now active!');

    // Load auto-read setting
    const config = vscode.workspace.getConfiguration('cursorChatReader');
    autoReadEnabled = config.get<boolean>('autoRead', false);

    // Register commands
    const readLastResponseCommand = vscode.commands.registerCommand(
        'cursorChatReader.readLastResponse',
        readLastChatResponse
    );

    const readSelectedCommand = vscode.commands.registerCommand(
        'cursorChatReader.readSelected',
        readSelectedText
    );

    const stopReadingCommand = vscode.commands.registerCommand(
        'cursorChatReader.stopReading',
        stopReading
    );

    const toggleAutoReadCommand = vscode.commands.registerCommand(
        'cursorChatReader.toggleAutoRead',
        toggleAutoRead
    );

    context.subscriptions.push(
        readLastResponseCommand,
        readSelectedCommand,
        stopReadingCommand,
        toggleAutoReadCommand
    );

    // Monitor for chat responses if auto-read is enabled
    if (autoReadEnabled) {
        setupAutoRead(context);
    }
}

function readLastChatResponse() {
    // Try to find the chat panel and extract the last response
    // This is a simplified approach - Cursor's chat UI structure may vary
    
    // Method 1: Try to get text from active editor if it's a chat response
    const activeEditor = vscode.window.activeTextEditor;
    if (activeEditor) {
        const text = activeEditor.document.getText();
        if (text.trim()) {
            speakText(text);
            return;
        }
    }

    // Method 2: Try to get selected text
    if (activeEditor && !activeEditor.selection.isEmpty) {
        const selectedText = activeEditor.document.getText(activeEditor.selection);
        speakText(selectedText);
        return;
    }

    // Method 3: Use clipboard as fallback
    vscode.env.clipboard.readText().then(text => {
        if (text && text.trim()) {
            speakText(text);
        } else {
            vscode.window.showInformationMessage('No text found to read. Select text or copy chat response to clipboard.');
        }
    });
}

function readSelectedText() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showInformationMessage('No active editor found.');
        return;
    }

    const selection = editor.selection;
    if (selection.isEmpty) {
        vscode.window.showInformationMessage('Please select some text to read.');
        return;
    }

    const text = editor.document.getText(selection);
    speakText(text);
}

function speakText(text: string) {
    if (!text || !text.trim()) {
        vscode.window.showWarningMessage('No text to read.');
        return;
    }

    // Stop any current speech
    stopReading();

    // Use system TTS (works reliably across platforms)
    useSystemTTS(text);
}

function useSystemTTS(text: string) {
    // Fallback for environments where Web Speech API isn't available
    // This uses system commands for TTS
    
    const platform = process.platform;
    let command: string;
    
    // Clean text for command line (escape special characters)
    // Limit length to avoid command line limits
    const maxLength = 2000;
    const truncatedText = text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    
    // Get configuration for system TTS
    const config = vscode.workspace.getConfiguration('cursorChatReader');
    const rate = config.get<number>('rate', 1.0);
    
    if (platform === 'win32') {
        // Windows: Use PowerShell's SpeechSynthesizer
        // Escape single quotes for PowerShell
        const escapedText = truncatedText.replace(/'/g, "''").replace(/\n/g, ' ');
        const rateParam = Math.max(0.1, Math.min(10, rate));
        command = `powershell -Command "Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Rate = [int](${rateParam} * 10 - 10); $synth.Speak('${escapedText}')"`;
    } else if (platform === 'darwin') {
        // macOS: Use 'say' command
        const escapedText = truncatedText.replace(/"/g, '\\"').replace(/\n/g, ' ');
        const rateParam = Math.max(0, Math.min(300, rate * 200));
        command = `say -r ${rateParam} "${escapedText}"`;
    } else {
        // Linux: Try espeak or festival
        const escapedText = truncatedText.replace(/"/g, '\\"').replace(/\n/g, ' ');
        const rateParam = Math.max(80, Math.min(450, rate * 175));
        command = `espeak -s ${rateParam} "${escapedText}" 2>/dev/null || festival --tts 2>/dev/null || echo "Please install espeak: sudo apt-get install espeak"`;
    }

    const { spawn } = require('child_process');
    vscode.window.setStatusBarMessage('Reading...', 2000);
    
    // Parse command for spawn (handles arguments properly)
    let commandParts: string[];
    if (platform === 'win32') {
        // PowerShell command needs special handling
        commandParts = ['powershell', '-Command', command.replace('powershell -Command ', '')];
    } else {
        // For Unix-like systems, split the command
        const parts = command.split(' ');
        commandParts = [parts[0], ...parts.slice(1)];
    }
    
    const proc = spawn(commandParts[0], commandParts.slice(1), {
        shell: platform === 'win32',
        stdio: 'ignore'
    });
    
    currentProcess = proc;
    
    proc.on('close', (code: number) => {
        currentProcess = null;
        if (code === 0) {
            vscode.window.setStatusBarMessage('Finished reading', 2000);
        } else {
            vscode.window.setStatusBarMessage('TTS completed', 2000);
        }
    });
    
    proc.on('error', (error: any) => {
        currentProcess = null;
        vscode.window.showErrorMessage(`TTS Error: ${error.message}. You may need to install a TTS engine.`);
        vscode.window.setStatusBarMessage('TTS Error', 2000);
    });
}

function stopReading() {
    if (currentProcess) {
        try {
            if (process.platform === 'win32') {
                // Windows: kill the process tree
                const { exec } = require('child_process');
                exec(`taskkill /F /T /PID ${currentProcess.pid}`, () => {});
            } else {
                // Unix-like: kill the process
                currentProcess.kill('SIGTERM');
            }
        } catch (e) {
            // Ignore errors when stopping
        }
        currentProcess = null;
    }
    vscode.window.setStatusBarMessage('Stopped reading', 2000);
}

function toggleAutoRead() {
    autoReadEnabled = !autoReadEnabled;
    const config = vscode.workspace.getConfiguration('cursorChatReader');
    config.update('autoRead', autoReadEnabled, vscode.ConfigurationTarget.Global);
    
    const message = autoReadEnabled 
        ? 'Auto-read enabled: Chat responses will be read automatically'
        : 'Auto-read disabled';
    vscode.window.showInformationMessage(message);
}

function setupAutoRead(context: vscode.ExtensionContext) {
    // Monitor for new chat responses
    // This is a simplified implementation - you may need to adjust based on Cursor's actual UI structure
    
    // Listen for document changes (if chat responses appear in documents)
    const disposable = vscode.workspace.onDidChangeTextDocument(event => {
        if (autoReadEnabled && event.contentChanges.length > 0) {
            // Check if this looks like a chat response (heuristic)
            const lastChange = event.contentChanges[event.contentChanges.length - 1];
            if (lastChange.text.length > 50) { // Only read substantial responses
                // Small delay to let the response complete
                setTimeout(() => {
                    readLastChatResponse();
                }, 500);
            }
        }
    });

    context.subscriptions.push(disposable);
}

export function deactivate() {
    stopReading();
}

// Type declarations for Web Speech API (when available in web context)
interface SpeechSynthesisUtterance {
    text: string;
    lang: string;
    voice: SpeechSynthesisVoice | null;
    volume: number;
    rate: number;
    pitch: number;
    onstart: ((this: SpeechSynthesisUtterance, ev: SpeechSynthesisEvent) => any) | null;
    onend: ((this: SpeechSynthesisUtterance, ev: SpeechSynthesisEvent) => any) | null;
    onerror: ((this: SpeechSynthesisUtterance, ev: SpeechSynthesisErrorEvent) => any) | null;
}

interface SpeechSynthesis {
    speak(utterance: SpeechSynthesisUtterance): void;
    cancel(): void;
    pause(): void;
    resume(): void;
    getVoices(): SpeechSynthesisVoice[];
    speaking: boolean;
    pending: boolean;
}

interface SpeechSynthesisVoice {
    voiceURI: string;
    name: string;
    lang: string;
    localService: boolean;
    default: boolean;
}

interface SpeechSynthesisEvent {
    charIndex: number;
    charLength: number;
    elapsedTime: number;
    name: string;
    utterance: SpeechSynthesisUtterance;
}

interface SpeechSynthesisErrorEvent extends SpeechSynthesisEvent {
    error: string;
}

