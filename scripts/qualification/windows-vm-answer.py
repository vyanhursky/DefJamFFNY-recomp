"""Make private unattended media for a fresh, owned Hyper-V qualification guest.

Run only on Windows, after restricting the private root's ACL. Requires the
checksum-verified pure-Python pycdlib wheel on PYTHONPATH. This creates files;
it never opens, partitions or formats any host disk. Windows Setup partitions
Disk 0 *inside* the new VM. Never attach this answer ISO to an existing machine.
Credentials stay in the private root; the host copy uses current-user DPAPI.
"""
import argparse
import base64
import ctypes
from ctypes import wintypes
import io
import json
from pathlib import Path
import secrets
import xml.etree.ElementTree as ET


def protected(value, decrypt=False):
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    raw = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(raw, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    dll = ctypes.WinDLL('crypt32', use_last_error=True)
    function = dll.CryptUnprotectData if decrypt else dll.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.memset(output.data, 0, output.size)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        kernel.LocalFree(output.data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--os', choices=('win11', 'win10'), required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    folder = root / 'secrets'
    folder.mkdir(exist_ok=True)
    secret_file = folder / 'guests.json'
    if secret_file.exists():
        credentials = json.loads(secret_file.read_text(encoding='utf-8'))
    else:
        credentials = {'admin_name': 'DJQualAdmin', 'user_name': 'DJQualUser'}
        for role in ('admin', 'user'):
            password = ('Dj9!' + secrets.token_urlsafe(27)).encode()
            credentials[role + '_dpapi'] = base64.b64encode(protected(password)).decode()
        secret_file.write_text(json.dumps(credentials), encoding='utf-8')
    passwords = {role: protected(base64.b64decode(credentials[role + '_dpapi']), True).decode()
                 for role in ('admin', 'user')}
    ns = 'urn:schemas-microsoft-com:unattend'
    ET.register_namespace('', ns)
    ET.register_namespace('wcm', 'http://schemas.microsoft.com/WMIConfig/2002/State')
    def add(parent, tag, text=None, **attributes):
        item = ET.SubElement(parent, '{' + ns + '}' + tag, attributes)
        if text is not None:
            item.text = str(text)
        return item
    answer = ET.Element('{' + ns + '}unattend')
    def component(settings, name):
        return add(settings, 'component', name=name, processorArchitecture='amd64',
                   publicKeyToken='31bf3856ad364e35', language='neutral', versionScope='nonSxS')
    def listed(parent, name):
        return add(parent, name, **{'{http://schemas.microsoft.com/WMIConfig/2002/State}action': 'add'})
    pe = add(answer, 'settings', **{'pass': 'windowsPE'})
    intl = component(pe, 'Microsoft-Windows-International-Core-WinPE')
    add(add(intl, 'SetupUILanguage'), 'UILanguage', 'en-US')
    for name in ('InputLocale', 'SystemLocale', 'UILanguage', 'UserLocale'):
        add(intl, name, 'en-US')
    setup = component(pe, 'Microsoft-Windows-Setup')
    disks = add(setup, 'DiskConfiguration')
    disk = listed(disks, 'Disk')
    add(disk, 'DiskID', 0)
    add(disk, 'WillWipeDisk', 'true')
    creates = add(disk, 'CreatePartitions')
    for order, kind, size in ((1, 'EFI', 260), (2, 'MSR', 16), (3, 'Primary', None)):
        part = listed(creates, 'CreatePartition')
        add(part, 'Order', order)
        add(part, 'Type', kind)
        add(part, 'Size' if size else 'Extend', size or 'true')
    modifies = add(disk, 'ModifyPartitions')
    for order, number, fmt in ((1, 1, 'FAT32'), (2, 3, 'NTFS')):
        part = listed(modifies, 'ModifyPartition')
        add(part, 'Order', order)
        add(part, 'PartitionID', number)
        add(part, 'Format', fmt)
        if number == 3:
            add(part, 'Letter', 'C')
            add(part, 'Label', 'Windows')
    add(disks, 'WillShowUI', 'OnError')
    image = add(add(setup, 'ImageInstall'), 'OSImage')
    metadata = listed(add(image, 'InstallFrom'), 'MetaData')
    add(metadata, 'Key', '/IMAGE/INDEX')
    add(metadata, 'Value', 1)
    target = add(image, 'InstallTo')
    add(target, 'DiskID', 0)
    add(target, 'PartitionID', 3)
    add(image, 'WillShowUI', 'OnError')
    add(add(setup, 'UserData'), 'AcceptEula', 'true')
    specialize = add(answer, 'settings', **{'pass': 'specialize'})
    shell = component(specialize, 'Microsoft-Windows-Shell-Setup')
    add(shell, 'ComputerName', 'DJQUAL-' + args.os.upper())
    add(shell, 'TimeZone', 'UTC')
    oobe = add(answer, 'settings', **{'pass': 'oobeSystem'})
    shell = component(oobe, 'Microsoft-Windows-Shell-Setup')
    options = add(shell, 'OOBE')
    add(options, 'HideEULAPage', 'true')
    add(options, 'HideOnlineAccountScreens', 'true')
    add(options, 'ProtectYourPC', 3)
    accounts = add(add(shell, 'UserAccounts'), 'LocalAccounts')
    for role, group in (('admin', 'Administrators'), ('user', 'Users')):
        account = listed(accounts, 'LocalAccount')
        add(account, 'Name', credentials[role + '_name'])
        add(account, 'Group', group)
        password = add(account, 'Password')
        add(password, 'Value', passwords[role])
        add(password, 'PlainText', 'true')
    autologon = add(shell, 'AutoLogon')
    add(autologon, 'Username', credentials['user_name'])
    add(autologon, 'Enabled', 'true')
    add(autologon, 'LogonCount', 2)
    password = add(autologon, 'Password')
    add(password, 'Value', passwords['user'])
    add(password, 'PlainText', 'true')
    xml = ET.tostring(answer, encoding='utf-8', xml_declaration=True)
    ET.fromstring(xml)
    import pycdlib
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, joliet=3, vol_ident='DJQUAL_ANSWER')
    iso.add_fp(io.BytesIO(xml), len(xml), iso_path='/AUTOUNATTEND.XML;1', joliet_path='/Autounattend.xml')
    destination = folder / (args.os + '-answer.iso')
    iso.write(str(destination))
    iso.close()
    print('Created private answer ISO:', destination)


if __name__ == '__main__':
    main()
