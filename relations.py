import mojira
import bisect
import tryashtools as tat

def main():
   dump = mojira.get_archive()
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
      append(['projects', fields['project']], ticket_id)
      if 'versions' in fields:
         for version in fields['versions']:
            append(['versions', version, 'affected'], ticket_id)
      if 'fixVersions' in fields:
         for version in fields['fixVersions']:
            append(['versions', version, 'fixed'], ticket_id)
      for label in fields['labels']:
         append(['labels', label], ticket_id)
      if 'customfield_12800' in fields and fields['customfield_12800'] is not None:
         append(['area', fields['customfield_12800']['id']], ticket_id)
      if 'customfield_12200' in fields and fields['customfield_12200'] is not None:
         append(['priority', fields['customfield_12200']['id']], ticket_id)
      if 'customfield_11901' in fields and fields['customfield_11901'] is not None:
         for entry in fields['customfield_11901']:
            append(['categories', entry['id']], ticket_id)
      if 'customfield_10500' in fields and fields['customfield_10500'] is not None:
         append(['confirmation', fields['customfield_10500']['id']], ticket_id)
      append(['users', fields['creator'], 'created'], ticket_id)
      append(['users', fields['reporter'], 'reported'], ticket_id)
      if 'assignee' in fields:
         append(['users', fields.get('assignee'), 'assigned'], ticket_id)
      for comment in fields['comment']['comments']:
         append(['users', comment.get('author'), 'comments', ticket_id], comment['id'])
         append(['users', comment.get('updateAuthor'), 'edits', ticket_id], comment['id'])
      for change in data['changelog']['histories']:
         append(['users', change['author'], 'changes', ticket_id], change['id'])
         for item in change['items']:
            if item['field'] == 'Key':
               ids['issues'][item['fromString']] = ticket_id
      for attachment in fields['attachment']:
         path = dump.get_attachment_path(attachment)
         attach_data = tat.read_json(path)
         attachment_id = attach_data['id']
         append(['users', attach_data.get('author'), 'attachments', ticket_id], attachment_id)
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
   tat.write_json(ids['issues'], dump.caches_folder / 'issue_keys.json', mini=True)
   tat.write_json(ids['users'], dump.caches_folder / 'user_keys.json', mini=True)
   tat.write_json(relations['groups'], dump.caches_folder / 'groups.json', mini=True)
   tat.write_json(relations['projects'], dump.caches_folder / 'projects.json', mini=True)
   tat.write_json(relations['resolutions'], dump.caches_folder / 'resolutions.json', mini=True)
   tat.write_json(relations['users'], dump.caches_folder / 'users.json', mini=True)
   tat.write_json(relations['versions'], dump.caches_folder / 'versions.json', mini=True)
   tat.write_json(relations['labels'], dump.caches_folder / 'labels.json', mini=True)
   tat.write_json(relations['categories'], dump.caches_folder / 'categories.json', mini=True)
   tat.write_json(relations['confirmation'], dump.caches_folder / 'confirmation.json', mini=True)
   tat.write_json(relations['priority'], dump.caches_folder / 'priority.json', mini=True)
   tat.write_json(relations['area'], dump.caches_folder / 'area.json', mini=True)

if __name__ == '__main__':
   main()
