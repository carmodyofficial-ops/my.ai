# COBOL (Legacy Maintenance)

Business-oriented, English-like, still running core banking/insurance/government batch on IBM mainframes (z/OS). Verbose, fixed decimal arithmetic (exact money), record-oriented file I/O. You will mostly **maintain**, not greenfield.

## Program structure — four divisions (in order)
1. **IDENTIFICATION DIVISION** — `PROGRAM-ID.` and metadata.
2. **ENVIRONMENT DIVISION** — machine/file links: `CONFIGURATION SECTION`, `INPUT-OUTPUT SECTION` -> `FILE-CONTROL` (`SELECT ... ASSIGN TO ...`, `ORGANIZATION`, `ACCESS MODE`).
3. **DATA DIVISION** — all data declared up front: `FILE SECTION` (`FD` file + record layouts), `WORKING-STORAGE SECTION` (persistent vars), `LOCAL-STORAGE` (re-init per call), `LINKAGE SECTION` (params passed in).
4. **PROCEDURE DIVISION** — the executable logic, organized into paragraphs/sections.

## Data: level numbers, PICTURE, USAGE
- **Level numbers** build hierarchy: `01` = record/group, `02`–`49` = subordinate fields, `77` = standalone, `88` = condition-name (boolean alias).
```cobol
01  CUSTOMER-REC.
    05  CUST-ID        PIC 9(6).
    05  CUST-NAME      PIC X(30).
    05  CUST-BALANCE   PIC S9(7)V99 COMP-3.
    05  CUST-STATUS    PIC X.
        88  IS-ACTIVE  VALUE 'A'.
```
- **PICTURE (PIC)** clauses: `9`=digit, `X`=any char, `A`=alpha, `S`=sign, `V`=**implied** decimal point (no stored byte), `P`=scaling. Repeat count `9(5)` = `99999`. Edit chars for display: `Z` zero-suppress, `,` `.` `$` `-` `CR` `B` `/`.
- **USAGE**: `DISPLAY` (default, 1 byte/char, printable), `COMP`/`BINARY` (binary int), `COMP-3`/`PACKED-DECIMAL` (packed BCD: 2 digits/byte + sign nibble — compact, exact, dominant for money), `COMP-1`/`COMP-2` (float, rare).
- `REDEFINES` = overlay same storage with another layout (union). `OCCURS n TIMES` = array/table (1-indexed; `OCCURS DEPENDING ON` = variable). `88` levels give readable conditions: `IF IS-ACTIVE`.

## Fixed-format source columns (traditional)
- **1–6** sequence numbers (ignored). **7** indicator: `*`=comment, `-`=continuation, `D`=debug, `/`=page eject. **8–11** Area A (division/section/paragraph names, `01`/`77` levels). **12–72** Area B (statements). **73–80** ignored (old card ID). Modern compilers also allow **free format**.

## PROCEDURE DIVISION verbs & flow
- `MOVE a TO b` (assign, with type conversion/truncation); `COMPUTE x = a * b + c` (arithmetic incl. `ROUNDED`, `ON SIZE ERROR`); `ADD`/`SUBTRACT`/`MULTIPLY`/`DIVIDE ... GIVING`.
- `IF ... THEN ... ELSE ... END-IF`; `EVALUATE` (case/decision table) `WHEN`; scope terminators `END-IF`/`END-PERFORM`/`END-READ` (prefer over the old period-terminated form).
- **PERFORM** = subroutine call to a paragraph: `PERFORM PARA-A`, `PERFORM PARA-A THRU PARA-Z`, `PERFORM ... N TIMES`, `PERFORM ... UNTIL cond` (test before), `PERFORM VARYING I FROM 1 BY 1 UNTIL I > 10` (loop). Inline `PERFORM ... END-PERFORM`.
- Paragraphs are labeled blocks; fall-through execution unless PERFORMed. `CALL 'SUBPROG' USING X Y` invokes another program (params via LINKAGE). `GOBACK`/`STOP RUN`/`EXIT PROGRAM`.
- `STRING`/`UNSTRING`/`INSPECT` for text; `ACCEPT`/`DISPLAY` for simple I/O.

## File handling
- Record-oriented. `ORGANIZATION IS SEQUENTIAL | INDEXED | RELATIVE`; `ACCESS MODE SEQUENTIAL | RANDOM | DYNAMIC`; `RECORD KEY` for **VSAM** indexed (KSDS) files. Verbs: `OPEN INPUT|OUTPUT|I-O|EXTEND`, `READ ... AT END | INTO`, `WRITE`, `REWRITE`, `DELETE`, `START`, `CLOSE`. Check **FILE STATUS** two-byte code after each op (`00`=ok, `10`=EOF, `23`=not found, `35`=missing).

## COPYBOOKs
- `COPY MYLAYOUT.` textually includes a shared source member (record layouts, constants) at compile time — the analog of headers; ensures the same DATA layout across programs. `COPY ... REPLACING ==a== BY ==b==` for parameterized inclusion.

## Condition names (88) & typical batch shape
- `88`-levels turn value tests into readable booleans and can `SET IS-ACTIVE TO TRUE` (assigns the first VALUE). Group them for status flags and menu/table-driven logic.
- Canonical batch program: `OPEN` files -> priming `READ` -> `PERFORM PROCESS-RECORD UNTIL EOF` (each iteration processes then `READ ... AT END SET EOF`) -> `CLOSE`. Accumulate totals in WORKING-STORAGE; write a report.
- Reference-modification substrings: `FIELD(3:4)` = 4 chars starting at position 3. `INSPECT ... TALLYING/REPLACING` counts/edits characters.

## Structured constructs & literals
- Figurative constants: `ZERO`/`ZEROES`, `SPACE`/`SPACES`, `HIGH-VALUES`/`LOW-VALUES` (x'FF'/x'00'), `QUOTES`, `NULL`. Continue with `-` in col 7 or use `&` (free format).
- `EVALUATE TRUE WHEN cond-1 ... WHEN OTHER` is the idiomatic multi-branch (decision table). `NEXT SENTENCE`/`CONTINUE` = no-op. `SET`/`SEARCH`/`SEARCH ALL` (binary search on `OCCURS ... INDEXED BY`).

## Mainframe context
- Runs under **JCL** (Job Control Language) which allocates datasets (`//DD` statements) and executes the load module as batch steps; online via **CICS** (transactions) or with **DB2** (embedded `EXEC SQL ... END-EXEC`, precompiled). Datasets are cataloged, record-format `FB`/`VB`. EBCDIC charset (not ASCII).

## Modernization / interop
- Compilers: IBM Enterprise COBOL, Micro Focus, **GnuCOBOL** (open source, compiles to C). Interop via CALL to C/Java, web-enable via CICS web services, or lift-and-shift to Linux/x86 with GnuCOBOL/Micro Focus. Data must cross EBCDIC↔ASCII and COMP-3↔binary boundaries carefully.

## Gotchas -> Fix
- **Numeric truncation on MOVE/arithmetic**: target PIC too small silently drops high-order digits or decimals -> size receiving fields correctly, use `COMPUTE ... ON SIZE ERROR`, `ROUNDED`; watch `V` scaling.
- **Money as float**: never use COMP-1/2 for currency -> use `COMP-3`/`PACKED-DECIMAL` with explicit `V99` for exact decimal.
- **Fixed record layouts are brittle**: changing a field's PIC shifts every downstream byte offset and breaks COPYBOOK consumers, files, and CICS maps -> change the copybook and recompile **all** users; add `FILLER`; never reuse REDEFINES carelessly.
- **REDEFINES misread**: overlaying incompatible USAGE (DISPLAY over COMP-3) yields garbage -> match storage format.
- **GOTO spaghetti / `PERFORM THRU`**: uncontrolled `GO TO` and fall-through across paragraphs make flow untraceable -> prefer structured `PERFORM`/`EVALUATE`; keep `EXIT` paragraphs as PERFORM targets.
- **Missing scope terminators**: a stray/misplaced period ends an `IF` early, so following statements always execute -> use explicit `END-IF`/`END-PERFORM`, not periods, inside logic.
- **Uninitialized WORKING-STORAGE**: no default zeroing across some calls -> `INITIALIZE` or `VALUE` clauses; beware `LOCAL-STORAGE` vs `WORKING-STORAGE` persistence.
- **Ignoring FILE STATUS**: unchecked I/O errors corrupt runs silently -> test status code after every file op; handle `AT END`.
- **EBCDIC vs ASCII / packed data on migration**: byte-level charset and COMP-3 differences corrupt data -> convert with proper codepage tools, not naive text transfer.
- **Column-sensitive fixed format**: code starting in the wrong area (A vs B) or past col 72 is dropped/errors -> respect margins or switch to free format.
- **Signed vs unsigned PIC 9**: `S` needed to keep sign; without it negatives are lost -> declare `S9(n)`.
- **OCCURS index out of range** (no bounds check unless `SSRANGE`) -> validate subscripts; compile with `SSRANGE` in test.
