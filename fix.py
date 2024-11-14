import tryashtools as tat
import os
import mojira

for file in list(tat.get_files('/d/Archives/Mojira/dump/avatars', True)):
   if tat.extension(file) == '':
      data = tat.read_bytes(file)
      if data.startswith(b'<svg') or data.startswith(b'<?xml'):
         os.rename(file, file + '.svg')
      elif data.startswith(b'\x89PNG\x0d\x0a\x1a\x0a'):
         os.rename(file, file + '.png')
      else:
         print(file, data)

for attachment in tat.get_files('/d/Archives/Mojira/dump/attachments'):
   data = tat.read_json(attachment)
   atchid = data['id']
   extension = os.path.splitext(data['filename'])[1]
   old_path = f'/d/Archives/Mojira/dump/attachments/content/{atchid}'
   new_path = f'/d/Archives/Mojira/dump/attachments/content/{atchid}{extension}'
   if os.path.exists(old_path):
      print(attachment)
      os.rename(old_path, new_path)
