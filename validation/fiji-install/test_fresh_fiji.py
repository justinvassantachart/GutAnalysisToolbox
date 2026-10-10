import importlib.util
import io
from unittest.mock import patch
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import stat
import subprocess
import shutil

SPEC = importlib.util.spec_from_file_location('fresh', Path(__file__).with_name('run_fresh_fiji.py'))
fresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fresh)


class ArchiveSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / 'archive.zip'
    def tearDown(self):
        self.temp.cleanup()
    def archive(self, names):
        with zipfile.ZipFile(self.path, 'w') as z:
            for name, content in names:
                z.writestr(name, content)
        return self.path
    def test_ganglia_reflection_against_actual_params_source(self):
        here = Path(__file__).resolve().parent
        java = shutil.which('java')
        javac = shutil.which('javac')
        self.assertIsNotNone(java, 'JDK required for the actual Params reflection contract')
        self.assertIsNotNone(javac, 'JDK required for the actual Params reflection contract')
        classes = self.root / 'actual-params-classes'
        classes.mkdir()
        source = here.parents[1] / 'src/main/java/Features/Core/Params.java'
        self.assertTrue(source.is_file())
        subprocess.run([javac, '--release', '11', '-d', str(classes), str(source),
                        str(here / 'Fresh_Ganglia_Params.java'),
                        str(here / 'Fresh_Ganglia_Evidence.java'),
                        str(here / 'GangliaParamsContractTest.java')],
                       check=True, capture_output=True, text=True, timeout=30)
        result = subprocess.run([java, '-Djava.awt.headless=true', '-cp', str(classes),
                                 'GangliaParamsContractTest'], check=True,
                                capture_output=True, text=True, timeout=30)
        self.assertIn('PASS actual Params', result.stdout)
        # The installed probe must execute the same tested setter helper.
        self.assertIn('Fresh_Ganglia_Params.configure(params)',
                      (here / 'Fresh_Ganglia_Probe.java').read_text())
        self.assertIn("HERE / 'Fresh_Ganglia_Params.java'", (here / 'run_fresh_fiji.py').read_text())

    def test_only_named_public_mask_tiffs_are_retained(self):
        here = Path(__file__).resolve().parent
        workflow = (here.parents[1] / '.github/workflows/native-mac-fresh-fiji.yml').read_text()
        self.assertIn('fresh-fiji-results/original_ganglia-mask.tif', workflow)
        self.assertIn('fresh-fiji-results/fork_ganglia-mask.tif', workflow)
        self.assertNotIn('fresh-fiji-results/**/*.tif', workflow)
        probe = (here / 'Fresh_Ganglia_Probe.java').read_text()
        self.assertIn('"mask_pixels_uint8_row_major_sha256"', probe)
        self.assertIn('"mask_tiff_sha256"', probe)
        self.assertIn("HERE / 'Fresh_Ganglia_Evidence.java'", (here / 'run_fresh_fiji.py').read_text())

    def test_actual_gat_reference_uses_four_tiles(self):
        reference = fresh.MANIFEST['neuron_reference']
        self.assertEqual(reference['tiles'], 4)
        self.assertEqual(reference['corpus_case'], 'repo_DYM_22_7_Pr_Hu_crop_c1_t1_x0_y0')
        self.assertEqual(fresh.MANIFEST['expected_neuron_label_sha256'], 'ea1767df58491cc03927e121943d955708450d091f3416b2493e1c93e51cd443')
    def test_empty_engine_directory_is_never_initialized(self):
        directory=self.root/'engines';directory.mkdir()
        with self.assertRaises(ValueError):
            fresh.verify_engine_files(directory,[{'filename':'real.jar','sha256':'0'*64}])
    def test_engine_requires_exact_bytes_and_no_extra_jars(self):
        directory=self.root/'engines';directory.mkdir();jar=directory/'real.jar';jar.write_bytes(b'verified')
        artifact={'filename':'real.jar','sha256':fresh.sha256(jar)}
        self.assertEqual(1,len(fresh.verify_engine_files(directory,[artifact])))
        jar.write_bytes(b'changed')
        with self.assertRaises(ValueError):fresh.verify_engine_files(directory,[artifact])
        jar.write_bytes(b'verified');(directory/'unrequested.jar').write_bytes(b'extra')
        with self.assertRaises(ValueError):fresh.verify_engine_files(directory,[artifact])
    def test_native_binary_is_separately_required(self):
        directory=self.root/'engine';directory.mkdir();jar=directory/'engine.jar';jar.write_bytes(b'engine')
        native=directory/'native.jar';native.write_bytes(b'cpu');native_hash=fresh.sha256(native);native.unlink()
        artifacts=[{'filename':'engine.jar','sha256':fresh.sha256(jar)},
                   {'filename':'native.jar','sha256':native_hash,'platform':'macosx-arm64'}]
        fresh.verify_engine_files(directory,artifacts)
        with self.assertRaises(ValueError):fresh.verify_engine_files(directory,artifacts,include_native=True)
        native.write_bytes(b'cpu');self.assertEqual(2,len(fresh.verify_engine_files(directory,artifacts,True)))
    def test_model_conflict_is_reported_without_overwrite(self):
        model=self.root/'rdf.yaml';model.write_bytes(b'actual descriptor')
        with self.assertRaises(ValueError):fresh.verify_required_assets(self.root,[{'path':'rdf.yaml','sha256':'0'*64}])
        self.assertEqual(b'actual descriptor',model.read_bytes())
    def test_engine_manifest_matches_previously_validated_artifacts(self):
        dependencies=json.loads((Path(__file__).resolve().parents[2]/'native-inference/validation/workflows/dependencies.json').read_text())['artifacts']
        expected=[a for a in dependencies if 'engine' in a['groups'] and a.get('platform','macosx-arm64')=='macosx-arm64']
        self.assertEqual(expected,fresh.MANIFEST['ganglia_engine']['artifacts'])
        self.assertEqual(8,len(expected))
        self.assertEqual('2.0.0',fresh.MANIFEST['ganglia_engine']['catalog_resolved_version'])
    def test_current_updater_application_pins_are_explicit(self):
        pins = fresh.MANIFEST['ganglia_engine']['required_updater_assets']
        self.assertEqual([
            {'path': 'jars/dl-modelrunner-0.6.4.jar',
             'sha256': '376d94bc2a921923c942b735fa4088ca7fb16e1a18c1dc09441401a606af2ce4'},
            {'path': 'plugins/DeepImageJ-3.2.1-SNAPSHOT.jar',
             'sha256': '139ec702a1e29e5845d031f1886fe4c3811efac841b429fc83b8f1cf43b80302'},
        ], pins[:2])
        engine = fresh.MANIFEST['ganglia_engine']
        self.assertEqual('2.4.1+cpu', engine['model_declared_version'])
        self.assertEqual('pytorch-2.0.0-2.0.0-macosx-arm64-cpu', engine['directory'])
        self.assertEqual(6, len(pins[2:]))

    def test_updater_assets_require_current_path_and_exact_bytes(self):
        for pin in fresh.MANIFEST['ganglia_engine']['required_updater_assets'][:2]:
            with self.subTest(path=pin['path']):
                asset = self.root / pin['path']
                asset.parent.mkdir(parents=True, exist_ok=True)
                # Small fixture bytes exercise the verifier, not a native runtime.
                asset.write_bytes(b'verified fixture')
                expected = {'path': pin['path'], 'sha256': fresh.sha256(asset)}
                self.assertEqual([expected], fresh.verify_required_assets(self.root, [expected]))
                asset.write_bytes(b'changed fixture')
                with self.assertRaises(ValueError):
                    fresh.verify_required_assets(self.root, [expected])
                asset.write_bytes(b'verified fixture')
                asset.rename(asset.with_name('older-version.jar'))
                with self.assertRaises(ValueError):
                    fresh.verify_required_assets(self.root, [expected])

    def test_current_packager_documentation_passes_fresh_fiji_overlay(self):
        repository = Path(__file__).resolve().parents[2]
        spec = importlib.util.spec_from_file_location('preview_package', repository / 'scripts/package-apple-silicon-preview.py')
        package = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(package)
        build = self.root / 'build'
        (build / 'target/classes/Features/Inference').mkdir(parents=True)
        (build / 'target/classes/UI').mkdir()
        (build / 'pom.xml').write_text('<project xmlns="http://maven.apache.org/POM/4.0.0"><version>test</version></project>')
        classes = ['UI/GatPluginUI.class', 'Features/Inference/NativeStarDist.class',
                   'Features/Inference/NativeAlignmentClient.class']
        with zipfile.ZipFile(build / 'target/GutAnalysisToolbox_-test.jar', 'w') as jar:
            jar.writestr('plugins.config', 'fixture registration')
            for name in classes:
                (build / 'target/classes' / name).write_bytes(b'compiled fixture')
                jar.writestr(name, b'compiled fixture')
        bundles = {
            'inference': ['gat-native-inference.jar', 'THIRD_PARTY_NOTICES.md',
                          'lib/tensorflow-core-native-test-macosx-arm64.jar'],
            'alignment': ['gat-native-alignment.jar', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
                          'source/pom.xml', 'source/src/main/java/TemplateMatching/NativeAlignmentMain.java',
                          'source/src/main/java/TemplateMatching/Align_slices.java',
                          'source/src/main/java/TemplateMatching/cvMatch_Template.java',
                          'lib/opencv-test-macosx-arm64.jar', 'lib/openblas-test-macosx-arm64.jar',
                          'lib/javacpp-test-macosx-arm64.jar'],
        }
        for worker, members in bundles.items():
            target = build / ('native-' + worker) / 'target'
            target.mkdir(parents=True)
            with zipfile.ZipFile(target / ('gat-native-' + worker + '-macosx-arm64.zip'), 'w') as archive:
                for name in members:
                    archive.writestr('gat-native-' + worker + '/' + name, b'packaging fixture')
        for name in ['LICENSE', 'docs/apple-silicon.md', 'docs/apple-silicon-workflow-matrix.md',
                     'docs/preview-5-setup.md', 'docs/validation/maintainer-review-2026-10-06.md',
                     'docs/validation/fork-hardening-2026-10-06.md']:
            destination = build / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repository / name, destination)
        output = self.root / 'packages'
        with patch.object(package, '__file__', str(build / 'scripts/package-apple-silicon-preview.py')), \
                patch('sys.argv', ['package-preview', '--output', str(output)]), \
                patch.object(package.subprocess, 'check_output', side_effect=['1' * 40, '']):
            package.main()
        fiji = self.root / 'Fiji'
        (fiji / 'plugins').mkdir(parents=True)
        (fiji / 'jars').mkdir()
        fresh.overlay(fiji, archive=output / 'GAT-test-macos-arm64-preview.zip',
                      source_commit='1' * 40, evidence=self.root / 'evidence')
        for name in fresh.OVERLAY_DOCUMENTS:
            self.assertTrue((fiji / name).is_file(), name)

    def test_overlay_rejects_unknown_docs_and_executable_paths_before_mutation(self):
        plugin = io.BytesIO()
        with zipfile.ZipFile(plugin, 'w') as jar:
            jar.writestr('UI/GatPluginUI.class', b'fixture')
            jar.writestr('plugins.config', b'fixture')
        fiji = self.root / 'Fiji'
        (fiji / 'plugins').mkdir(parents=True)
        (fiji / 'jars').mkdir()
        for name in ['PREVIEW_6_SETUP.md', 'PREVIEW_5_SETUP.md/run.sh',
                     'BUILD_INFO.json/run.sh', 'install.sh', 'plugins/extra.sh']:
            with self.subTest(path=name):
                self.archive([('BUILD_INFO.json', json.dumps({'source_commit': '1' * 40,
                                                             'source_worktree_modified': False})),
                              ('plugins/GAT.jar', plugin.getvalue()), (name, 'unexpected')])
                with self.assertRaisesRegex(ValueError, 'Unexpected overlay path'):
                    fresh.overlay(fiji, archive=self.path, source_commit='1' * 40,
                                  evidence=self.root / 'evidence')
                self.assertEqual([], list((fiji / 'plugins').iterdir()))
                self.assertEqual([], list((fiji / 'jars').iterdir()))

    def test_normal_layout(self):
        self.archive([('Fiji/', ''),('Fiji/jars/ij.jar','data')])
        self.assertEqual(4, fresh.safe_archive(self.path, 'Fiji', True))
    def test_traversal_absolute_backslash_and_wrong_root(self):
        for name in ('../evil','/tmp/evil','Fiji/../evil','Fiji\\evil','Fiji.app/evil'):
            with self.subTest(name=name):
                self.archive([(name,'x')])
                with self.assertRaises(ValueError):
                    fresh.safe_archive(self.path, 'Fiji', True)
    def test_duplicate_member(self):
        self.archive([('Fiji/a','x'),('Fiji/a','y')])
        with self.assertRaises(ValueError):
            fresh.safe_archive(self.path, 'Fiji', True)
    def test_symlink_escape_and_write_through(self):
        for target, child in (('../../escape',None),('other','Fiji/link/child')):
            with zipfile.ZipFile(self.path,'w') as z:
                info=zipfile.ZipInfo('Fiji/link'); info.external_attr=(stat.S_IFLNK|0o777)<<16
                z.writestr(info,target)
                if child:z.writestr(child,'x')
            with self.assertRaises(ValueError):fresh.safe_archive(self.path,'Fiji',True)
    def test_safe_distribution_symlink_but_no_overlay_symlinks(self):
        with zipfile.ZipFile(self.path,'w') as z:
            info=zipfile.ZipInfo('Fiji/java/link');info.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(info,'../real')
        fresh.safe_archive(self.path,'Fiji',True)
        with self.assertRaises(ValueError):fresh.safe_archive(self.path)
    def test_overlay_rejects_worker_classes_in_plugin(self):
        self.archive([('UI/GatPluginUI.class','x'),('plugins.config','x'),('org/tensorflow/types/TFloat32.class','x')])
        with zipfile.ZipFile(self.path) as z:
            with self.assertRaises(ValueError):fresh.validate_gat_jar(z)
    def test_pin_conflict_is_reported_not_repaired(self):
        pin=fresh.MANIFEST['expected_plugin_artifacts'][0]
        records=[{'path':'plugins/'+pin['file'],'sha256':'0'*64,'bytes':42}]
        compared=fresh.compare_pins(records)
        self.assertEqual('CONFLICT',compared[0]['status'])
        self.assertEqual('0'*64,records[0]['sha256'])
    def test_overlay_rejects_wrong_source_before_mutating(self):
        fiji=self.root/'Fiji';(fiji/'plugins').mkdir(parents=True);(fiji/'jars').mkdir()
        self.archive([('BUILD_INFO.json',json.dumps({'source_commit':'0'*40,'source_worktree_modified':False}))])
        with self.assertRaises(ValueError):fresh.overlay(fiji,archive=self.path,source_commit='1'*40,evidence=self.root/'evidence')
        self.assertEqual([],list((fiji/'plugins').iterdir()))
    def test_existing_plugins_not_replaced_arbitrarily(self):
        fiji=self.root/'Fiji';(fiji/'plugins').mkdir(parents=True);(fiji/'jars').mkdir()
        with zipfile.ZipFile(fiji/'plugins'/'unrelated.jar','w') as z:z.writestr('Other.class','untouched')
        with zipfile.ZipFile(fiji/'plugins'/'old-GAT.jar','w') as z:z.writestr('UI/GatPluginUI.class','old')
        self.archive([('UI/GatPluginUI.class','new'),('plugins.config','entry')])
        result=fresh.overlay(fiji,plugin=self.path,source_commit='1'*40,evidence=self.root/'evidence')
        self.assertTrue((fiji/'plugins'/'unrelated.jar').exists())
        self.assertFalse((fiji/'plugins'/'old-GAT.jar').exists())
        self.assertEqual(1,len(result['displaced_GAT_only']))
        self.assertFalse(result['runtime_dependency_jars_changed'])
    def test_environment_ignores_java_injections(self):
        from unittest.mock import patch
        with patch.dict('os.environ', {'JAVA_TOOL_OPTIONS':'bad','JAVA_HOME':'bad','CLASSPATH':'bad'}):
            env=fresh.clean_env(self.root)
        self.assertNotIn('JAVA_TOOL_OPTIONS',env)
        self.assertNotIn('JAVA_HOME',env)
        self.assertNotIn('CLASSPATH',env)
        self.assertEqual(str(self.root),env['HOME'])


class HistoricalRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.parent = Path(self.temp.name).resolve()
        self.env_patch = patch.dict(fresh.os.environ, {'RUNNER_TEMP': str(self.parent), 'GITHUB_ACTIONS': 'true'})
        self.env_patch.start()
        self.work = fresh.create_work_root()
        self.root = self.work / 'official' / 'Fiji'
        self.evidence = self.parent / 'evidence'; self.evidence.mkdir()
        self.original_manifest = fresh.MANIFEST
        self.manifest = json.loads(json.dumps(fresh.MANIFEST))
        self.payloads = {}
        for artifact in self.manifest['historical_runtime']['artifacts']:
            target = self.root / artifact['path']; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'live-updater-' + target.name.encode())
            payload = b'historical-' + target.name.encode()
            self.payloads[artifact['url']] = payload
            artifact['sha256'] = fresh.hashlib.sha256(payload).hexdigest()
            artifact['bytes'] = len(payload)
            for pin in self.manifest['ganglia_engine']['required_updater_assets']:
                if pin['path'] == artifact['path']:
                    pin['sha256'] = artifact['sha256']
        (self.root / 'models').mkdir()
        (self.root / 'models' / 'model.pt').write_bytes(b'unchanged model')
        (self.root / 'config.txt').write_bytes(b'unchanged launcher setting')
        self.manifest_patch = patch.object(fresh, 'MANIFEST', self.manifest)
        self.manifest_patch.start()
        fresh.register_fresh_installation(self.root, self.work, self.manifest['fiji'])
        self.before = fresh.full_inventory(self.root)

    def tearDown(self):
        fresh._FRESH_INSTALLATIONS.pop(self.root, None)
        fresh._FRESH_WORKSPACES.pop(self.work, None)
        self.manifest_patch.stop()
        self.env_patch.stop()
        self.temp.cleanup()

    def fake_download(self, url, path, env, log, **kwargs):
        path.write_bytes(self.payloads[url])
        return {'url': url, 'sha256': fresh.sha256(path), 'bytes': path.stat().st_size}

    def apply(self, **kwargs):
        with patch.object(fresh, 'download', side_effect=self.fake_download):
            return fresh.apply_historical_runtime(kwargs.get('root', self.root),
                                                  kwargs.get('work', self.work),
                                                  kwargs.get('evidence', self.evidence), {})

    def test_opt_in_cli_and_default_never_downloads_or_changes_runtime(self):
        parser = fresh.build_parser()
        argv = ['--output', 'out', '--original-jar', 'original.jar', '--fork-archive', 'fork.zip',
                '--fork-commit', '1' * 40]
        self.assertFalse(parser.parse_args(argv).historical_runtime)
        self.assertTrue(parser.parse_args(argv + ['--historical-runtime']).historical_runtime)
        with patch.object(fresh, 'apply_historical_runtime') as replacement:
            result = fresh.configure_runtime(self.root, self.work, self.evidence, {})
            replacement.assert_not_called()
        self.assertEqual('official-updater', result['mode'])
        self.assertEqual(self.before, fresh.full_inventory(self.root))
        self.assertEqual([], list(self.evidence.iterdir()))

    def test_control_arguments_must_be_paired(self):
        for extra in (['--control-jar', 'control.jar'], ['--control-commit', '2' * 40]):
            with self.subTest(extra=extra), patch('sys.argv', ['fresh', '--output', str(self.evidence),
                    '--original-jar', 'original.jar', '--fork-archive', 'fork.zip', '--fork-commit', '1' * 40] + extra):
                with self.assertRaises(SystemExit) as error:
                    fresh.main()
                self.assertEqual(2, error.exception.code)

    def test_manifest_keeps_exact_original_hashes_and_official_urls(self):
        original = self.original_manifest
        self.assertFalse(original['historical_runtime']['default_enabled'])
        expected = {p['path']: p['sha256'] for p in original['ganglia_engine']['required_updater_assets'][:2]}
        self.assertEqual(expected, {a['path']: a['sha256'] for a in original['historical_runtime']['artifacts']})
        self.assertEqual(fresh.HISTORICAL_URLS,
                         {a['path']: a['url'] for a in original['historical_runtime']['artifacts']})

    def test_success_backs_up_only_two_displaced_jars_outside_classpath(self):
        result = self.apply()
        self.assertEqual('PASS', result['status'])
        self.assertEqual('historical-test-only', result['mode'])
        self.assertEqual(set(fresh.HISTORICAL_URLS), {r['path'] for r in result['inventory_delta']})
        for artifact in result['artifacts']:
            target = self.root / artifact['path']
            backup = Path(artifact['backup'])
            self.assertFalse(backup.is_relative_to(self.root))
            self.assertTrue(backup.is_relative_to(self.work / 'historical-runtime' / 'displaced'))
            self.assertEqual(artifact['displaced_sha256'], fresh.sha256(backup))
            self.assertEqual(artifact['sha256'], fresh.sha256(target))
            self.assertEqual(fresh.HISTORICAL_URLS[artifact['path']], artifact['download']['url'])
        self.assertEqual(b'unchanged model', (self.root / 'models/model.pt').read_bytes())
        self.assertEqual('PASS', json.loads((self.evidence / 'historical-runtime-audit.json').read_text())['status'])
        self.assertTrue((self.evidence / 'historical-runtime-before.json').is_file())
        self.assertTrue((self.evidence / 'historical-runtime-after.json').is_file())

    def test_already_pinned_dependencies_remain_unchanged(self):
        for artifact in fresh.historical_artifacts():
            (self.root / artifact['path']).write_bytes(self.payloads[artifact['url']])
        before = fresh.full_inventory(self.root)
        result = self.apply()
        self.assertEqual([], result['inventory_delta'])
        self.assertEqual(before, fresh.full_inventory(self.root))
        self.assertTrue(all(not a['replaced'] and 'backup' not in a for a in result['artifacts']))

    def test_non_ci_execution_is_rejected_before_download_or_mutation(self):
        with patch.dict(fresh.os.environ, {'GITHUB_ACTIONS': 'false'}):
            with self.assertRaisesRegex(ValueError, 'disposable GitHub Actions'):
                self.apply()
        self.assertEqual(self.before, fresh.full_inventory(self.root))

    def test_wrong_or_traversing_root_is_rejected(self):
        for root in (self.parent, self.work / 'fork/Fiji', self.work / 'official/../official/Fiji'):
            with self.subTest(root=root), self.assertRaises(ValueError):
                self.apply(root=root)
        self.assertEqual(self.before, fresh.full_inventory(self.root))

    def test_unregistered_workspace_or_extraction_is_rejected(self):
        for registry, key in ((fresh._FRESH_WORKSPACES, self.work),
                              (fresh._FRESH_INSTALLATIONS, self.root)):
            value = registry.pop(key)
            try:
                with self.assertRaisesRegex(ValueError, 'freshly unpacked'):
                    self.apply()
            finally:
                registry[key] = value

    def test_unpinned_archive_cannot_register_historical_installation(self):
        with self.assertRaisesRegex(ValueError, 'unverified Fiji'):
            fresh.register_fresh_installation(self.root, self.work, {'sha256': '0' * 64, 'bytes': 1})

    def test_symlink_root_is_rejected(self):
        other = self.root.with_name('real-Fiji')
        self.root.rename(other); self.root.symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.apply()

    def test_symlink_target_and_symlink_target_parent_are_rejected(self):
        target = self.root / 'jars/dl-modelrunner-0.6.4.jar'
        actual = target.with_suffix('.backup'); target.rename(actual); target.symlink_to(actual)
        with self.assertRaisesRegex(ValueError, 'Symlink forbidden'):
            self.apply()
        target.unlink(); actual.rename(target)
        directory = target.parent; actual_directory = directory.with_name('real-jars')
        directory.rename(actual_directory); directory.symlink_to(actual_directory, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink forbidden'):
            self.apply()

    def test_hardlinked_target_is_rejected(self):
        target = self.root / 'jars/dl-modelrunner-0.6.4.jar'
        fresh.os.link(target, self.parent / 'external.jar')
        with self.assertRaisesRegex(ValueError, 'unlinked jar'):
            self.apply()
        self.assertEqual(self.before, fresh.full_inventory(self.root))

    def test_missing_target_is_not_silently_added(self):
        (self.root / 'jars/dl-modelrunner-0.6.4.jar').unlink()
        with self.assertRaisesRegex(ValueError, 'existing regular'):
            self.apply()

    def test_target_traversal_absolute_backslash_and_extra_target_are_rejected(self):
        artifacts = self.manifest['historical_runtime']['artifacts']
        path = artifacts[0]['path']
        for unsafe in ('../jars/dl-modelrunner-0.6.4.jar', '/tmp/evil.jar', 'jars\\evil.jar'):
            artifacts[0]['path'] = unsafe
            with self.subTest(path=unsafe), self.assertRaisesRegex(ValueError, 'allowlist'):
                self.apply()
        artifacts[0]['path'] = path
        artifacts.append(dict(artifacts[0]))
        with self.assertRaisesRegex(ValueError, 'allowlist'):
            self.apply()
        self.assertEqual(self.before, fresh.full_inventory(self.root))

    def test_wrong_url_or_weakened_hash_is_rejected(self):
        artifact = self.manifest['historical_runtime']['artifacts'][0]
        for field, unsafe in (('url', 'https://example.com/arbitrary.jar'), ('sha256', '0' * 64)):
            old = artifact[field]; artifact[field] = unsafe
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'allowlist'):
                self.apply()
            artifact[field] = old
        self.assertEqual(self.before, fresh.full_inventory(self.root))

    def test_download_hash_or_size_failure_leaves_both_jars_untouched(self):
        for wrong in (b'wrong hash', b''):
            with self.subTest(wrong=wrong):
                artifact = self.manifest['historical_runtime']['artifacts'][1]
                self.payloads[artifact['url']] = wrong
                with self.assertRaisesRegex(ValueError, 'hash/length mismatch'):
                    self.apply()
                self.assertEqual(self.before, fresh.full_inventory(self.root))
                audit = json.loads((self.evidence / 'historical-runtime-audit.json').read_text())
                self.assertEqual('FAIL', audit['status'])
                shutil.rmtree(self.work / 'historical-runtime')
                for path in self.evidence.iterdir():
                    path.unlink()

    def test_duplicate_or_alternate_version_jar_is_rejected(self):
        for relative in ('plugins/nested/dl-modelrunner-0.6.4.jar', 'jars/dl-modelrunner-0.6.3.jar',
                         'jars/DeepImageJ-3.2.1-SNAPSHOT.jar', 'plugins/DeepImageJ-3.2.0.jar'):
            duplicate = self.root / relative; duplicate.parent.mkdir(parents=True, exist_ok=True)
            duplicate.write_bytes(b'duplicate')
            with self.subTest(path=relative), self.assertRaisesRegex(ValueError, 'Duplicate or shadowing'):
                self.apply()
            duplicate.unlink()

    def test_evidence_inside_runtime_and_reused_staging_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside the temporary runtime'):
            self.apply(evidence=self.root)
        (self.work / 'historical-runtime').mkdir()
        with self.assertRaises(FileExistsError):
            self.apply()

    def test_existing_evidence_is_not_overwritten(self):
        (self.evidence / 'historical-runtime-audit.json').write_text('existing evidence')
        with self.assertRaisesRegex(ValueError, 'evidence already exists'):
            self.apply()
        self.assertEqual('existing evidence', (self.evidence / 'historical-runtime-audit.json').read_text())
        self.assertEqual(self.before, fresh.full_inventory(self.root))

    def test_full_inventory_rejects_extra_diff_outside_runtime_jars(self):
        replace = fresh.os.replace
        def unsafe_replace(source, target):
            replace(source, target)
            (self.root / 'config.txt').write_bytes(b'unexpected extra mutation')
        with patch.object(fresh.os, 'replace', side_effect=unsafe_replace):
            with self.assertRaisesRegex(ValueError, 'exact expected dependency delta'):
                self.apply()
        audit = json.loads((self.evidence / 'historical-runtime-audit.json').read_text())
        self.assertEqual('FAIL', audit['status'])
        self.assertTrue((self.evidence / 'historical-runtime-after.json').exists())

    def test_inventory_rejects_added_removed_and_duplicate_paths(self):
        for after in (self.before + [{'path': 'extra.txt', 'bytes': 1, 'sha256': 'a' * 64}],
                      self.before[1:], self.before + [self.before[0]]):
            with self.subTest(after=after), self.assertRaises(ValueError):
                fresh.historical_inventory_delta(self.before, after, fresh.historical_artifacts())

    def test_download_time_runtime_change_is_detected_before_replacement(self):
        def changing_download(*args, **kwargs):
            result = self.fake_download(*args, **kwargs)
            (self.root / 'models/model.pt').write_bytes(b'concurrent modification')
            return result
        with patch.object(fresh, 'download', side_effect=changing_download):
            with self.assertRaisesRegex(ValueError, 'changed while historical'):
                fresh.apply_historical_runtime(self.root, self.work, self.evidence, {})
        for artifact in fresh.historical_artifacts():
            self.assertEqual(b'live-updater-' + Path(artifact['path']).name.encode(),
                             (self.root / artifact['path']).read_bytes())


if __name__=='__main__':unittest.main()
