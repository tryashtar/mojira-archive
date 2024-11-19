import dictdiffer
import tryashtools as tat

files = ['groups.json', 'issue_keys.json', 'projects.json', 'resolutions.json', 'user_keys.json', 'users.json', 'versions.json']
for file in files:
   print(file)
   f1 = tat.read_json(f'/d/Archives/Mojira/caches-full/{file}')
   f2 = tat.read_json(f'/d/Archives/Mojira/caches-incremental/{file}')
   diffs = dictdiffer.diff(f1, f2)
   for diff in diffs:
      print(diff)
   print()
