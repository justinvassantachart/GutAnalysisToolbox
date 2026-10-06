import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
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
    def test_exact_reviewed_swig_versions_accepted(self):
        for version in ('4.5.0','4.5.1'):
            with self.subTest(version=version):
                self.assertEqual(p.parse_swig_version('\nSWIG Version '+version+'\n\nCompiled with clang++\n'),version)

    def test_unknown_swig_versions_rejected(self):
        for version in ('4.4.0','4.5.2','4.5.10','4.5.01','4.50.0','5.0.0'):
            with self.subTest(version=version),self.assertRaisesRegex(ValueError,'matching generator notices'):
                p.parse_swig_version('SWIG Version '+version)

    def test_ambiguous_or_suffixed_swig_versions_rejected(self):
        for log in ('','4.5.1','SWIG Version 4.5.1-dev','SWIG Version 4.5.0.1',
                    'SWIG Version 4.5.1 (modified)','SWIG Version 4.5.0\nSWIG Version 4.5.1',
                    'SWIG Version 4.5.1\nSWIG Version 4.5.1'):
            with self.subTest(log=log),self.assertRaisesRegex(ValueError,'unambiguous'):
                p.parse_swig_version(log)

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
        for version in ('4.5.0','4.5.1'):
            with self.subTest(version=version):
                assets=p.legal_assets(version)
                self.assertIn('LICENSES/GPL-2.0.txt',assets)
                self.assertIn(b'either version 2',assets['LICENSES/GLENCOE-WRAPPER-HEADER.txt'])
                self.assertIn(b'Redistribution and use',assets['LICENSES/MICROSOFT-CODEC-HEADER.txt'])
                for name in ('LICENSE','COPYRIGHT','LICENSE-UNIVERSITIES'):
                    self.assertIn('LICENSES/SWIG-3-'+name,assets)
                    self.assertIn('LICENSES/SWIG-'+version+'-'+name,assets)
                self.assertIn('LICENSES/SWIG-GPL-3.0.txt',assets)

    def test_unreviewed_license_version_rejected(self):
        with self.assertRaisesRegex(ValueError,'matching generator notices'):p.legal_assets('4.5.2')

    def test_missing_generator_notices_rejected_even_if_manifest_omits_them(self):
        required=['LICENSES/SWIG-4.5.1-'+n for n in ('LICENSE','COPYRIGHT','LICENSE-UNIVERSITIES')]
        required+=['LICENSES/SWIG-3-COPYRIGHT','LICENSES/SWIG-3-LICENSE-UNIVERSITIES','LICENSES/SWIG-GPL-3.0.txt']
        for missing in required:
            with self.subTest(missing=missing),tempfile.TemporaryDirectory() as td:
                root=Path(td)/'assets';shutil.copytree(p.ASSETS,root)
                manifest=json.loads((root/'license-manifest.json').read_text())
                manifest['files']=[x for x in manifest['files'] if x['path']!=missing]
                (root/'license-manifest.json').write_text(json.dumps(manifest))
                with mock.patch.object(p,'ASSETS',root),self.assertRaisesRegex(ValueError,'notices are missing'):
                    p.legal_assets('4.5.1')

    def test_reviewed_notice_hash_cannot_be_overridden_by_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'assets';shutil.copytree(p.ASSETS,root)
            path='LICENSES/SWIG-4.5.1-COPYRIGHT';(root/path).write_bytes(b'changed')
            manifest=json.loads((root/'license-manifest.json').read_text())
            for item in manifest['files']:
                if item['path']==path:item['sha256']=p.digest(b'changed')
            (root/'license-manifest.json').write_text(json.dumps(manifest))
            with mock.patch.object(p,'ASSETS',root),self.assertRaisesRegex(ValueError,'Reviewed SWIG notice checksum'):
                p.legal_assets('4.5.1')

    def test_unpinned_generator_notice_provenance_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'assets';shutil.copytree(p.ASSETS,root)
            manifest=json.loads((root/'license-manifest.json').read_text())
            for item in manifest['files']:
                if item['path']=='LICENSES/SWIG-4.5.1-LICENSE':
                    item['source_url']='https://raw.githubusercontent.com/swig/swig/master/LICENSE'
            (root/'license-manifest.json').write_text(json.dumps(manifest))
            with mock.patch.object(p,'ASSETS',root),self.assertRaisesRegex(ValueError,'source provenance'):
                p.legal_assets('4.5.1')

    def test_duplicate_license_records_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'assets';shutil.copytree(p.ASSETS,root)
            manifest=json.loads((root/'license-manifest.json').read_text())
            manifest['files'].append(manifest['files'][0])
            (root/'license-manifest.json').write_text(json.dumps(manifest))
            with mock.patch.object(p,'ASSETS',root),self.assertRaisesRegex(ValueError,'Duplicate license'):
                p.legal_assets('4.5.1')
    def test_tampered_license_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'assets';shutil.copytree(p.ASSETS,root)
            (root/'LICENSES/GPL-2.0.txt').write_text('missing')
            with mock.patch.object(p,'ASSETS',root),self.assertRaisesRegex(ValueError,'checksum'):
                p.legal_assets("4.5.0")
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
                data=p.corresponding_source(archive,source,p.legal_assets("4.5.0"),"4.5.0")
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for name in ['jxrlib/Makefile','jxrlib/cpp/lib.cpp','jxrlib/java/JXR.i','jxrlib/java/target/swig/JXR_wrap.cxx','jxrlib/gat-compat.h','jxrlib/gat-legacy-swig/std_vector.i','rebuild.sh','LICENSES/GPL-2.0.txt']:
                    self.assertIn(name,z.namelist())
                self.assertFalse(any('/fixtures/' in n or '/bin/' in n for n in z.namelist()))

    def test_source_archive_records_exact_generator_and_provenance(self):
        for version in ('4.5.0','4.5.1'):
            with self.subTest(version=version),tempfile.TemporaryDirectory() as td:
                source,archive,patches=self.source_fixture(Path(td))
                with mock.patch.dict(p.check.ARTIFACTS,patches):
                    data=p.corresponding_source(archive,source,p.legal_assets(version),version)
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    self.assertEqual(z.read('SWIG_VERSION'),(version+'\n').encode())
                    self.assertEqual(json.loads(z.read('SOURCE_PROVENANCE.json'))['swig_generator'],p.reviewed_swig_generator(version))
                    self.assertIn('LICENSES/SWIG-'+version+'-COPYRIGHT',z.namelist())
                    self.assertIn(p.digest((version+'\n').encode())+'  SWIG_VERSION',z.read('SHA256SUMS').decode())

    def generated_zip(self,version='4.5.1'):
        return p.zip_bytes({'SWIG_VERSION':(version+'\n').encode(),
                            'jxrlib/java/target/swig/JXR_wrap.cxx':b'generated JNI',
                            'jxrlib/java/target/swig/ome/jxrlib/JXRJNI.java':b'generated Java'})

    def test_regeneration_accepts_only_matching_recorded_swig(self):
        for version in ('4.5.0','4.5.1'):
            with self.subTest(version=version),tempfile.TemporaryDirectory() as td,\
                    mock.patch.object(p.shutil,'which',return_value='/reviewed/swig'),\
                    mock.patch.object(p.subprocess,'check_output',return_value='\nSWIG Version '+version+'\n'),\
                    mock.patch.object(p.check,'run') as run:
                p.verify_generated_sources(self.generated_zip(version),Path(td),version)
                self.assertEqual(run.call_args.args[0][:2],['make','swig'])
                self.assertIn('gat-legacy-swig',run.call_args.args[0][2])
                self.assertFalse((Path(td)/'source-regeneration').exists())

    def test_regeneration_rejects_different_available_swig(self):
        with tempfile.TemporaryDirectory() as td,mock.patch.object(p.shutil,'which',return_value='/reviewed/swig'),\
                mock.patch.object(p.subprocess,'check_output',return_value='SWIG Version 4.5.0'),\
                mock.patch.object(p.check,'run') as run,self.assertRaisesRegex(ValueError,'Matching SWIG 4.5.1'):
            p.verify_generated_sources(self.generated_zip(),Path(td),'4.5.1')
        run.assert_not_called()

    def test_regeneration_rejects_wrong_archive_swig_version(self):
        with tempfile.TemporaryDirectory() as td,mock.patch.object(p.check,'run') as run,\
                self.assertRaisesRegex(ValueError,'source SWIG version mismatch'):
            p.verify_generated_sources(self.generated_zip('4.5.0'),Path(td),'4.5.1')
        run.assert_not_called()

    def test_regeneration_still_rejects_changed_generated_source(self):
        with tempfile.TemporaryDirectory() as td,mock.patch.object(p.shutil,'which',return_value='/reviewed/swig'),\
                mock.patch.object(p.subprocess,'check_output',return_value='SWIG Version 4.5.1'):
            def change_source(*args,**kwargs):
                (Path(td)/'source-regeneration/jxrlib/java/target/swig/JXR_wrap.cxx').write_bytes(b'changed JNI')
            with mock.patch.object(p.check,'run',side_effect=change_source),self.assertRaisesRegex(ValueError,'does not match preferred'):
                p.verify_generated_sources(self.generated_zip(),Path(td),'4.5.1')

    def test_offline_rebuild_exact_version_gate(self):
        # Only shell-gate unit fixtures. Fake platform/build commands never
        # compile code and are not evidence of native macOS validation.
        cases=[('4.5.0','4.5.0',True),('4.5.1','4.5.1',True),
               ('4.5.1','4.5.0',False),('4.5.1','4.5.10',False),
               ('4.5.1','4.5.1-dev',False),('4.5.2','4.5.2',False),
               ('4.5.1','4.5.1\nSWIG Version 4.5.1',False)]
        for recorded,actual,accepted in cases:
            with self.subTest(recorded=recorded,actual=actual),tempfile.TemporaryDirectory() as td:
                root=Path(td);(root/'jxrlib').mkdir();bin_dir=root/'bin';bin_dir.mkdir()
                java=root/'jdk';(java/'include').mkdir(parents=True);(java/'include/jni.h').touch()
                shutil.copyfile(p.ASSETS/'rebuild.sh',root/'rebuild.sh')
                (root/'SWIG_VERSION').write_text(recorded+'\n')
                commands={'uname':'case "$1" in -s) echo Darwin;; -m) echo arm64;; esac',
                          'swig':"printf '%s\\n' 'SWIG Version "+actual+"'",
                          'make':'printf "%s\\n" "$*" >> "$BUILD_CALLS"'}
                commands.update({name:':' for name in ('file','lipo','otool','shasum')})
                for name,body in commands.items():
                    tool=bin_dir/name;tool.write_text('#!/bin/sh\n'+body+'\n');tool.chmod(0o755)
                env=dict(os.environ,PATH=str(bin_dir)+os.pathsep+os.environ['PATH'],JAVA_HOME=str(java),
                         SWIG=str(bin_dir/'swig'),BUILD_CALLS=str(root/'build-calls'))
                result=subprocess.run(['sh',str(root/'rebuild.sh'),'--regenerate'],env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode==0,accepted,result.stdout+result.stderr)
                self.assertEqual((root/'build-calls').exists(),accepted)
    def test_changed_upstream_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source,archive,patches=self.source_fixture(Path(td));(source/'cpp/lib.cpp').write_text('changed function')
            with mock.patch.dict(p.check.ARTIFACTS,patches),self.assertRaisesRegex(ValueError,'source changed'):
                p.corresponding_source(archive,source,{},"4.5.0")
    def test_missing_generated_wrapper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source,archive,patches=self.source_fixture(Path(td));(source/'java/target/swig/JXR_wrap.cxx').unlink()
            with mock.patch.dict(p.check.ARTIFACTS,patches),self.assertRaisesRegex(ValueError,'Generated JNI'):
                p.corresponding_source(archive,source,{},"4.5.0")
    def test_symlink_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'actual').write_bytes(b'x');(root/'link').symlink_to(root/'actual')
            with self.assertRaisesRegex(ValueError,'symlink'):p.local_file(root,'link')

    def test_trusted_root_accepts_ancestor_alias_but_not_internal_links(self):
        # Reproduce macOS /var -> /private/var on Linux without changing /var.
        with tempfile.TemporaryDirectory() as td:
            parent=Path(td)
            real=parent/'private'/'var';real.mkdir(parents=True)
            alias=parent/'var';alias.symlink_to(real,target_is_directory=True)
            actual=real/'fixture';actual.mkdir()
            (actual/'source.c').write_bytes(b'unchanged source')
            trusted=alias/'fixture'
            self.assertEqual(p.local_file(trusted,'source.c'),b'unchanged source')
            inside=actual/'nested';inside.mkdir();(inside/'child.c').write_bytes(b'child')
            (actual/'linked-dir').symlink_to(inside,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):
                p.local_file(trusted,'linked-dir/child.c')
            outside=real/'outside';outside.mkdir();(outside/'secret').write_bytes(b'outside')
            (actual/'escape').symlink_to(outside,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):
                p.local_file(trusted,'escape/secret')
            with self.assertRaisesRegex(ValueError,'Unsafe archive path'):
                p.local_file(trusted,'../outside/secret')

if __name__=='__main__':unittest.main()
