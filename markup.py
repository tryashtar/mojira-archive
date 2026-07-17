import copy
import os
import pathlib
import re
import urllib.parse
import subprocess
import json
import dataclasses

import bs4
import dotenv

import mojira
import relations

from jiratypes import Issue, RevisionChange
from web import html_diff

@dataclasses.dataclass
class RevisionPaths:
   before: pathlib.Path
   after: pathlib.Path
   diff: pathlib.Path

@dataclasses.dataclass
class RevisionData:
   before: bs4.Tag | None
   after: bs4.Tag | None
   diff: bs4.Tag | None

def load_revision_data(paths: RevisionPaths) -> RevisionData:
   return RevisionData(
      load_if_exists(paths.before),
      load_if_exists(paths.after),
      load_if_exists(paths.diff)
   )

def load_if_exists(path: pathlib.Path) -> bs4.BeautifulSoup | None:
   if path.exists():
      return load(path)
   return None

# use html.parser because lxml wraps the tags in <html><body>...</body></html>
# and I'd rather not unwrap it and return a plain bs4.Tag
def load(path: pathlib.Path) -> bs4.BeautifulSoup:
   with open(path, 'r', encoding='utf-8') as file:
      return bs4.BeautifulSoup(file, 'html.parser')

def render_revision(renderer: subprocess.Popen, issue_id: int, change: RevisionChange, paths: RevisionPaths):
   if change['fromString'] is not None and change['toString'] is not None and not paths.diff.exists():
      before = load_if_exists(paths.before)
      if before is None:
         html = convert(renderer, change['fromString'], issue_id)
         write(paths.before, html)
         before = bs4.BeautifulSoup(html, 'html.parser')
      after = load_if_exists(paths.after)
      if after is None:
         html = convert(renderer, change['fromString'], issue_id)
         write(paths.after, html)
         after = bs4.BeautifulSoup(html, 'html.parser')
      diff = html_diff(bs4.BeautifulSoup(), before, after)
      write(paths.diff, diff.decode(formatter='html5'))
   else:
      if change['fromString'] is not None:
         render_to_file(renderer, issue_id, change['fromString'], paths.before)
      if change['toString'] is not None:
         render_to_file(renderer, issue_id, change['toString'], paths.after)

class MarkupSource:
   def __init__(self, folder: pathlib.Path):
      self.folder = folder

   def get_issue_description_path(self, issue_id: str) -> pathlib.Path:
      return self.folder / issue_id / 'description.html'

   def get_issue_description_revision_paths(self, issue_id: str, revision_id: str) -> RevisionPaths:
      root = self.folder / issue_id / 'revisions' / revision_id / 'description'
      return RevisionPaths(root / 'before.html', root / 'after.html', root / 'diff.html')

   def get_issue_environment_path(self, issue_id: str) -> pathlib.Path:
      return self.folder / issue_id / 'environment.html'

   def get_issue_environment_revision_paths(self, issue_id: str, revision_id: str) -> RevisionPaths:
      root = self.folder / issue_id / 'revisions' / revision_id / 'environment'
      return RevisionPaths(root / 'before.html', root / 'after.html', root / 'diff.html')

   def get_comment_body_path(self, issue_id: str, comment_id: str) -> pathlib.Path:
      return self.folder / issue_id / 'comments' / (comment_id + '.html')

   def get_secret_comment_body_path(self, issue_id: str, comment_id: str) -> pathlib.Path:
      return self.folder / issue_id / 'secret_comments' / (comment_id + '.html')

   def get_deleted_comment_body_path(self, issue_id: str, revision_id: str) -> pathlib.Path:
      return self.folder / issue_id / 'deleted_comments' / (revision_id + '.html')

   def get_issue_description(self, issue_id: str) -> bs4.BeautifulSoup:
      return load(self.get_issue_description_path(issue_id))

   def get_issue_description_revision(self, issue_id: str, revision_id: str) -> RevisionData:
      paths = self.get_issue_description_revision_paths(issue_id, revision_id)
      return load_revision_data(paths)

   def get_issue_environment(self, issue_id: str) -> bs4.BeautifulSoup:
      return load(self.get_issue_environment_path(issue_id))

   def get_issue_environment_revision(self, issue_id: str, revision_id: str) -> RevisionData:
      paths = self.get_issue_environment_revision_paths(issue_id, revision_id)
      return load_revision_data(paths)

   def get_comment_body(self, issue_id: str, comment_id: str) -> bs4.BeautifulSoup:
      return load(self.get_comment_body_path(issue_id, comment_id))

   def get_secret_comment_body(self, issue_id: str, comment_id: str) -> bs4.BeautifulSoup:
      return load(self.get_secret_comment_body_path(issue_id, comment_id))

   def get_deleted_comment_body(self, issue_id: str, comment_id: str) -> bs4.BeautifulSoup:
      return load(self.get_deleted_comment_body_path(issue_id, comment_id))

   def render_issue(self, issue: Issue, renderer: subprocess.Popen):
      issue_id = int(issue['id'])
      if issue['fields']['description'] is not None:
         path = self.get_issue_description_path(issue['id'])
         render_to_file(renderer, issue_id, issue['fields']['description'], path)
      if 'environment' in issue['fields'] and issue['fields']['environment'] is not None:
         path = self.get_issue_environment_path(issue['id'])
         render_to_file(renderer, issue_id, issue['fields']['environment'], path)
      for revision in issue['changelog']['histories']:
         for entry in revision['items']:
            if entry['field'] == 'description':
               paths = self.get_issue_description_revision_paths(issue['id'], revision['id'])
               render_revision(renderer, issue_id, entry, paths)
            elif entry['field'] == 'environment':
               paths = self.get_issue_environment_revision_paths(issue['id'], revision['id'])
               render_revision(renderer, issue_id, entry, paths)
            elif entry['field'] == 'Comment':
               assert entry['from'] is not None
               assert entry['to'] is None
               path = self.get_deleted_comment_body_path(issue['id'], revision['id'])
               render_to_file(renderer, issue_id, entry['from'], path)
      for comment in issue['fields']['comment']['comments']:
         path = self.get_comment_body_path(issue['id'], comment['id'])
         render_to_file(renderer, issue_id, comment['body'], path)

def main():
   print('Loading...')
   dotenv.load_dotenv()
   archive = mojira.Archive(folder=pathlib.Path(os.environ['ARCHIVE_DATA']))
   keys = relations.KeyLookups()
   keys.load(pathlib.Path(os.environ['ARCHIVE_RELATIONS']) / 'keys')
   secret_comments = mojira.SecretComments(pathlib.Path(os.environ['ARCHIVE_SECRET_COMMENTS']))
   markup_out = pathlib.Path(os.environ['ARCHIVE_MARKUP'])
   process = get_process(archive, keys, '.')
   source = MarkupSource(markup_out)
   print('Converting...')
   for i, issue in enumerate(archive.issues()):
      if i % 10000 == 0:
         print(i)
      source.render_issue(issue, process)
   print('Secrets...')
   for issue_id, comments in secret_comments.comments.items():
      print(issue_id)
      for comment in comments:
         path = source.get_secret_comment_body_path(issue_id, comment['id'])
         render_to_file(process, int(issue_id), comment['body'], path)

def get_process(archive: mojira.Archive, keys: relations.KeyLookups, root: str) -> subprocess.Popen:
   print('Configuring...')
   input_args = {
      'issues': str(archive.issues_folder),
      'users': str(archive.users_folder),
      'attachments': str(archive.attachments_folder),
      'root': root
   }
   print('Compiling...')
   subprocess.run(['mvn', 'package'], cwd='renderer', check=True)
   print('Starting...')
   process = subprocess.Popen(
      ['java', '-jar', 'renderer/target/renderer-1.0-SNAPSHOT-shaded.jar', json.dumps(input_args)],
      encoding='utf-8',
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE
   )
   assert process.stdin is not None
   issue_map = {k: int(v) for k, v in keys.issue_keys.items()}
   configure_data = {
      'type': 'configure',
      'issue_map': issue_map,
      'user_map': keys.user_keys
   }
   process.stdin.write(json.dumps(configure_data) + '\n')
   process.stdin.flush()
   return process

def convert(process: subprocess.Popen, markup: str, issue_id: int | None) -> str:
   assert process.stdin is not None
   command = {
      'type': 'render',
      'markup': markup,
      'issue': issue_id
   }
   process.stdin.write((json.dumps(command) + '\n'))
   process.stdin.flush()
   assert process.stdout is not None
   output_text = process.stdout.readline()
   output = json.loads(output_text)
   return output['rendered']

def render_to_file(renderer: subprocess.Popen, issue_id: int, markup: str, path: pathlib.Path):
   if not path.exists():
      html = convert(renderer, markup, issue_id)
      write(path, html)

def write(path: pathlib.Path, text: str):
   path.parent.mkdir(parents=True, exist_ok=True)
   with open(path, 'w', encoding='utf-8') as file:
      file.write(text)

@dataclasses.dataclass
class ParsedMarkupAttachment:
   tag: bs4.Tag
   attr: str
   id: str
   filename: str

@dataclasses.dataclass
class ParsedMarkupIssue:
   tag: bs4.Tag
   attr: str
   key: str

@dataclasses.dataclass
class ParsedMarkupIcon:
   tag: bs4.Tag
   attr: str
   path: str

@dataclasses.dataclass
class ParsedMarkupUser:
   tag: bs4.Tag
   attr: str
   username: str

@dataclasses.dataclass
class ParsedMarkup:
   root: bs4.Tag
   attachments: list[ParsedMarkupAttachment]
   thumbnails: list[ParsedMarkupAttachment]
   issues: list[ParsedMarkupIssue]
   icons: list[ParsedMarkupIcon]
   users: list[ParsedMarkupUser]

   # we need to fully copy the root, and repoint the references to the new root, rather than creating independent copies
   # copy.deepcopy is supposed to do this, but it seems to not work nicely with bs4 tags
   # so here is a manual implementation
   def clone(self):
      new_root = copy.deepcopy(self.root)
      mapping = dict(zip(
         (id(x) for x in self.root.find_all()),
         new_root.find_all(),
      ))
      def remap_list(list: list) -> list:
         return [dataclasses.replace(item, tag=mapping[id(item.tag)]) for item in list]
      return ParsedMarkup(
         root=new_root,
         attachments=remap_list(self.attachments),
         thumbnails=remap_list(self.thumbnails),
         issues=remap_list(self.issues),
         icons=remap_list(self.icons),
         users=remap_list(self.users),
      )

BROWSE_RE = re.compile(r'^./browse/([A-Z]+-[0-9]+)$')
ATTACH_RE = re.compile(r'^./secure/attachment/([0-9]+)/(.+)$')
THUMBNAIL_RE = re.compile(r'^./secure/thumbnail/([0-9]+)/(.+)$')
ICON_RE = re.compile(r'^./images/(.+)$')
USER_RE = re.compile(r'^./secure/ViewProfile\.jspa\?name=(.*)$')

def parse_markup(markup: bs4.Tag) -> ParsedMarkup:
   result = ParsedMarkup(markup, [], [], [], [], [])
   def append_link(tag: bs4.Tag, link: str, attr: str):
      if (match := ATTACH_RE.match(link)) is not None:
         attach_id, attach_name = match.group(1, 2)
         result.attachments.append(ParsedMarkupAttachment(tag, attr, attach_id, attach_name))
      if (match := THUMBNAIL_RE.match(link)) is not None:
         attach_id, attach_name = match.group(1, 2)
         result.thumbnails.append(ParsedMarkupAttachment(tag, attr, attach_id, attach_name))
      if (match := ICON_RE.match(link)) is not None:
         icon_path = match.group(1)
         result.icons.append(ParsedMarkupIcon(tag, attr, icon_path))
      if (match := BROWSE_RE.match(link)) is not None:
         key = match.group(1)
         result.issues.append(ParsedMarkupIssue(tag, attr, key))
      if (match := USER_RE.match(link)) is not None:
         username = urllib.parse.unquote_plus(match.group(1))
         result.users.append(ParsedMarkupUser(tag, attr, username))
   for tag in markup.find_all(name='a', attrs={'href': True}):
      current_link = tag['href']
      if isinstance(current_link, str) and current_link.startswith('./'):
         append_link(tag, current_link, 'href')
   for tag in markup.find_all(name='img', attrs={'src': True}):
      current_link = tag['src']
      if isinstance(current_link, str) and current_link.startswith('./'):
         append_link(tag, current_link, 'src')
   for tag in markup.find_all(name='object', attrs={'data': True}):
      current_link = tag['data']
      if isinstance(current_link, str) and current_link.startswith('./'):
         append_link(tag, current_link, 'data')
      for embed in tag.find_all(name='embed', attrs={'src': True}):
         embed_link = embed['src']
         if isinstance(embed_link, str) and embed_link.startswith('./'):
            append_link(embed, embed_link, 'src')
   return result

if __name__ == '__main__':
   main()
