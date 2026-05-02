import json
import os
import urllib.request
import urllib.error

from flask import Flask, make_response, render_template, request

from core.controller import Controller as Controller8051
from core.util import fill_memory
from core8085.controller import Controller as Controller8085

# from core.flags import flags

CLEAR_TOKEN = "batman"
app = Flask(__name__, static_folder="static")
controllers = {
    "8051": Controller8051(),
    "8085": Controller8085(),
}
memory_overrides = {
    "8051": {},
    "8085": {},
}

app.jinja_env.globals.update(zip=zip)


def _normalize_device(value: str) -> str:
    if not value:
        return "8051"
    value = value.strip().lower()
    if value == "8085":
        return "8085"
    return "8051"


def _get_device_from_request(payload: dict = None) -> str:
    payload = payload or {}
    return _normalize_device(
        request.args.get("device") or payload.get("device") or payload.get("device_name")
    )


def _get_controller(device: str):
    return controllers[device]


def _set_memory_value(device: str, controller, memloc: str, memdata: str, bank: str = None) -> bool:
    if device == "8085":
        controller.op.memory_write(memloc, memdata)
        return True

    addr_int = int(str(memloc), 16)

    if bank == "rom":
        if addr_int <= int(controller.op.memory_rom._memory_limit_hex, 16):
            addr = format(addr_int, controller.op.memory_rom._format_spec)
            controller.op.memory_rom.write(addr, memdata)
            return True
        raise ValueError("Memory address out of range")

    if bank == "ram":
        if addr_int <= int(controller.op.memory_ram._memory_limit_hex, 16):
            addr = format(addr_int, controller.op.memory_ram._format_spec)
            controller.op.memory_ram.write(addr, memdata)
            return True
        raise ValueError("Memory address out of range")

    if addr_int <= int(controller.op.memory_ram._memory_limit_hex, 16):
        addr = format(addr_int, controller.op.memory_ram._format_spec)
        controller.op.memory_ram.write(addr, memdata)
        return True
    if addr_int <= int(controller.op.memory_rom._memory_limit_hex, 16):
        addr = format(addr_int, controller.op.memory_rom._format_spec)
        controller.op.memory_rom.write(addr, memdata)
        return True
    raise ValueError("Memory address out of range")


def _apply_memory_overrides(device: str, controller) -> None:
    overrides = memory_overrides.get(device, {})
    for addr, (value, bank) in overrides.items():
        _set_memory_value(device, controller, addr, value, bank)


def _get_8051_ram_and_rom(controller):
    _memory_ram, _memory_rom = None, None
    _ram = fill_memory(controller.op.memory_ram, 256).sort()
    if _ram:
        _ram = list(_ram.items())
        _memory_ram = [_ram[x : x + 16] for x in range(0, len(_ram), 16)]

    _rom = fill_memory(controller.op.memory_rom, 256).sort()
    if _rom:
        _rom = list(_rom.items())
        _memory_rom = [_rom[x : x + 16] for x in range(0, len(_rom), 16)]

    return _memory_ram, _memory_rom


def _get_8085_memory_rows(controller, start: int = 0, size: int = 256):
    memory = controller.op.memory
    rows = []
    row = []
    for i in range(start, start + size):
        addr = format(i, "#06x")
        row.append((addr, memory[addr]))
        if len(row) == 16:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def _format_range(start: str, end: str) -> str:
    return f"{start.upper()}-{end.upper()}"


def _render_state(device: str, controller):
    if device == "8085":
        start = format(0, "#06x")
        end = format(255, "#06x")
        return {
            "registers_flags": render_template(
                "render_registers_flags.html",
                registers=controller.op.super_memory._registers_todict(),
                flags=controller.op.flags.todict(),
            ),
            "memory": render_template(
                "render_memory.html",
                memory_rows=_get_8085_memory_rows(controller),
                ram_range=_format_range(start, end),
            ),
            "assembler": render_template(
                "render_assembler.html",
                assembler=controller.op._assembler,
            ),
        }

    ram_range = _format_range(
        controller.op.memory_ram._starting_address,
        controller.op.memory_ram._memory_limit_hex,
    )
    rom_range = _format_range(
        controller.op.memory_rom._starting_address,
        controller.op.memory_rom._memory_limit_hex,
    )
    ram, rom = _get_8051_ram_and_rom(controller)
    return {
        "registers_flags": render_template(
            "render_registers_flags.html",
            registers=controller.op.super_memory._registers_todict(),
            flags=controller.op.super_memory.PSW.flags(),
            general_purpose_registers=controller.op.super_memory._general_purpose_registers,
        ),
        "memory": render_template(
            "render_memory.html",
            ram=ram,
            rom=rom,
            ram_range=ram_range,
            rom_range=rom_range,
        ),
        "assembler": render_template("render_assembler.html", assembler=controller.op._assembler),
    }


@app.route("/reset", methods=["POST"])
def reset():
    device = _get_device_from_request()
    controller = _get_controller(device)
    controller.reset()
    memory_overrides[device] = {}
    return _render_state(device, controller)


@app.route("/assemble", methods=["POST"])
def assemble():
    commands_json = request.data
    if commands_json:
        commands_dict = json.loads(commands_json)
        _commands = commands_dict.get("code", None)
        _flags = commands_dict.get("flags", None)
        device = _get_device_from_request(commands_dict)
        controller = _get_controller(device)
        if _commands and _flags:
            try:
                controller.reset()
                controller.set_flags(_flags)
                controller.parse_all(_commands)
                _apply_memory_overrides(device, controller)
                if device == "8085":
                    return render_template(
                        "render_memory.html",
                        memory_rows=_get_8085_memory_rows(controller),
                        ram_range=_format_range(format(0, "#06x"), format(255, "#06x")),
                    )
                ram, rom = _get_8051_ram_and_rom(controller)
                return render_template(
                    "render_memory.html",
                    ram=ram,
                    rom=rom,
                    ram_range=_format_range(
                        controller.op.memory_ram._starting_address,
                        controller.op.memory_ram._memory_limit_hex,
                    ),
                    rom_range=_format_range(
                        controller.op.memory_rom._starting_address,
                        controller.op.memory_rom._memory_limit_hex,
                    ),
                )
            except Exception as e:
                print(e)
                return make_response(f"Exception raised {e}", 400)
    return make_response("Record not found", 400)


@app.route("/run", methods=["POST"])
def run():
    payload = {}
    if request.data:
        payload = json.loads(request.data)
    device = _get_device_from_request(payload)
    controller = _get_controller(device)
    print(controller.ready)
    if controller.ready:
        try:
            controller.run()
            if device == "8051":
                controller.inspect()
            return _render_state(device, controller)

        except Exception as e:
            print(e)
            return make_response(f"Exception raised {e}", 400)
    return make_response("Controller not ready", 400)


@app.route("/run-once", methods=["POST"])
def step():
    payload = {}
    if request.data:
        payload = json.loads(request.data)
    device = _get_device_from_request(payload)
    controller = _get_controller(device)
    print(controller.ready)
    if controller.ready:
        try:
            controller.run_once()
            state = _render_state(device, controller)
            state["index"] = controller._run_idx
            return state
        except Exception as e:
            print(e)
            return make_response(f"Exception raised {e}", 400)
    return make_response("Controller not ready", 400)


@app.route("/memory-edit", methods=["POST"])
def update_memory():
    mem_data = request.data
    if mem_data:
        payload = json.loads(mem_data)
        device = _get_device_from_request(payload)
        controller = _get_controller(device)
        mem_items = payload.get("mem_edit") or payload
        bank = payload.get("bank")
        print(mem_items)
        try:
            for memloc, memdata in mem_items:
                print("=============================")
                print(memloc, memdata)
                _set_memory_value(device, controller, memloc, memdata, bank)
                memory_overrides.setdefault(device, {})[memloc] = (memdata, bank)
            controller._run_idx = 0
            state = _render_state(device, controller)
            state["index"] = controller._run_idx
            return state
        except ValueError as e:
            return make_response(str(e), 400)
        except Exception as e:
            print(e)
            return make_response(f"Exception raised {e}", 400)
    return make_response("Controller not ready", 400)


@app.route("/", methods=["GET"])
def main():
    device = _normalize_device(request.args.get("device"))
    if device == "8085":
        controllers[device] = Controller8085()
    else:
        controllers[device] = Controller8051()
    controller = _get_controller(device)
    supported_opcodes = sorted(list(controller.lookup.keys()))
    ram, rom = (None, None)
    memory_rows = None
    ram_range = None
    rom_range = None
    if device == "8051":
        ram, rom = _get_8051_ram_and_rom(controller)
        ram_range = _format_range(
            controller.op.memory_ram._starting_address,
            controller.op.memory_ram._memory_limit_hex,
        )
        rom_range = _format_range(
            controller.op.memory_rom._starting_address,
            controller.op.memory_rom._memory_limit_hex,
        )
    else:
        memory_rows = _get_8085_memory_rows(controller)
        ram_range = _format_range(format(0, "#06x"), format(255, "#06x"))
    return render_template(
        "index.html",
        ram=ram,
        rom=rom,
        memory_rows=memory_rows,
        ram_range=ram_range,
        rom_range=rom_range,
        registers=controller.op.super_memory._registers_todict(),
        general_purpose_registers=controller.op.super_memory._general_purpose_registers if device == "8051" else None,
        flags=controller.op.super_memory.PSW.flags() if device == "8051" else controller.op.flags.todict(),
        supported_opcodes=supported_opcodes,
        has_server_key=bool(os.environ.get("GROQ_API_KEY")),
        device_name=device,
        app_name="SimLab",
    )


@app.route("/api/ai-help", methods=["POST"])
def ai_help():
    """AI Learning Assistant endpoint for explaining 8051 code using Groq (Free API)"""
    try:
        # Get Groq API key from request or environment
        request_data = json.loads(request.data)
        api_key = request_data.get('api_key') or os.environ.get('GROQ_API_KEY')
        
        if not api_key:
            return make_response(
                json.dumps({
                    "error": "Groq API key not provided. Set GROQ_API_KEY environment variable or provide it in the request.",
                    "info": "Get a free key at https://console.groq.com"
                }),
                400
            )
        
        user_message = request_data.get('message', '')
        code = request_data.get('code', '')
        mode = request_data.get('mode', 'chat')
        
        if not user_message:
            return make_response(json.dumps({"error": "No message provided"}), 400)
        
        device_name = request_data.get("device_name") or "8051"

        # Build system prompt based on mode
        if mode == "explain":
            system_prompt = f"""You are an expert {device_name} microcontroller assembly language tutor.
Your role is to help students learn {device_name} assembly programming by explaining code clearly and thoroughly.
- Explain each instruction and what it does
- Break down the code into logical sections
- Explain register usage and memory operations
- Be concise but thorough
- Use simple language suitable for beginners"""
        elif mode == "tutor":
            system_prompt = f"""You are an interactive {device_name} learning tutor.
Help students understand how code executes step-by-step:
- Trace through execution with specific memory and register values
- Explain state changes at each step
- Point out important concepts
- Use examples to illustrate concepts
- Encourage active learning"""
        else:  # chat
            system_prompt = f"""You are a helpful {device_name} microcontroller tutor.
Help students learn assembly programming by answering their questions.
- Provide clear, concise explanations
- Give practical examples
- Point to relevant resources and concepts
- Encourage curiosity and learning
- Help debug code if asked"""
        
        # Call Groq API via standard HTTP request (no external library needed!)
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"{device_name}-Simulator/1.0"
        }
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        req = urllib.request.Request(url, headers=headers, data=json.dumps(data).encode('utf-8'))
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            ai_message = result['choices'][0]['message']['content']
        
        return json.dumps({"message": ai_message})
        
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8')
        print(f"Groq API Error: {error_msg}")
        detailed_error = "Please check your API key."
        try:
            error_data = json.loads(error_msg)
            if "error" in error_data and "message" in error_data["error"]:
                detailed_error = error_data["error"]["message"]
        except Exception:
            pass
        return make_response(json.dumps({"error": f"Groq: {detailed_error}"}), 400)
    except Exception as e:
        print(f"AI Error: {str(e)}")
        return make_response(
            json.dumps({"error": f"AI Error: {str(e)}"}),
            500
        )
