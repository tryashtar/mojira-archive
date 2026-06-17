import mojira
import pathlib

archive = mojira.Archive(pathlib.Path('/d/Archives/Mojira/data'))
keys = {}
for issue in archive.issues():
   for entry in issue['changelog']['histories']:
      for change in entry['items']:
         key = (change['field'], change['from'] is not None, change['fromString'] is not None, change['to'] is not None, change['toString'] is not None)
         if key not in keys:
            rep = (repr(change['field']), repr(change['from']), repr(change['fromString']), repr(change['to']), repr(change['toString']), issue['id'])
            keys[key] = [0, rep]
         keys[key][0] += 1
for entry in keys.values():
   print(entry)
