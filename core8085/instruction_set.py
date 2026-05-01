from core8085.flags import flags
from core8085.util import construct_hex, decompose_byte, ishex, tohex, twos_complement


class Instructions:
    def __init__(self, op) -> None:
        self.op = op
        self._jump_flag = False
        self._base = 16
        pass

    def _is_jump_opcode(self, opcode) -> bool:
        opcode = opcode.upper()
        return opcode in [
            "JNC",
            "JC",
            "JZ",
            "JNZ",
            "JMP",
            "JP",
            "JM",
            "JPE",
            "JPO",
            "CALL",
            "CC",
            "CNC",
            "CZ",
            "CNZ",
            "CP",
            "CM",
            "CPE",
            "CPO",
        ]

    def _next_addr(self, addr) -> str:
        return format(int(str(addr), 16) + 1, "#06x")

    def _check_carry(self, data_1, data_2, og2, add=True, _AC=True, _CY=True) -> None:
        """
        Method to check both `CY` and `AC` flags.

        `aux_data` are the LSB of the two data to be added
        For example: for `0x11` and `0xae`, `aux_data=["0x1", "0xe"]`
        """
        decomposed_data_1 = decompose_byte(data_1, nibble=True)
        decomposed_data_2 = decompose_byte(data_2, nibble=True)
        carry_data, aux_data = list(zip(decomposed_data_1, decomposed_data_2))

        if _AC:
            flags.AC = False
            if (int(aux_data[0], 16) + int(aux_data[1], 16)) >= 16:
                print("AUX FLAG")
                flags.AC = True

        if not _CY:
            return

        if not add:
            flags.CY = False
            if int(str(data_1), 16) < int(str(og2), 16):
                print("CARRY FLAG-")
                flags.CY = True
        return

    def _check_parity(self, data_bin: str) -> None:
        flags.P = False
        _count_1s = data_bin.count("1")
        if not _count_1s % 2:
            flags.P = True
            print("PARITY")
        return

    def _check_sign(self, data_bin: str) -> None:
        flags.S = False
        if int(data_bin[0]):
            flags.S = True
            print("SIGN")
        return

    def _check_zero(self, result: str) -> None:
        flags.Z = False
        if int(result, 2) == 0:
            flags.Z = True
            print("ZERO")
        return

    def _check_flags(self, data_bin, _P=True, _S=True, _Z=True) -> bool:
        if _P:
            self._check_parity(data_bin)
        if _S:
            self._check_sign(data_bin)
        if _Z:
            self._check_zero(data_bin)
        return True

    def _check_flags_and_compute(self, data_1, data_2, add=True, _AC=True, _CY=True, _P=True, _S=True, _Z=True):
        og2 = data_2
        if not add:
            data_2 = twos_complement(str(data_2))

        result = int(str(data_1), 16) + int(str(data_2), 16)
        if result > 255:
            if _CY:
                flags.CY = True
                print("CARRY FLAG+")
            result -= 256
        result_hex = format(result, "#04x")
        data_bin = format(result, "08b")

        self._check_carry(data_1, data_2, og2, add=add, _AC=_AC, _CY=_CY)
        self._check_flags(data_bin, _P=_P, _S=_S, _Z=_Z)
        return result_hex

    def _jump_to(self, target, bounce_to_label, bounce_to_address):
        if ishex(str(target)):
            target = tohex(str(target))
            return bounce_to_address(target) if bounce_to_address else False
        return bounce_to_label(target) if bounce_to_label else False

    def _logic_write_a(self, result: int, set_ac: bool = False) -> bool:
        flags.CY = False
        flags.AC = bool(set_ac)
        result &= 0xFF
        self.op.memory_write("A", format(result, "#04x"))
        self._check_flags(format(result, "08b"))
        return True

    def _add_with_carry(self, data_1, data_2, carry_in: int = 0) -> str:
        data_1_val = int(str(data_1), 16)
        data_2_val = int(str(data_2), 16)
        result = data_1_val + data_2_val + carry_in
        flags.CY = result > 0xFF
        flags.AC = ((data_1_val & 0x0F) + (data_2_val & 0x0F) + carry_in) > 0x0F
        result &= 0xFF
        self._check_flags(format(result, "08b"))
        return format(result, "#04x")

    def _sub_with_borrow(self, data_1, data_2, borrow_in: int = 0) -> str:
        data_1_val = int(str(data_1), 16)
        data_2_val = int(str(data_2), 16)
        result = data_1_val - data_2_val - borrow_in
        flags.CY = result < 0
        flags.AC = ((data_1_val & 0x0F) - (data_2_val & 0x0F) - borrow_in) < 0
        result &= 0xFF
        self._check_flags(format(result, "08b"))
        return format(result, "#04x")

    def mvi(self, addr: str, data: str) -> bool:
        """
        MoVe Immediate

        Store the immediate `data` into `addr`

        Parameters
        ----------
        addr : `str`
            Address
        data : `str`
            Data
        """
        self.op.memory_write(addr, data)
        return True

    def mov(self, to_addr: str, from_addr: str) -> bool:
        """
        MOVe data `from_addr` to `to_addr`

        Parameters
        ----------
        to_addr : `str`
            To address
        from_addr : `str`
            From address
        """
        data = self.op.memory_read(from_addr)
        self.op.memory_write(to_addr, data)
        return True

    def sta(self, addr: str) -> bool:
        """
        STore Accumulator

        Parameters
        ----------
        addr : `str`
            store the accumulator data in `addr`
        """
        data = self.op.memory_read("A")
        self.op.memory_write(addr, data)
        return True

    def db(self, *args) -> bool:
        """
        Directive to store the data at address location pointed by the ``PC``

        Parameters
        ----------
        *args : `tuple`
        """
        for x in args:
            self.op.super_memory.PC.write(x)
        return True

    def add(self, to_addr, from_addr=None) -> bool:
        """
        Adds `to_addr` with `from_addr`

        Parameters
        ----------
        from_addr : `str`
            From address

        to_addr : `str`
            To address
        """
        if not from_addr:
            from_addr = to_addr
            to_addr = "A"
        from_data = self.op.memory_read(from_addr)
        to_data = self.op.memory_read(to_addr)
        data = self._check_flags_and_compute(from_data, to_data)
        self.op.memory_write(to_addr, data)
        return True

    def sub(self, from_addr: str, to_addr: str = None) -> bool:
        """
        Subtracts `to_addr` from `from_addr` with Borrow

        Parameters
        ----------
        from_addr : `str`
            From address

        to_addr : `str`
            To address
        """
        if not to_addr:
            to_addr = from_addr
            from_addr = "A"
        to_data = self.op.memory_read(to_addr)
        from_data = self.op.memory_read(from_addr)
        result_data = self._check_flags_and_compute(from_data, to_data, add=False)
        self.op.memory_write(from_addr, result_data)
        return True

    def sbb(self, from_addr: str, to_addr: str = None) -> bool:
        """
        Subtracts `to_addr` from `from_addr` with Borrow

        Parameters
        ----------
        from_addr : `str`
            From address

        to_addr : `str`
            To address
        """
        if not to_addr:
            to_addr = from_addr
            from_addr = "A"
        to_data = self.op.memory_read(to_addr)
        from_data = self.op.memory_read(from_addr)
        if flags.CY:
            flags.CY = False
            from_data += 1
        result_data = self._check_flags_and_compute(from_data, to_data, add=False)
        self.op.memory_write(from_addr, result_data)
        return True

    def adc(self, addr: str) -> bool:
        """
        ADd with Carry
        """
        data_1 = self.op.memory_read("A")
        data_2 = self.op.memory_read(addr)
        result = self._add_with_carry(data_1, data_2, carry_in=1 if flags.CY else 0)
        self.op.memory_write("A", result)
        return True

    def aci(self, data: str) -> bool:
        """
        Add immediate with Carry
        """
        data_1 = self.op.memory_read("A")
        result = self._add_with_carry(data_1, data, carry_in=1 if flags.CY else 0)
        self.op.memory_write("A", result)
        return True

    def adi(self, data: str) -> bool:
        """
        Add immediate
        """
        data_1 = self.op.memory_read("A")
        result = self._add_with_carry(data_1, data, carry_in=0)
        self.op.memory_write("A", result)
        return True

    def ana(self, addr: str) -> bool:
        """
        AND logical instruction
        """
        data_1 = int(str(self.op.memory_read("A")), 16)
        data_2 = int(str(self.op.memory_read(addr)), 16)
        return self._logic_write_a(data_1 & data_2, set_ac=True)

    def ani(self, data: str) -> bool:
        """
        AND immediate
        """
        data_1 = int(str(self.op.memory_read("A")), 16)
        data_2 = int(str(data), 16)
        return self._logic_write_a(data_1 & data_2, set_ac=True)

    def xra(self, addr: str) -> bool:
        """
        XOR logical instruction
        """
        data_1 = int(str(self.op.memory_read("A")), 16)
        data_2 = int(str(self.op.memory_read(addr)), 16)
        return self._logic_write_a(data_1 ^ data_2)

    def xri(self, data: str) -> bool:
        """
        XOR immediate
        """
        data_1 = int(str(self.op.memory_read("A")), 16)
        data_2 = int(str(data), 16)
        return self._logic_write_a(data_1 ^ data_2)

    def ori(self, data: str) -> bool:
        """
        OR immediate
        """
        data_1 = int(str(self.op.memory_read("A")), 16)
        data_2 = int(str(data), 16)
        return self._logic_write_a(data_1 | data_2)

    def sui(self, data: str) -> bool:
        """
        Subtract immediate
        """
        data_1 = self.op.memory_read("A")
        result = self._sub_with_borrow(data_1, data, borrow_in=0)
        self.op.memory_write("A", result)
        return True

    def sbi(self, data: str) -> bool:
        """
        Subtract immediate with Borrow
        """
        data_1 = self.op.memory_read("A")
        result = self._sub_with_borrow(data_1, data, borrow_in=1 if flags.CY else 0)
        self.op.memory_write("A", result)
        return True

    def cpi(self, data: str) -> bool:
        """
        Compare immediate
        """
        data_1 = self.op.memory_read("A")
        self._sub_with_borrow(data_1, data, borrow_in=0)
        return True

    def lda(self, addr: str) -> bool:
        """
        Load Accumulator direct
        """
        data = self.op.memory_read(addr)
        self.op.memory_write("A", data)
        return True

    def ldax(self, addr: str) -> bool:
        """
        Load Accumulator indirect (BC or DE)
        """
        address = self.op.register_pair_read(addr)
        data = self.op.memory_read(address)
        self.op.memory_write("A", data)
        return True

    def stax(self, addr: str) -> bool:
        """
        Store Accumulator indirect (BC or DE)
        """
        address = self.op.register_pair_read(addr)
        data = self.op.memory_read("A")
        self.op.memory_write(address, data)
        return True

    def lxi(self, addr, data) -> bool:
        """
        Load eXtended register

        Parameters
        ----------
        addr : `str`
        data : `str`
        """
        self.op.register_pair_write(addr, data)
        return True

    def inr(self, addr: str) -> bool:
        """
        InCrement Register

        Parameters
        ----------
        addr : `str`, `hex`
        """
        data = self.op.memory_read(addr)
        data_to_write = self._check_flags_and_compute(data, "0x01", _CY=False)
        self.op.memory_write(addr, data_to_write)
        return True

    def inx(self, addr: str) -> bool:
        """
        InCrement eXtended register

        Parameters
        ----------
        addr : `str`

        Note
        ----
        The flags are not at all affected by the execution of this instruction.
        """
        data = self.op.register_pair_read(addr)
        data_to_write = format(int(data, 16) + 1, "#06x")
        self.op.register_pair_write(addr, data_to_write)
        return True

    def dcr(self, addr: str) -> bool:
        """
        DeCrement Register

        Parameters
        ----------
        addr : `str`, `hex`
        """
        data = self.op.memory_read(addr)
        data_to_write = self._check_flags_and_compute(data, "0x01", add=False, _CY=False)
        self.op.memory_write(addr, data_to_write)
        return True

    def dcx(self, addr: str) -> bool:
        """
        DeCrement eXtended register
        Decrements the `addr` register pair.

        Parameters
        ----------
        addr : `str`, (`B`, `D`, `H`)

        The flags are not at all affected by the execution of this instruction.
        """
        data = self.op.register_pair_read(addr)
        data_to_write = format(int(data, 16) - 1, "#06x")
        self.op.register_pair_write(addr, data_to_write)
        return True

    def lhld(self, addr: str) -> bool:
        """
        Loads the data from `addr` into HL pair.

        Parameters
        ----------
        addr : `str`, hex
        """
        data_1 = self.op.memory_read(addr)
        nxt_addr = format(int(addr, 16) + 1, "#06x")
        data_2 = self.op.memory_read(nxt_addr)
        self.op.memory_write("H", data_2)
        self.op.memory_write("L", data_1)
        return True

    def xchg(self, *args) -> bool:
        """
        eXChanGes the data stored in HL and DE pairs.
        """
        data_1 = self.op.register_pair_read("H")
        data_2 = self.op.register_pair_read("D")
        self.op.register_pair_write("D", data_1)
        self.op.register_pair_write("H", data_2)
        return True

    def dad(self, addr: str) -> bool:
        """
        Adds the HL and `addr` pair and store the result in HL.

        Parameters
        ----------
        addr : `str` (rp, `B`, `D`, `H`)

        Note
        ----
        `DAD` only affects the `CY` flag

        """
        data_1 = self.op.register_pair_read(addr)
        data_2 = self.op.register_pair_read("H")
        addition = int(data_1, 16) + int(data_2, 16)

        # check `CY` flag
        if addition > int("0xffff", 16):
            addition = addition - (int("0xffff", 16) + 1)
            flags.CY = True

        addition = format(addition, "#06x")
        self.op.register_pair_write("H", addition)
        return True

    def jnc(self, label, *args, **kwargs) -> bool:
        """
        Jump if Not Carry
        """
        bounce_to_label = kwargs.get("bounce_to_label")
        if not flags.CY:
            return bounce_to_label(label)
        return True

    def jc(self, label, *args, **kwargs) -> bool:
        """
        Jump if Carry
        """
        bounce_to_label = kwargs.get("bounce_to_label")
        if flags.CY:
            return bounce_to_label(label)
        return True

    def jz(self, label, *args, **kwargs) -> bool:
        """
        Jump if Zero
        """
        bounce_to_label = kwargs.get("bounce_to_label")
        if flags.Z:
            return bounce_to_label(label)
        return True

    def jnz(self, label, *args, **kwargs) -> bool:
        """
        Jump if Not Zero
        """
        bounce_to_label = kwargs.get("bounce_to_label")
        if not flags.Z:
            return bounce_to_label(label)
        return True

    def shld(self, addr: str) -> bool:
        """
        Store HL pair data

        Parameters
        ----------
        addr : `str`
            Address
        """
        data_1 = self.op.memory_read("H")
        data_2 = self.op.memory_read("L")
        self.op.memory_write(addr, data_2)
        nxt_addr = format(int(addr, 16) + 1, "#06x")
        self.op.memory_write(nxt_addr, data_1)
        return True

    def ora(self, addr: str) -> bool:
        """
        OR logical instruction

        Parameters
        ----------
        addr : `str`
            Address
        """
        data_1 = int(str(self.op.memory_read("A")), 16)
        data_2 = int(str(self.op.memory_read(addr)), 16)
        return self._logic_write_a(data_1 | data_2)

    def ral(self) -> bool:
        """
        <--CY--A7----A0<---<-
        |                   |
        ->------------------>
        """
        data = self.op.memory_read("A")
        data_bin = list(format(int(str(data), 16), "08b"))
        rolled_data_bin = []

        for i in range(0, len(data_bin[:-1])):
            rolled_data_bin.append(data_bin[i + 1])

        # CY into new LSB
        rolled_data_bin.insert(8, str(int(flags.CY)))
        # MSB into CY
        flags.CY = bool(int(data_bin[0]))

        rolled_data_bin = "".join(rolled_data_bin)
        data_new = format(int(rolled_data_bin, 2), "#02x")
        self.op.memory_write("A", data_new)
        return True

    def rlc(self) -> bool:
        """
        CY<---A7----A0<---<-
            |              |
            ->------------->
        """
        data = self.op.memory_read("A")
        data_bin = list(format(int(str(data), 16), "08b"))
        rolled_data_bin = []

        for i in range(0, len(data_bin[:-1])):
            rolled_data_bin.append(data_bin[i + 1])

        rolled_data_bin.insert(8, str(int(data_bin[0])))
        flags.CY = bool(int(data_bin[0]))

        rolled_data_bin = "".join(rolled_data_bin)
        data_new = format(int(rolled_data_bin, 2), "#02x")
        self.op.memory_write("A", data_new)
        return True

    def rrc(self) -> bool:
        """
        CY<---A0----A7<---<-
            |              |
            ->------------->
        """
        data = self.op.memory_read("A")
        data_bin = list(format(int(str(data), 16), "08b"))
        rolled_data_bin = []

        for i in range(1, len(data_bin)):
            rolled_data_bin.append(data_bin[i - 1])

        rolled_data_bin.insert(0, str(int(data_bin[-1])))
        flags.CY = bool(int(data_bin[-1]))

        rolled_data_bin = "".join(rolled_data_bin)
        data_new = format(int(rolled_data_bin, 2), "#02x")
        self.op.memory_write("A", data_new)
        return True

    def rar(self) -> bool:
        """
        <--CY--A7----A0<---<-
        |                   |
        ->------------------>
        """
        data = self.op.memory_read("A")
        data_bin = list(format(int(str(data), 16), "08b"))
        rolled_data_bin = [str(int(flags.CY))]
        rolled_data_bin.extend(data_bin[:-1])

        flags.CY = bool(int(data_bin[-1]))
        rolled_data_bin = "".join(rolled_data_bin)
        data_new = format(int(rolled_data_bin, 2), "#02x")
        self.op.memory_write("A", data_new)
        return True

    def cma(self) -> bool:
        """
        Complement Accumulator
        """
        data = int(str(self.op.memory_read("A")), 16)
        self.op.memory_write("A", format((~data) & 0xFF, "#04x"))
        return True

    def cmc(self) -> bool:
        """
        Complement Carry
        """
        flags.CY = not flags.CY
        return True

    def stc(self) -> bool:
        """
        Set Carry
        """
        flags.CY = True
        return True

    def daa(self) -> bool:
        """
        Decimal Adjust Accumulator
        """
        a_val = int(str(self.op.memory_read("A")), 16)
        correction = 0
        if (a_val & 0x0F) > 9 or flags.AC:
            correction += 0x06
        if (a_val & 0xF0) > 0x90 or flags.CY or ((a_val + correction) > 0x9F):
            correction += 0x60

        result = a_val + correction
        flags.CY = result > 0xFF
        flags.AC = ((a_val & 0x0F) + (correction & 0x0F)) > 0x0F
        result &= 0xFF
        self.op.memory_write("A", format(result, "#04x"))
        self._check_flags(format(result, "08b"))
        return True

    def jmp(self, label, *args, **kwargs) -> bool:
        bounce_to_label = kwargs.get("bounce_to_label")
        bounce_to_address = kwargs.get("bounce_to_address")
        return self._jump_to(label, bounce_to_label, bounce_to_address)

    def jp(self, label, *args, **kwargs) -> bool:
        bounce_to_label = kwargs.get("bounce_to_label")
        bounce_to_address = kwargs.get("bounce_to_address")
        if not flags.S:
            return self._jump_to(label, bounce_to_label, bounce_to_address)
        return True

    def jm(self, label, *args, **kwargs) -> bool:
        bounce_to_label = kwargs.get("bounce_to_label")
        bounce_to_address = kwargs.get("bounce_to_address")
        if flags.S:
            return self._jump_to(label, bounce_to_label, bounce_to_address)
        return True

    def jpe(self, label, *args, **kwargs) -> bool:
        bounce_to_label = kwargs.get("bounce_to_label")
        bounce_to_address = kwargs.get("bounce_to_address")
        if flags.P:
            return self._jump_to(label, bounce_to_label, bounce_to_address)
        return True

    def jpo(self, label, *args, **kwargs) -> bool:
        bounce_to_label = kwargs.get("bounce_to_label")
        bounce_to_address = kwargs.get("bounce_to_address")
        if not flags.P:
            return self._jump_to(label, bounce_to_label, bounce_to_address)
        return True

    def call(self, label, *args, **kwargs) -> bool:
        bounce_to_label = kwargs.get("bounce_to_label")
        bounce_to_address = kwargs.get("bounce_to_address")
        push_return_address = kwargs.get("push_return_address")
        if push_return_address:
            push_return_address()
        return self._jump_to(label, bounce_to_label, bounce_to_address)

    def cc(self, label, *args, **kwargs) -> bool:
        if flags.CY:
            return self.call(label, *args, **kwargs)
        return True

    def cnc(self, label, *args, **kwargs) -> bool:
        if not flags.CY:
            return self.call(label, *args, **kwargs)
        return True

    def cz(self, label, *args, **kwargs) -> bool:
        if flags.Z:
            return self.call(label, *args, **kwargs)
        return True

    def cnz(self, label, *args, **kwargs) -> bool:
        if not flags.Z:
            return self.call(label, *args, **kwargs)
        return True

    def cp(self, label, *args, **kwargs) -> bool:
        if not flags.S:
            return self.call(label, *args, **kwargs)
        return True

    def cm(self, label, *args, **kwargs) -> bool:
        if flags.S:
            return self.call(label, *args, **kwargs)
        return True

    def cpe(self, label, *args, **kwargs) -> bool:
        if flags.P:
            return self.call(label, *args, **kwargs)
        return True

    def cpo(self, label, *args, **kwargs) -> bool:
        if not flags.P:
            return self.call(label, *args, **kwargs)
        return True

    def ret(self, *args, **kwargs) -> bool:
        resume_from_return = kwargs.get("resume_from_return")
        if resume_from_return:
            return resume_from_return()
        return True

    def rc(self, *args, **kwargs) -> bool:
        if flags.CY:
            return self.ret(*args, **kwargs)
        return True

    def rnc(self, *args, **kwargs) -> bool:
        if not flags.CY:
            return self.ret(*args, **kwargs)
        return True

    def rz(self, *args, **kwargs) -> bool:
        if flags.Z:
            return self.ret(*args, **kwargs)
        return True

    def rnz(self, *args, **kwargs) -> bool:
        if not flags.Z:
            return self.ret(*args, **kwargs)
        return True

    def rp(self, *args, **kwargs) -> bool:
        if not flags.S:
            return self.ret(*args, **kwargs)
        return True

    def rm(self, *args, **kwargs) -> bool:
        if flags.S:
            return self.ret(*args, **kwargs)
        return True

    def rpe(self, *args, **kwargs) -> bool:
        if flags.P:
            return self.ret(*args, **kwargs)
        return True

    def rpo(self, *args, **kwargs) -> bool:
        if not flags.P:
            return self.ret(*args, **kwargs)
        return True

    def pchl(self, *args, **kwargs) -> bool:
        bounce_to_address = kwargs.get("bounce_to_address")
        if bounce_to_address:
            return bounce_to_address(self.op.register_pair_read("H"))
        return True

    def sphl(self) -> bool:
        data = self.op.register_pair_read("H")
        self.op.memory_write("SP", data)
        return True

    def xthl(self) -> bool:
        sp_addr = int(str(self.op.super_memory.SP), 16)
        low_addr = format(sp_addr + 1, "#06x")
        high_addr = format(sp_addr + 2, "#06x")

        low = self.op.memory_read(low_addr)
        high = self.op.memory_read(high_addr)

        h = self.op.memory_read("H")
        l = self.op.memory_read("L")

        self.op.memory_write("H", high)
        self.op.memory_write("L", low)
        self.op.memory_write(high_addr, h)
        self.op.memory_write(low_addr, l)
        return True

    def nop(self) -> bool:
        return True

    def di(self) -> bool:
        return True

    def ei(self) -> bool:
        return True

    def in_(self, port: str) -> bool:
        self.op.memory_write("A", "0x00")
        return True

    def out(self, port: str) -> bool:
        return True

    def rim(self) -> bool:
        return True

    def sim(self) -> bool:
        return True

    def rst(self, num: str, *args, **kwargs) -> bool:
        bounce_to_address = kwargs.get("bounce_to_address")
        push_return_address = kwargs.get("push_return_address")
        if push_return_address:
            push_return_address()
        if bounce_to_address:
            address = format(int(str(num), 16) * 8, "#06x")
            return bounce_to_address(address)
        return True

    def cmp(self, addr) -> bool:
        """
        CoMPareAccumulator
        CMP is same as SUB except it doesn't save the result!

        CMP R; R = A, B, C, D, E, H, L, or M

        A < R --> `CY` is set; `Z is reset
        A = R --> `CY` is reset; `Z` is set
        A > R --> `CY` and `Z` are reset

        ** Check the condition of other flags in this instruction **

        Parameters
        ----------
        addr : `str`
            Address
        """
        data_1 = self.op.memory_read("A")
        data_2 = self.op.memory_read(addr)
        self._check_flags_and_compute(data_1, data_2, add=False)
        return True

    def push(self, addr: str) -> bool:
        """
        PUSH rp
        rp = BC, DE, HL, or PSW

        Pushs the register pair into the stack.

        Parameters
        ----------
        addr : `str`
            Address
        """
        addr = addr.upper()
        if addr == "PSW":
            data_1 = construct_hex(str(self.op.memory_read("A")), self.op.flags.PSW)
        else:
            data_1 = self.op.register_pair_read(addr)
        return self.op.super_memory.SP.write(data_1)

    def pop(self, addr: str) -> bool:
        """
        POP rp
        rp = BC, DE, HL, or PSW

        Pushs a register pair from the stack and store it in `addr`

        Parameters
        ----------
        addr : `str`
            Address
        """
        addr = addr.upper()
        data_1 = self.op.super_memory.SP.read()
        if addr == "PSW":
            acc, psw = decompose_byte(str(data_1))
            self.op.memory_write("A", acc)
            self.op.flags.PSW = psw
            return True
        return self.op.register_pair_write(addr, data_1)

    def hlt(self) -> bool:
        raise StopIteration

    pass
