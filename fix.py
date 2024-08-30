import mojira
import tryashtools as tat
import pathlib

dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
client = mojira.get_client()
pairs = {}
print('making pairs')
for file in tat.get_files(dump.tickets_folder, True):
   data = tat.read_json(file)
   pairs[data['id']] = data['key']
print('fixing')
for file in tat.get_files(dump.tickets_folder, True):
   data = tat.read_json(file)
   for link in data['fields']['issuelinks']:
      inw = link.get('inwardIssue')
      outw = link.get('outwardIssue')
      if inw is not None:
         if inw in pairs:
            link['inwardIssue'] = pairs[inw]
         else:
            issue = client.issue(inw)
            link['inwardIssue'] = issue.key
      if outw is not None:
         link['outwardIssue'] = outw['key']
   tat.write_json(data, file)
