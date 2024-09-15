import mojira
import pathlib
import tryashtools as tat
import os

def main():
   dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
   relations = tat.read_json(dump.root_folder / 'relations.json')
   results = {}
   for i,(username,user) in enumerate(relations['users'].items()):
      print(i+1, len(relations['users']), username)
      total = 0
      if 'attachments' in user:
         for entries in user['attachments'].values():
            for entry in entries:
               total += os.path.getsize(dump.attachments_folder / entry)
      results[username] = total
   for username, total in sorted(results.items(), key=lambda item: item[1], reverse=True):
      print((total, username))

if __name__ == '__main__':
   main()
