#!/usr/bin/env python3
"""Lấy blob giải mã FBE từ vendor stock vào recovery ramdisk của tree.

Dùng:  python3 tools/collect_fbe_blobs.py <vendor_dir> [<system_dir>]
  vendor_dir: thư mục đã giải nén/mount của vendor.img (có etc/init, bin, lib)
  system_dir: (tuỳ chọn) system.img, để tìm rc/service nằm ở system

Kết quả (trong recovery/root):
  system/bin/<service>, system/lib[64]/*.so (lib phụ thuộc lấy từ vendor),
  vendor/etc/vintf/manifest.xml (chỉ các <hal> keymaster/gatekeeper/weaver),
  init.recovery.fbe.rc (service + trigger khởi động)
"""
import os, re, shutil, subprocess, sys
import xml.etree.ElementTree as ET

PAT = re.compile(r'keymaster|gatekeeper|qseecom|weaver', re.I)
EXTRA_LIB = re.compile(r'QSEEComAPI|keymaster|gatekeeper|weaver|qseecom', re.I)

if len(sys.argv) < 2:
    sys.exit(__doc__)
vendor = os.path.abspath(sys.argv[1])
system = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
tree = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
root = os.path.join(tree, 'recovery', 'root')
warn = []

def readelf(args, path):
    return subprocess.run(['readelf'] + args + [path], capture_output=True, text=True).stdout

def elf_class(path):
    out = readelf(['-h'], path)
    return 'lib64' if 'ELF64' in out else 'lib'

def needed(path):
    return re.findall(r'\(NEEDED\).*\[(.+?)\]', readelf(['-d'], path))

def find_in(base, libdir, name):
    for sub in ('', 'hw', 'egl'):
        p = os.path.join(base, libdir, sub, name)
        if os.path.isfile(p):
            return p
    return None

def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    os.chmod(dst, 0o755)

copied_libs = set()
def add_lib(path_or_name, cls):
    queue = [path_or_name]
    while queue:
        item = queue.pop()
        src = item if os.path.isabs(item) else find_in(vendor, cls, item)
        name = os.path.basename(item)
        if src is None:
            if system and find_in(system, cls, name):
                continue  # dùng bản có sẵn của TWRP/system
            if (cls, name) not in copied_libs:
                warn.append(f'thiếu lib {cls}/{name} (không có trong vendor)')
                copied_libs.add((cls, name))
            continue
        if (cls, name) in copied_libs:
            continue
        copied_libs.add((cls, name))
        copy(src, os.path.join(root, 'system', cls, name))
        queue += needed(src)

# 1) tìm service trong các file .rc
rc_dirs = [os.path.join(vendor, 'etc', 'init')]
if system:
    rc_dirs.append(os.path.join(system, 'etc', 'init'))
services = {}
for d in rc_dirs:
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.rc'):
            continue
        for line in open(os.path.join(d, fn), errors='ignore'):
            m = re.match(r'\s*service\s+(\S+)\s+(\S+)(.*)', line)
            if m and (PAT.search(m.group(1)) or PAT.search(m.group(2))):
                name, path, args = m.groups()
                if 'keystore' in name.lower() and not PAT.search(path):
                    continue
                services[name] = (path, args.strip(), fn)

if not services:
    sys.exit('Không tìm thấy service keymaster/gatekeeper/qseecomd trong rc. Kiểm tra lại vendor_dir.')

# 2) copy binary + thư viện
rc_out = ['# Sinh bởi tools/collect_fbe_blobs.py -- đừng sửa tay, chạy lại script.', '']
chmods = []
hal_names = []
for name, (path, args, fn) in services.items():
    base = os.path.basename(path)
    src = None
    for b in (vendor, system):
        if b and os.path.isfile(os.path.join(b, path.lstrip('/').split('/', 1)[1] if path.startswith(('/vendor/', '/system/')) else path.lstrip('/'))):
            src = os.path.join(b, path.lstrip('/').split('/', 1)[1])
            break
    if not src:
        warn.append(f'service {name}: không thấy binary {path}')
        continue
    copy(src, os.path.join(root, 'system', 'bin', base))
    chmods.append(f'    chmod 0755 /system/bin/{base}')
    cls = elf_class(src)
    for n in needed(src):
        add_lib(n, cls)
    rc_out += [f'service {name} /system/bin/{base} {args}'.rstrip(),
               '    user root', '    group root', '    disabled',
               '    seclabel u:r:recovery:s0', '']
    (hal_names if '@' in base else []).append(name)
    print(f'[+] {name:45s} <- {path}  ({fn}, {cls})')

# thư viện bổ sung bị dlopen (không nằm trong NEEDED)
for cls in ('lib', 'lib64'):
    for sub in ('', 'hw'):
        d = os.path.join(vendor, cls, sub)
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith('.so') and EXTRA_LIB.search(f):
                    add_lib(os.path.join(d, f), cls)

# 3) trigger khởi động
rc_out += ['on fs'] + chmods + ['    chmod 0660 /dev/qseecom', '    chown root root /dev/qseecom', '', 'on boot', '    start qseecomd', '']
if hal_names:
    rc_out += ['on property:hwservicemanager.ready=true'] + [f'    start {n}' for n in hal_names] + ['']
open(os.path.join(root, 'init.recovery.fbe.rc'), 'w').write('\n'.join(rc_out))

# 4) vintf: chỉ giữ <hal> liên quan FBE
hals = []
cands = [os.path.join(vendor, 'etc', 'vintf', 'manifest.xml')]
fd = os.path.join(vendor, 'etc', 'vintf', 'manifest')
if os.path.isdir(fd):
    cands += [os.path.join(fd, f) for f in sorted(os.listdir(fd)) if f.endswith('.xml')]
for c in cands:
    if os.path.isfile(c):
        try:
            for h in ET.parse(c).getroot().iter('hal'):
                if PAT.search(h.findtext('name') or ''):
                    hals.append(h)
        except ET.ParseError as e:
            warn.append(f'bỏ qua {c}: {e}')
if hals:
    m = ET.Element('manifest', version='1.0', type='device')
    m.extend(hals)
    out = os.path.join(root, 'vendor', 'etc', 'vintf', 'manifest.xml')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ET.ElementTree(m).write(out, encoding='utf-8', xml_declaration=True)
    print(f'[+] vintf: {len(hals)} <hal>')
else:
    warn.append('không tìm thấy <hal> keymaster/gatekeeper trong vintf của vendor')

print(f'\nĐã copy {len(copied_libs)} thư viện.')
for w in warn:
    print('CẢNH BÁO:', w)
