"""Check the actual bounded GitHub matrix expression without third-party packages."""
import ast,json,re,types,unittest
from pathlib import Path

WORKFLOW=Path(__file__).resolve().parents[1]/'.github/workflows/probe.yml'
ALL_SOURCES=['易茅时价','今日酒价','茅粉鲁智深','国酒酱香']


def selected_sources(event,source):
 text=WORKFLOW.read_text()
 expression=re.search(r"source: \$\{\{ fromJSON\((.+)\) \}\}",text).group(1)
 expression=expression.replace('&&',' and ').replace('||',' or ')
 tree=ast.parse(expression,mode='eval')
 # Only the two known context fields, literals, equality and short-circuit
 # Boolean operations are needed. Refuse calls or any expanded expression.
 for node in ast.walk(tree):
  if not isinstance(node,(ast.Expression,ast.BoolOp,ast.And,ast.Or,ast.Compare,ast.Eq,ast.Constant,ast.Attribute,ast.Name,ast.Load)):
   raise ValueError('unexpected matrix syntax')
  if isinstance(node,ast.Attribute) and (not isinstance(node.value,ast.Name) or (node.value.id,node.attr) not in {('github','event_name'),('inputs','source')}):
   raise ValueError('unexpected matrix context')
  if isinstance(node,ast.Name) and node.id not in {'github','inputs'}:raise ValueError('unexpected matrix name')
 value=eval(compile(tree,str(WORKFLOW),'eval'),{'__builtins__':{}},{'github':types.SimpleNamespace(event_name=event),'inputs':types.SimpleNamespace(source=source)})
 return json.loads(value)


class WorkflowSourceTests(unittest.TestCase):
 def test_each_supported_manual_single_source_is_isolated(self):
  for source in ['易茅时价','今日酒价','茅粉鲁智深']:
   with self.subTest(source=source):self.assertEqual(selected_sources('workflow_dispatch',source),[source])

 def test_manual_default_remains_all_sources(self):
  self.assertEqual(selected_sources('workflow_dispatch','全部'),ALL_SOURCES)
  self.assertIn("default: '全部'",WORKFLOW.read_text())
  self.assertIn("options: ['全部', '易茅时价', '今日酒价', '茅粉鲁智深']",WORKFLOW.read_text())

 def test_schedule_remains_all_sources(self):
  for source in ['',None,'今日酒价','茅粉鲁智深']:
   with self.subTest(source=source):self.assertEqual(selected_sources('schedule',source),ALL_SOURCES)

 def test_push_remains_yimao_only_regardless_of_input(self):
  for source in ['',None,'全部','今日酒价','茅粉鲁智深']:
   with self.subTest(source=source):self.assertEqual(selected_sources('push',source),['易茅时价'])

 def test_existing_schedule_concurrency_and_permissions_unchanged(self):
  text=WORKFLOW.read_text()
  self.assertEqual(re.findall(r"- cron: '([^']+)'",text),['30 23 * * *','50 1 * * *','15,40 2 * * *','20 3 * * *'])
  self.assertIn('permissions:\n  contents: write\n',text)
  self.assertIn('concurrency:\n  group: public-wholesale-probe\n  cancel-in-progress: false\n',text)
  self.assertIn('max-parallel: 1',text)
  self.assertIn('timeout-minutes: 6',text)
  self.assertIn("assert request['version']==1 and request['source']=='易茅时价'",text)


if __name__=='__main__':unittest.main()
