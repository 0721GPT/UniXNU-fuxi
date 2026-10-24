#!/usr/bin/env python3
"""Compile the public IOStorageFamily sources into an archive for the kernel link.

Why: NativeUfs and NativeRamBlock subclass IOBlockStorageDevice, so the kernel link
needs that class implementation. XNU only installs the header
(INSTALLHDR IOBlockStorageDevice.h), and the upstream flow gets the class from the
original kernelcache during prelink. A bring-up kernel built from source needs the
implementation compiled in, which is what this step does.

The compile flags come from the bsd_init.o record of the baseline XNU pass, so the
objects match the rest of the kernel, with -x c++ forced because the sources are C++.
"""
import json
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/bsd/DEVELOPMENT/bsd_init.o.json'
SOURCE = ROOT / 'refer' / 'IOStorageFamily'

# BlockStorageDeviceDriverKit needs DriverKit headers that a kernel build does not
# provide, and IOUserBlockStorageDevice_kext is the user-space bridge. Neither is
# needed for NativeUfs.
SKIP = {'IOUserBlockStorageDevice_kext.cpp'}

record = json.loads(RECORD.read_text().strip().rstrip(','))
out = ROOT / 'build/fuxi-io-storage'
out.mkdir(parents=True, exist_ok=True)

if not SOURCE.is_dir():
    raise SystemExit('missing %s; run "unixnu fetch IOStorageFamily" first' % SOURCE)

sources = sorted(p for p in SOURCE.glob('*.cpp') if p.name not in SKIP)
if not sources:
    raise SystemExit('no IOStorageFamily sources found')

baseline = record['arguments']
objects = []
failures = []

for source in sources:
    destination = out / (source.stem + '.o')
    command = []
    index = 0
    while index < len(baseline):
        value = baseline[index]
        if value == record['file']:
            command.extend(['-x', 'c++', str(source)])
        elif value == '-o':
            command.extend(['-o', str(destination)])
            index += 1
        elif value in ('-MF', '-MJ'):
            index += 1
        elif value not in ('-MD', '-MP'):
            command.append(value)
        index += 1
    command.extend([
        '-I', str(SOURCE),
        # prepare-storage-headers.py stages the public IOKit/storage headers here.
        '-I', str(ROOT / 'build' / 'storage-abi' / 'include'),
        # RootDomain.h reaches for IOPMPrivate.h, a private XNU header that the
        # export pass does not install; the working tree still has it.
        '-I', str(ROOT / '.cache' / 'xnu-work' / 'iokit'),
        '-Wno-everything',
    ])

    result = subprocess.run(command, cwd=record['directory'], capture_output=True, text=True)
    (out / (source.stem + '.log')).write_text(result.stdout + result.stderr)
    if result.returncode:
        failures.append((source.name, (result.stdout + result.stderr)[-1200:]))
        continue

    data = destination.read_bytes()
    if struct.unpack_from('<4I', data) != (0xfeedfacf, 0x100000c, 0, 1):
        failures.append((source.name, 'not an ordinary ARM64 Mach-O object'))
        continue
    objects.append(destination)

for name, message in failures:
    print('FAILED %s' % name)
    print(message)

if failures:
    raise SystemExit('%d of %d IOStorageFamily sources failed' % (len(failures), len(sources)))
if not objects:
    raise SystemExit('no objects produced')

archive = out / 'libFuxiIOStorage.a'
archive.unlink(missing_ok=True)
subprocess.run(['xcrun', 'ar', 'rcs', archive, *objects], check=True)
print('%d IOStorageFamily sources archived: %s' % (len(objects), archive.relative_to(ROOT)))
