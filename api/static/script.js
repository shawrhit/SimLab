window.onload = function () {
    console.log("load");
    const deviceName = document.body?.dataset?.deviceName || "8051";
    const deviceSelect = document.getElementById("device-select");
    // reload code contents
    const codeStorageKey = `code_${deviceName.toLowerCase()}`;
    document.getElementById("code").value = localStorage.getItem(codeStorageKey) || "";
    RenderLineNumbers();

    if (deviceSelect) {
        deviceSelect.value = deviceName;
        deviceSelect.addEventListener("change", () => {
            const selected = deviceSelect.value;
            const url = new URL(window.location.href);
            url.searchParams.set("device", selected);
            window.location.assign(url.toString());
        });
    }

    document.getElementById("run").disabled = true;
    document.getElementById("step").disabled = true;

    document.getElementById("code").addEventListener("input", function () {
        RenderLineNumbers();
    });

    document.getElementById("code").addEventListener("scroll", function () {
        document.getElementById("track").scrollTop = this.scrollTop;
    });

    document.getElementById("assemble").addEventListener("click", function () {
        console.log("assemble")
        const request = new XMLHttpRequest();
        request.open("POST", `/assemble`);
        request.setRequestHeader("Content-Type", "application/json");
        request.onload = () => {
            const response = request.responseText;
            if (request.status != 200) {
                alert(response)
            }
            else {
                document.getElementById("run").disabled = false
                document.getElementById("step").disabled = false
                document.getElementById("memory-container").innerHTML = response;
                ProgressSideBar(_code, 0, "assembled")
            }
        };
        var _code = document.getElementById("code").value.trim();
        if (_code) {
            // save code
            localStorage.setItem(codeStorageKey, _code)
            console.log("sent")
            request.send(JSON.stringify(
                {
                    "code": _code,
                    "flags": GetFlags(),
                    "device": deviceName
                }
            ));
        }
    });

    document.getElementById("run").addEventListener("click", function () {
        console.log("run");
        const request = new XMLHttpRequest();
        request.open("POST", `/run`);
        request.setRequestHeader("Content-Type", "application/json");
        request.onload = () => {
            const response = request.responseText;
            if (request.status != 200) {
                alert(response);
            }
            else {
                const _resp_dict = JSON.parse(response)
                document.getElementById("registers-flags").innerHTML = _resp_dict["registers_flags"];
                document.getElementById("memory-container").innerHTML = _resp_dict["memory"];
                document.getElementById("assembler-container").innerHTML = _resp_dict["assembler"];
                ProgressSideBar(_code, _code.split("\n").filter(line => IsCodeLine(line)).length, "run")
            }
        };
        var _code = document.getElementById("code").value.trim();
        request.send(JSON.stringify({
            "code": _code,
            "device": deviceName
        }));
    });

    document.getElementById("step").addEventListener("click", function () {
        console.log("step");
        const request = new XMLHttpRequest();
        request.open("POST", `/run-once`);
        request.setRequestHeader("Content-Type", "application/json");
        request.onload = () => {
            const response = request.responseText;
            if (request.status != 200) {
                AlertProgressSideBar()
                alert(response)
            }
            else {
                const _resp_dict = JSON.parse(response)
                index = _resp_dict["index"];
                document.getElementById("registers-flags").innerHTML = _resp_dict["registers_flags"];
                document.getElementById("memory-container").innerHTML = _resp_dict["memory"];
                document.getElementById("assembler-container").innerHTML = _resp_dict["assembler"];
                document.getElementById("code").value = _code;
                ProgressSideBar(_code, index, "step")
            }
        };
        var _code = document.getElementById("code").value.trim();
        request.send(JSON.stringify({
            "code": _code,
            "device": deviceName
        }));
    });

    document.getElementById("reset").addEventListener("click", function () {
        console.log("reset")
        const request = new XMLHttpRequest();
        request.open("POST", `/reset?device=${encodeURIComponent(deviceName)}`);
        request.onload = () => {
            const response = request.responseText;
            if (request.status != 200) {
                alert(response)
            }
            else {
                const _resp_dict = JSON.parse(response)
                document.getElementById("registers-flags").innerHTML = _resp_dict["registers_flags"];
                document.getElementById("memory-container").innerHTML = _resp_dict["memory"];
                document.getElementById("assembler-container").innerHTML = _resp_dict["assembler"];
                document.getElementById("run").disabled = true
                document.getElementById("step").disabled = true
                RenderLineNumbers()

            }
        };
        request.send();
    });

    // memory-edit EventListener
    document.getElementById("memory_edit_input").addEventListener("keyup", event => {
        if (event.key === "Enter") {
            event.preventDefault();
            _mem_edit = ProcessMemEdit(event.target.value)
            if (!_mem_edit) {
                alert("invalid")
            }
            const request = new XMLHttpRequest();
            request.open("POST", `/memory-edit`);
            request.setRequestHeader("Content-Type", "application/json");
            request.onload = () => {
                const response = request.responseText;
                if (request.status != 200) {
                    alert(response)
                }
                else {
                    const _resp_dict = JSON.parse(response)
                    index = _resp_dict["index"];
                    document.getElementById("registers-flags").innerHTML = _resp_dict["registers_flags"];
                    document.getElementById("memory-container").innerHTML = _resp_dict["memory"];
                    document.getElementById("assembler-container").innerHTML = _resp_dict["assembler"];
                }
            }
            request.send(JSON.stringify({
                "device": deviceName,
                "mem_edit": _mem_edit
            }));
        }
    });
    InitMemoryCellEditor(deviceName);
    ShowPhoneWarning();
    var footer = document.querySelector("header");
    if (footer) {
        footer.innerHTML = ``
    }
}

function GetFlags() {
    var flags_dict = {}
    document.querySelectorAll(".flag-input").forEach(element => {
        flags_dict[element.id] = element.checked
    });
    return flags_dict
}
function AlertProgressSideBar() {
    var track = document.getElementById("track");
    _track = track.value.trim().split("\n")
    _track[_track.length - 1] = "!"
    track.value = _track.join("\n")
}
function StripComment(line) {
    return line.split(";")[0].trim()
}
function IsCodeLine(line) {
    var cleaned = StripComment(line);
    return cleaned !== "" && !cleaned.match(/^[A-Za-z_][A-Za-z0-9_]*:$/);
}
function RenderLineNumbers() {
    var code = document.getElementById("code");
    var track = document.getElementById("track");
    if (!code || !track) return;
    var lineCount = Math.max(code.value.split("\n").length, 1);
    var numbers = [];
    for (let i = 1; i <= lineCount; i++) {
        numbers.push(String(i).padStart(2, " "));
    }
    track.value = numbers.join("\n");
    track.scrollTop = code.scrollTop;
}
function ProgressSideBar(code, index, mode = "step") {
    var track = document.getElementById("track");
    var codeBox = document.getElementById("code");
    var code_split = code.split("\n")
    var executed = 0;
    var markers = [];
    for (let i = 0; i < code_split.length; i++) {
        if (!IsCodeLine(code_split[i])) {
            markers.push("");
            continue;
        }
        if (mode === "assembled" || mode === "run") {
            markers.push("✓");
        }
        else if (executed < index - 1) {
            markers.push("✓");
        }
        else if (executed === index - 1) {
            markers.push("▶");
        }
        else {
            markers.push(String(i + 1).padStart(2, " "));
        }
        executed += 1;
    }
    track.value = markers.join("\n");
    if (codeBox) {
        track.scrollTop = codeBox.scrollTop;
    }
}
function ShowPhoneWarning() {
    var warning = document.getElementById("phone-warning");
    var close = document.getElementById("phone-warning-close");
    if (!warning || !close) return;
    if (window.matchMedia("(max-width: 640px)").matches && localStorage.getItem("phone_warning_seen") !== "true") {
        warning.classList.add("show");
    }
    close.addEventListener("click", function () {
        localStorage.setItem("phone_warning_seen", "true");
        warning.classList.remove("show");
    });
}
function ParseHex(data) {
    if (data.match("0[x|X][a-fA-F0-9]+")) {
        return data
    }
    else if (data.match("[a-fA-F0-9]+H$")) {
        _match = data.match("[a-fA-F0-9]+")[0]
        return "0x" + _match
    }
    return "0x" + data
}
function ProcessMemEdit(data) {
    // check if range => randomize
    if (data.includes(":")) {
        data = data.split(":")
        _data = []
        for (let i = 0; i < data.length; i++) {
            data[i] = ParseHex(data[i])
        }
        start = parseInt(data[0])
        end = parseInt(data[1])

        idx = 0
        for (let i = start; i <= end; i++) {
            _data[idx++] = ["0x" + i.toString(16), "0x" + parseInt(Math.random() * 255).toString(16)]
        }
        return _data
    }
    else if (!data.includes("=")) {
        return false
    }
    data = data.split("=")
    for (let i = 0; i < data.length; i++) {
        data[i] = ParseHex(data[i])
    }
    return [data]
}

function NormalizeHexInput(value) {
    var cleaned = (value || "").trim();
    if (!cleaned) return "";
    if (/^0x[0-9a-f]+$/i.test(cleaned)) return cleaned;
    if (/^[0-9a-f]+h$/i.test(cleaned)) return cleaned;
    if (/^[0-9a-f]+$/i.test(cleaned)) return cleaned + "H";
    return cleaned;
}

function InitMemoryCellEditor(deviceName) {
    var memoryContainer = document.getElementById("memory-container");
    var backdrop = document.getElementById("mem-dialog-backdrop");
    var dialog = document.getElementById("mem-dialog");
    var addrEl = document.getElementById("mem-address");
    var valueInput = document.getElementById("mem-value");
    var writeBtn = document.getElementById("mem-write-btn");
    var closeBtn = document.getElementById("mem-dialog-close");
    var cancelBtn = document.getElementById("mem-dialog-cancel");
    if (!memoryContainer || !backdrop || !dialog || !addrEl || !valueInput || !writeBtn) return;

    var activeAddr = null;
    var activeBank = null;

    document.body.appendChild(backdrop);
    document.body.appendChild(dialog);

    function openDialog(addr, value, bank) {
        activeAddr = addr;
        activeBank = bank || null;
        addrEl.textContent = addr;
        valueInput.value = (value || "").trim();
        backdrop.classList.add("open");
        dialog.classList.add("open");
        valueInput.focus();
        valueInput.select();
    }

    function closeDialog() {
        activeAddr = null;
        activeBank = null;
        valueInput.value = "";
        backdrop.classList.remove("open");
        dialog.classList.remove("open");
    }

    function writeMemory() {
        if (!activeAddr) return;
        var normalizedValue = NormalizeHexInput(valueInput.value);
        if (!normalizedValue) {
            alert("Enter a hex value like 05H or 0x05");
            return;
        }
        var memEdit = ProcessMemEdit(`${activeAddr}=${normalizedValue}`);
        if (!memEdit) {
            alert("Invalid memory edit");
            return;
        }
        const request = new XMLHttpRequest();
        request.open("POST", `/memory-edit`);
        request.setRequestHeader("Content-Type", "application/json");
        request.onload = () => {
            const response = request.responseText;
            if (request.status != 200) {
                alert(response)
            }
            else {
                const _resp_dict = JSON.parse(response)
                document.getElementById("registers-flags").innerHTML = _resp_dict["registers_flags"];
                document.getElementById("memory-container").innerHTML = _resp_dict["memory"];
                document.getElementById("assembler-container").innerHTML = _resp_dict["assembler"];
                closeDialog();
            }
        };
        request.send(JSON.stringify({
            "device": deviceName,
            "mem_edit": memEdit,
            "bank": activeBank
        }));
    }

    memoryContainer.addEventListener("click", (event) => {
        var cell = event.target.closest(".memory-cell");
        if (!cell) return;
        var addr = cell.getAttribute("data-addr");
        var bank = cell.getAttribute("data-bank");
        var value = cell.textContent;
        if (!addr) return;
        openDialog(addr, value, bank);
    });

    backdrop.addEventListener("click", closeDialog);
    if (closeBtn) closeBtn.addEventListener("click", closeDialog);
    if (cancelBtn) cancelBtn.addEventListener("click", closeDialog);
    if (writeBtn) writeBtn.addEventListener("click", writeMemory);
    valueInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            writeMemory();
        }
        if (event.key === "Escape") {
            closeDialog();
        }
    });
}

// ============ AI PANEL FUNCTIONALITY ============
document.addEventListener('DOMContentLoaded', function() {
    const deviceName = document.body?.dataset?.deviceName || document.body?.dataset?.device || '8051';
    const aiPanel = document.getElementById('ai-panel');
    const aiPanelToggle = document.getElementById('ai-panel-toggle');
    const aiPanelClose = document.getElementById('ai-panel-close');
    const aiExplainBtn = document.getElementById('ai-explain-btn');
    const aiTutorBtn = document.getElementById('ai-tutor-btn');
    const aiSendBtn = document.getElementById('ai-send-btn');
    const aiInput = document.getElementById('ai-input');
    const aiChatMessages = document.getElementById('ai-chat-messages');
    const aiApiKey = document.getElementById('ai-api-key');
    const aiKeyHelp = document.getElementById('ai-key-help');

    if (!aiPanel || !aiPanelToggle) return;

    // Move AI elements directly to the document body. 
    
    document.body.appendChild(aiPanelToggle);
    document.body.appendChild(aiPanel);

    // Load saved API key from localStorage
    const savedKey = localStorage.getItem('groq_api_key');
    if (savedKey && aiApiKey) {
        aiApiKey.value = savedKey;
    }

    // Save API key when changed
    if (aiApiKey) {
        aiApiKey.addEventListener('change', () => {
            localStorage.setItem('groq_api_key', aiApiKey.value);
        });
    }

    // Help link
    if (aiKeyHelp) {
        aiKeyHelp.addEventListener('click', () => {
            window.open('https://console.groq.com', '_blank');
        });
    }

    // Toggle AI panel
    aiPanelToggle.addEventListener('click', (event) => {
        event.preventDefault();
        aiPanel.classList.add('open');
        aiPanelToggle.style.display = 'none';
    });

    if (aiPanelClose) {
        aiPanelClose.addEventListener('click', () => {
            aiPanel.classList.remove('open');
            aiPanelToggle.style.display = 'inline-flex';
        });
    }

    // Send message to AI
    function sendMessage(userMessage, mode = 'chat') {
        if (!userMessage.trim()) return;

        const apiKey = aiApiKey ? aiApiKey.value.trim() : '';

        // Add user message to chat
        const userMsgDiv = document.createElement('div');
        userMsgDiv.style.cssText = 'padding: 8px; background: rgba(10,132,255,0.15); border-radius: 6px; color: #0A84FF; font-size: 12px; word-wrap: break-word;';
        userMsgDiv.textContent = userMessage;
        aiChatMessages.appendChild(userMsgDiv);

        // Clear input
        aiInput.value = '';

        // Show loading
        const loadingDiv = document.createElement('div');
        loadingDiv.style.cssText = 'padding: 8px; color: rgba(255,255,255,0.5); font-size: 12px;';
        loadingDiv.innerHTML = 'Thinking...';
        aiChatMessages.appendChild(loadingDiv);
        aiChatMessages.scrollTop = aiChatMessages.scrollHeight;

        // Get code context if available
        const codeContext = document.getElementById('code').value;

        // Send to backend
        const request = new XMLHttpRequest();
        request.open('POST', '/api/ai-help');
        request.setRequestHeader('Content-Type', 'application/json');
        request.onload = () => {
            loadingDiv.remove();
            if (request.status === 200) {
                const response = JSON.parse(request.responseText);
                const aiMsgDiv = document.createElement('div');
                aiMsgDiv.className = 'ai-message-content';
                aiMsgDiv.style.cssText = 'padding: 8px; background: rgba(255,255,255,0.05); border-radius: 6px; color: rgba(255,255,255,0.9); font-size: 12px; word-wrap: break-word; line-height: 1.4;';
                
                if (typeof marked !== 'undefined') {
                    aiMsgDiv.innerHTML = marked.parse(response.message);
                } else {
                    aiMsgDiv.style.whiteSpace = 'pre-wrap';
                    aiMsgDiv.textContent = response.message;
                }
                aiChatMessages.appendChild(aiMsgDiv);
            } else {
                try {
                    const errorResponse = JSON.parse(request.responseText);
                    const errorDiv = document.createElement('div');
                    errorDiv.style.cssText = 'padding: 8px; background: rgba(255,0,0,0.1); border-radius: 6px; color: #ff6b6b; font-size: 12px;';
                    errorDiv.innerHTML = '<strong>Error:</strong> ' + (errorResponse.error || errorResponse.info || 'Unknown error');
                    aiChatMessages.appendChild(errorDiv);
                } catch (e) {
                    const errorDiv = document.createElement('div');
                    errorDiv.style.cssText = 'padding: 8px; background: rgba(255,0,0,0.1); border-radius: 6px; color: #ff6b6b; font-size: 12px;';
                    errorDiv.textContent = 'Error: ' + (request.responseText || 'Failed to get response');
                    aiChatMessages.appendChild(errorDiv);
                }
            }
            aiChatMessages.scrollTop = aiChatMessages.scrollHeight;
        };

        request.onerror = () => {
            loadingDiv.remove();
            const errorDiv = document.createElement('div');
            errorDiv.style.cssText = 'padding: 8px; background: rgba(255,0,0,0.1); border-radius: 6px; color: #ff6b6b; font-size: 12px;';
            errorDiv.textContent = 'Connection error. Check your internet and API key.';
            aiChatMessages.appendChild(errorDiv);
        };

        request.send(JSON.stringify({
            message: userMessage,
            code: codeContext,
            mode: mode,
            api_key: apiKey,
            device_name: deviceName
        }));
    }

    // Explain code button
    aiExplainBtn.addEventListener('click', () => {
        const code = document.getElementById('code').value;
        if (!code.trim()) {
            alert('Please write some code first!');
            return;
        }
        aiPanel.classList.add('open');
        sendMessage(`Please explain this ${deviceName} assembly code line by line:\n\n${code}`, 'explain');
    });

    // Step-by-step tutor button
    aiTutorBtn.addEventListener('click', () => {
        const code = document.getElementById('code').value;
        if (!code.trim()) {
            alert('Please write some code first!');
            return;
        }
        aiPanel.classList.add('open');
        sendMessage(`Please provide a step-by-step explanation of how this ${deviceName} code executes:\n\n${code}`, 'tutor');
    });

    // Send button
    aiSendBtn.addEventListener('click', () => {
        const message = aiInput.value.trim();
        if (message) {
            sendMessage(message, 'chat');
        }
    });

    // Enter key to send
    aiInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const message = aiInput.value.trim();
            if (message) {
                sendMessage(message, 'chat');
            }
        }
    });
});
