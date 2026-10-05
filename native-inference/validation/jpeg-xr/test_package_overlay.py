import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import struct
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

spec=importlib.util.spec_from_file_location('overlay_packager',Path(__file__).with_name('package-overlay.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


def macho(dependencies=None, identity='/Users/build/libjxrjava.dylib', cpu=0x0100000c, rpath=None):
    commands=[]
    for kind, name in [(0xd,identity)]+[(0xc,x) for x in (dependencies if dependencies is not None else sorted(p.SYSTEM_LIBRARIES))]:
        b=name.encode()+b'\0';size=(24+len(b)+7)//8*8
        commands.append(struct.pack('<6I',kind,size,24,0,0,0)+b+b'\0'*(size-24-len(b)))
    if rpath:
        b=rpath.encode()+b'\0';size=(12+len(b)+7)//8*8
        commands.append(struct.pack('<3I',0x8000001c,size,12)+b+b'\0'*(size-12-len(b)))
    return struct.pack('<8I',0xfeedfacf,cpu,0,6,len(commands),sum(map(len,commands)),0,0)+b''.join(commands)


class PackagingTests(unittest.TestCase):
    def test_build_install_id_is_not_a_dependency(self):
        result=p.audit_macho(macho())
        self.assertEqual(result['install_id'],'/Users/build/libjxrjava.dylib')
        self.assertEqual(set(result['runtime_dependencies']),p.SYSTEM_LIBRARIES)
    def test_non_system_dependency_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'runtime dependency'):
            p.audit_macho(macho(['/opt/homebrew/lib/libunexpected.dylib']))
    def test_custom_rpath_rejected(self):
        with self.assertRaisesRegex(ValueError,'runtime dependency'):
            p.audit_macho(macho(rpath='/Users/build'))
    def test_x86_64_rejected(self):
        with self.assertRaisesRegex(ValueError,'arm64'):
            p.audit_macho(macho(cpu=0x01000007))
    def test_truncated_commands_rejected(self):
        with self.assertRaises(ValueError):p.audit_macho(macho()[:-2])
    def test_unsafe_paths_rejected(self):
        for name in ['../out','/out','a/../../b','C:/bad','a\\bad','a//b','a/./b','']:
            with self.subTest(name=name),self.assertRaises(ValueError):p.safe_name(name)
    def test_resource_only_deterministic_archive(self):
        entries={p.RESOURCE:b'fixture-not-executed','META-INF/notice.txt':b'notice'}
        first=p.zip_bytes(entries);self.assertEqual(first,p.zip_bytes(dict(reversed(list(entries.items())))))
        with zipfile.ZipFile(io.BytesIO(first)) as z:
            self.assertIn(p.RESOURCE,z.namelist());self.assertFalse(any(x.endswith('.class') for x in z.namelist()))
    def test_license_assets_cover_gpl_and_bsd_and_both_swig_sources(self):
        assets=p.legal_assets()
        self.assertIn('LICENSES/GPL-2.0.txt',assets)
        self.assertIn(b'either version 2',assets['LICENSES/GLENCOE-WRAPPER-HEADER.txt'])
        self.assertIn(b'Redistribution and use',assets['LICENSES/MICROSOFT-CODEC-HEADER.txt'])
        self.assertIn('LICENSES/SWIG-4.5.0-COPYRIGHT',assets)
    def test_tampered_license_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'assets';shutil.copytree(p.ASSETS,root)
            (root/'LICENSES/GPL-2.0.txt').write_text('missing')
            with mock.patch.object(p,'ASSETS',root),self.assertRaisesRegex(ValueError,'checksum'):
                p.legal_assets()
    def test_failed_or_wrong_platform_reports_rejected(self):
        report={'mode':'native','target':'osx_arm64','status':'pass','upstream_commit':p.check.COMMIT,'fixtures':13,
          'published_jni_signatures_matched':59,'exact_linux_reference':True,
          'artifacts':{n:{'url':v[0],'sha256':v[1]}for n,v in p.check.ARTIFACTS.items()}}
        p.verify_pass(report)
        for key,value in [('status','failed'),('target','linux_64'),('fixtures',12),('published_jni_signatures_matched',58)]:
            bad=dict(report);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):p.verify_pass(bad)
    def source_fixture(self,root):
        source=root/'source';source.mkdir()
        files={'Makefile':b'swig:\n\ttrue\n','cpp/lib.cpp':b'unchanged source','java/JXR.i':b'interface',
               'fixtures/image.jxr':b'not redistributed','bin/tool.exe':b'not redistributed'}
        archive=root/'upstream.tar.gz'
        with tarfile.open(archive,'w:gz') as t:
            for name,data in files.items():
                entry=tarfile.TarInfo('jxrlib-'+p.check.COMMIT+'/'+name);entry.size=len(data);t.addfile(entry,io.BytesIO(data))
                target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        for name,data in [('gat-compat.h',p.COMPAT),('gat-legacy-swig/std_vector.i',b'pinned'),
                          ('java/target/swig/JXR_wrap.cxx',b'generated'),('java/target/swig/ome/jxrlib/JXRJNI.java',b'generated')]:
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        patches={'jxrlib-v0.2.4.tar.gz':('unused',p.check.sha256(archive)),
                 'swig-3.0.10-std_vector.i':('unused',hashlib.sha256(b'pinned').hexdigest())}
        return source,archive,patches
    def test_complete_build_inputs_and_no_fixture_redistribution(self):
        with tempfile.TemporaryDirectory() as td:
            source,archive,patches=self.source_fixture(Path(td))
            with mock.patch.dict(p.check.ARTIFACTS,patches):
                data=p.corresponding_source(archive,source,p.legal_assets())
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for name in ['jxrlib/Makefile','jxrlib/cpp/lib.cpp','jxrlib/java/JXR.i','jxrlib/java/target/swig/JXR_wrap.cxx','jxrlib/gat-compat.h','jxrlib/gat-legacy-swig/std_vector.i','rebuild.sh','LICENSES/GPL-2.0.txt']:
                    self.assertIn(name,z.namelist())
                self.assertFalse(any('/fixtures/' in n or '/bin/' in n for n in z.namelist()))
    def test_changed_upstream_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source,archive,patches=self.source_fixture(Path(td));(source/'cpp/lib.cpp').write_text('changed function')
            with mock.patch.dict(p.check.ARTIFACTS,patches),self.assertRaisesRegex(ValueError,'source changed'):
                p.corresponding_source(archive,source,{})
    def test_missing_generated_wrapper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source,archive,patches=self.source_fixture(Path(td));(source/'java/target/swig/JXR_wrap.cxx').unlink()
            with mock.patch.dict(p.check.ARTIFACTS,patches),self.assertRaisesRegex(ValueError,'Generated JNI'):
                p.corresponding_source(archive,source,{})
    def test_symlink_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'actual').write_bytes(b'x');(root/'link').symlink_to(root/'actual')
            with self.assertRaisesRegex(ValueError,'symlink'):p.local_file(root,'link')

if __name__=='__main__':unittest.main()
