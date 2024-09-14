import mojira
import tryashtools as tat
import pathlib

dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
client = mojira.get_client()
pairs = {}
print('making pairs')
files = list(tat.get_files(dump.tickets_folder, True))
for i,file in enumerate(files):
   print((i+1),len(files),file)
   data = tat.read_json(file)
   pairs[data['key']] = data['id']
print('fixing')
for i,file in enumerate(files):
   print((i+1),len(files),file)
   data = tat.read_json(file)
   for link in data['fields']['issuelinks']:
      inw = link.get('inwardIssue')
      outw = link.get('outwardIssue')
      if inw is not None:
         if inw in pairs:
            link['inwardIssue'] = pairs[inw]
         elif '-' not in inw:
            link['inwardIssue'] = inw
         else:
            print('Looking up ' + inw)
            issue = client.issue(inw)
            link['inwardIssue'] = issue.id
      if outw is not None:
         if outw in pairs:
            link['outwardIssue'] = pairs[outw]
         elif '-' not in outw:
            link['outwardIssue'] = outw
         else:
            print('Looking up ' + outw)
            issue = client.issue(outw)
            link['outwardIssue'] = issue.id
   new_path = dump.root_folder / 'new_issues' / (data['id'] + '.json')
   if not new_path.exists():
      tat.write_json(data, new_path)
