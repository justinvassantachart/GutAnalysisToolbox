import importlib.util
from pathlib import Path
import tempfile
import unittest
SPEC=importlib.util.spec_from_file_location('source_audit',Path(__file__).with_name('verify_v2_sources.py'))
audit=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(audit)
class SourceAuditTests(unittest.TestCase):
 def test_only_the_named_projection_method_can_differ(self):
  with tempfile.TemporaryDirectory() as d:
   roots=[Path(d)/x for x in ('original','control','fork')]
   for i,root in enumerate(roots):
    p=root/audit.PREP_PATH;p.parent.mkdir(parents=True)
    p.write_text('    public static GangliaPrep prepareGangliaInputs() {\n'+('control\n' if i==1 else 'original\n')+'        return new GangliaPrep(dij, rgb);\n    }')
    for path in audit.HELPERS:
     p=root/path;p.parent.mkdir(parents=True,exist_ok=True)
     p.write_text('class A {\n    public static ImagePlus mip(ImagePlus s) { return '+('fixed' if i==2 else 'old')+'; }\n void extractChannel() { unchanged(); }\n}' if path.endswith('/ImageOps.java') else 'identical helper')
   result=audit.audit(*roots);self.assertEqual('PASS',result['status'])
   row=result['unchanged_helpers']['src/main/java/Features/Tools/ImageOps.java']
   self.assertFalse(row['all_byte_identical']);self.assertTrue(row['non_projection_code_byte_identical'])
   p=roots[2]/'src/main/java/Features/Tools/ImageOps.java';p.write_text(p.read_text().replace('unchanged()', 'changed()'))
   self.assertEqual('FAIL',audit.audit(*roots)['status'])
 def test_unclosed_projection_method_fails(self):
  with self.assertRaises(ValueError):audit.without_mip('    public static ImagePlus mip(ImagePlus s) {')
