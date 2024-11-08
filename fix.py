import mojira
import pathlib
import tryashtools as tat

dump = mojira.Dump(pathlib.Path('/d/Archives/Mojira/dump'))
for file in tat.get_files(dump.root_folder / 'markup'):
   file_id = tat.base_name(file)
   markup = tat.read_json(file)
   ticket = tat.read_json(dump.get_issue_path(file_id))
   print(file_id)
   new_markup = []
   if 'description' in markup:
      from_val = ticket['fields']['description']
      to_val = markup['description']
      if from_val is not None:
         new_markup.append({'type':'description','markup':from_val,'rendered':to_val})
   if 'customfield_12700' in markup:
      from_val = ticket['fields']['customfield_12700']
      to_val = markup['customfield_12700']
      if from_val is not None:
         new_markup.append({'type':'customfield_12700','markup':from_val,'rendered':to_val})
   if 'environment' in markup:
      from_val = ticket['fields']['environment']
      to_val = markup['environment']
      if from_val is not None:
         new_markup.append({'type':'environment','markup':from_val,'rendered':to_val})
   if 'comments' in markup:
      for i in range(len(markup['comments'])):
         from_val = ticket['fields']['comment']['comments'][i]['body']
         to_val = markup['comments'][i]
         new_markup.append({'type':'comment','markup':from_val,'rendered':to_val})
   if 'history' in markup:
      for i in range(len(markup['history'])):
         for k,value in markup['history'][i].items():
            old_out = value['from']
            new_out = value['to']
            for entry in ticket['changelog']['histories'][i]['items']:
               if entry['field'] == k:
                  old_in = entry['fromString']
                  new_in = entry['toString']
                  if old_in is not None:
                     new_markup.append({'type':k,'markup':old_in,'rendered':old_out})
                  if new_in is not None:
                     new_markup.append({'type':k,'markup':new_in,'rendered':new_out})
   new_path = dump.root_folder / 'new_markup' / (file_id + '.json')
   tat.write_json(new_markup, new_path)
