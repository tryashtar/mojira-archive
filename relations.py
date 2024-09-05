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
   files = list(tat.get_files(dump.tickets_folder, True))
   total = len(files)
   for i,issue in enumerate(files):
      data = tat.read_json(issue)
      key = data['key']
      print(f'{i+1} / {total} - {key}')
      fields = data['fields']
      append(['resolutions', fields['resolution']], key)
      for version in fields['versions']:
         append(['versions', version, 'affected'], key)
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
   tat.write_json(relations, dump.root_folder / 'relations.json')

if __name__ == '__main__':
   main()
