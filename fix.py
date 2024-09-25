import mojira
import pathlib
import tryashtools as tat

dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
for ticket in tat.get_files(dump.tickets_folder):
   data = tat.read_json(ticket)
   attachments = data['fields']['attachment']
   changed = False
   for attach in attachments:
      if type(attach) is dict:
         changed = True
         key = attach['id']
         path = dump.attachments_folder / (key + '.json')
         tat.write_json(attach, path)
   if changed:
      print(data['key'])
      data['fields']['attachment'] = list(map(lambda x: x['id'], attachments))
      tat.write_json(data, ticket)
