import pathlib
import mojira
import json

old_folder = pathlib.Path('/d/Archives/Mojira/data/users')
new_folder = pathlib.Path('/d/Archives/Mojira/data/users2')
for path in old_folder.iterdir():
   if path.is_file():
      with open(path, 'r', encoding='utf-8') as file:
         data = json.load(file)
      key = data['key']
      new_path = new_folder / (mojira.encode_user_string(key) + '.json')
      path.copy(new_path)
