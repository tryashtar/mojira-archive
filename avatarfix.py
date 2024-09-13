import mojira
import pathlib
import tryashtools as tat
import re

dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
client = mojira.get_client()
results = {}
def download_avatar(url, folder):
   avatarid = re.search(r'avatarId=(\d+)', url).groups(1)[0]
   filepath = dump.root_folder / 'avatars' / folder / avatarid
   if not filepath.exists():
      response = client._session.get(url)
      tat.write_bytes(response.content, filepath)
for project in dump.projects.values():
   avatar = project['avatarUrls']['48x48']
   print(project['key'])
   download_avatar(avatar, 'projects')
print('Users...')
userlist = list(tat.get_files(dump.users_folder, True))
for i,userfile in enumerate(userlist):
   data = tat.read_json(userfile)
   print(i+1, len(userlist), data['name'])
   avatar = data['avatarUrls']['48x48']
   download_avatar(avatar, 'users')
   avatarid = re.search(r'avatarId=(\d+)', avatar).groups(1)[0]
   if avatarid not in results:
      results[avatarid] = {}
   results[avatarid][data['key']] = avatar
for key,val in results.items():
   if len(val) > 1:
      print(len(val), key)
tat.write_json(results, dump.root_folder / 'avatars.json')
