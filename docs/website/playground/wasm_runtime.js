/**
 * Lateralus WASM Playground Runtime Shim
 * Provides host functions (env.println, env.http_get) and execution harness.
 */
(function(window) {
    'use strict';

    class LateralusWasmRuntime {
        constructor() {
            this.memory = null;
            this.outputBuffer = [];
        }

        createImports(printCallback) {
            const self = this;
            return {
                env: {
                    println: (ptr, len) => {
                        const text = self.readString(ptr, len);
                        self.outputBuffer.push(text);
                        if (printCallback) {
                            printCallback(text);
                        } else {
                            console.log('[Lateralus]', text);
                        }
                    },
                    http_get: (urlPtr, urlLen, outPtr, outCap) => {
                        const url = self.readString(urlPtr, urlLen);
                        console.warn('[Lateralus] Synchronous http_get shim requested for:', url);
                        return 0;
                    },
                    memory: new WebAssembly.Memory({ initial: 256, maximum: 1024 })
                }
            };
        }

        readString(ptr, len) {
            if (!this.memory) return '';
            const bytes = new Uint8Array(this.memory.buffer, ptr, len);
            return new TextDecoder('utf-8').decode(bytes);
        }

        async instantiate(wasmBytes, printCallback) {
            const imports = this.createImports(printCallback);
            const result = await WebAssembly.instantiate(wasmBytes, imports);
            if (result.instance.exports.memory) {
                this.memory = result.instance.exports.memory;
            } else if (imports.env.memory) {
                this.memory = imports.env.memory;
            }
            return result.instance;
        }
    }

    window.LateralusWasmRuntime = LateralusWasmRuntime;
})(window);
