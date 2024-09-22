import mojira
import pathlib
import bisect
import tryashtools as tat

def main():
   dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
   relations = {}
   def append(path, value):
      block = relations
      for i,entry in enumerate(path):
         if entry is None:
            entry = ''
         if entry not in block:
            if i == len(path) - 1:
               block[entry] = []
            else:
               block[entry] = {}
         block = block[entry]
         if i == len(path) - 1:
            bisect.insort(block, value)
   print('Tickets...')
   files = list(tat.get_files(dump.tickets_folder, True))
   total = len(files)
   for i,issue in enumerate(files):
      data = tat.read_json(issue)
      key = data['id']
      print(f'{i+1} / {total} - {data['key']}')
      if 'issues' not in relations:
         relations['issues'] = {}
      relations['issues'][data['key']] = key
      fields = data['fields']
      append(['resolutions', fields['resolution']], key)
      if 'versions' in fields:
         for version in fields['versions']:
            append(['versions', version, 'affected'], key)
      if 'fixVersions' in fields:
         for version in fields['fixVersions']:
            append(['versions', version, 'fixed'], key)
      append(['users', fields['creator'], 'created'], key)
      append(['users', fields['reporter'], 'reported'], key)
      if 'assignee' in fields:
         append(['users', fields['assignee'], 'assigned'], key)
      for attachment in fields['attachment']:
         append(['users', attachment.get('author'), 'attachments', key], attachment['id'])
      for comment in fields['comment']['comments']:
         append(['users', comment.get('author'), 'comments', key], comment['id'])
         append(['users', comment.get('updateAuthor'), 'edits', key], comment['id'])
      for change in data['changelog']['histories']:
         append(['users', change['author'], 'changes', key], change['id'])
   print('Users...')
   users = list(tat.get_files(dump.users_folder, False))
   total = len(users)
   for i,user in enumerate(users):
      data = tat.read_json(user)
      key = data['key']
      print(f'{i+1} / {total} - {key}')
      for group in data['groups']['items']:
         append(['groups', group['name']], key)
   print('Writing...')
   tat.write_json(relations, dump.root_folder / 'relations.json', mini=True)

if __name__ == '__main__':
   main()
