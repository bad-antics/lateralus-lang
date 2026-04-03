// ═══════════════════════════════════════════════════════════════════════════
// Lateralus Language — VS Code Extension Entry Point
// ═══════════════════════════════════════════════════════════════════════════
// Activates the Lateralus Language Server (LSP) for diagnostics,
// completions, hover info, and go-to-definition in .ltl files.
//
// The LSP server is a Python process running lateralus_lang.lsp_server
// communicating over stdin/stdout JSON-RPC.
// ═══════════════════════════════════════════════════════════════════════════

const vscode = require("vscode");
const { spawn } = require("child_process");
const path = require("path");
const net = require("net");

/** @type {import('child_process').ChildProcess | null} */
let serverProcess = null;

/** @type {vscode.OutputChannel} */
let outputChannel;

/** @type {vscode.StatusBarItem} */
let statusBarItem;

/**
 * Find the Python interpreter to use for the LSP server.
 * Checks: 1) config setting, 2) python3, 3) python
 */
function findPython() {
    const config = vscode.workspace.getConfiguration("lateralus");
    const configured = config.get("pythonPath", "");
    if (configured) return configured;

    // Try python3 first, fallback to python
    const { execSync } = require("child_process");
    try {
        execSync("python3 --version", { stdio: "ignore" });
        return "python3";
    } catch {
        return "python";
    }
}

/**
 * Find the lateralus_lang package — either installed or in workspace.
 */
function findLateralusModule() {
    // Check if lateralus_lang is in the workspace
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (workspaceFolders) {
        for (const folder of workspaceFolders) {
            const modPath = path.join(folder.uri.fsPath, "lateralus_lang");
            try {
                require("fs").accessSync(modPath);
                return folder.uri.fsPath;
            } catch {}
        }
    }
    return null;
}

/**
 * Start the LSP server process.
 */
function startServer() {
    const pythonPath = findPython();
    const modulePath = findLateralusModule();

    const args = ["-m", "lateralus_lang.lsp_server"];
    const options = {
        stdio: ["pipe", "pipe", "pipe"],
    };

    if (modulePath) {
        options.cwd = modulePath;
        options.env = {
            ...process.env,
            PYTHONPATH: modulePath + (process.env.PYTHONPATH ? ":" + process.env.PYTHONPATH : ""),
        };
    }

    outputChannel.appendLine(`[lateralus] starting LSP (${pythonPath})`);

    serverProcess = spawn(pythonPath, args, options);

    serverProcess.on("error", (err) => {
        outputChannel.appendLine(`[lateralus] Server error: ${err.message}`);
        updateStatus("error");
    });

    serverProcess.on("exit", (code, signal) => {
        outputChannel.appendLine(`[lateralus] Server exited (code=${code}, signal=${signal})`);
        updateStatus("stopped");
        serverProcess = null;
    });

    serverProcess.stderr.on("data", (data) => {
        outputChannel.appendLine(`[lateralus-lsp] ${data.toString().trim()}`);
    });

    // Forward diagnostics from server stdout to our handler
    let buffer = "";
    serverProcess.stdout.on("data", (data) => {
        buffer += data.toString();
        processMessages(buffer, (remaining) => { buffer = remaining; });
    });

    updateStatus("running");
    initializeServer();
}

/**
 * Process JSON-RPC messages from the server.
 */
function processMessages(buffer, setRemaining) {
    while (true) {
        const headerEnd = buffer.indexOf("\r\n\r\n");
        if (headerEnd === -1) break;

        const header = buffer.substring(0, headerEnd);
        const match = header.match(/Content-Length:\s*(\d+)/i);
        if (!match) break;

        const contentLength = parseInt(match[1], 10);
        const start = headerEnd + 4;
        if (buffer.length < start + contentLength) break;

        const content = buffer.substring(start, start + contentLength);
        buffer = buffer.substring(start + contentLength);

        try {
            const msg = JSON.parse(content);
            handleServerMessage(msg);
        } catch (e) {
            outputChannel.appendLine(`[lateralus] Parse error: ${e.message}`);
        }
    }
    setRemaining(buffer);
}

/**
 * Handle a message from the LSP server.
 */
function handleServerMessage(msg) {
    if (msg.method === "textDocument/publishDiagnostics") {
        publishDiagnostics(msg.params);
    } else if (msg.id !== undefined && msg.result !== undefined) {
        // Response to a request — resolve pending promise
        const resolver = pendingRequests.get(msg.id);
        if (resolver) {
            resolver(msg.result);
            pendingRequests.delete(msg.id);
        }
    }
}

/** @type {Map<number, Function>} */
const pendingRequests = new Map();
let nextRequestId = 1;

/**
 * Send a JSON-RPC message to the server.
 */
function sendToServer(msg) {
    if (!serverProcess || !serverProcess.stdin.writable) return;
    const content = JSON.stringify(msg);
    const header = `Content-Length: ${Buffer.byteLength(content)}\r\n\r\n`;
    serverProcess.stdin.write(header + content);
}

/**
 * Send a request and return a Promise for the response.
 */
function sendRequest(method, params) {
    return new Promise((resolve, reject) => {
        const id = nextRequestId++;
        pendingRequests.set(id, resolve);
        sendToServer({ jsonrpc: "2.0", id, method, params });

        // Timeout after 5 seconds
        setTimeout(() => {
            if (pendingRequests.has(id)) {
                pendingRequests.delete(id);
                reject(new Error(`Request ${method} timed out`));
            }
        }, 5000);
    });
}

/**
 * Send a notification (no response expected).
 */
function sendNotification(method, params) {
    sendToServer({ jsonrpc: "2.0", method, params });
}

/**
 * Initialize the LSP server with capabilities.
 */
async function initializeServer() {
    try {
        const result = await sendRequest("initialize", {
            processId: process.pid,
            capabilities: {
                textDocument: {
                    completion: { completionItem: { snippetSupport: true } },
                    hover: {},
                    synchronization: {
                        didOpen: true,
                        didChange: true,
                        didClose: true,
                    },
                },
            },
            rootUri: vscode.workspace.workspaceFolders?.[0]?.uri.toString() || null,
        });

        outputChannel.appendLine(`[lateralus] LSP ready`);

        // Send initialized notification
        sendNotification("initialized", {});

        // Open all currently open .ltl documents
        for (const doc of vscode.workspace.textDocuments) {
            if (isLateralusDocument(doc)) {
                notifyDidOpen(doc);
            }
        }
    } catch (err) {
        outputChannel.appendLine(`[lateralus] Initialize failed: ${err.message}`);
    }
}

// ─── Diagnostics ──────────────────────────────────────────────────────────

/** @type {vscode.DiagnosticCollection} */
let diagnosticCollection;

function publishDiagnostics(params) {
    const uri = vscode.Uri.parse(params.uri);
    const diagnostics = (params.diagnostics || []).map((d) => {
        const range = new vscode.Range(
            d.range.start.line, d.range.start.character,
            d.range.end.line, d.range.end.character
        );
        const diag = new vscode.Diagnostic(range, d.message, severityMap(d.severity));
        if (d.source) diag.source = d.source;
        if (d.code) diag.code = d.code;
        return diag;
    });
    diagnosticCollection.set(uri, diagnostics);
}

function severityMap(sev) {
    switch (sev) {
        case 1: return vscode.DiagnosticSeverity.Error;
        case 2: return vscode.DiagnosticSeverity.Warning;
        case 3: return vscode.DiagnosticSeverity.Information;
        case 4: return vscode.DiagnosticSeverity.Hint;
        default: return vscode.DiagnosticSeverity.Error;
    }
}

// ─── Document Sync ────────────────────────────────────────────────────────

function isLateralusDocument(doc) {
    return doc.languageId === "lateralus" || doc.fileName.endsWith(".ltl");
}

function notifyDidOpen(doc) {
    sendNotification("textDocument/didOpen", {
        textDocument: {
            uri: doc.uri.toString(),
            languageId: doc.languageId || "lateralus",
            version: doc.version,
            text: doc.getText(),
        },
    });
}

function notifyDidChange(event) {
    const doc = event.document;
    sendNotification("textDocument/didChange", {
        textDocument: {
            uri: doc.uri.toString(),
            version: doc.version,
        },
        contentChanges: [{ text: doc.getText() }],
    });
}

function notifyDidClose(doc) {
    sendNotification("textDocument/didClose", {
        textDocument: { uri: doc.uri.toString() },
    });
}

// ─── Completions ──────────────────────────────────────────────────────────

class LateralusCompletionProvider {
    async provideCompletionItems(document, position, token) {
        if (!serverProcess) return [];

        try {
            const result = await sendRequest("textDocument/completion", {
                textDocument: { uri: document.uri.toString() },
                position: { line: position.line, character: position.character },
            });

            if (!result || !result.items) return [];

            return result.items.map((item) => {
                const ci = new vscode.CompletionItem(item.label, item.kind || vscode.CompletionItemKind.Text);
                if (item.detail) ci.detail = item.detail;
                if (item.documentation) ci.documentation = item.documentation;
                if (item.insertText) ci.insertText = item.insertText;
                return ci;
            });
        } catch {
            return [];
        }
    }
}

// ─── Hover ────────────────────────────────────────────────────────────────

class LateralusHoverProvider {
    async provideHover(document, position, token) {
        if (!serverProcess) return null;

        try {
            const result = await sendRequest("textDocument/hover", {
                textDocument: { uri: document.uri.toString() },
                position: { line: position.line, character: position.character },
            });

            if (!result || !result.contents) return null;

            const md = new vscode.MarkdownString();
            if (typeof result.contents === "string") {
                md.appendMarkdown(result.contents);
            } else if (result.contents.value) {
                md.appendCodeblock(result.contents.value, result.contents.language || "lateralus");
            }
            return new vscode.Hover(md);
        } catch {
            return null;
        }
    }
}

// ─── Status Bar ───────────────────────────────────────────────────────────

function updateStatus(state) {
    switch (state) {
        case "running":
            statusBarItem.text = "$(circle-filled) LTL";
            statusBarItem.tooltip = "Lateralus LSP  ·  running";
            statusBarItem.color = new vscode.ThemeColor("terminal.ansiCyan");
            break;
        case "error":
            statusBarItem.text = "$(circle-slash) LTL";
            statusBarItem.tooltip = "Lateralus LSP  ·  error — click to restart";
            statusBarItem.color = new vscode.ThemeColor("errorForeground");
            break;
        case "stopped":
            statusBarItem.text = "$(circle-outline) LTL";
            statusBarItem.tooltip = "Lateralus LSP  ·  stopped";
            statusBarItem.color = new vscode.ThemeColor("disabledForeground");
            break;
    }
    statusBarItem.show();
}

// ─── Extension Lifecycle ──────────────────────────────────────────────────

function activate(context) {
    outputChannel = vscode.window.createOutputChannel("Lateralus");
    outputChannel.appendLine("[lateralus] activated v2.2.0");

    // Status bar
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.command = "lateralus.restartServer";
    context.subscriptions.push(statusBarItem);

    // Diagnostics collection
    diagnosticCollection = vscode.languages.createDiagnosticCollection("lateralus");
    context.subscriptions.push(diagnosticCollection);

    // Register providers
    const ltlSelector = { language: "lateralus", scheme: "file" };
    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(ltlSelector, new LateralusCompletionProvider(), ".", ":"),
        vscode.languages.registerHoverProvider(ltlSelector, new LateralusHoverProvider())
    );

    // Document sync events
    context.subscriptions.push(
        vscode.workspace.onDidOpenTextDocument((doc) => {
            if (isLateralusDocument(doc)) notifyDidOpen(doc);
        }),
        vscode.workspace.onDidChangeTextDocument((event) => {
            if (isLateralusDocument(event.document)) notifyDidChange(event);
        }),
        vscode.workspace.onDidCloseTextDocument((doc) => {
            if (isLateralusDocument(doc)) notifyDidClose(doc);
        })
    );

    // Commands
    context.subscriptions.push(
        vscode.commands.registerCommand("lateralus.restartServer", () => {
            outputChannel.appendLine("[lateralus] Restarting server...");
            stopServer();
            setTimeout(startServer, 500);
        }),
        vscode.commands.registerCommand("lateralus.showOutput", () => {
            outputChannel.show();
        })
    );

    // Start the language server
    const config = vscode.workspace.getConfiguration("lateralus");
    if (config.get("enableLSP", true)) {
        startServer();
    } else {
        outputChannel.appendLine("[lateralus] LSP disabled via settings");
        updateStatus("stopped");
    }
}

function stopServer() {
    if (serverProcess) {
        try {
            sendNotification("shutdown", {});
            setTimeout(() => {
                if (serverProcess) {
                    serverProcess.kill("SIGTERM");
                    serverProcess = null;
                }
            }, 1000);
        } catch {
            if (serverProcess) serverProcess.kill("SIGKILL");
            serverProcess = null;
        }
    }
}

function deactivate() {
    stopServer();
    if (outputChannel) outputChannel.dispose();
    if (statusBarItem) statusBarItem.dispose();
}

module.exports = { activate, deactivate };
