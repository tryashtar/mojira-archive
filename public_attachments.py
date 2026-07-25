import json
import pathlib

from jiratypes import Attachment, Issue

public = pathlib.Path('/d/Archives/Mojira/public/data/issues')
for path in public.iterdir():
   with open(path, 'r', encoding='utf-8') as file:
      issue: Issue = json.load(file)
   for attachment_id in issue['fields']['attachment']:
      print(attachment_id)
      private_data_path = pathlib.Path('/d/Archives/Mojira/private/data/attachments') / (attachment_id + '.json')
      public_data_path = pathlib.Path('/d/Archives/Mojira/public/data/attachments') / (attachment_id + '.json')
      public_data_path.symlink_to('../../../private/data/attachments/' + attachment_id + '.json')
      with open(private_data_path, 'r', encoding='utf-8') as file:
         attachment: Attachment = json.load(file)
      ext = attachment['filename'].split('.')[-1]
      public_content_path = pathlib.Path('/d/Archives/Mojira/public/data/attachments/content') / (attachment_id + '.' + ext)
      public_content_path.symlink_to('../../../../private/data/attachments/content/' + attachment_id + '.' + ext)
