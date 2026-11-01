# RV32 Zbb 1.0 specification excerpt

Source: _The RISC-V Instruction Set Manual, Volume I: Unprivileged ISA_,
release 20250508, section 29.4.2 (Zbb: Basic bit-manipulation) and the
section 29.5 pages of the 18 RV32 Zbb instructions. Copied from
`/opt/riscv-docs/riscv-isa-unprivileged.html` in the demo's pinned Sandbox
image, SHA-256
`3cd7425244ec9c23822d81cc740ea649395c148d06bf57bb9c09b7855cbfaa44`.
The manual is licensed CC-BY-4.0 by RISC-V International. The text is
unchanged; the encoding diagrams are transcribed into tables. Regenerate with
`python3 -I specs/extract_zbb.py <html> specs/zbb.md <release>`.

Scope for this Project: RV32 only. Rows and encodings marked RV64 (`clzw`,
`ctzw`, `cpopw`, `rolw`, `roriw`, `rorw`, and the RV64 forms of `zext.h`,
`rori` and `rev8`) are out of scope. On RV32, `rori` encodings with
`shamt[5]=1` are reserved.


### 29.4.2. Zbb: Basic bit-manipulation

#### 29.4.2.1. Logical with negate

| RV32 | RV64 | Mnemonic | Instruction |
|---|---|---|---|
| ✓ | ✓ | andn _rd_, _rs1_, _rs2_ | AND with inverted operand |
| ✓ | ✓ | orn _rd_, _rs1_, _rs2_ | OR with inverted operand |
| ✓ | ✓ | xnor _rd_, _rs1_, _rs2_ | Exclusive NOR |

> Implementation Hint The Logical with Negate instructions can be implemented by inverting the _rs2_ inputs to the base-required AND, OR, and XOR logic instructions. In some implementations, the inverter on rs2 used for subtraction can be reused for this purpose.

#### 29.4.2.2. Count leading/trailing zero bits

| RV32 | RV64 | Mnemonic | Instruction |
|---|---|---|---|
| ✓ | ✓ | clz _rd_, _rs_ | Count leading zero bits |
|  | ✓ | clzw _rd_, _rs_ | Count leading zero bits in word |
| ✓ | ✓ | ctz _rd_, _rs_ | Count trailing zero bits |
|  | ✓ | ctzw _rd_, _rs_ | Count trailing zero bits in word |

#### 29.4.2.3. Count population

These instructions count the number of set bits (1-bits). This is also commonly referred to as population count.

| RV32 | RV64 | Mnemonic | Instruction |
|---|---|---|---|
| ✓ | ✓ | cpop _rd_, _rs_ | Count set bits |
|  | ✓ | cpopw _rd_, _rs_ | Count set bits in word |

#### 29.4.2.4. Integer minimum/maximum

The integer minimum/maximum instructions are arithmetic R-type instructions that return the smaller/larger of two operands.

| RV32 | RV64 | Mnemonic | Instruction |
|---|---|---|---|
| ✓ | ✓ | max _rd_, _rs1_, _rs2_ | Maximum |
| ✓ | ✓ | maxu _rd_, _rs1_, _rs2_ | Unsigned maximum |
| ✓ | ✓ | min _rd_, _rs1_, _rs2_ | Minimum |
| ✓ | ✓ | minu _rd_, _rs1_, _rs2_ | Unsigned minimum |

#### 29.4.2.5. Sign extension and zero extension

These instructions perform the sign extension or zero extension of the least significant 8 bits or 16 bits of the source register.

These instructions replace the generalized idioms `slli rd,rs,(XLEN-<size>) + srai` (for sign extension of 8-bit and 16-bit quantities) and `slli + srli` (for zero extension of 16-bit quantities).

| RV32 | RV64 | Mnemonic | Instruction |
|---|---|---|---|
| ✓ | ✓ | sext.b _rd_, _rs_ | Sign-extend byte |
| ✓ | ✓ | sext.h _rd_, _rs_ | Sign-extend halfword |
| ✓ | ✓ | zext.h _rd_, _rs_ | Zero-extend halfword |

#### 29.4.2.6. Bitwise rotation

Bitwise rotation instructions are similar to the shift-logical operations from the base spec. However, where the shift-logical instructions shift in zeros, the rotate instructions shift in the bits that were shifted out of the other side of the value. Such operations are also referred to as ‘circular shifts’.

| RV32 | RV64 | Mnemonic | Instruction |
|---|---|---|---|
| ✓ | ✓ | rol _rd_, _rs1_, _rs2_ | Rotate left (Register) |
|  | ✓ | rolw _rd_, _rs1_, _rs2_ | Rotate Left Word (Register) |
| ✓ | ✓ | ror _rd_, _rs1_, _rs2_ | Rotate right (Register) |
| ✓ | ✓ | rori _rd_, _rs1_, _shamt_ | Rotate right (Immediate) |
|  | ✓ | roriw _rd_, _rs1_, _shamt_ | Rotate right Word (Immediate) |
|  | ✓ | rorw _rd_, _rs1_, _rs2_ | Rotate right Word (Register) |

> Architecture Explanation The rotate instructions were included to replace a common four-instruction sequence to achieve the same effect (neg; sll/srl; srl/sll; or)

#### 29.4.2.7. OR Combine

orc.b sets the bits of each byte in the result _rd_ to all zeros if no bit within the respective byte of _rs_ is set, or to all ones if any bit within the respective byte of _rs_ is set.

One use-case is string-processing functions, such as strlen and strcpy, which can use orc.b to test for the terminating zero byte by counting the set bits in leading non-zero bytes in a word.

| RV32 | RV64 | Mnemonic | Instruction |
|---|---|---|---|
| ✓ | ✓ | orc.b _rd_, _rs_ | Bitwise OR-Combine, byte granule |

#### 29.4.2.8. Byte-reverse

rev8 reverses the byte-ordering of _rs_.

| RV32 | RV64 | Mnemonic | Instruction |
|---|---|---|---|
| ✓ | ✓ | rev8 _rd_, _rs_ | Byte-reverse register |

### 29.5.2. andn

**Synopsis**

AND with inverted operand

**Mnemonic**

andn _rd_, _rs1_, _rs2_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0100000 (ANDN) | rs2 | rs1 | 111 (ANDN) | rd | 0110011 (OP) |

**Description**

This instruction performs the bitwise logical AND operation between _rs1_ and the bitwise inversion of _rs2_.

**Operation**

```
X(rd) = X(rs1) & ~X(rs2);
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |
| Zbkb (Bit-manipulation for Cryptography) | v1.0 | Ratified |

### 29.5.25. orn

**Synopsis**

OR with inverted operand

**Mnemonic**

orn _rd_, _rs1_, _rs2_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0100000 (ORN) | rs2 | rs1 | 110 (ORN) | rd | 0110011 (OP) |

**Description**

This instruction performs the bitwise logical OR operation between _rs1_ and the bitwise inversion of _rs2_.

**Operation**

```
X(rd) = X(rs1) | ~X(rs2);
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |
| Zbkb (Bit-manipulation for Cryptography) | v1.0 | Ratified |

### 29.5.47. xnor

**Synopsis**

Exclusive NOR

**Mnemonic**

xnor _rd_, _rs1_, _rs2_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0100000 (XNOR) | rs2 | rs1 | 100 (XNOR) | rd | 0110011 (OP) |

**Description**

This instruction performs the bit-wise exclusive-NOR operation on _rs1_ and _rs2_.

**Operation**

```
X(rd) = ~(X(rs1) ^ X(rs2));
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | 0.93 | Ratified |
| Zbkb (Bit-manipulation for Cryptography) | v1.0 | Ratified |

### 29.5.14. clz

**Synopsis**

Count leading zero bits

**Mnemonic**

clz _rd_, _rs_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0110000 (CLZ) | 00000 (CLZ) | rs1 | 001 (CLZ) | rd | 0010011 (OP-IMM) |

**Description**

This instruction counts the number of 0’s before the first 1, starting at the most-significant bit (i.e., XLEN-1) and progressing to bit 0. Accordingly, if the input is 0, the output is XLEN, and if the most-significant bit of the input is a 1, the output is 0.

**Operation**

```
val HighestSetBit : forall ('N : Int), 'N >= 0. bits('N) -> int

function HighestSetBit x = {
  foreach (i from (xlen - 1) to 0 by 1 in dec)
    if [x[i]] == 0b1 then return(i) else ();
  return -1;
}

let rs = X(rs);
X[rd] = (xlen - 1) - HighestSetBit(rs);
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |

### 29.5.18. ctz

**Synopsis**

Count trailing zeros

**Mnemonic**

ctz _rd_, _rs_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0110000 (CTZ/CTZW) | 00001 (CTZ/CTZW) | rs1 | 001 (CTZ/CTZW) | rd | 0010011 (OP-IMM) |

**Description**

This instruction counts the number of 0’s before the first 1, starting at the least-significant bit (i.e., 0) and progressing to the most-significant bit (i.e., XLEN-1). Accordingly, if the input is 0, the output is XLEN, and if the least-significant bit of the input is a 1, the output is 0.

**Operation**

```
val LowestSetBit : forall ('N : Int), 'N >= 0. bits('N) -> int

function LowestSetBit x = {
  foreach (i from 0 to (xlen - 1) by 1 in dec)
    if [x[i]] == 0b1 then return(i) else ();
  return xlen;
}

let rs = X(rs);
X[rd] = LowestSetBit(rs);
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |

### 29.5.16. cpop

**Synopsis**

Count set bits

**Mnemonic**

cpop _rd_, _rs_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0110000 (CPOP) | 00010 (CPOP) | rs1 | 001 (CPOP) | rd | 0010011 (OP-IMM) |

**Description**

This instructions counts the number of 1’s (i.e., set bits) in the source register.

**Operation**

```
let bitcount = 0;
let rs = X(rs);

foreach (i from 0 to (xlen - 1) in inc)
    if rs[i] == 0b1 then bitcount = bitcount + 1 else ();

X[rd] = bitcount
```

> Software Hint This operations is known as population count, popcount, sideways sum, bit summation, or Hamming weight. The GCC builtin function `__builtin_popcount (unsigned int x)` is implemented by cpop on RV32 and by cpopw on RV64. The GCC builtin function `__builtin_popcountl (unsigned long x)` for LP64 is implemented by cpop on RV64.

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |

### 29.5.20. max

**Synopsis**

Maximum

**Mnemonic**

max _rd_, _rs1_, _rs2_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0000101 (MINMAX/CLMUL) | rs2 | rs1 | 110 (MAX) | rd | 0110011 (OP) |

**Description**

This instruction returns the larger of two signed integers.

**Operation**

```
let rs1_val = X(rs1);
let rs2_val = X(rs2);

let result = if   rs1_val <_s rs2_val
             then rs2_val
             else rs1_val;

X(rd) = result;
```

> Software Hint Calculating the absolute value of a signed integer can be performed using the following sequence: neg rD,rS followed by max rD,rS,rD. When using this common sequence, it is suggested that they are scheduled with no intervening instructions so that implementations that are so optimized can fuse them together.

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |

### 29.5.21. maxu

**Synopsis**

Unsigned maximum

**Mnemonic**

maxu _rd_, _rs1_, _rs2_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0000101 (MINMAX/CLMUL) | rs2 | rs1 | 111 (MAXU) | rd | 0110011 (OP) |

**Description**

This instruction returns the larger of two unsigned integers.

**Operation**

```
let rs1_val = X(rs1);
let rs2_val = X(rs2);

let result = if   rs1_val <_u rs2_val
             then rs2_val
             else rs1_val;

X(rd) = result;
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |

### 29.5.22. min

**Synopsis**

Minimum

**Mnemonic**

min _rd_, _rs1_, _rs2_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0000101 (MINMAX/CLMUL) | rs2 | rs1 | 100 (MIN) | rd | 0110011 (OP) |

**Description**

This instruction returns the smaller of two signed integers.

**Operation**

```
let rs1_val = X(rs1);
let rs2_val = X(rs2);

let result = if   rs1_val <_s rs2_val
             then rs1_val
             else rs2_val;

X(rd) = result;
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |

### 29.5.23. minu

**Synopsis**

Unsigned minimum

**Mnemonic**

minu _rd_, _rs1_, _rs2_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0000101 (MINMAX/CLMUL) | rs2 | rs1 | 101 (MINU) | rd | 0110011 (OP) |

**Description**

This instruction returns the smaller of two unsigned integers.

**Operation**

```
let rs1_val = X(rs1);
let rs2_val = X(rs2);

let result = if   rs1_val <_u rs2_val
             then rs1_val
             else rs2_val;

X(rd) = result;
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |

### 29.5.37. sext.b

**Synopsis**

Sign-extend byte

**Mnemonic**

sext.b _rd_, _rs_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0110000 | 00100 (SEXT.B) | rs1 | 001 (SEXT.B/SEXT.H) | rd | 0010011 (OP-IMM) |

**Description**

This instruction sign-extends the least-significant byte in the source to XLEN by copying the most-significant bit in the byte (i.e., bit 7) to all of the more-significant bits.

**Operation**

```
X(rd) = EXTS(X(rs)[7..0]);
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | 0.93 | Ratified |

### 29.5.38. sext.h

**Synopsis**

Sign-extend halfword

**Mnemonic**

sext.h _rd_, _rs_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0110000 | 00101 (SEXT.H) | rs1 | 001 (SEXT.B/SEXT.H) | rd | 0010011 (OP-IMM) |

**Description**

This instruction sign-extends the least-significant halfword in _rs_ to XLEN by copying the most-significant bit in the halfword (i.e., bit 15) to all of the more-significant bits.

**Operation**

```
X(rd) = EXTS(X(rs)[15..0]);
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | 0.93 | Ratified |

### 29.5.50. zext.h

**Synopsis**

Zero-extend halfword

**Mnemonic**

zext.h _rd_, _rs_

**Encoding (RV32)**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0000100 | 00000 | rs | 100 (ZEXT.H) | rd | 0110011 (OP) |

**Encoding (RV64)**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0000100 | 00000 | rs | 100 (ZEXT.H) | rd | 0111011 (OP-32) |

**Description**

This instruction zero-extends the least-significant halfword of the source to XLEN by inserting 0’s into all of the bits more significant than 15.

**Operation**

```
X(rd) = EXTZ(X(rs)[15..0]);
```

> Note The zext.h mnemonic corresponds to different instruction encodings in RV32 and RV64.

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | 0.93 | Ratified |

### 29.5.31. rol

**Synopsis**

Rotate Left (Register)

**Mnemonic**

rol _rd_, _rs1_, _rs2_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0110000 (ROL) | rs2 | rs1 | 001 (ROL) | rd | 0110011 (OP) |

**Description**

This instruction performs a rotate left of _rs1_ by the amount in least-significant log2(XLEN) bits of _rs2_.

**Operation**

```
let shamt = if   xlen == 32
            then X(rs2)[4..0]
            else X(rs2)[5..0];
let result = (X(rs1) << shamt) | (X(rs1) >> (xlen - shamt));

X(rd) = result;
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | 0.93 | Ratified |
| Zbkb (Bit-manipulation for Cryptography) | v1.0 | Ratified |

### 29.5.33. ror

**Synopsis**

Rotate Right

**Mnemonic**

ror _rd_, _rs1_, _rs2_

**Encoding**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0110000 (ROR) | rs2 | rs1 | 101 (ROR) | rd | 0110011 (OP) |

**Description**

This instruction performs a rotate right of _rs1_ by the amount in least-significant log2(XLEN) bits of _rs2_.

**Operation**

```
let shamt = if   xlen == 32
            then X(rs2)[4..0]
            else X(rs2)[5..0];
let result = (X(rs1) >> shamt) | (X(rs1) << (xlen - shamt));

X(rd) = result;
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | 0.93 | Ratified |
| Zbkb (Bit-manipulation for Cryptography) | v1.0 | Ratified |

### 29.5.34. rori

**Synopsis**

Rotate Right (Immediate)

**Mnemonic**

rori _rd_, _rs1_, _shamt_

**Encoding (RV32)**

| [31:25] | [24:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 0110000 (RORI) | shamt | rs1 | 101 (RORI) | rd | 0010011 (OP-IMM) |

**Encoding (RV64)**

| [31:26] | [25:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|---|
| 011000 (RORI) | shamt | rs1 | 101 (RORI) | rd | 0010011 (OP-IMM) |

**Description**

This instruction performs a rotate right of _rs1_ by the amount in the least-significant log2(XLEN) bits of _shamt_. For RV32, the encodings corresponding to shamt[5]=1 are reserved.

**Operation**

```
let shamt = if   xlen == 32
            then shamt[4..0]
            else shamt[5..0];
let result = (X(rs1) >> shamt) | (X(rs1) << (xlen - shamt));

X(rd) = result;
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | 0.93 | Ratified |
| Zbkb (Bit-manipulation for Cryptography) | v1.0 | Ratified |

### 29.5.24. orc.b

**Synopsis**

Bitwise OR-Combine, byte granule

**Mnemonic**

orc.b _rd_, _rs_

**Encoding**

| [31:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|
| 001010000111 | rs | 101 | rd | 0010011 (OP-IMM) |

**Description**

Combines the bits within each byte using bitwise logical OR. This sets the bits of each byte in the result _rd_ to all zeros if no bit within the respective byte of _rs_ is set, or to all ones if any bit within the respective byte of _rs_ is set.

**Operation**

```
let input = X(rs);
let output : xlenbits = 0;

foreach (i from 0 to (xlen - 8) by 8) {
   output[(i + 7)..i] = if   input[(i + 7)..i] == 0
                        then 0b00000000
                        else 0b11111111;
}

X[rd] = output;
```

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |

### 29.5.29. rev8

**Synopsis**

Byte-reverse register

**Mnemonic**

rev8 _rd_, _rs_

**Encoding (RV32)**

| [31:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|
| 011010011000 | rs | 101 | rd | 0010011 (OP-IMM) |

**Encoding (RV64)**

| [31:20] | [19:15] | [14:12] | [11:7] | [6:0] |
|---|---|---|---|---|
| 011010111000 | rs | 101 | rd | 0010011 (OP-IMM) |

**Description**

This instruction reverses the order of the bytes in _rs_.

**Operation**

```
let input = X(rs);
let output : xlenbits = 0;
let j = xlen - 1;

foreach (i from 0 to (xlen - 8) by 8) {
   output[i..(i + 7)] = input[(j - 7)..j];
   j = j - 8;
}

X[rd] = output
```

> Note The rev8 mnemonic corresponds to different instruction encodings in RV32 and RV64.

> Software Hint The byte-reverse operation is only available for the full register width. To emulate word-sized and halfword-sized byte-reversal, perform a `rev8 rd,rs` followed by a `srai rd,rd,K`, where K is XLEN-32 and XLEN-16, respectively.

**Included in**

| Extension | Minimum version | Lifecycle state |
|---|---|---|
| Zbb (Basic bit-manipulation) | v1.0 | Ratified |
| Zbkb (Bit-manipulation for Cryptography) | v1.0 | Ratified |
