import dataclasses
import pathlib
import json
import urllib.parse
import typing
from jiratypes import Attachment, Field, Issue, IssueType, LinkType, NewComment, Project, Resolution, Status, User

@dataclasses.dataclass
class ValueDisplay:
   name: str
   description: str | None
   icon: str | None

META_TYPE = typing.Literal['issuetype', 'resolution', 'status', 'project']

class ArchiveMetas:
   def __init__(self):
      self.fields_path = pathlib.PurePath('fields.json')
      self.issue_types_path = pathlib.PurePath('issue_types.json')
      self.link_types_path = pathlib.PurePath('link_types.json')
      self.resolutions_path = pathlib.PurePath('resolutions.json')
      self.statuses_path = pathlib.PurePath('statuses.json')
      self.projects_path = pathlib.PurePath('projects.json')
      self.fields: dict[str, Field] = {}
      self.issue_types: dict[str, IssueType] = {}
      self.link_types: dict[str, LinkType] = {}
      self.resolutions: dict[str, Resolution] = {}
      self.statuses: dict[str, Status] = {}
      self.projects: dict[str, Project] = {}
      self.metas: dict[META_TYPE, dict[str, IssueType | Resolution | Status | Project]] = {
         'issuetype': self.issue_types,
         'resolution': self.resolutions,
         'status': self.statuses,
         'project': self.projects
      }

   def display_value(self, meta_id: META_TYPE, value_id: str | None) -> ValueDisplay | None:
      if meta_id == 'resolution' and value_id is None:
         return ValueDisplay('Unresolved', None, None)
      assert value_id is not None
      if value_id not in self.metas[meta_id]:
         return None
      meta = self.metas[meta_id][value_id]
      icon = meta['avatarUrls']['48x48'] if 'avatarUrls' in meta else None
      return ValueDisplay(meta['name'], meta['description'], icon)

   def load(self, folder: pathlib.Path):
      load_one(self.fields, folder / self.fields_path)
      load_one(self.issue_types, folder / self.issue_types_path)
      load_one(self.link_types, folder / self.link_types_path)
      load_one(self.resolutions, folder / self.resolutions_path)
      load_one(self.statuses, folder / self.statuses_path)
      self.projects.clear()
      for entry in load_or(folder / self.projects_path, default=[]):
         entry['versions'] = key_by(entry['versions'], 'id')
         self.projects[entry['id']] = entry

   def save(self, folder: pathlib.Path):
      save_one(self.fields, folder / self.fields_path)
      save_one(self.issue_types, folder / self.issue_types_path)
      save_one(self.link_types, folder / self.link_types_path)
      save_one(self.resolutions, folder / self.resolutions_path)
      save_one(self.statuses, folder / self.statuses_path)
      save_projects: dict[str, typing.Any] = {}
      for key, value in self.projects.items():
         final_value: dict[str, typing.Any] = {}
         for k, v in value.items():
            final_value[k] = v
         final_value['versions'] = list(final_value['versions'].values())
         save_projects[key] = final_value
      save_one(save_projects, folder / self.projects_path)

   def import_field(self, field: Field):
      self.fields[field['id']] = field

   def import_issue_type(self, issue_type: IssueType):
      self.issue_types[issue_type['id']] = issue_type

   def import_link_type(self, link_type: LinkType):
      self.link_types[link_type['id']] = link_type

   def import_resolution(self, resolution: Resolution):
      self.resolutions[resolution['id']] = resolution

   def import_status(self, status: Status):
      self.statuses[status['id']] = status

   def import_project(self, project: Project):
      self.projects[project['id']] = project

class Archive:
   def __init__(self, folder: pathlib.Path):
      self.folder = folder
      self.attachments_folder = self.folder / 'attachments'
      self.attachments_content_folder = self.attachments_folder / 'content'
      self.issues_folder = self.folder / 'issues'
      self.users_folder = self.folder / 'users'
      self.unknown_users_folder = self.users_folder / 'unknown'
      self.project_avatars_folder = self.folder / 'avatars/projects'
      self.users_avatars_folder = self.folder / 'avatars/users'

   def issue_ids(self) -> typing.Generator[str, None, None]:
      for path in self.issues_folder.iterdir():
         yield path.stem

   def issues(self) -> typing.Generator[Issue, None, None]:
      for path in self.issues_folder.iterdir():
         with open(path, 'r', encoding='utf-8') as file:
            yield json.load(file)

   def get_issue_path(self, issue_id: str) -> pathlib.Path:
      return self.issues_folder / (issue_id + '.json')

   def get_issue_data(self, issue_id: str) -> Issue | None:
      path = self.get_issue_path(issue_id)
      if not path.exists():
         return None
      with open(path, 'r', encoding='utf-8') as file:
         return json.load(file)

   def user_keys(self) -> typing.Generator[str, None, None]:
      for path in self.users_folder.iterdir():
         if path.is_file():
            yield urllib.parse.unquote_plus(path.stem)

   def users(self) -> typing.Generator[User, None, None]:
      for path in self.users_folder.iterdir():
         with open(path, 'r', encoding='utf-8') as file:
            yield json.load(file)

   def get_user_path(self, user_key: str, unknown=False) -> pathlib.Path:
      base_folder = self.unknown_users_folder if unknown else self.users_folder
      return base_folder / (urllib.parse.quote_plus(user_key) + '.json')

   def get_user_data(self, user_key: str) -> User | None:
      path = self.get_user_path(user_key, unknown=False)
      if not path.exists():
         return None
      with open(path, 'r', encoding='utf-8') as file:
         return json.load(file)

   def get_unknown_user_data(self, user_key: str) -> dict[str, typing.Any] | None:
      path = self.get_user_path(user_key, unknown=True)
      if not path.exists():
         return None
      with open(path, 'r', encoding='utf-8') as file:
         return json.load(file)

   def get_avatar_id(self, url: str):
      url_obj = urllib.parse.urlparse(url)
      queries = urllib.parse.parse_qs(url_obj.query)
      avatarid = queries['avatarId'][0]
      return avatarid

   def get_attachment_data_path(self, attach_id: str) -> pathlib.Path:
      return self.attachments_folder / (attach_id + '.json')

   def get_attachment_data(self, attach_id: str) -> Attachment | None:
      path = self.get_attachment_data_path(attach_id)
      if not path.exists():
         return None
      with open(path, 'r', encoding='utf-8') as file:
         return json.load(file)

   def get_attachment_content_path(self, attach_id: str, file_name: str) -> pathlib.Path:
      extension = pathlib.PurePath(file_name).suffix
      return self.attachments_content_folder / (attach_id + extension)

   def import_unknown_user(self, user_key: str, data: dict[str, typing.Any]):
      path = self.get_user_path(user_key, unknown=True)
      path.parent.mkdir(parents=True, exist_ok=True)
      with open(path, 'w', encoding='utf-8') as file:
         json.dump(data, file, indent=3)

   def import_user(self, user: User):
      path = self.get_user_path(user['key'], unknown=False)
      path.parent.mkdir(parents=True, exist_ok=True)
      with open(path, 'w', encoding='utf-8') as file:
         json.dump(user, file, indent=3)

   def import_issue(self, issue: Issue):
      path = self.get_issue_path(issue['id'])
      path.parent.mkdir(parents=True, exist_ok=True)
      with open(path, 'w', encoding='utf-8') as file:
         json.dump(issue, file, indent=3)

def key_by(items: list[dict[str, typing.Any]], key: str) -> dict[str, dict[str, typing.Any]]:
   result = {}
   for item in items:
      result[item[key]] = item
   return result

def load_or(path: pathlib.Path, default: typing.Any) -> typing.Any:
   if path.exists():
      with open(path, 'r', encoding='utf-8') as file:
         return json.load(file)
   return default

def load_one(data: dict[str, typing.Any], path: pathlib.Path):
   data.clear()
   for entry in load_or(path, []):
      data[entry['id']] = entry

def save_one(data: dict[str, typing.Any], path: pathlib.Path):
   path.parent.mkdir(parents=True, exist_ok=True)
   with open(path, 'w', encoding='utf-8') as file:
      json.dump(list(data.values()), file, indent=3)

class SecretComments:
   def __init__(self, path: pathlib.Path):
      with open(path, 'r', encoding='utf-8') as file:
         self.comments: dict[str, list[NewComment]] = json.load(file)

   def get(self, issue_id: str) -> list[NewComment]:
      return self.comments.get(issue_id, [])
