"""Canonical numeric root archives; never run maintenance scripts or dylibs."""
from pathlib import Path, PurePosixPath
import hashlib,io,os,subprocess,sys,tarfile,tempfile
package=Path(sys.argv[1]).resolve()
def records(path):
    result={}
    for flag in ('--fsys-tarfile','--ctrl-tarfile'):
        raw=subprocess.check_output(['dpkg-deb',flag,str(path)])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            entries={}
            for member in archive:
                name=str(PurePosixPath(member.name))
                if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or not (member.isdir() or member.isfile()):raise ValueError('Unsafe archive entry')
                if name in entries:raise ValueError('Duplicate archive entry')
                digest=hashlib.sha256(archive.extractfile(member).read()).hexdigest() if member.isfile() else None
                entries[name]=(member.isdir(),member.mode,digest)
            result[flag]=entries
    return result
before=records(package)
with tempfile.TemporaryDirectory(prefix='lmb-repack-',dir=package.parent,ignore_cleanup_errors=True) as folder:
    root=Path(folder);stage=root/'stage';rebuilt=root/'rebuilt.deb'
    subprocess.run(['dpkg-deb','--raw-extract',str(package),str(stage)],check=True)
    for flag,entries in before.items():
        target=stage if flag=='--fsys-tarfile' else stage/'DEBIAN'
        for name,(_,mode,_) in entries.items():os.chmod(target/name,mode)
    subprocess.run(['dpkg-deb','--build','--root-owner-group','-Zxz',str(stage),str(rebuilt)],check=True)
    assert records(rebuilt)==before,'Repacking changed bytes/types/modes'
    for flag in before:
        raw=subprocess.check_output(['dpkg-deb',flag,str(rebuilt)])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            for entry in archive:assert entry.uid==0 and entry.gid==0,(entry.name,entry.uid,entry.gid)
    os.replace(rebuilt,package)
print('Payload/control bytes, types and modes unchanged; numeric archive ownership root:root.')
