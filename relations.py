import mojira
import bisect
import tryashtools as tat

def main():
   dump = mojira.get_dump()
   relations = {}
   ids = {'issues':{},'users':{}}
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
      ticket_id = data['id']
      print(f'{i+1} / {total} - {data['key']}')
      ids['issues'][data['key']] = ticket_id
      fields = data['fields']
      append(['resolutions', fields['resolution']], ticket_id)
      if 'versions' in fields:
         for version in fields['versions']:
            append(['versions', version, 'affected'], ticket_id)
      if 'fixVersions' in fields:
         for version in fields['fixVersions']:
            append(['versions', version, 'fixed'], ticket_id)
      append(['users', fields['creator'], 'created'], ticket_id)
      append(['users', fields['reporter'], 'reported'], ticket_id)
      if 'assignee' in fields:
         append(['users', fields['assignee'], 'assigned'], ticket_id)
      for comment in fields['comment']['comments']:
         append(['users', comment.get('author'), 'comments', ticket_id], comment['id'])
         append(['users', comment.get('updateAuthor'), 'edits', ticket_id], comment['id'])
      for change in data['changelog']['histories']:
         append(['users', change['author'], 'changes', ticket_id], change['id'])
         for item in change['items']:
            if item['field'] == 'Key':
               ids['issues'][item['fromString']] = ticket_id
   print('Attachments...')
   files = list(tat.get_files(dump.attachments_folder))
   total = len(files)
   for i,attach in enumerate(files):
      data = tat.read_json(attach)
      attachment_id = data['id']
      print(f'{i+1} / {total} - {data['filename']}')
      append(['users', data.get('author'), 'attachments', attachment_id], data['id'])
   print('Users...')
   users = list(tat.get_files(dump.users_folder, False))
   total = len(users)
   for i,user in enumerate(users):
      data = tat.read_json(user)
      user_key = data['key']
      print(f'{i+1} / {total} - {data['name']}')
      ids['users'][data['name']] = user_key
      for group in data['groups']['items']:
         append(['groups', group['name']], user_key)
   print('Writing...')
   tat.write_json(relations, dump.root_folder / 'relations.json', mini=True)
   tat.write_json(ids, dump.root_folder / 'ids.json', mini=True)

if __name__ == '__main__':
   main()
