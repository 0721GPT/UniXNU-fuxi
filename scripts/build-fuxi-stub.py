#!/usr/bin/env python3
"""Compile the fuxi bring-up stubs into an archive the kernel link picks up.

UniXNU's XNU patches reference several native symbols unconditionally, so a
reduced defconfig still fails at link. The stub definitions are weak: any real
archive added later wins, and none of the stubbed entry points is reachable
because they sit behind boot arguments the fuxi payload never passes.

The archive is appended to the link through CONFIG_XNU_EXTRA_LD_ARCHIVES, which
build-xnu-4k-baseline.sh appends to KERNEL_EXTRA_ARCHIVES.
"""
import json
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
recipe = ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/bsd_init.o.json'
record = json.loads(recipe.read_text().strip().rstrip(','))

source = ROOT / 'scripts' / 'fuxi-stub.c'
if not source.is_file():
    raise SystemExit('missing %s' % source)

out = ROOT / 'build/fuxi-stub'
out.mkdir(parents=True, exist_ok=True)
destination = out / 'fuxi-stub.o'

command = []
index = 0
arguments = record['arguments']
while index < len(arguments):
    value = arguments[index]
    if value == record['file']:
        command.append(str(source))
    elif value == '-o':
        command.extend(['-o', str(destination)])
        index += 1
    elif value in ('-MF', '-MJ'):
        index += 1
    elif value not in ('-MD', '-MP'):
        command.append(value)
    index += 1

result = subprocess.run(command, cwd=record['directory'], capture_output=True, text=True)
(out / 'fuxi-stub.log').write_text(result.stdout + result.stderr)
if result.returncode:
    raise SystemExit(result.stderr[-4500:])

data = destination.read_bytes()
if struct.unpack_from('<4I', data) != (0xfeedfacf, 0x100000c, 0, 1):
    raise SystemExit('fuxi stubs must be ordinary ARM64 Mach-O objects')

archive = out / 'libFuxiBringUpStub.a'
archive.unlink(missing_ok=True)
subprocess.run(['xcrun', 'ar', 'rcs', archive, destination], check=True)
print('fuxi bring-up stubs archived: %s' % archive.relative_to(ROOT))
