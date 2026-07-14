import bs4

import mojira
import pathlib
import markup
import relations

archive = mojira.Archive(pathlib.Path('/d/Archives/Mojira/data'))
rels = relations.KeyLookups()
rels.load(pathlib.Path('/d/Archives/Mojira/relations/keys'))
for (root, dirs, files) in pathlib.Path('/d/Archives/Mojira/markup').walk():
   for path in files:
      with open(root / path, 'r', encoding='utf-8') as file:
         soup = bs4.BeautifulSoup(file, 'html.parser')
      parsed = markup.parse_markup(soup)
      for entry in parsed.issues:
         if rels.try_get_issue_key(entry.key) is None:
            print('issue', root / path, entry.key)
      for entry in parsed.users:
         if rels.try_get_user_key(entry.username) is None and archive.get_user_data(entry.username) is None:
            print('user', root / path, entry.username)
      for entry in [*parsed.attachments, *parsed.thumbnails]:
         data = archive.get_attachment_data(entry.id)
         if data is None:
            print('attach', root / path, entry.id, entry.filename)
