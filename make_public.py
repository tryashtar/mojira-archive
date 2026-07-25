import json
import pathlib

from jiratypes import Issue

private = pathlib.Path('/d/Archives/Mojira/private/data/issues')
public = pathlib.Path('/d/Archives/Mojira/public/data/issues')
for path in private.iterdir():
   print(path.stem)
   with open(path, 'r', encoding='utf-8') as file:
      issue: Issue = json.load(file)
   if issue['fields']['project'] in ('11500', '11301', '10800', '10500'):
      continue
   if 'security' in issue['fields'] and issue['fields']['security']['id'] in ('10318', '10502'):
      continue
   issue['fields']['comment']['comments'] = [x for x in issue['fields']['comment']['comments'] if not ('visibility' in x and x['visibility']['value'] != 'users')]
   destination = public / (issue['id'] + '.json')
   with open(destination, 'w', encoding='utf-8') as file:
      json.dump(issue, file, indent=3)
