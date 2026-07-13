import mojira
import pathlib

archive = mojira.Archive(pathlib.Path('/d/Archives/Mojira/data'))
usernames: set[str] = set()
userkeys: set[str] = set()
for user in archive.users():
   name = user['name'].casefold().replace('/', '_')
   key = user['key'].replace('/', '_')
   if name in usernames:
      print(name, user['name'])
   usernames.add(name)
   if key in userkeys:
      print(key, user['key'])
   userkeys.add(key)
   if '⁄' in name or '⁄' in key:
      print(name, key)
print(len(usernames))
print(len(userkeys))
