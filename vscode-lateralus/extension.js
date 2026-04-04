// ═══════════════════════════════════════════════════════════════════════════
// Lateralus Language — VS Code Extension Entry Point
// ═══════════════════════════════════════════════════════════════════════════
// Activates the Lateralus Language Server (LSP) for diagnostics,
// completions, hover info, go-to-definition, references, formatting,
// code actions, signature help, symbols, and rename in .ltl files.
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
    } else if (msg.method === "window/showMessage") {
        // Handle server-initiated showMessage
        const text = msg.params?.message || "";
        switch (msg.params?.type) {
            case 1: vscode.window.showErrorMessage(text); break;
            case 2: vscode.window.showWarningMessage(text); break;
            default: vscode.window.showInformationMessage(text); break;
        }
    } else if (msg.method === "window/logMessage") {
        outputChannel.appendLine(`[lateralus-lsp] ${msg.params?.message || ""}`);
    } else if (msg.id !== undefined && msg.result !== undefined) {
        // Response to a request — resolve pending promise
        const resolver = pendingRequests.get(msg.id);
        if (resolver) {
            resolver.resolve(msg.result);
            pendingRequests.delete(msg.id);
        }
    } else if (msg.id !== undefined && msg.error !== undefined) {
        // Error response
        const resolver = pendingRequests.get(msg.id);
        if (resolver) {
            resolver.reject(new Error(msg.error.message || "LSP error"));
            pendingRequests.delete(msg.id);
        }
    }
}

/** @type {Map<number, {resolve: Function, reject: Function}>} */
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
        pendingRequests.set(id, { resolve, reject });
        sendToServer({ jsonrpc: "2.0", id, method, params });

        // Timeout after 10 seconds
        setTimeout(() => {
            if (pendingRequests.has(id)) {
                pendingRequests.delete(id);
                reject(new Error(`Request ${method} timed out`));
            }
        }, 10000);
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
                    definition: {},
                    references: {},
                    formatting: {},
                    codeAction: { codeActionLiteralSupport: { codeActionKind: { valueSet: ["quickfix", "refactor", "source"] } } },
                    signatureHelp: { signatureInformation: { documentationFormat: ["markdown", "plaintext"] } },
                    documentSymbol: { hierarchicalDocumentSymbolSupport: true },
                    rename: { prepareSupport: true },
                    synchronization: {
                        didOpen: true,
                        didChange: true,
                        didClose: true,
                        didSave: true,
                    },
                },
                workspace: {
                    symbol: {},
                    workspaceFolders: true,
                },
            },
            rootUri: vscode.workspace.workspaceFolders?.[0]?.uri.toString() || null,
        });

        outputChannel.appendLine(`[lateralus] LSP ready — server capabilities: ${JSON.stringify(result?.capabilities || {})}`);

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
    return ["lateralus", "lateralus-asm", "lateralus-markup", "lateralus-cfg", "lateralus-notebook"]
        .includes(doc.languageId);
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

function notifyDidSave(doc) {
    sendNotification("textDocument/didSave", {
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

            if (!result) return [];
            const items = Array.isArray(result) ? result : (result.items || []);

            return items.map((item) => {
                const ci = new vscode.CompletionItem(item.label, item.kind || vscode.CompletionItemKind.Text);
                if (item.detail) ci.detail = item.detail;
                if (item.documentation) {
                    ci.documentation = typeof item.documentation === "string"
                        ? item.documentation
                        : new vscode.MarkdownString(item.documentation?.value || "");
                }
                if (item.insertText) {
                    ci.insertText = item.insertTextFormat === 2
                        ? new vscode.SnippetString(item.insertText)
                        : item.insertText;
                }
                if (item.filterText) ci.filterText = item.filterText;
                if (item.sortText) ci.sortText = item.sortText;
                if (item.preselect) ci.preselect = item.preselect;
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
            } else if (Array.isArray(result.contents)) {
                for (const c of result.contents) {
                    if (typeof c === "string") {
                        md.appendMarkdown(c + "\n\n");
                    } else {
                        md.appendCodeblock(c.value, c.language || "lateralus");
                    }
                }
            } else if (result.contents.value) {
                if (result.contents.kind === "markdown") {
                    md.appendMarkdown(result.contents.value);
                } else {
                    md.appendCodeblock(result.contents.value, result.contents.language || "lateralus");
                }
            }

            let range;
            if (result.range) {
                range = new vscode.Range(
                    result.range.start.line, result.range.start.character,
                    result.range.end.line, result.range.end.character
                );
            }

            return new vscode.Hover(md, range);
        } catch {
            return null;
        }
    }
}

// ─── Go to Definition ─────────────────────────────────────────────────────

class LateralusDefinitionProvider {
    async provideDefinition(document, position, token) {
        if (!serverProcess) return null;

        try {
            const result = await sendRequest("textDocument/definition", {
                textDocument: { uri: document.uri.toString() },
                position: { line: position.line, character: position.character },
            });

            if (!result) return null;

            // Result can be Location | Location[] | LocationLink[]
            const locations = Array.isArray(result) ? result : [result];
            return locations.map((loc) => {
                const uri = vscode.Uri.parse(loc.targetUri || loc.uri);
                const range = loc.targetRange || loc.range;
                return new vscode.Location(
                    uri,
                    new vscode.Range(
                        range.start.line, range.start.character,
                        range.end.line, range.end.character
                    )
                );
            });
        } catch {
            return null;
        }
    }
}

// ─── Find References ──────────────────────────────────────────────────────

class LateralusReferenceProvider {
    async provideReferences(document, position, context, token) {
        if (!serverProcess) return [];

        try {
            const result = await sendRequest("textDocument/references", {
                textDocument: { uri: document.uri.toString() },
                position: { line: position.line, character: position.character },
                context: { includeDeclaration: context.includeDeclaration },
            });

            if (!result) return [];

            return result.map((loc) => {
                return new vscode.Location(
                    vscode.Uri.parse(loc.uri),
                    new vscode.Range(
                        loc.range.start.line, loc.range.start.character,
                        loc.range.end.line, loc.range.end.character
                    )
                );
            });
        } catch {
            return [];
        }
    }
}

// ─── Document Formatting ──────────────────────────────────────────────────

class LateralusDocumentFormattingProvider {
    async provideDocumentFormattingEdits(document, options, token) {
        if (!serverProcess) return [];

        try {
            const result = await sendRequest("textDocument/formatting", {
                textDocument: { uri: document.uri.toString() },
                options: {
                    tabSize: options.tabSize,
                    insertSpaces: options.insertSpaces,
                    trimTrailingWhitespace: true,
                    insertFinalNewline: true,
                },
            });

            if (!result) return [];

            return result.map((edit) => {
                return new vscode.TextEdit(
                    new vscode.Range(
                        edit.range.start.line, edit.range.start.character,
                        edit.range.end.line, edit.range.end.character
                    ),
                    edit.newText
                );
            });
        } catch {
            return [];
        }
    }
}

// ─── Document Range Formatting ────────────────────────────────────────────

class LateralusDocumentRangeFormattingProvider {
    async provideDocumentRangeFormattingEdits(document, range, options, token) {
        if (!serverProcess) return [];

        try {
            const result = await sendRequest("textDocument/rangeFormatting", {
                textDocument: { uri: document.uri.toString() },
                range: {
                    start: { line: range.start.line, character: range.start.character },
                    end: { line: range.end.line, character: range.end.character },
                },
                options: {
                    tabSize: options.tabSize,
                    insertSpaces: options.insertSpaces,
                },
            });

            if (!result) return [];

            return result.map((edit) => {
                return new vscode.TextEdit(
                    new vscode.Range(
                        edit.range.start.line, edit.range.start.character,
                        edit.range.end.line, edit.range.end.character
                    ),
                    edit.newText
                );
            });
        } catch {
            return [];
        }
    }
}

// ─── Code Actions ─────────────────────────────────────────────────────────

class LateralusCodeActionProvider {
    async provideCodeActions(document, range, context, token) {
        if (!serverProcess) return [];

        try {
            const result = await sendRequest("textDocument/codeAction", {
                textDocument: { uri: document.uri.toString() },
                range: {
                    start: { line: range.start.line, character: range.start.character },
                    end: { line: range.end.line, character: range.end.character },
                },
                context: {
                    diagnostics: context.diagnostics.map((d) => ({
                        range: {
                            start: { line: d.range.start.line, character: d.range.start.character },
                            end: { line: d.range.end.line, character: d.range.end.character },
                        },
                        message: d.message,
                        severity: d.severity,
                        code: d.code,
                        source: d.source,
                    })),
                },
            });

            if (!result) return [];

            return result.map((action) => {
                const codeAction = new vscode.CodeAction(action.title, codeActionKindMap(action.kind));
                if (action.diagnostics) {
                    codeAction.diagnostics = action.diagnostics.map((d) => {
                        return new vscode.Diagnostic(
                            new vscode.Range(
                                d.range.start.line, d.range.start.character,
                                d.range.end.line, d.range.end.character
                            ),
                            d.message,
                            severityMap(d.severity)
                        );
                    });
                }
                if (action.edit) {
                    const workspaceEdit = new vscode.WorkspaceEdit();
                    if (action.edit.changes) {
                        for (const [uri, edits] of Object.entries(action.edit.changes)) {
                            const docUri = vscode.Uri.parse(uri);
                            for (const edit of edits) {
                                workspaceEdit.replace(
                                    docUri,
                                    new vscode.Range(
                                        edit.range.start.line, edit.range.start.character,
                                        edit.range.end.line, edit.range.end.character
                                    ),
                                    edit.newText
                                );
                            }
                        }
                    }
                    if (action.edit.documentChanges) {
                        for (const change of action.edit.documentChanges) {
                            if (change.edits) {
                                const docUri = vscode.Uri.parse(change.textDocument.uri);
                                for (const edit of change.edits) {
                                    workspaceEdit.replace(
                                        docUri,
                                        new vscode.Range(
                                            edit.range.start.line, edit.range.start.character,
                                            edit.range.end.line, edit.range.end.character
                                        ),
                                        edit.newText
                                    );
                                }
                            }
                        }
                    }
                    codeAction.edit = workspaceEdit;
                }
                if (action.isPreferred) codeAction.isPreferred = true;
                return codeAction;
            });
        } catch {
            return [];
        }
    }
}

function codeActionKindMap(kind) {
    switch (kind) {
        case "quickfix": return vscode.CodeActionKind.QuickFix;
        case "refactor": return vscode.CodeActionKind.Refactor;
        case "refactor.extract": return vscode.CodeActionKind.RefactorExtract;
        case "refactor.inline": return vscode.CodeActionKind.RefactorInline;
        case "refactor.rewrite": return vscode.CodeActionKind.RefactorRewrite;
        case "source": return vscode.CodeActionKind.Source;
        case "source.organizeImports": return vscode.CodeActionKind.SourceOrganizeImports;
        case "source.fixAll": return vscode.CodeActionKind.SourceFixAll;
        default: return vscode.CodeActionKind.QuickFix;
    }
}

// ─── Signature Help ───────────────────────────────────────────────────────

class LateralusSignatureHelpProvider {
    async provideSignatureHelp(document, position, token, context) {
        if (!serverProcess) return null;

        try {
            const result = await sendRequest("textDocument/signatureHelp", {
                textDocument: { uri: document.uri.toString() },
                position: { line: position.line, character: position.character },
            });

            if (!result || !result.signatures || result.signatures.length === 0) return null;

            const sigHelp = new vscode.SignatureHelp();
            sigHelp.activeSignature = result.activeSignature || 0;
            sigHelp.activeParameter = result.activeParameter || 0;

            sigHelp.signatures = result.signatures.map((sig) => {
                const sigInfo = new vscode.SignatureInformation(sig.label);
                if (sig.documentation) {
                    sigInfo.documentation = typeof sig.documentation === "string"
                        ? sig.documentation
                        : new vscode.MarkdownString(sig.documentation?.value || "");
                }
                if (sig.parameters) {
                    sigInfo.parameters = sig.parameters.map((p) => {
                        const paramInfo = new vscode.ParameterInformation(p.label);
                        if (p.documentation) {
                            paramInfo.documentation = typeof p.documentation === "string"
                                ? p.documentation
                                : new vscode.MarkdownString(p.documentation?.value || "");
                        }
                        return paramInfo;
                    });
                }
                return sigInfo;
            });

            return sigHelp;
        } catch {
            return null;
        }
    }
}

// ─── Document Symbols ─────────────────────────────────────────────────────

class LateralusDocumentSymbolProvider {
    async provideDocumentSymbols(document, token) {
        if (!serverProcess) return [];

        try {
            const result = await sendRequest("textDocument/documentSymbol", {
                textDocument: { uri: document.uri.toString() },
            });

            if (!result) return [];

            // Handle both flat SymbolInformation[] and hierarchical DocumentSymbol[]
            if (result.length > 0 && result[0].range) {
                // DocumentSymbol (hierarchical)
                return result.map((sym) => convertDocumentSymbol(sym));
            } else {
                // SymbolInformation (flat)
                return result.map((sym) => {
                    return new vscode.SymbolInformation(
                        sym.name,
                        symbolKindMap(sym.kind),
                        sym.containerName || "",
                        new vscode.Location(
                            vscode.Uri.parse(sym.location.uri),
                            new vscode.Range(
                                sym.location.range.start.line, sym.location.range.start.character,
                                sym.location.range.end.line, sym.location.range.end.character
                            )
                        )
                    );
                });
            }
        } catch {
            return [];
        }
    }
}

function convertDocumentSymbol(sym) {
    const range = new vscode.Range(
        sym.range.start.line, sym.range.start.character,
        sym.range.end.line, sym.range.end.character
    );
    const selRange = sym.selectionRange
        ? new vscode.Range(
            sym.selectionRange.start.line, sym.selectionRange.start.character,
            sym.selectionRange.end.line, sym.selectionRange.end.character
        )
        : range;

    const docSym = new vscode.DocumentSymbol(
        sym.name,
        sym.detail || "",
        symbolKindMap(sym.kind),
        range,
        selRange
    );

    if (sym.children && sym.children.length > 0) {
        docSym.children = sym.children.map((c) => convertDocumentSymbol(c));
    }

    return docSym;
}

// ─── Workspace Symbols ────────────────────────────────────────────────────

class LateralusWorkspaceSymbolProvider {
    async provideWorkspaceSymbols(query, token) {
        if (!serverProcess) return [];

        try {
            const result = await sendRequest("workspace/symbol", {
                query: query,
            });

            if (!result) return [];

            return result.map((sym) => {
                return new vscode.SymbolInformation(
                    sym.name,
                    symbolKindMap(sym.kind),
                    sym.containerName || "",
                    new vscode.Location(
                        vscode.Uri.parse(sym.location.uri),
                        new vscode.Range(
                            sym.location.range.start.line, sym.location.range.start.character,
                            sym.location.range.end.line, sym.location.range.end.character
                        )
                    )
                );
            });
        } catch {
            return [];
        }
    }
}

function symbolKindMap(kind) {
    const map = {
        1: vscode.SymbolKind.File,
        2: vscode.SymbolKind.Module,
        3: vscode.SymbolKind.Namespace,
        4: vscode.SymbolKind.Package,
        5: vscode.SymbolKind.Class,
        6: vscode.SymbolKind.Method,
        7: vscode.SymbolKind.Property,
        8: vscode.SymbolKind.Field,
        9: vscode.SymbolKind.Constructor,
        10: vscode.SymbolKind.Enum,
        11: vscode.SymbolKind.Interface,
        12: vscode.SymbolKind.Function,
        13: vscode.SymbolKind.Variable,
        14: vscode.SymbolKind.Constant,
        15: vscode.SymbolKind.String,
        16: vscode.SymbolKind.Number,
        17: vscode.SymbolKind.Boolean,
        18: vscode.SymbolKind.Array,
        19: vscode.SymbolKind.Object,
        20: vscode.SymbolKind.Key,
        21: vscode.SymbolKind.Null,
        22: vscode.SymbolKind.EnumMember,
        23: vscode.SymbolKind.Struct,
        24: vscode.SymbolKind.Event,
        25: vscode.SymbolKind.Operator,
        26: vscode.SymbolKind.TypeParameter,
    };
    return map[kind] || vscode.SymbolKind.Variable;
}

// ─── Rename ───────────────────────────────────────────────────────────────

class LateralusRenameProvider {
    async prepareRename(document, position, token) {
        if (!serverProcess) return null;

        try {
            const result = await sendRequest("textDocument/prepareRename", {
                textDocument: { uri: document.uri.toString() },
                position: { line: position.line, character: position.character },
            });

            if (!result) return null;

            if (result.range) {
                return {
                    range: new vscode.Range(
                        result.range.start.line, result.range.start.character,
                        result.range.end.line, result.range.end.character
                    ),
                    placeholder: result.placeholder || document.getText(
                        new vscode.Range(
                            result.range.start.line, result.range.start.character,
                            result.range.end.line, result.range.end.character
                        )
                    ),
                };
            }

            // Fallback: result is just a Range
            if (result.start) {
                return new vscode.Range(
                    result.start.line, result.start.character,
                    result.end.line, result.end.character
                );
            }

            return null;
        } catch {
            return null;
        }
    }

    async provideRenameEdits(document, position, newName, token) {
        if (!serverProcess) return null;

        try {
            const result = await sendRequest("textDocument/rename", {
                textDocument: { uri: document.uri.toString() },
                position: { line: position.line, character: position.character },
                newName: newName,
            });

            if (!result) return null;

            const workspaceEdit = new vscode.WorkspaceEdit();
            if (result.changes) {
                for (const [uri, edits] of Object.entries(result.changes)) {
                    const docUri = vscode.Uri.parse(uri);
                    for (const edit of edits) {
                        workspaceEdit.replace(
                            docUri,
                            new vscode.Range(
                                edit.range.start.line, edit.range.start.character,
                                edit.range.end.line, edit.range.end.character
                            ),
                            edit.newText
                        );
                    }
                }
            }
            if (result.documentChanges) {
                for (const change of result.documentChanges) {
                    if (change.edits) {
                        const docUri = vscode.Uri.parse(change.textDocument.uri);
                        for (const edit of change.edits) {
                            workspaceEdit.replace(
                                docUri,
                                new vscode.Range(
                                    edit.range.start.line, edit.range.start.character,
                                    edit.range.end.line, edit.range.end.character
                                ),
                                edit.newText
                            );
                        }
                    }
                }
            }
            return workspaceEdit;
        } catch {
            return null;
        }
    }
}

// ─── Folding Range ────────────────────────────────────────────────────────

class LateralusFoldingRangeProvider {
    async provideFoldingRanges(document, context, token) {
        if (!serverProcess) return [];

        try {
            const result = await sendRequest("textDocument/foldingRange", {
                textDocument: { uri: document.uri.toString() },
            });

            if (!result) return [];

            return result.map((r) => {
                const kind = r.kind === "comment" ? vscode.FoldingRangeKind.Comment
                    : r.kind === "imports" ? vscode.FoldingRangeKind.Imports
                    : vscode.FoldingRangeKind.Region;
                return new vscode.FoldingRange(r.startLine, r.endLine, kind);
            });
        } catch {
            return [];
        }
    }
}

// ─── Selection Range ──────────────────────────────────────────────────────

class LateralusSelectionRangeProvider {
    async provideSelectionRanges(document, positions, token) {
        if (!serverProcess) return [];

        try {
            const result = await sendRequest("textDocument/selectionRange", {
                textDocument: { uri: document.uri.toString() },
                positions: positions.map((p) => ({ line: p.line, character: p.character })),
            });

            if (!result) return [];

            return result.map((sr) => convertSelectionRange(sr));
        } catch {
            return [];
        }
    }
}

function convertSelectionRange(sr) {
    const range = new vscode.Range(
        sr.range.start.line, sr.range.start.character,
        sr.range.end.line, sr.range.end.character
    );
    const selRange = new vscode.SelectionRange(range, sr.parent ? convertSelectionRange(sr.parent) : undefined);
    return selRange;
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
    outputChannel.appendLine("[lateralus] activated v2.5.1");

    // Status bar
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.command = "lateralus.restartServer";
    context.subscriptions.push(statusBarItem);

    // Diagnostics collection
    diagnosticCollection = vscode.languages.createDiagnosticCollection("lateralus");
    context.subscriptions.push(diagnosticCollection);

    // Language selectors — support all Lateralus file types
    const ltlSelector = [
        { language: "lateralus", scheme: "file" },
        { language: "lateralus-asm", scheme: "file" },
        { language: "lateralus-markup", scheme: "file" },
        { language: "lateralus-cfg", scheme: "file" },
        { language: "lateralus-notebook", scheme: "file" },
    ];

    // Register all providers
    context.subscriptions.push(
        // Completions  (trigger on . : |)
        vscode.languages.registerCompletionItemProvider(ltlSelector, new LateralusCompletionProvider(), ".", ":", "|"),
        // Hover
        vscode.languages.registerHoverProvider(ltlSelector, new LateralusHoverProvider()),
        // Go to Definition
        vscode.languages.registerDefinitionProvider(ltlSelector, new LateralusDefinitionProvider()),
        // Find References
        vscode.languages.registerReferenceProvider(ltlSelector, new LateralusReferenceProvider()),
        // Document Formatting
        vscode.languages.registerDocumentFormattingEditProvider(ltlSelector, new LateralusDocumentFormattingProvider()),
        // Range Formatting
        vscode.languages.registerDocumentRangeFormattingEditProvider(ltlSelector, new LateralusDocumentRangeFormattingProvider()),
        // Code Actions (quick fixes, refactors)
        vscode.languages.registerCodeActionsProvider(ltlSelector, new LateralusCodeActionProvider(), {
            providedCodeActionKinds: [
                vscode.CodeActionKind.QuickFix,
                vscode.CodeActionKind.Refactor,
                vscode.CodeActionKind.Source,
                vscode.CodeActionKind.SourceOrganizeImports,
                vscode.CodeActionKind.SourceFixAll,
            ],
        }),
        // Signature Help  (trigger on ( ,)
        vscode.languages.registerSignatureHelpProvider(ltlSelector, new LateralusSignatureHelpProvider(), {
            triggerCharacters: ["(", ","],
            retriggerCharacters: [","],
        }),
        // Document Symbols  (Outline view / Ctrl+Shift+O)
        vscode.languages.registerDocumentSymbolProvider(ltlSelector, new LateralusDocumentSymbolProvider()),
        // Workspace Symbols  (Ctrl+T)
        vscode.languages.registerWorkspaceSymbolProvider(new LateralusWorkspaceSymbolProvider()),
        // Rename  (F2)
        vscode.languages.registerRenameProvider(ltlSelector, new LateralusRenameProvider()),
        // Folding Ranges
        vscode.languages.registerFoldingRangeProvider(ltlSelector, new LateralusFoldingRangeProvider()),
        // Selection Range (Expand/Shrink Selection)
        vscode.languages.registerSelectionRangeProvider(ltlSelector, new LateralusSelectionRangeProvider())
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
        }),
        vscode.workspace.onDidSaveTextDocument((doc) => {
            if (isLateralusDocument(doc)) notifyDidSave(doc);
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
        }),
        vscode.commands.registerCommand("lateralus.formatDocument", () => {
            vscode.commands.executeCommand("editor.action.formatDocument");
        }),
        vscode.commands.registerCommand("lateralus.organizeImports", async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor && isLateralusDocument(editor.document)) {
                try {
                    const result = await sendRequest("textDocument/codeAction", {
                        textDocument: { uri: editor.document.uri.toString() },
                        range: {
                            start: { line: 0, character: 0 },
                            end: { line: editor.document.lineCount - 1, character: 0 },
                        },
                        context: { diagnostics: [], only: ["source.organizeImports"] },
                    });
                    if (result && result.length > 0 && result[0].edit) {
                        const edit = new vscode.WorkspaceEdit();
                        const changes = result[0].edit.changes || {};
                        for (const [uri, edits] of Object.entries(changes)) {
                            for (const e of edits) {
                                edit.replace(
                                    vscode.Uri.parse(uri),
                                    new vscode.Range(
                                        e.range.start.line, e.range.start.character,
                                        e.range.end.line, e.range.end.character
                                    ),
                                    e.newText
                                );
                            }
                        }
                        await vscode.workspace.applyEdit(edit);
                    }
                } catch (err) {
                    outputChannel.appendLine(`[lateralus] Organize imports failed: ${err.message}`);
                }
            }
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
