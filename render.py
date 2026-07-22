import dataclasses
import math
import os
import sys
import typing
import json
import itertools
import bisect
import re
import copy
import urllib.parse
import datetime
import pathlib
import zlib

import dotenv
import bs4
import natsort
import PIL.Image

import markup_relations
import mojira
import relations
import markup

from jiratypes import Attachment, Comment, Issue, NewAuthor, NewComment, Project, Revision, RevisionChange, UnknownUser, User, Version
from web import (HtmlFile, Tag, add_metadata, append_class, append_desc_item, append_row, html_diff, html_to_text, inline_list, make_file,
   make_table, new_content_tag, relative_link, relative_path, render_date, render_date_range, render_datetime, render_time, same_day, write_html
)
from display import (CachedFieldInfo, CachedGroupInfo, CachedIssue, CachedMetaInfo, CachedProjectInfo, CachedUser, CachedValueInfo,
   CachedVersionInfo, DisplayCache, HistoricFields, HistoricProjectValue, HistoricValue, InitialData, MergedRevision, RenderableComment,
   RenderableMention, ValueDisplay, ViewPerms, category_splitter, format_number, revision_order_key, get_avatar_path,
   get_link_dir, get_user, import_fake_missing_data, issue_detail_links, label_splitter, merge_revisions,
   project_detail_links, try_project, user_role
)

@dataclasses.dataclass
class ProjectPage:
   main: HtmlFile
   versions: HtmlFile | None
   issues: HtmlFile
   versions_folder: pathlib.PurePath

   def get_version_path(self, version: Version) -> pathlib.PurePath:
      return self.versions_folder / (version['name'].replace('/', '_') + '.html')

@dataclasses.dataclass
class FieldPage:
   page: HtmlFile
   values_folder: pathlib.PurePath

   def get_value_path(self, value_name: str) -> pathlib.PurePath:
      return self.values_folder / (value_name.replace('/', '_') + '.html')

@dataclasses.dataclass
class GroupPage:
   users: HtmlFile
   comments: HtmlFile | None

@dataclasses.dataclass
class Website:
   root: pathlib.Path
   web_export: pathlib.PurePath
   home: HtmlFile
   all_issues_list: HtmlFile
   all_users_list: HtmlFile
   all_secret_comments_list: HtmlFile | None
   issues_folder: pathlib.PurePath
   users_folder: pathlib.PurePath
   group_pages: dict[str, GroupPage]
   project_pages: dict[str, ProjectPage]
   field_pages: dict[str, FieldPage]
   meta_pages: dict[mojira.META_TYPE, FieldPage]
   archive: mojira.Archive
   metas: mojira.ArchiveMetas
   secret_comments: mojira.SecretComments
   keys: relations.KeyLookups
   markup_source: markup.MarkupSource
   perms: ViewPerms
   cache: DisplayCache

   def get_issue_path(self, issue: Issue) -> pathlib.PurePath:
      return self.get_issue_key_path(issue['key'])

   def get_issue_key_path(self, issue_key: str) -> pathlib.PurePath:
      return self.issues_folder / (issue_key + '.html')

   def get_user_path(self, user: User | UnknownUser) -> pathlib.PurePath:
      return self.get_user_name_path(user['name'])

   def get_user_name_path(self, username: str) -> pathlib.PurePath:
      return self.users_folder / (mojira.encode_user_string(username.lower())[:100] + '.html')

def make_jira_file(root: pathlib.Path, path: pathlib.PurePath, title: str) -> HtmlFile:
   file = make_file(path, title)
   file.page.head.append(file.page.soup.new_tag('link', rel='icon', type='image/x-icon', href=relative_link(root, file.path, pathlib.PurePath('data/assets/favicon.ico'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('web/css/misode-reset.css'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('web/css/misode-style.css'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('data/assets/mojira.css'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('web/css/style.css'))))
   file.page.head.append(file.page.soup.new_tag('script', defer='', src=relative_link(root, file.path, pathlib.PurePath('web/js/main.js'))))
   return file

def save_file(website: Website, file: HtmlFile):
   write_html(website.root / file.path, file.page)

def main():
   print('Loading...')
   PIL.Image.MAX_IMAGE_PIXELS = 16384 * 16384
   dotenv.load_dotenv()
   root = pathlib.Path(os.environ['ARCHIVE_ROOT'])
   archive = mojira.Archive(pathlib.Path(os.environ['ARCHIVE_DATA']))
   metas = mojira.ArchiveMetas()
   metas.load(archive.folder)
   import_fake_missing_data(archive, metas)
   rels = relations.RelationsBundle(
      keys=relations.KeyLookups(),
      user=relations.UserRelations(),
      fields=relations.FieldRelations()
   )
   rels.load(pathlib.Path(os.environ['ARCHIVE_RELATIONS']))
   markup_source = markup.MarkupSource(pathlib.Path(os.environ['ARCHIVE_MARKUP']))
   markup_rels = markup_relations.MarkupRelations()
   markup_rels.load(pathlib.Path(os.environ['ARCHIVE_MARKUP_RELATIONS']))
   secret_comments = mojira.SecretComments(pathlib.Path(os.environ['ARCHIVE_SECRET_COMMENTS']))
   secret_comments.remove_uuid_comments()
   meta_list: list[mojira.META_TYPE] = ['resolution', 'status']
   web_export = pathlib.PurePath(os.environ['WEB_EXPORT'])
   perms_data = json.loads(os.environ['WEB_PERMS'])
   perms = ViewPerms(perms_data)
   cache = DisplayCache(archive, metas, rels, markup_source, markup_rels, secret_comments, perms)
   website = Website(
      root=root,
      web_export=web_export,
      home=make_jira_file(root, web_export / 'home.html', 'Mojira Archive'),
      all_issues_list=make_jira_file(root, web_export / 'issues.html', 'All Issues'),
      all_users_list=make_jira_file(root, web_export / 'users.html', 'All Users'),
      all_secret_comments_list=make_jira_file(root, web_export / 'secret_comments.html', 'Secret Comments') if not perms.hidden_secret_comments else None,
      issues_folder=web_export / 'issues',
      users_folder=web_export / 'users',
      project_pages={},
      field_pages={},
      meta_pages={},
      group_pages={},
      archive=archive,
      metas=metas,
      secret_comments=secret_comments,
      keys=rels.keys,
      markup_source=markup_source,
      perms=perms,
      cache=cache
   )
   for value in cache.projects.values():
      key = value.project['key']
      full_title = f'[{key}] {value.project['name']}'
      website.project_pages[value.project['id']] = ProjectPage(
         make_jira_file(root, web_export / 'projects' / (key + '.html'), full_title),
         make_jira_file(root, web_export / 'projects' / key / 'versions.html', full_title) if len(value.versions) > 0 else None,
         make_jira_file(root, web_export / 'projects' / key / 'issues.html', full_title),
         web_export / 'projects' / key / 'versions'
      )
   for field in cache.fields.values():
      website.field_pages[field.id] = FieldPage(
         make_jira_file(root, web_export / 'fields' / (field.name + '.html'), field.name),
         web_export / 'fields' / field.name
      )
   for meta_id in meta_list:
      meta = cache.metas[meta_id]
      website.meta_pages[meta_id] = FieldPage(
         make_jira_file(root, web_export / 'fields' / (meta.name + '.html'), meta.name),
         web_export / 'fields' / meta.name
      )
   for group in cache.groups.values():
      if len(group.comments) > 0:
         comments = make_jira_file(root, web_export / 'groups' / group.id / 'comments.html', group.id)
      else:
         comments = None
      website.group_pages[group.id] = GroupPage(
         make_jira_file(root, web_export / 'groups' / group.id / 'users.html', group.id),
          comments
      )

   print('Rendering...')
   to_render = sys.argv
   if 'all' in to_render:
      to_render.extend(['home', 'fields', 'metas', 'project_main', 'project_versions', 'project_issues', 'project_version_issues', 'field_issues', 'meta_issues', 'issues_list', 'issues', 'users', 'group_users', 'group_comments', 'users_list', 'secret_comments'])
   if 'issue_lists' in to_render:
      to_render.extend(['project_issues', 'project_version_issues', 'field_issues', 'meta_issues', 'issues_list'])
   if 'user_lists' in to_render:
      to_render.extend(['group_users', 'users_list'])
   if 'groups' in to_render:
      to_render.extend(['group_users', 'group_comments'])
   if 'home' in to_render:
      print('Home...')
      make_home_page(website, website.home)
      save_file(website, website.home)
   if 'metas' in to_render:
      print('Metas...')
      for meta_id in meta_list:
         print('\t' + meta_id)
         field_page = website.meta_pages[meta_id]
         make_meta_page(website, field_page.page, cache.metas[meta_id])
         save_file(website, field_page.page)
   if 'fields' in to_render:
      print('Fields...')
      for field in reversed(cache.fields.values()):
         print('\t' + field.id)
         field_page = website.field_pages[field.id]
         make_field_page(website, field_page.page, field)
         save_file(website, field_page.page)
   project_order = list(reversed(cache.projects.values()))
   if 'project_main' in to_render:
      print('Project main...')
      for info in project_order:
         print('\t' + info.project['key'])
         project_page = website.project_pages[info.project['id']]
         make_project_main_page(website, project_page.main, info)
         save_file(website, project_page.main)
   if 'project_versions' in to_render:
      print('Project versions...')
      for info in project_order:
         print('\t' + info.project['key'])
         project_page = website.project_pages[info.project['id']]
         if project_page.versions is not None:
            make_project_versions_page(website, project_page.versions, info)
            save_file(website, project_page.versions)
   if 'project_issues' in to_render:
      print('Project issues...')
      for info in project_order:
         print('\t' + info.project['key'])
         project_page = website.project_pages[info.project['id']]
         make_project_issues_page(website, project_page.issues, info)
         save_file(website, project_page.issues)
   if 'project_version_issues' in to_render:
      print('Project versions issues...')
      for info in project_order:
         print('\t' + info.project['key'])
         project_page = website.project_pages[info.project['id']]
         for vinfo in info.versions.values():
            print('\t\t' + vinfo.version['name'])
            full_title = f'[{info.project['key']}] {vinfo.version['name']}'
            file = make_jira_file(root, project_page.get_version_path(vinfo.version), full_title)
            make_version_page(website, file, vinfo)
            save_file(website, file)
   if 'meta_issues' in to_render:
      print('Meta issues...')
      for meta_id in meta_list:
         print('\t' + meta_id)
         field_page = website.meta_pages[meta_id]
         field_info = cache.metas[meta_id]
         for value_info in reversed(field_info.values.values()):
            print('\t\t' + value_info.display.name)
            full_title = f'[{field_info.name}] {value_info.display.name}'
            file = make_jira_file(root, field_page.get_value_path(value_info.display.name), full_title)
            make_meta_value_page(website, file, field_info, value_info)
            save_file(website, file)
   if 'field_issues' in to_render:
      print('Field issues...')
      for field_info in reversed(cache.fields.values()):
         print('\t' + field_info.id)
         field_page = website.field_pages[field_info.id]
         for value_info in reversed(field_info.values.values()):
            print('\t\t' + value_info.display.name)
            full_title = f'[{field_info.name}] {value_info.display.name}'
            file = make_jira_file(root, field_page.get_value_path(value_info.display.name), full_title)
            make_field_value_page(website, file, field_info, value_info)
            save_file(website, file)
   if 'issues_list' in to_render:
      print('All issues...')
      make_all_issues_page(website, website.all_issues_list)
      save_file(website, website.all_issues_list)
   if 'issues' in to_render:
      print('Issues...')
      for i, issue_id in enumerate(cache.all_issues):
         issue = cache.issue_getter(issue_id)
         if i % 1000 == 0:
            print(f'\t== {i} ==')
         print('\t' + issue.issue['key'])
         path = website.get_issue_path(issue.issue)
         full_title = f'[{issue.issue['key']}] {issue.issue['fields']['summary']}'
         file = make_jira_file(root, path, full_title)
         make_issue_page(website, file, issue)
         save_file(website, file)
      print('Moved issues...')
      for issue_key, issue_id in rels.keys.issue_keys.items():
         if issue_id in cache.valid_issues:
            issue = cache.just_issue_getter(issue_id)
            if issue['key'] != issue_key:
               print('\t' + issue_key)
               from_path = website.get_issue_key_path(issue_key)
               to_path = website.get_issue_path(issue)
               relative = relative_path(root, from_path, root / to_path)
               from_full = root / from_path
               if from_full.is_symlink():
                  if from_full.readlink() != relative:
                     from_full.unlink()
                     from_full.symlink_to(relative)
               else:
                  from_full.symlink_to(relative)
   if 'group_users' in to_render:
      print('Group users...')
      for group in reversed(cache.groups.values()):
         print('\t\t' + group.id)
         group_page = website.group_pages[group.id]
         make_group_users_page(website, group_page.users, group)
         save_file(website, group_page.users)
   if 'group_comments' in to_render:
      print('Group comments...')
      for group in cache.groups.values():
         print('\t\t' + group.id)
         group_page = website.group_pages[group.id]
         if group_page.comments is not None:
            make_group_comments_page(website, group_page.comments, group)
            save_file(website, group_page.comments)
   if 'secret_comments' in to_render:
      print('Secret comments...')
      if website.all_secret_comments_list is not None:
         make_secret_comments_page(website, website.all_secret_comments_list)
         save_file(website, website.all_secret_comments_list)
   if 'users_list' in to_render:
      print('All users...')
      make_all_users_page(website, website.all_users_list)
      save_file(website, website.all_users_list)
   if 'users' in to_render:
      print('Users...')
      for i, user_key in enumerate(cache.all_users):
         user = cache.user_getter(user_key)
         if i % 1000 == 0:
            print(f'\t== {i} ==')
         print('\t' + user.user['name'])
         path = website.get_user_path(user.user)
         file = make_jira_file(root, path, user.user['displayName'])
         make_user_page(website, file, user)
         save_file(website, file)

# all pages
def main_content(website: Website, file: HtmlFile) -> bs4.Tag:
   file.page.body.append(make_generic_header(website, file))
   # content for misode.css
   content = file.page.soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   file.page.body.append(make_generic_footer(website, file))
   return content

def make_generic_header(website: Website, file: HtmlFile) -> bs4.Tag:
   header = new_content_tag(file.page.soup, 'header', [
      # header-main for misode.css
      new_content_tag(file.page.soup, 'a', 'Mojira Archive', attrs={'class': 'header-main', 'href': relative_link(website.root, file.path, website.home.path)}),
      new_content_tag(file.page.soup, 'form', attrs={'id': 'jump', 'class': 'jump'}, content=[
         file.page.soup.new_tag('input', attrs={'id': 'jump-input', 'type': 'text', 'name': 'jump', 'placeholder': 'Issue or User'}),
         new_content_tag(file.page.soup, 'button', attrs={'id': 'jump-submit', 'type': 'submit'}, content='Go'),
         new_content_tag(file.page.soup, 'script', f'window.jumpStart = "{relative_path(website.root, file.path, website.root / website.web_export)}";')
      ])
   ])
   file.page.head.append(file.page.soup.new_tag('script', defer='', src=relative_link(website.root, file.path, pathlib.PurePath('web/js/jump.js'))))
   return header

def make_generic_footer(website: Website, file: HtmlFile) -> bs4.Tag:
   footer = new_content_tag(file.page.soup, 'footer', [
      new_content_tag(file.page.soup, 'p', [
         'Pre-migration archive of ',
         new_content_tag(file.page.soup, 'a', attrs={'href': 'https://bugs.mojang.com'}, content='bugs.mojang.com'),
         ' by ',
         new_content_tag(file.page.soup, 'a', attrs={'href': 'https://github.com/tryashtar'}, content='tryashtar'),
         '.'
      ])
   ])
   return footer

def include_wiki_rendering(website: Website, file: HtmlFile):
   file.page.head.append(file.page.soup.new_tag('link', attrs={'rel': 'preload', 'as': 'style', 'href': relative_link(website.root, file.path, pathlib.PurePath('web/css/jira-wiki.css'))}))
   file.page.head.append(file.page.soup.new_tag('link', attrs={'rel': 'preload', 'as': 'style', 'href': relative_link(website.root, file.path, pathlib.PurePath('web/css/wiki-tweaks.css'))}))

def fix_markup(website: Website, file: HtmlFile, parsed: markup.ParsedMarkup):
   for entry in parsed.issues:
      issue_id = website.keys.get_issue_key(entry.key)
      if issue_id in website.cache.valid_issues:
         entry.tag.attrs[entry.attr] = relative_link(website.root, file.path, website.get_issue_key_path(entry.key))
      else:
         del entry.tag.attrs[entry.attr]
         del entry.tag.attrs['title']
   for entry in parsed.users:
      _user_key = website.keys.get_user_key(entry.username)
      entry.tag.attrs[entry.attr] = relative_link(website.root, file.path, website.get_user_name_path(entry.username))
   for entry in parsed.attachments + parsed.thumbnails:
      data = website.cache.attachment_getter(entry.id)
      path = relative_path(website.root, file.path, website.archive.get_attachment_content_path(entry.id, data['filename']))
      entry.tag.attrs[entry.attr] = urllib.parse.quote(str(path))
   for entry in parsed.thumbnails:
      append_class(entry.tag, 'thumbnail')
   for entry in parsed.icons:
      path = relative_path(website.root, file.path, website.archive.folder / 'assets/images' / entry.path)
      entry.tag.attrs[entry.attr] = urllib.parse.quote(str(path))

def embed_wiki(website: Website, file: HtmlFile, parsed: markup.ParsedMarkup) -> bs4.Tag:
   cloned = parsed.clone()
   fix_markup(website, file, cloned)
   return new_content_tag(file.page.soup, 'div', attrs={'class': 'jira-wiki'}, content=[
      new_content_tag(file.page.soup, 'template', attrs={'shadowrootmode': 'open'}, content=[
         file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('web/css/jira-wiki.css'))),
         file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('data/assets/mojira.css'))),
         file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('web/css/wiki-tweaks.css'))),
         new_content_tag(file.page.soup, 'div', cloned.root)
      ])
   ])

# grid pages
def make_home_page(website: Website, file: HtmlFile):
   soup = file.page.soup
   content = main_content(website, file)

   issue_count = len(website.cache.all_issues)
   user_count = len(website.cache.all_users)
   add_metadata(file, 'Mojira Archive', f'{format_number(issue_count)} issues, {format_number(user_count)} users', None)

   full_list_grid: list[list[Tag]] = [
      [
         new_content_tag(soup, 'a', attrs={'class': 'tile-grid-name', 'href': relative_link(website.root, file.path, website.all_issues_list.path)}, content='All Issues'),
         f'{format_number(issue_count)} issues'
      ],
      [
         new_content_tag(soup, 'a', attrs={'class': 'tile-grid-name', 'href': relative_link(website.root, file.path, website.all_users_list.path)}, content='All Users'),
         f'{format_number(user_count)} users'
      ]
   ]
   if website.all_secret_comments_list is not None:
      comment_count = sum(len(x) for x in website.secret_comments.comments.values())
      full_list_grid.append([
         new_content_tag(soup, 'a', attrs={'class': 'tile-grid-name', 'href': relative_link(website.root, file.path, website.all_secret_comments_list.path)}, content='Secret Comments'),
         f'{format_number(comment_count)} comments'
      ])

   main = build_grid_main(soup, [
      # tile-grid-name for style.css
      ('Full Lists', build_tile_grid(soup, full_list_grid)),
      ('Projects', build_tile_grid(soup, (project_grid_entry(website, file, x) for x in website.cache.projects.values()))),
      ('Fields', build_tile_grid(soup,
         [meta_grid_entry(website, file, website.cache.metas[x]) for x in website.meta_pages.keys()]
         + [field_grid_entry(website, file, x) for x in website.cache.fields.values()]
      )),
      ('User Groups', build_tile_grid(soup, (group_grid_entry(website, file, x) for x in website.cache.groups.values())))
   ])
   content.append(main)

def make_meta_page(website: Website, file: HtmlFile, meta: CachedMetaInfo):
   soup = file.page.soup
   content = main_content(website, file)

   add_metadata(file, meta.name, f'{len(meta.values)} values', None)

   main = build_grid_main(soup, [
      (meta.name, build_tile_grid(soup, (meta_value_grid_entry(website, file, meta.id, x) for x in meta.values.values())))
   ])
   content.append(main)

def make_field_page(website: Website, file: HtmlFile, field: CachedFieldInfo):
   soup = file.page.soup
   content = main_content(website, file)

   add_metadata(file, field.name, f'{len(field.values)} values', None)

   main = build_grid_main(soup, [
      (field.name, build_tile_grid(soup, (field_value_grid_entry(website, file, field.id, x) for x in field.values.values())))
   ])
   content.append(main)

def build_grid_main(soup: bs4.BeautifulSoup, grids: list[tuple[Tag, Tag]]) -> bs4.Tag:
   # tile-grid-main for style.css
   main = soup.new_tag('div', attrs={'class': 'tile-grid-main'})
   for title, grid in grids:
      main.append(new_content_tag(soup, 'h2', title))
      main.append(grid)
   return main

def build_tile_grid(soup: bs4.BeautifulSoup, entries: typing.Iterable[list[Tag]]) -> bs4.Tag:
   # tile-grid for style.css
   grid = soup.new_tag('div', attrs={'class': 'tile-grid'})
   for tags in entries:
      grid.append(new_content_tag(soup, 'div', tags))
   return grid

def project_grid_entry(website: Website, file: HtmlFile, info: CachedProjectInfo) -> list[Tag]:
   project_page = website.project_pages[info.project['id']]
   content: list[Tag] = [
      project_link(website, file, info.project, with_icon=True),
      # tile-grid-name for style.css
      new_content_tag(file.page.soup, 'span', attrs={'class': 'tile-grid-name'}, content=info.project['name']),
      new_content_tag(file.page.soup, 'a', f'{format_number(len(info.issues))} issues', attrs={'href': relative_link(website.root, file.path, project_page.issues.path)}),
   ]
   if project_page.versions is not None:
      content.append(new_content_tag(file.page.soup, 'a', f'{format_number(len(info.versions))} versions', attrs={'href': relative_link(website.root, file.path, project_page.versions.path)}))
   return content

def meta_grid_entry(website: Website, file: HtmlFile, meta: CachedMetaInfo) -> list[Tag]:
   link = relative_link(website.root, file.path, website.meta_pages[meta.id].page.path)
   content: list[Tag] = [
      # tile-grid-name for style.css
      new_content_tag(file.page.soup, 'a', attrs={'class': 'tile-grid-name', 'href': link}, content=meta.name),
   ]
   if len(meta.values) > 15:
      content.append(f'{format_number(len(meta.values))} values')
   else:
      tags = inline_list(file.page.soup, (meta_link_display(website, file, meta.id, x.display) for x in meta.values.values()))
      content.append(tags)
   return content

def field_grid_entry(website: Website, file: HtmlFile, field: CachedFieldInfo) -> list[Tag]:
   link = relative_link(website.root, file.path, website.field_pages[field.id].page.path)
   content: list[Tag] = [
      # tile-grid-name for style.css
      new_content_tag(file.page.soup, 'a', attrs={'class': 'tile-grid-name', 'href': link}, content=field.name),
   ]
   if len(field.values) > 15:
      content.append(f'{format_number(len(field.values))} values')
   else:
      tags = inline_list(file.page.soup, (field_link_display(website, file, field.id, x.display) for x in field.values.values()))
      content.append(tags)
   return content

def group_grid_entry(website: Website, file: HtmlFile, group: CachedGroupInfo) -> list[Tag]:
   title = group_name(website, file, group.id)
   # tile-grid-name for style.css
   append_class(title, 'tile-grid-name')
   content: list[Tag] = [
      title,
      new_content_tag(file.page.soup, 'a', f'{format_number(len(group.users))} users', attrs={'href': relative_link(website.root, file.path, website.group_pages[group.id].users.path)}),
   ]
   group_page = website.group_pages[group.id]
   if group_page.comments is not None:
      comment_count = sum(len(x) for x in group.comments.values())
      content.append(new_content_tag(file.page.soup, 'a', f'{format_number(comment_count)} restricted comments', attrs={'href': relative_link(website.root, file.path, group_page.comments.path)}))
   return content

def meta_value_grid_entry(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, value: CachedValueInfo) -> list[Tag]:
   content: list[Tag] = [
      # tile-grid-name for style.css
      new_content_tag(file.page.soup, 'span', attrs={'class': 'tile-grid-name'}, content=meta_link_display(website, file, meta_id, value.display))
   ]
   content.append(new_content_tag(file.page.soup, 'p', f'{format_number(len(value.issues))} issues'))
   if value.display.description is not None:
      # tile-grid-desc for style.css
      content.append(new_content_tag(file.page.soup, 'p', attrs={'class': 'tile-grid-desc'}, content=value.display.description))
   return content

def field_value_grid_entry(website: Website, file: HtmlFile, field_id: str, value: CachedValueInfo) -> list[Tag]:
   content: list[Tag] = [
      # tile-grid-name for style.css
      new_content_tag(file.page.soup, 'span', attrs={'class': 'tile-grid-name'}, content=field_link_display(website, file, field_id, value.display))
   ]
   content.append(new_content_tag(file.page.soup, 'p', f'{format_number(len(value.issues))} issues'))
   if value.display.description is not None:
      # tile-grid-desc for style.css
      content.append(new_content_tag(file.page.soup, 'p', attrs={'class': 'tile-grid-desc'}, content=value.display.description))
   return content

# info pages
def make_project_main_page(website: Website, file: HtmlFile, info: CachedProjectInfo):
   soup = file.page.soup
   content = main_content(website, file)

   top = build_info_top(soup, project_key(website, file, info.project, with_icon=True), info.project['name'])
   # issue-body for misode.css
   body: list[bs4.Tag] = []
   if info.description is not None:
      body.append(info.description)
      desc_text = html_to_text(info.description)
   else:
      desc_text = None

   add_metadata(file, info.project['name'], desc_text, info.project['avatarUrls']['48x48'])

   details = build_info_details(soup, project_details(website, file, info))
   main = build_info_main(soup, top, body, details, None, None)
   content.append(main)

def project_details(website: Website, file: HtmlFile, info: CachedProjectInfo) -> typing.Generator[tuple[Tag, Tag]]:
   project_page = website.project_pages[info.project['id']]
   if website.perms.hidden_json_data:
      data_link = None
   else:
      data_link = relative_path(website.root, file.path, website.archive.folder / website.metas.projects_path)
   links = project_detail_links(info.project, data_link)
   yield ('Project Lead:', user_link(website, file, info.project['lead']))
   yield ('Issues:', new_content_tag(file.page.soup, 'a', format_number(len(info.issues)), attrs={'href': relative_link(website.root, file.path, project_page.issues.path)}))
   if project_page.versions is not None:
      yield ('Versions:', new_content_tag(file.page.soup, 'a', format_number(len(info.versions)), attrs={'href': relative_link(website.root, file.path, project_page.versions.path)}))
   yield ('Links:', build_link_list(file.page.soup, 'ul', links))

def make_version_page(website: Website, file: HtmlFile, info: CachedVersionInfo):
   soup = file.page.soup
   content = main_content(website, file)

   project = website.cache.projects[str(info.version['projectId'])].project
   top = build_info_top(soup, project_link(website, file, project, with_icon=True), info.version['name'])
   body: list[bs4.Tag] = []
   if (description := info.version.get('description')) is not None and len(description) > 0:
      desc = new_content_tag(soup, 'div', description)
      body.append(desc)

   add_metadata(file, info.version['name'], description, project['avatarUrls']['48x48'])

   details = build_info_details(soup, version_details(website, file, info.version))
   main = build_info_main(soup, top, body, details, None, None)
   content.append(main)

   tables: list[VirtualTable] = []
   tab_data: list[InfoTabData] = []
   if len(info.affected) > 0:
      affected_table = create_issue_list(website, file, 'affected', website.cache.get_issues(info.affected))
      tables.append(affected_table)
      tab_data.append(InfoTabData(
         'affected',
         ['Affected Issues', count_badge(soup, len(info.affected))],
         [affected_table.filters, affected_table.table]
      ))
   if len(info.fixed) > 0:
      fixed_table = create_issue_list(website, file, 'fixed', website.cache.get_issues(info.affected))
      tables.append(fixed_table)
      tab_data.append(InfoTabData(
         'fixed',
         ['Fixed Issues', count_badge(soup, len(info.fixed))],
         [fixed_table.filters, fixed_table.table]
      ))
   tabs = build_info_tabs(soup, tab_data, orderable=False)
   main.append(tabs)
   add_table_scripts(website, file, [(x.data, x.rows) for x in tables])

def version_details(website: Website, file: HtmlFile, version: Version) -> typing.Generator[tuple[Tag, Tag]]:
   if 'startDate' in version:
      yield ('Start Date:', render_date(file.page.soup, datetime.datetime.fromisoformat(version['startDate'])))
   if 'releaseDate' in version:
      yield ('Release Date:', render_date(file.page.soup, datetime.datetime.fromisoformat(version['releaseDate'])))
   yield ('Released:', 'Yes' if version['released'] else 'No')
   yield ('Archived:', 'Yes' if version['archived'] else 'No')

def make_user_page(website: Website, file: HtmlFile, info: CachedUser):
   soup = file.page.soup
   content = main_content(website, file)

   include_wiki_rendering(website, file)
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('web/css/diff.css'))))

   ref = user_reference(website, file, info.user)
   top = build_info_top(soup, None, ref.outer)

   add_metadata(file, info.user['displayName'], info.user['name'], info.user['avatarUrls']['48x48'])

   details = build_info_details(soup, user_details(website, file, info.user))
   main = build_info_main(soup, top, [], details, None, None)
   content.append(main)

   reported_and_created = [x for x in info.reported if x in info.created]
   reported_not_created = [x for x in info.reported if x not in info.created]
   created_not_reported = [x for x in info.created if x not in info.reported]
   issue_list = reported_and_created + created_not_reported + reported_not_created
   tables: list[VirtualTable] = []
   pages: list[PageSection] = []
   tab_data: list[InfoTabData] = []
   if len(issue_list) > 0:
      reported_table = create_issue_list(website, file, 'reported', website.cache.get_issues(issue_list))
      tables.append(reported_table)
      tab_data.append(InfoTabData(
         'reported',
         ['Reported Issues', count_badge(soup, len(issue_list))],
         [reported_table.filters, reported_table.table]
      ))
   if len(info.assigned) > 0:
      assigned_table = create_issue_list(website, file, 'assigned', website.cache.get_issues(info.assigned))
      tables.append(assigned_table)
      tab_data.append(InfoTabData(
         'assigned',
         ['Assigned Issues', count_badge(soup, len(info.assigned))],
         [assigned_table.filters, assigned_table.table]
      ))
   comment_section = issue_comments(website, file, info.comments)
   pages.append(comment_section)
   tab_data.append(InfoTabData(
      'comments',
      ['Comments', count_badge(soup, len(info.comments))],
      [comment_section.controls, comment_section.section]
   ))
   if len(info.attachments) > 0:
      attachment_section = user_attachments(website, file, info.attachments)
      pages.append(attachment_section)
      tab_data.append(InfoTabData(
         'attachments',
         ['Attachments', count_badge(soup, sum(len(x) for x in info.attachments.values()))],
         [attachment_section.controls, attachment_section.section]
      ))
   activity_section = user_activity(website, file, info.changes)
   pages.append(activity_section)
   tab_data.append(InfoTabData(
      'activity',
      ['Activity', count_badge(soup, sum(len(x) for x in info.changes.values()))],
      [activity_section.controls, activity_section.section]
   ))
   if len(info.mentions) > 0:
      mention_section = issue_mentions(website, file, info.mentions)
      pages.append(mention_section)
      tab_data.append(InfoTabData(
         'mentions',
         ['Mentions', count_badge(soup, len(info.mentions))],
         [mention_section.controls, mention_section.section]
      ))
   tabs = build_info_tabs(soup, tab_data, orderable=True)
   main.append(tabs)
   add_table_scripts(website, file, [(x.data, x.rows) for x in tables])
   add_page_scripts(website, file, [(x.data, x.content) for x in pages if x.data is not None])

def user_details(website: Website, file: HtmlFile, user: User | UnknownUser) -> typing.Generator[tuple[Tag, Tag]]:
   yield ('Username:', user['name'])
   yield ('User Key:', user['key'])
   yield ('Time Zone:', user['timeZone'])
   yield ('Active:', 'Yes' if user['active'] else 'No')
   if 'groups' in user:
      yield ('Deleted:', 'Yes' if user['deleted'] else 'No')
      group_list = new_content_tag(file.page.soup, 'ul', content=[
         new_content_tag(file.page.soup, 'li', group_link(website, file, x['name'])) for x in user['groups']['items']
      ])
      yield ('Groups:', group_list)
      data_link = relative_path(website.root, file.path, website.archive.get_user_path(user['key']))
   else:
      yield ('Unknown User:', 'Yes')
      data_link = relative_path(website.root, file.path, website.archive.get_user_path(user['key'], unknown=True))
   if not website.perms.hidden_json_data:
      links = [('JSON', urllib.parse.quote(str(data_link)))]
      yield ('Links:', build_link_list(file.page.soup, 'ul', links))

def make_issue_page(website: Website, file: HtmlFile, issue: CachedIssue):
   soup = file.page.soup
   content = main_content(website, file)

   key = issue.issue['key']
   fields = issue.issue['fields']
   summary = fields['summary']
   project_info = website.cache.projects.get(fields['project'])
   project = None if project_info is None else project_info.project
   full_title = f'[{key}] {summary}'

   include_wiki_rendering(website, file)
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('web/css/diff.css'))))

   top = issue_top(website, file, project, key, summary)

   if issue.description is not None:
      desc = embed_wiki(website, file, issue.description)
      desc_text = html_to_text(desc)
   else:
      desc = None
      desc_text = None
   if issue.environment is not None:
      env = embed_wiki(website, file, issue.environment)
   else:
      env = None
   impact = fields.get('customfield_11801')
   body = issue_body(soup, desc, env, impact)

   details = build_info_details(soup, issue_details(website, file, issue.issue))
   linked = issue_links(website, file, issue.linked_issues)
   image_url = project['avatarUrls']['48x48'] if project is not None else None
   if len(fields['attachment']) > 0:
      attaches = issue_attachments(website, file, fields['attachment'])
      for entry in fields['attachment']:
         attach = website.cache.attachment_getter(entry)
         if attach['mimeType'].startswith('image/'):
            image_url = attach['content']
            break
   else:
      attaches = None
   main = build_info_main(soup, top, body, details, linked, attaches)
   # misode does this
   main.attrs['id'] = 'issue'
   content.append(main)

   add_metadata(file, full_title, desc_text, image_url)

   comment_section = issue_comments(website, file, issue.comments)
   history_section = issue_history(website, file, issue, issue.issue['changelog']['histories'])
   pages: list[PageSection] = [comment_section, history_section]
   tab_data: list[InfoTabData] = [
      InfoTabData(
         'comments',
         ['Comments', count_badge(soup, len(issue.comments))],
         [comment_section.controls, comment_section.section]
      ),
      InfoTabData(
         'history',
         ['History', count_badge(soup, len(issue.issue['changelog']['histories']))],
         [history_section.controls, history_section.section]
      )
   ]
   if len(issue.mentions) > 0:
      mention_section = issue_mentions(website, file, issue.mentions)
      pages.append(mention_section)
      tab_data.append(InfoTabData(
         'mentions',
         ['Mentions', count_badge(soup, len(issue.mentions))],
         [mention_section.controls, mention_section.section]
      ))
   tabs = build_info_tabs(soup, tab_data, orderable=True)
   main.append(tabs)
   add_page_scripts(website, file, [(x.data, x.content) for x in pages if x.data is not None])

def issue_details(website: Website, file: HtmlFile, issue: Issue) -> typing.Generator[tuple[Tag, Tag]]:
   soup = file.page.soup
   fields = issue['fields']
   yield issue_detail_meta(website, file, 'resolution', fields['resolution'])
   is_resolved = fields['resolution'] is not None
   resolved_statuses = ('5',)
   unresolved_statuses = ('1', '4')
   if (is_resolved and fields['status'] not in resolved_statuses) or (not is_resolved and fields['status'] not in unresolved_statuses):
      yield issue_detail_meta(website, file, 'status', fields['status'])
   if (security := fields.get('security')) is not None:
      yield issue_detail_field(website, file, 'security', security['id'])
   if (reporter := fields.get('reporter')) is not None:
      yield ('Reporter:', user_link(website, file, reporter))
   if (creator := fields.get('creator')) is not None and reporter != creator:
      yield ('Creator:', user_link(website, file, creator))
   if (team := fields.get('customfield_11800')) is not None:
      yield ('Partner Team:', team)
   if (assignee := fields.get('assignee')) is not None:
      yield ('Assignee:', user_link(website, file, assignee))
   yield ('Created:', render_datetime(soup, datetime.datetime.fromisoformat(fields['created'])))
   yield ('Updated:', render_datetime(soup, datetime.datetime.fromisoformat(fields['updated'])))
   if (triaged := fields.get('customfield_12201')) is not None:
      yield ('Triaged:', render_datetime(soup, datetime.datetime.fromisoformat(triaged)))
   if (resolved := fields['resolutiondate']) is not None:
      yield ('Resolved:', render_datetime(soup, datetime.datetime.fromisoformat(resolved)))
   yield ('Votes:', count_badge(soup, fields['votes']['votes']))
   yield ('Watchers:', count_badge(soup, fields['watches']['watchCount']))
   if (confirmed := fields.get('customfield_10500')) is not None:
      yield issue_detail_field(website, file, 'customfield_10500', confirmed['id'])
   if (priority := fields.get('priority')) is not None:
      yield issue_detail_field(website, file, 'priority', priority['id'])
   if (mpriority := fields.get('customfield_12200')) is not None:
      yield issue_detail_field(website, file, 'customfield_12200', mpriority['id'])
   if (ado := fields.get('customfield_11500')) is not None:
      yield ('ADO:', ado)
   if (area := fields.get('customfield_12800')) is not None:
      yield issue_detail_field(website, file, 'customfield_12800', area['id'])
   if (category := fields.get('customfield_11901')) is not None:
      category_list = inline_list(soup, map(lambda x: field_link(website, file, 'customfield_11901', x['id']), category))
      yield (issue_detail_field_label(website, file, 'customfield_11901'), category_list)
   if (components := fields.get('components')) is not None and len(components) > 0:
      component_list = inline_list(soup, map(lambda x: field_link(website, file, 'components', x['id']), components))
      yield (issue_detail_field_label(website, file, 'components'), component_list)
   if (game_mode := fields.get('customfield_10501')) is not None:
      yield issue_detail_field(website, file, 'customfield_10501', game_mode['id'])
   if (platform := fields.get('customfield_10402')) is not None:
      yield issue_detail_field(website, file, 'customfield_10402', platform['id'])
   if (rplatform := fields.get('customfield_12301')) is not None:
      yield issue_detail_field(website, file, 'customfield_12301', rplatform['id'])
   if (dplatform := fields.get('customfield_12400')) is not None:
      yield issue_detail_field(website, file, 'customfield_12400', dplatform['id'])
   if (lplatform := fields.get('customfield_12900')) is not None:
      yield issue_detail_field(website, file, 'customfield_12900', lplatform['id'])
   if (os := fields.get('customfield_11300')) is not None:
      yield ('OS Version:', os)
   label_list = inline_list(soup, map(lambda x: field_link(website, file, 'labels', x), fields['labels']))
   yield (issue_detail_field_label(website, file, 'labels'), label_list)
   project = try_project(website.cache, fields['project'])
   if 'versions' in fields and project is not None:
      versions = [website.cache.projects[project['id']].versions[x].version for x in fields['versions']]
      yield ('Affects Versions:', version_list(website, file, project, versions))
   if (regression := fields.get('customfield_11802')) is not None:
      yield ('Regression Builds:', regression)
   if 'fixVersions' in fields and project is not None:
      versions = [website.cache.projects[project['id']].versions[x].version for x in fields['fixVersions']]
      yield ('Fix Versions:', version_list(website, file, project, versions))
   if website.perms.hidden_json_data:
      data_link = None
   else:
      data_link = relative_path(website.root, file.path, website.archive.get_issue_path(issue['id']))
   links = issue_detail_links(issue, project, data_link)
   yield ('Links:', build_link_list(file.page.soup, 'ul', links))

def build_info_top(soup: bs4.BeautifulSoup, key: Tag | None, summary: Tag) -> bs4.Tag:
   title_content: list[Tag] = []
   if key is not None:
      title_content.append(key)
   # classes for misode.css
   title_content.append(new_content_tag(soup, 'h1', attrs={'class': 'issue-summary'}, content=summary))
   return new_content_tag(soup, 'div', attrs={'class': 'issue-top'}, content=[
      new_content_tag(soup, 'div', attrs={'class': 'issue-title'}, content=title_content)
   ])

def build_info_main(soup: bs4.BeautifulSoup, top: bs4.Tag, body: typing.Iterable[bs4.Tag], details: bs4.Tag, links: bs4.Tag | None, attachments: bs4.Tag | None) -> bs4.Tag:
   # classes for misode.css
   issue_div = soup.new_tag('div', attrs={'class': 'issue'})
   issue_div.append(top)
   body_div = new_content_tag(soup, 'div', attrs={'class': 'issue-body'}, content=body)
   issue_div.append(new_content_tag(soup, 'div', attrs={'class': 'issue-split'}, content=[
      body_div,
      details
   ]))
   if links is not None:
      body_div.append(links)
   if attachments is not None:
      body_div.append(attachments)
   return issue_div

def build_info_details(soup: bs4.BeautifulSoup, entries: typing.Iterable[tuple[Tag, Tag]]) -> bs4.Tag:
   # issue-details for misode.css
   result = soup.new_tag('dl', attrs={'class': 'issue-details'})
   for label, value in entries:
      append_desc_item(soup, result, label, value)
   return result

def build_link_list(soup: bs4.BeautifulSoup, tag_type: str, entries: typing.Iterable[tuple[str, str]]) -> bs4.Tag:
   result = soup.new_tag(tag_type)
   for label, link in entries:
      result.append(new_content_tag(soup, 'li', new_content_tag(soup, 'a', label, attrs={'href': link})))
   return result

def build_attachment_list(soup: bs4.BeautifulSoup, attachments: list[bs4.Tag]) -> bs4.Tag:
   # issue-attachment-section for style.css
   return new_content_tag(soup, 'details', attrs={'open': '', 'class': 'issue-attachment-section'}, content=[
      new_content_tag(soup, 'summary', [
         new_content_tag(soup, 'h2', content=[
            'Attachments',
            count_badge(soup, len(attachments))
         ])
      ]),
      # attachments for misode.css
      new_content_tag(soup, 'div', attrs={'class': 'attachments'}, content=attachments)
   ])

def build_link_section(soup: bs4.BeautifulSoup, link_types: dict[str, list[bs4.Tag]]) -> bs4.Tag:
   link_lists: list[bs4.Tag] = []
   for link_desc, issues in link_types.items():
      link_list: list[bs4.Tag] = []
      for linked_issue in issues:
         link_list.append(linked_issue)
      link_block = new_content_tag(soup, 'details', attrs={'open': ''}, content=[
         # issue-link-type for misode.css
         new_content_tag(soup, 'summary', attrs={'class': 'issue-link-type'}, content=[
            new_content_tag(soup, 'h3', content=[
               link_desc,
               count_badge(soup, len(issues))
            ]),
         ]),
         new_content_tag(soup, 'div', content=link_list)
      ])
      link_lists.append(link_block)
   # issue-link-section for style.css
   link_section = new_content_tag(soup, 'details', attrs={'open': '', 'class': 'issue-link-section'}, content=[
      new_content_tag(soup, 'summary', [
         new_content_tag(soup, 'h2', content='Linked Issues')
      ]),
      new_content_tag(soup, 'div', attrs={'class': 'issue-link-section'}, content=link_lists)
   ])
   return link_section

@dataclasses.dataclass
class InfoTabData:
   name: str
   label: list[Tag]
   content: list[Tag]

def build_info_tabs(soup: bs4.BeautifulSoup, tabs: typing.Iterable[InfoTabData], orderable: bool) -> bs4.Tag:
   # classes for style.css
   result = soup.new_tag('div', attrs={'class': 'issue-tabs'})
   tabbed_content = soup.new_tag('div', attrs={'class': 'issue-tabs-content'})
   for i, entry in enumerate(tabs):
      tab_content = new_content_tag(soup, 'div', attrs={'id': f'issue-tab-content-{entry.name}', 'class': 'issue-tab-content'}, content=entry.content)
      tabbed_content.append(tab_content)
      radio = soup.new_tag('input', attrs={'type': 'radio', 'name': 'issue-tabs', 'id': f'issue-tab-{entry.name}'})
      if i == 0:
         radio.attrs['checked'] = ''
      label = new_content_tag(soup, 'label', attrs={'for': f'issue-tab-{entry.name}'}, content=entry.label)
      result.append(radio)
      result.append(label)
   if orderable:
      checkbox = order_checkbox(soup)
      result.extend(checkbox)
   result.append(tabbed_content)
   return result

def order_checkbox(soup: bs4.BeautifulSoup) -> list[bs4.Tag]:
   checkbox = soup.new_tag('input', attrs={'type': 'checkbox', 'name': 'issue-order', 'id': 'issue-tab-order'})
   label = new_content_tag(soup, 'label', attrs={'for': 'issue-tab-order'}, content='')
   return [checkbox, label]

# list pages
def make_all_issues_page(website: Website, file: HtmlFile):
   soup = file.page.soup
   content = main_content(website, file)

   table = create_issue_list(website, file, 'issue', website.cache.get_issues(website.cache.all_issues))

   add_metadata(file, 'All Issues', f'{format_number(len(website.cache.all_issues))} issues', None)

   list_main = build_list_main(soup, ['All Issues'], None, [table.filters, table.table])
   content.append(list_main)
   add_table_scripts(website, file, [(table.data, table.rows)])

def make_meta_value_page(website: Website, file: HtmlFile, meta: CachedMetaInfo, value: CachedValueInfo):
   soup = file.page.soup
   content = main_content(website, file)

   table = create_issue_list(website, file, 'issue', website.cache.get_issues(value.issues))

   add_metadata(file, value.display.name, value.display.description, value.display.icon)

   flink = relative_link(website.root, file.path, website.meta_pages[meta.id].page.path)
   badge = meta_badge_display(website, file, meta.id, value.display)
   if badge.resolved:
      h2_tag = new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-resolved'}, content=badge.outer)
   elif badge.progress:
      h2_tag = new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-progress'}, content=badge.outer)
   else:
      h2_tag = badge.outer
   h1: list[Tag] = [new_content_tag(soup, 'a', attrs={'href': flink}, content=meta.name)]
   h2: list[Tag] = [h2_tag, ' issues']
   list_main = build_list_main(soup, h1, h2, [table.filters, table.table])
   content.append(list_main)
   add_table_scripts(website, file, [(table.data, table.rows)])

def make_field_value_page(website: Website, file: HtmlFile, field: CachedFieldInfo, value: CachedValueInfo):
   soup = file.page.soup
   content = main_content(website, file)

   table = create_issue_list(website, file, 'issue', website.cache.get_issues(value.issues))

   add_metadata(file, value.display.name, value.display.description, value.display.icon)

   flink = relative_link(website.root, file.path, website.field_pages[field.id].page.path)
   value_tag = field_badge_display(website, file, field.id, value.display)
   h1: list[Tag] = [new_content_tag(soup, 'a', attrs={'href': flink}, content=field.name)]
   h2: list[Tag] = [value_tag.outer, ' issues']
   list_main = build_list_main(soup, h1, h2, [table.filters, table.table])
   content.append(list_main)
   add_table_scripts(website, file, [(table.data, table.rows)])

def make_project_issues_page(website: Website, file: HtmlFile, info: CachedProjectInfo):
   soup = file.page.soup
   content = main_content(website, file)

   table = create_issue_list(website, file, 'issue', website.cache.get_issues(info.issues))

   add_metadata(file, info.project['name'], f'{format_number(len(info.issues))} issues', info.project['avatarUrls']['48x48'])

   h1: list[Tag] = [project_link(website, file, info.project, with_icon=True), ' issues']
   list_main = build_list_main(soup, h1, None, [table.filters, table.table])
   content.append(list_main)
   add_table_scripts(website, file, [(table.data, table.rows)])

def make_project_versions_page(website: Website, file: HtmlFile, info: CachedProjectInfo):
   soup = file.page.soup
   content = main_content(website, file)

   table = create_versions_table(website, file, info.project, info.versions.values())

   add_metadata(file, info.project['name'], f'{format_number(len(info.versions))} versions', info.project['avatarUrls']['48x48'])

   h1: list[Tag] = [project_link(website, file, info.project, with_icon=True), ' versions']
   # issue-list for misode.css
   list_main = build_list_main(soup, h1, None, [new_content_tag(soup, 'div', attrs={'class': 'issue-list'}, content=table)])
   content.append(list_main)

def make_all_users_page(website: Website, file: HtmlFile):
   soup = file.page.soup
   content = main_content(website, file)

   table = create_user_list(website, file, 'user', (website.cache.user_getter(x) for x in website.cache.all_users))

   add_metadata(file, 'All Users', f'{format_number(len(website.cache.all_users))} all_users', None)

   list_main = build_list_main(soup, ['All Users'], None, [table.filters, table.table])
   content.append(list_main)
   add_table_scripts(website, file, [(table.data, table.rows)])

def make_group_users_page(website: Website, file: HtmlFile, info: CachedGroupInfo):
   soup = file.page.soup
   content = main_content(website, file)

   table = create_user_list(website, file, 'user', (website.cache.user_getter(x) for x in info.users))

   add_metadata(file, info.id, f'{format_number(len(info.users))} users', None)

   list_main = build_list_main(soup, [group_name(website, file, info.id)], None, [table.filters, table.table])
   content.append(list_main)
   add_table_scripts(website, file, [(table.data, table.rows)])

def make_group_comments_page(website: Website, file: HtmlFile, info: CachedGroupInfo):
   soup = file.page.soup
   content = main_content(website, file)

   include_wiki_rendering(website, file)

   add_metadata(file, info.id, f'{format_number(len(info.comments))} comments', None)

   section = build_user_section(soup, 'group', 200, [comment_to_user(website, file, x) for x in info.comments])

   user_main = build_user_main(soup, [group_name(website, file, info.id)], ['Restricted comments'], [section.controls, section.section])
   content.append(user_main)
   pages: list[PageSection] = [section]
   add_page_scripts(website, file, [(x.data, x.content) for x in pages if x.data is not None])

def make_secret_comments_page(website: Website, file: HtmlFile):
   soup = file.page.soup
   content = main_content(website, file)

   include_wiki_rendering(website, file)

   all_comments: list[RenderableComment] = []
   for issue_id, comments in website.secret_comments.comments.items():
      if issue_id in website.cache.valid_issues:
         issue = website.cache.just_issue_getter(issue_id)
         comments = website.cache.secret_comment_getter(issue_id)
         for comment in comments:
            renderable = RenderableComment(comment.comment, issue, comment.body, datetime.datetime.fromisoformat(comment.comment['created']), secret=True)
            bisect.insort_left(all_comments, renderable, key=lambda x: x.date)

   add_metadata(file, 'Secret Comments', f'{format_number(len(all_comments))} comments', None)

   section = build_user_section(soup, 'secrets', 200, [comment_to_user(website, file, x) for x in all_comments])

   user_main = build_user_main(soup, ['Secret comments'], None, [section.controls, section.section])
   content.append(user_main)
   pages: list[PageSection] = [section]
   add_page_scripts(website, file, [(x.data, x.content) for x in pages if x.data is not None])

def build_list_main(soup: bs4.BeautifulSoup, h1: typing.Iterable[Tag], h2: typing.Iterable[Tag] | None, parts: typing.Iterable[Tag]) -> bs4.Tag:
   # list-main for style.css
   main = soup.new_tag('div', attrs={'class': 'list-main'})
   main.append(new_content_tag(soup, 'h1', h1))
   if h2 is not None:
      main.append(new_content_tag(soup, 'h2', h2))
   for part in parts:
      main.append(part)
   return main

def build_user_main(soup: bs4.BeautifulSoup, h1: typing.Iterable[Tag], h2: typing.Iterable[Tag] | None, parts: typing.Iterable[Tag]) -> bs4.Tag:
   # user-main for style.css
   main = soup.new_tag('div', attrs={'class': 'user-main'})
   main.append(new_content_tag(soup, 'h1', h1))
   if h2 is not None:
      main.append(new_content_tag(soup, 'h2', h2))
   content = new_content_tag(soup, 'div', attrs={'class': 'user-main-content-wrapper'}, content=order_checkbox(soup))
   content.append(new_content_tag(soup, 'div', attrs={'class': 'user-main-content'}, content=parts))
   main.append(content)
   return main

def create_versions_table(website: Website, file: HtmlFile, project: Project, versions: typing.Iterable[CachedVersionInfo]) -> bs4.Tag:
   soup = file.page.soup
   table = make_table(soup, [
      new_content_tag(soup, 'th', new_content_tag(soup, 'div', 'Name'), attrs={'class': 'version-table-name'}),
      new_content_tag(soup, 'th', new_content_tag(soup, 'div', 'Description'), attrs={'class': 'version-table-desc'}),
      new_content_tag(soup, 'th', new_content_tag(soup, 'div', 'Date'), attrs={'class': 'version-table-date'}),
      new_content_tag(soup, 'th', new_content_tag(soup, 'div', 'Affected'), attrs={'class': 'version-table-issues'}),
      new_content_tag(soup, 'th', new_content_tag(soup, 'div', 'Fixed'), attrs={'class': 'version-table-issues'}),
   ])
   # version-table for style.css
   table.attrs['class'] = 'issue-table'
   for info in versions:
      link = relative_link(website.root, file.path, website.project_pages[project['id']].get_version_path(info.version))
      badge = status_badge(soup, info.version['name'])
      append_row(soup, table, [
         # classes for style.css
         new_content_tag(soup, 'td', attrs={'class': 'version-table-name'}, content=new_content_tag(soup, 'a', attrs={'href': link}, content=new_content_tag(soup, 'div', badge))),
         new_content_tag(soup, 'td', attrs={'class': 'version-table-desc'}, content=new_content_tag(soup, 'div', info.version['description'] if 'description' in info.version else [])),
         new_content_tag(soup, 'td', attrs={'class': 'version-table-date'}, content=new_content_tag(soup, 'div', render_date(soup, datetime.datetime.fromisoformat(info.version['releaseDate'])) if 'releaseDate' in info.version else [])),
         new_content_tag(soup, 'td', attrs={'class': 'version-table-issues'}, content=new_content_tag(soup, 'div', f'{format_number(len(info.affected))} issues' if len(info.affected) > 0 else [])),
         new_content_tag(soup, 'td', attrs={'class': 'version-table-issues'}, content=new_content_tag(soup, 'div', f'{format_number(len(info.fixed))} issues' if len(info.fixed) > 0 else [])),
      ])
   # issue-table-container for misode.css
   return new_content_tag(soup, 'div', attrs={'class': 'issue-table-container'}, content=table)

TableData = typing.TypedDict('TableData', {
   'rowHeight': int,
   'tableHeaderId': str,
   'tableBodyId': str,
   'scrollId': str,
   'countId': str,
   'labelText': str,
   'search': dict[str, list[str]], # map of input element ID -> issue values
   'filter': dict[str, list[str | None]], # map of select element ID -> issue values
   'sort': list[list[int]], # map of column indices -> row indices sorted by issue value
   'rows': int
})

PageSectionData = typing.TypedDict('PageSectionData', {
   'contentId': str,
   'visibleId': str,
   'prevId': str,
   'pageId': str,
   'nextId': str,
   'orderId': str,
   'pageSize': int,
   'anchors': list[str | None] | None,
   'count': int
})

def js_compressed_string(value: str) -> tuple[str, int]:
   compressed = zlib.compress(value.encode('utf-8'), level=9, wbits=-15)
   length = len(compressed)
   if length % 2 == 1:
      compressed += b'\0'
   chars: list[str] = []
   for i in range(0, len(compressed), 2):
      codepoint = compressed[i] | (compressed[i + 1] << 8)
      chars.append(js_codepoint(codepoint))
   return ('"' + ''.join(chars) + '"', length)

def js_codepoint(codepoint: int) -> str:
   escape_map = {0x5c: r'\\', 0x22: r'\"', 0x0a: r'\n', 0x0d: r'\r', 0x09: r'\t'}
   if codepoint in escape_map:
      return escape_map[codepoint]
   if codepoint <= 0x20 or codepoint in (0x2028, 0x2029) or (0xd800 <= codepoint <= 0xdfff):
      return f'\\u{codepoint:04x}'
   return chr(codepoint)

def set_promise_obj(file: HtmlFile, access: str, data: typing.Mapping[str, typing.Any] | list):
   value_str = json.dumps(data, separators=(',', ':'))
   compressed, length = js_compressed_string(value_str)
   file.page.body.append(new_content_tag(file.page.soup, 'script',
      f'{access} = decompressString({compressed}, {length}).then(text => JSON.parse(text));\n'
   ))

def set_promise_str(file: HtmlFile, access: str, data: str):
   compressed, length = js_compressed_string(data)
   file.page.body.append(new_content_tag(file.page.soup, 'script',
      f'{access} = decompressString({compressed}, {length});\n'
   ))

def append_decompressor(website: Website, file: HtmlFile):
   src = relative_link(website.root, file.path, pathlib.PurePath('web/js/decompress.js'))
   existing = file.page.head.find(name='script', attrs={'src': src})
   if existing is None:
      file.page.head.append(file.page.soup.new_tag('script', attrs={'src': src}))

def add_table_scripts(website: Website, file: HtmlFile, tables: list[tuple[TableData, list[bs4.Tag]]]):
   if len(tables) == 0:
      return
   @dataclasses.dataclass
   class TableEntry:
      data: TableData
      row_batches: list[list[str]]
      def to_empty(self) -> str:
         batches = [f'{{length:{len(x)}}}' for x in self.row_batches]
         return f'{{rowBatches:[{','.join(batches)}]}}'
   table_entries: list[TableEntry] = []
   for table, rows in tables:
      row_data = [x.decode(formatter='html5') for x in rows]
      row_batches = [list(x) for x in itertools.batched(row_data, 10_000)]
      table_entries.append(TableEntry(table, row_batches))
   file.page.body.append(new_content_tag(file.page.soup, 'script',
      f'window.tablePromises = [{','.join(x.to_empty() for x in table_entries)}];\n'
   ))
   for i, entry in enumerate(table_entries):
      set_promise_obj(file, f'window.tablePromises[{i}].data', entry.data)
      for j, row_batch in enumerate(entry.row_batches):
         set_promise_obj(file, f'window.tablePromises[{i}].rowBatches[{j}].data', row_batch)
   file.page.head.append(file.page.soup.new_tag('script', defer='', src=relative_link(website.root, file.path, pathlib.PurePath('web/js/table.js'))))
   append_decompressor(website, file)

def add_page_scripts(website: Website, file: HtmlFile, sections: list[tuple[PageSectionData, list[bs4.Tag]]]):
   if len(sections) == 0:
      return
   @dataclasses.dataclass
   class PagesEntry:
      data: PageSectionData
      content_batches: list[list[str]]
      def to_empty(self) -> str:
         batches = [f'{{length:{len(x)}}}' for x in self.content_batches]
         return f'{{contentBatches:[{','.join(batches)}]}}'
   page_entries: list[PagesEntry] = []
   for section, content in sections:
      content_data = [x.decode(formatter='html5') for x in content]
      content_batches = [list(x) for x in itertools.batched(content_data, 1000)]
      page_entries.append(PagesEntry(section, content_batches))
   file.page.body.append(new_content_tag(file.page.soup, 'script',
      f'window.pagePromises = [{','.join(x.to_empty() for x in page_entries)}];\n'
   ))
   for i, entry in enumerate(page_entries):
      set_promise_obj(file, f'window.pagePromises[{i}].data', entry.data)
      for j, content_batch in enumerate(entry.content_batches):
         set_promise_obj(file, f'window.pagePromises[{i}].contentBatches[{j}].content', content_batch)
   file.page.head.append(file.page.soup.new_tag('script', defer='', src=relative_link(website.root, file.path, pathlib.PurePath('web/js/pages.js'))))
   append_decompressor(website, file)

@dataclasses.dataclass
class VirtualTable:
   table: bs4.Tag
   filters: bs4.Tag
   data: TableData
   rows: list[bs4.Tag]

@dataclasses.dataclass
class VirtualTableSettings:
   columns: dict[str, str]
   search: dict[str, str]
   filter: dict[str, tuple[str, list[ValueDisplay]]]

def build_virtual_table(soup: bs4.BeautifulSoup, settings: VirtualTableSettings, data: TableData, rows: list[bs4.Tag]) -> VirtualTable:
   assert settings.search.keys() == data['search'].keys()
   assert settings.filter.keys() == data['filter'].keys()
   assert len(settings.columns) == len(data['sort'])
   assert all(len(x) == len(rows) for x in data['sort'])
   assert all(len(x) == len(rows) for x in data['search'].values())
   assert all(len(x) == len(rows) for x in data['filter'].values())
   assert data['rows'] == len(rows)

   # issue-table for misode.css
   # other classes for style.css
   issue_table = soup.new_tag('div', attrs={'class': 'issue-table'})
   header = soup.new_tag('div', attrs={'class': 'issue-table-header', 'id': data['tableHeaderId']})
   issue_table.append(header)
   for text, cls in settings.columns.items():
      header.append(new_content_tag(soup, 'div', text, attrs={'class': cls}))
   issue_body = soup.new_tag('div', attrs={'id': data['tableBodyId'], 'class': 'issue-table-body'})
   issue_table.append(issue_body)
   for i, row in enumerate(itertools.islice(rows, 30)):
      issue_body.append(new_content_tag(soup, 'div', attrs={'class': 'issue-table-virtual-row', 'style': f'top: {i * 32}px;'}, content=row))
   issue_body.insert(0, soup.new_tag('div', attrs={'id': data['scrollId'], 'class': 'issue-table-scroll'}))
   # filters for misode.css
   filters = soup.new_tag('div', attrs={'class': 'filters'})
   for id, name in settings.search.items():
      search = soup.new_tag('input', attrs={'name': 'search', 'type': 'text', 'placeholder': name, 'id': id})
      filters.append(search)
   for id, (name, options) in settings.filter.items():
      values = data['filter'][id]
      if len(set(values)) > 1:
         dropdown = new_content_tag(soup, 'select', attrs={'name': id, 'id': id}, content=[new_content_tag(soup, 'option', name, attrs={'value': ''})])
         for option in options:
            if option.id in values:
               dropdown.append(new_content_tag(soup, 'option', option.name, attrs={'value': 'null' if option.id is None else option.id}))
         filters.append(dropdown)
      else:
         del data['filter'][id]
   # issue-controls for misode.css
   controls = new_content_tag(soup, 'div', attrs={'class': 'issue-controls'}, content=[
      new_content_tag(soup, 'div', attrs={'id': data['countId']}, content=[f'{format_number(len(rows))} {data['labelText']}'])
   ])
   # issue-list for misode.css
   result = new_content_tag(soup, 'div', attrs={'class': 'issue-list'}, content=[
      controls,
      new_content_tag(soup, 'div', attrs={'class': 'issue-table-container'}, content=issue_table)
   ])
   return VirtualTable(result, filters, data, rows)

def create_issue_list(website: Website, file: HtmlFile, id_prefix: str, issues: typing.Iterable[Issue]) -> VirtualTable:
   soup = file.page.soup
   summary_id = f'{id_prefix}-table-search'
   project_id = f'{id_prefix}-table-filter-project'
   resolution_id = f'{id_prefix}-table-filter-resolution'
   confirmation_id = f'{id_prefix}-table-filter-confirmation'
   priority_id = f'{id_prefix}-table-filter-priority'
   # classes for misode.css
   columns: dict[str, str] = {
      'Key': 'issue-table-key',
      'Summary': 'issue-table-summary',
      'Status': 'issue-table-status',
      'Reporter': 'issue-table-username',
      'Assignee': 'issue-table-username',
      'Created': 'issue-table-time',
   }
   search: dict[str, str] = {
      summary_id: 'Summary'
   }
   filter: dict[str, tuple[str, list[ValueDisplay]]] = {
      project_id: ('Project', [ValueDisplay(x.project['id'], x.project['key'], None, None) for x in website.cache.projects.values()]),
      resolution_id: ('Resolution', [x.display for x in website.cache.metas['resolution'].values.values()]),
      confirmation_id: ('Confirmation', [x.display for x in website.cache.fields['customfield_10500'].values.values()]),
      priority_id: ('Priority', [x.display for x in website.cache.fields['customfield_12200'].values.values()]),
   }
   settings = VirtualTableSettings(columns, search, filter)
   rows: list[bs4.Tag] = []
   search_data: dict[str, list[str]] = {
      summary_id: []
   }
   filter_data: dict[str, list[str | None]] = {
      project_id: [],
      resolution_id: [],
      confirmation_id: [],
      priority_id: []
   }
   sort_data: list[list[tuple[int, typing.Any]]] = [[], [], [], [], [], []]
   for i, issue in enumerate(issues):
      link = relative_link(website.root, file.path, website.get_issue_path(issue))
      key_part = issue_key_issue(website, file, issue, with_icon=True)
      key = new_content_tag(soup, 'a', attrs={'class': 'issue-table-key', 'href': link}, content=key_part)
      if issue['fields']['reporter'] is not None:
         reporter_ref = user_reference_key(website, file, issue['fields']['reporter'])
         # assign a without href to inner tag for mojira.css
         reporter_ref.inner.name = 'a'
         reporter = [soup.new_tag('a', attrs={'class': 'overlay', 'href': reporter_ref.link}), reporter_ref.outer]
         reporter_name = reporter_ref.display_name
      else:
         reporter = []
         reporter_name = None
      if 'assignee' in issue['fields'] and issue['fields']['assignee'] is not None:
         assignee_ref = user_reference_key(website, file, issue['fields']['assignee'])
         # assign a without href to inner tag for mojira.css
         assignee_ref.inner.name = 'a'
         assignee = [soup.new_tag('a', attrs={'class': 'overlay', 'href': assignee_ref.link}), assignee_ref.outer]
         assignee_name = assignee_ref.display_name
      else:
         assignee = []
         assignee_name = None
      status = merged_status(website, file, issue)
      created_date = datetime.datetime.fromisoformat(issue['fields']['created'])
      row_tags = [
         key,
         new_content_tag(soup, 'div', issue['fields']['summary'], attrs={'class': 'issue-table-summary', 'title': issue['fields']['summary']}),
         new_content_tag(soup, 'a', new_content_tag(soup, 'div', status.badge.outer), attrs={'class': 'issue-table-status', 'href': status.badge.link}),
         new_content_tag(soup, 'div', reporter, attrs={'class': 'issue-table-username'}),
         new_content_tag(soup, 'div', assignee, attrs={'class': 'issue-table-username'}),
         new_content_tag(soup, 'div', render_datetime(soup, created_date), attrs={'class': 'issue-table-time'})
      ]
      def sorter_key(x: tuple[int, typing.Any]):
         key = natsort.natsort_keygen(alg=natsort.ns.IGNORECASE)
         return key(x[1])
      status_order = ['unresolved', 'progress', 'confirmed', 'priority', 'resolved']
      bisect.insort_left(sort_data[0], (i, issue['key']), key=sorter_key)
      bisect.insort_left(sort_data[1], (i, issue['fields']['summary']), key=sorter_key)
      bisect.insort_left(sort_data[2], (i, (status_order.index(status.kind), html_to_text(status.badge.outer))), key=sorter_key)
      bisect.insort_left(sort_data[3], (i, (reporter_name is None, reporter_name)), key=sorter_key)
      bisect.insort_left(sort_data[4], (i, (assignee_name is None, assignee_name)), key=sorter_key)
      bisect.insort_left(sort_data[5], (i, created_date), key=lambda x: x[1])
      search_data[summary_id].append(issue['fields']['summary'].lower())
      filter_data[project_id].append(issue['fields']['project'])
      filter_data[confirmation_id].append(issue['fields']['customfield_10500']['id'] if 'customfield_10500' in issue['fields'] and issue['fields']['customfield_10500'] is not None else None)
      filter_data[priority_id].append(issue['fields']['customfield_12200']['id'] if 'customfield_12200' in issue['fields'] and issue['fields']['customfield_12200'] is not None else None)
      filter_data[resolution_id].append(issue['fields']['resolution'])
      row = new_content_tag(soup, 'div', content=row_tags)
      # issue-table-row for style.css
      if status.kind == 'resolved':
         # issue-resolved for misode.css
         row.attrs['class'] = 'issue-table-row issue-resolved'
      elif status.kind == 'progress':
         row.attrs['class'] = 'issue-table-row issue-progress'
      else:
         row.attrs['class'] = 'issue-table-row'
      rows.append(row)
   data: TableData = {
      'rowHeight': 32,
      'tableHeaderId': f'{id_prefix}-table-header',
      'tableBodyId': f'{id_prefix}-table-body',
      'scrollId': f'{id_prefix}-table-scroll',
      'countId': f'{id_prefix}-table-count',
      'labelText': 'issues',
      'search': search_data,
      'filter': filter_data,
      'sort': [[x[0] for x in y] for y in sort_data],
      'rows': len(rows)
   }
   return build_virtual_table(soup, settings, data, rows)

def create_user_list(website: Website, file: HtmlFile, id_prefix: str, users: typing.Iterable[CachedUser]) -> VirtualTable:
   soup = file.page.soup
   displayname_id = f'{id_prefix}-table-search'
   # classes for style.css
   columns: dict[str, str] = {
      'Username': 'user-table-username',
      'Display Name': 'user-table-fullname',
      'Role': 'user-table-role',
      'Created': 'user-table-number',
      'Assigned': 'user-table-number',
   }
   search: dict[str, str] = {
      displayname_id: 'Display Name'
   }
   settings = VirtualTableSettings(columns, search, {})
   rows: list[bs4.Tag] = []
   search_data: dict[str, list[str]] = {
      displayname_id: []
   }
   sort_data: list[list[tuple[int, typing.Any]]] = [[], [], [], [], []]
   for i, info in enumerate(users):
      user = info.user
      user_ref = user_reference(website, file, user)
      # assign a without href to inner tag for mojira.css
      user_ref.inner.name = 'a'
      user_content = [soup.new_tag('a', attrs={'class': 'overlay', 'href': user_ref.link}), user_ref.outer]
      role = user_role(user) if 'groups' in user else None
      if role is None:
         role_tag = soup.new_tag('div', attrs={'class': 'user-table-role'})
         index = 9999
      else:
         group, index = role
         link = relative_link(website.root, file.path, website.group_pages[group].users.path)
         role_tag = new_content_tag(soup, 'a', attrs={'class': 'user-table-role', 'href': link}, content=[
            group_name(website, file, group)
         ])
      row_tags = [
         new_content_tag(soup, 'div', attrs={'class': 'user-table-username'}, content=user['name']),
         new_content_tag(soup, 'div', attrs={'class': 'user-table-fullname'}, content=user_content),
         role_tag,
         new_content_tag(soup, 'div', attrs={'class': 'user-table-number'}, content=f'{format_number(len(info.created))} issues' if len(info.created) > 0 else []),
         new_content_tag(soup, 'div', attrs={'class': 'user-table-number'}, content=f'{format_number(len(info.assigned))} issues' if len(info.assigned) > 0 else []),
      ]
      def sorter_key(x: tuple[int, typing.Any]):
         key = natsort.natsort_keygen(alg=natsort.ns.IGNORECASE)
         return key(x[1])
      bisect.insort_left(sort_data[0], (i, user['name']), key=sorter_key)
      bisect.insort_left(sort_data[1], (i, user['displayName']), key=sorter_key)
      bisect.insort_left(sort_data[2], (i, index), key=lambda x: x[1])
      bisect.insort_left(sort_data[3], (i, -len(info.created)), key=lambda x: x[1])
      bisect.insort_left(sort_data[4], (i, -len(info.assigned)), key=lambda x: x[1])
      search_data[displayname_id].append(user['displayName'].lower())
      row = new_content_tag(soup, 'div', content=row_tags)
      row.attrs['class'] = 'issue-table-row'
      rows.append(row)
   data: TableData = {
      'rowHeight': 32,
      'tableHeaderId': f'{id_prefix}-table-header',
      'tableBodyId': f'{id_prefix}-table-body',
      'scrollId': f'{id_prefix}-table-scroll',
      'countId': f'{id_prefix}-table-count',
      'labelText': 'users',
      'search': search_data,
      'filter': {},
      'sort': [[x[0] for x in y] for y in sort_data],
      'rows': len(rows)
   }
   return build_virtual_table(soup, settings, data, rows)

# comment-like sections
@dataclasses.dataclass
class RenderableUserEntry:
   anchor: str | None
   head: list[Tag]
   body: list[Tag]

def comment_to_user(website: Website, file: HtmlFile, comment: RenderableComment) -> RenderableUserEntry:
   anchor = f'comment-id-{comment.comment['id']}'
   head = user_head_comment(website, file, comment.comment, secret=comment.secret, issue=comment.external_issue)
   body = embed_wiki(website, file, comment.parsed)
   return RenderableUserEntry(anchor, list(head), [body])

@dataclasses.dataclass
class RenderableRevision:
   id: str
   user_key: str | None
   start_time: datetime.datetime
   end_time: datetime.datetime | None
   external_issue: Issue | None
   content: list[Tag]

def get_renderable_revisions(website: Website, file: HtmlFile, issue_id: str, external_issue: Issue | None, initial_project: str, revisions: list[Revision]) -> list[RenderableRevision]:
   merged = merge_revisions(revisions, datetime.timedelta(minutes=10))
   labels = TrackedMultiValueRevision('Labels', 'labels', label_splitter, lambda x: historic_field_list(website, file, 'labels', x))
   categories = TrackedMultiValueRevision('Category', 'labels', category_splitter, lambda x: historic_field_list(website, file, 'customfield_11901', x))
   issue_project = TrackedProjectRevision(initial_project)
   result: list[RenderableRevision] = []
   for revision in merged:
      items = list(merged_revision_changes(website, file, issue_id, revision, issue_project, labels, categories))
      if len(items) > 0:
         render = RenderableRevision(revision.changes[0].id, revision.user_key, revision.start_time, revision.end_time, external_issue, items)
         result.append(render)
   return result

def revision_to_user(website: Website, file: HtmlFile, revision: RenderableRevision) -> RenderableUserEntry:
   soup = file.page.soup
   anchor = f'history-id-{revision.id}'
   time_part = render_datetime(soup, revision.start_time) if revision.end_time is None else render_date_range(soup, revision.start_time, revision.end_time)
   head: list[Tag] = []

   if revision.external_issue is None:
      link = f'#{anchor}'
   else:
      link = relative_link(website.root, file.path, website.get_issue_path(revision.external_issue)) + f'#{anchor}'
   if revision.user_key is not None:
      head.extend([
         comment_author(website, file, revision.user_key),
         ' ',
      ])
   link_part = new_content_tag(soup, 'a', attrs={'href': link}, content=[])
   if revision.external_issue is not None:
      head.append(new_content_tag(soup, 'span', 'on', attrs={'class': 'comment-on'}))
      head.append(' ')
      # issue-key for misode.css
      issue_key = new_content_tag(soup, 'span', attrs={'class': 'issue-key'}, content=revision.external_issue['key'])
      link_part.append(issue_key)
      link_part.append(' ')
   link_part.append(new_content_tag(soup, 'span', attrs={'class': 'comment-time'}, content=time_part))
   head.append(
      new_content_tag(soup, 'span', attrs={'class': 'comment-link'}, content=[
         link_part
      ])
   )
   body = revision.content
   return RenderableUserEntry(anchor, head, body)

def mention_to_user(website: Website, file: HtmlFile, mention: RenderableMention) -> RenderableUserEntry:
   if mention.comment is not None:
      head = user_head_comment(website, file, mention.comment, secret=False, issue=mention.issue)
      body = embed_wiki(website, file, mention.parsed)
      return RenderableUserEntry(None, list(head), [body])
   else:
      head = user_head_issue(website, file, mention.issue)
      body = embed_wiki(website, file, mention.parsed)
      return RenderableUserEntry(None, list(head), [body])

@dataclasses.dataclass
class PageSection:
   section: bs4.Tag
   controls: bs4.Tag
   data: PageSectionData | None
   content: list[bs4.Tag]

def build_page_section(soup: bs4.BeautifulSoup, id_prefix: str, page_size: int, entries: typing.Iterable[tuple[bs4.Tag, str | None]]) -> PageSection:
   content: list[bs4.Tag] = []
   anchors: list[str | None] = []
   first_page: list[bs4.Tag] = []
   for batch in itertools.batched(entries, page_size):
      for entry, anchor in batch:
         content.append(entry)
         anchors.append(anchor)
         if len(first_page) < page_size:
            first_page.append(entry)
   # comment-section for style.css
   section = new_content_tag(soup, 'div', attrs={'id': f'{id_prefix}-section-content'}, content=first_page)
   if len(content) > page_size:
      data: PageSectionData | None = {
         'contentId': f'{id_prefix}-section-content',
         'visibleId': f'{id_prefix}-section-visible',
         'prevId': f'{id_prefix}-section-prev-page',
         'pageId': f'{id_prefix}-section-page',
         'nextId': f'{id_prefix}-section-next-page',
         'orderId': 'issue-tab-order',
         'pageSize': page_size,
         'anchors': None if all(x is None for x in anchors) else anchors,
         'count': len(content)
      }
      controls = new_content_tag(soup, 'div', attrs={'class': 'issue-controls comment-controls'}, content=[
         new_content_tag(soup, 'div', attrs={'class': 'issue-pagination'}, content=[
            new_content_tag(soup, 'button', attrs={'id': data['prevId'], 'disabled': ''}, content=[
               new_content_tag(soup, 'svg', attrs={'xmlns': 'http://www.w3.org/2000/svg', 'viewBox': '0 0 16 16', 'width': '16', 'height': '16'}, content=[
                  soup.new_tag('path', attrs={'d': 'M9.78 12.78a.75.75 0 0 1-1.06 0L4.47 8.53a.75.75 0 0 1 0-1.06l4.25-4.25a.751.751 0 0 1 1.042.018.751.751 0 0 1 .018 1.042L6.06 8l3.72 3.72a.75.75 0 0 1 0 1.06Z'})
               ])
            ]),
            soup.new_tag('input', attrs={'id': data['pageId'], 'class': 'issue-page', 'type': 'number', 'value': '1', 'min': '1', 'max': str(int(math.ceil(len(content) / page_size))), 'inputmode': 'numeric'}),
            new_content_tag(soup, 'button', attrs={'id': data['nextId']}, content=[
               new_content_tag(soup, 'svg', attrs={'xmlns': 'http://www.w3.org/2000/svg', 'viewBox': '0 0 16 16', 'width': '16', 'height': '16'}, content=[
                  soup.new_tag('path', attrs={'d': 'M6.22 3.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06Z'})
               ])
            ])
         ]),
         new_content_tag(soup, 'div', attrs={'id': data['visibleId'], 'class': 'issue-count'}, content=f'1 - {format_number(len(first_page))}'),
      ])
   else:
      data = None
      controls = new_content_tag(soup, 'div', [])
   return PageSection(section, controls, data, content)

def build_user_section(soup: bs4.BeautifulSoup, id_prefix: str, page_size: int, entries: typing.Iterable[RenderableUserEntry]) -> PageSection:
   comments: list[tuple[bs4.Tag, str | None]] = []
   for entry in entries:
      comment = soup.new_tag('div', attrs={'class': 'comment'})
      if entry.anchor is not None:
         comment.append(soup.new_tag('div', attrs={'class': 'anchor', 'id': entry.anchor}))
      comment.append(new_content_tag(soup, 'div', attrs={'class': 'comment-head'}, content=entry.head))
      comment.append(new_content_tag(soup, 'div', attrs={'class': 'comment-body'}, content=entry.body))
      comments.append((comment, entry.anchor))
   section = build_page_section(soup, id_prefix, page_size, comments)
   append_class(section.section, 'comment-section')
   wrapper = new_content_tag(soup, 'div', attrs={'class': 'comment-section-wrapper'}, content=section.section)
   return PageSection(wrapper, section.controls, section.data, section.content)

# history
def historic_issue(website: Website, file: HtmlFile, info: CachedIssue, data: InitialData) -> bs4.Tag:
   issue = info.issue
   fields = data.fields
   initial_project = try_project(website.cache, fields['project'])

   assert 'key' in fields
   assert 'summary' in fields
   top = issue_top(website, file, initial_project, fields['key'], fields['summary'])
   if data.description_revision_id is not None:
      desc_soup = website.markup_source.get_issue_description_revision(issue['id'], data.description_revision_id).before
      desc = markup.parse_markup(desc_soup) if desc_soup is not None else None
   else:
      desc = info.description
   if desc is not None:
      desc = embed_wiki(website, file, desc)
   if data.environment_revision_id is not None:
      env_soup = website.markup_source.get_issue_environment_revision(issue['id'], data.environment_revision_id).before
      env = markup.parse_markup(env_soup) if env_soup is not None else None
   else:
      env = info.environment
   if env is not None:
      env = embed_wiki(website, file, env)
   impact = fields.get('customfield_11801')

   body = issue_body(file.page.soup, desc, env, impact)
   details = build_info_details(file.page.soup, historic_details(website, file, fields))
   linked = historic_links(website, file, fields['issuelinks'])
   if len(fields['attachments']) > 0:
      attaches = historic_attachments(website, file, fields['attachments'])
   else:
      attaches = None
   return build_info_main(file.page.soup, top, body, details, linked, attaches)

def historic_details(website: Website, file: HtmlFile, fields: HistoricFields) -> typing.Generator[tuple[Tag, Tag]]:
   resolution = fields.get('resolution')
   yield historic_detail_meta(website, file, 'resolution', resolution)
   is_resolved = resolution is not None
   resolved_statuses = ('5',)
   unresolved_statuses = ('1', '4')
   if (status := fields.get('status')) is not None:
      if (is_resolved and status not in resolved_statuses) or (not is_resolved and status not in unresolved_statuses):
         yield historic_detail_meta(website, file, 'status', status)
   if (security := fields.get('security')) is not None:
      yield historic_detail_field(website, file, 'security', security)
   if (partner := fields.get('customfield_11800')) is not None:
      yield ('Partner Team:', partner)
   if (assignee := fields.get('assignee')) is not None:
      yield ('Assignee:', historic_user(website, file, assignee))
   if (confirmation := fields.get('customfield_10500')) is not None:
      yield historic_detail_field(website, file, 'customfield_10500', confirmation)
   if (priority := fields.get('priority')) is not None:
      yield historic_detail_field(website, file, 'priority', priority)
   if (mpriority := fields.get('customfield_12200')) is not None:
      yield historic_detail_field(website, file, 'customfield_12200', mpriority)
   if (ado := fields.get('customfield_11500')) is not None:
      yield ('ADO:', ado)
   if (area := fields.get('customfield_12800')) is not None:
      yield historic_detail_field(website, file, 'customfield_12800', area)
   if (category := fields.get('customfield_11901')) is not None and len(category) > 0:
      category_list = historic_field_list(website, file, 'customfield_11901', category)
      yield (issue_detail_field_label(website, file, 'customfield_11901'), category_list)
   if (components := fields.get('components')) is not None and len(components) > 0:
      component_list = historic_field_list(website, file, 'components', components)
      yield (issue_detail_field_label(website, file, 'components'), component_list)
   if (gamemode := fields.get('customfield_10501')) is not None:
      yield historic_detail_field(website, file, 'customfield_10501', gamemode)
   if (platform := fields.get('customfield_10402')) is not None:
      yield historic_detail_field(website, file, 'customfield_10402', platform)
   if (rplatform := fields.get('customfield_12301')) is not None:
      yield historic_detail_field(website, file, 'customfield_12301', rplatform)
   if (dplatform := fields.get('customfield_12400')) is not None:
      yield historic_detail_field(website, file, 'customfield_12400', dplatform)
   if (lplatform := fields.get('customfield_12900')) is not None:
      yield historic_detail_field(website, file, 'customfield_12900', lplatform)
   if (version := fields.get('customfield_11300')) is not None:
      yield ('OS Version:', version)
   if 'labels' in fields:
      labels_list = historic_field_list(website, file, 'labels', fields['labels'])
      yield (issue_detail_field_label(website, file, 'labels'), labels_list)
   if 'versions' in fields:
      yield ('Affects Versions:', historic_version_list(website, file, fields['versions']))
   if (regression := fields.get('customfield_11802')) is not None:
      yield ('Regression Builds:', regression)
   if (fversions := fields.get('fixVersions')) is not None and len(fversions) > 0:
      yield ('Fix Versions:', historic_version_list(website, file, fversions))

# revisions
class TrackedMultiSetRevision:
   def __init__(self, name: str, field_id: str | None, creator: typing.Callable[[typing.Iterable[HistoricValue]], bs4.Tag]):
      self.added: list[HistoricValue] = []
      self.removed: list[HistoricValue] = []
      self.name = name
      self.field_id = field_id
      self.creator = creator

   def import_change(self, entry: RevisionChange):
      if entry['to'] is not None:
         assert entry['toString'] is not None
         self.added.append(HistoricValue(entry['to'], entry['toString']))
      if entry['from'] is not None:
         assert entry['fromString'] is not None
         self.removed.append(HistoricValue(entry['from'], entry['fromString']))

   def handle(self, website: Website, file: HtmlFile) -> typing.Generator[bs4.Tag]:
      soup = file.page.soup
      # revision-change for style.css
      if len(self.added) > 0:
         link = new_content_tag(soup, 'a', self.name, attrs={'href': relative_link(website.root, file.path, website.field_pages[self.field_id].page.path)}) if self.field_id is not None else self.name
         yield new_content_tag(soup, 'div', attrs={'class': 'revision-change'}, content=[
            revision_label(soup, ['Added ', link, ': ']),
            self.creator(self.added)
         ])
      if len(self.removed) > 0:
         link = new_content_tag(soup, 'a', self.name, attrs={'href': relative_link(website.root, file.path, website.field_pages[self.field_id].page.path)}) if self.field_id is not None else self.name
         yield new_content_tag(soup, 'div', attrs={'class': 'revision-change'}, content=[
            revision_label(soup, ['Removed ', link, ': ']),
            self.creator(self.removed)
         ])

class TrackedMultiSetProjectRevision:
   def __init__(self, name: str, field_id: str | None, creator: typing.Callable[[typing.Iterable[HistoricProjectValue]], bs4.Tag]):
      self.added: list[HistoricProjectValue] = []
      self.removed: list[HistoricProjectValue] = []
      self.name = name
      self.field_id = field_id
      self.creator = creator

   def import_change(self, entry: RevisionChange, before_project: str, after_project: str):
      if entry['to'] is not None:
         assert entry['toString'] is not None
         self.added.append(HistoricProjectValue(entry['to'], entry['toString'], after_project))
      if entry['from'] is not None:
         assert entry['fromString'] is not None
         self.removed.append(HistoricProjectValue(entry['from'], entry['fromString'], before_project))

   def handle(self, website: Website, file: HtmlFile) -> typing.Generator[bs4.Tag]:
      soup = file.page.soup
      # revision-change for style.css
      if len(self.added) > 0:
         link = new_content_tag(soup, 'a', self.name, attrs={'href': relative_link(website.root, file.path, website.field_pages[self.field_id].page.path)}) if self.field_id is not None else self.name
         yield new_content_tag(soup, 'div', attrs={'class': 'revision-change'}, content=[
            revision_label(soup, ['Added ', link, ': ']),
            self.creator(self.added)
         ])
      if len(self.removed) > 0:
         link = new_content_tag(soup, 'a', self.name, attrs={'href': relative_link(website.root, file.path, website.field_pages[self.field_id].page.path)}) if self.field_id is not None else self.name
         yield new_content_tag(soup, 'div', attrs={'class': 'revision-change'}, content=[
            revision_label(soup, ['Removed ', link, ': ']),
            self.creator(self.removed)
         ])

class TrackedMultiValueRevision:
   def __init__(self, name: str, field_id: str, splitter: typing.Callable[[str | None, str | None], list[HistoricValue]], creator: typing.Callable[[list[HistoricValue]], bs4.Tag]):
      self.previous: list[HistoricValue] | None = None
      self.name = name
      self.field_id = field_id
      self.splitter = splitter
      self.creator = creator

   def handle(self, website: Website, file: HtmlFile, revision: RevisionChange) -> typing.Generator[bs4.Tag]:
      soup = file.page.soup
      if self.previous is None:
         self.previous = self.splitter(revision['from'], revision['fromString'])
      new_values = self.splitter(revision['to'], revision['toString'])
      added_values = [x for x in new_values if x not in self.previous]
      removed_values = [x for x in self.previous if x not in new_values]
      link = relative_link(website.root, file.path, website.field_pages[self.field_id].page.path)
      # revision-change for style.css
      if len(added_values) > 0:
         label = new_content_tag(soup, 'a', self.name, attrs={'href': link})
         yield new_content_tag(soup, 'div', attrs={'class': 'revision-change'}, content=[
            revision_label(soup, ['Added ', label, ': ']),
            self.creator(added_values)
         ])
      if len(removed_values) > 0:
         label = new_content_tag(soup, 'a', self.name, attrs={'href': link})
         yield new_content_tag(soup, 'div', attrs={'class': 'revision-change'}, content=[
            revision_label(soup, ['Removed ', label, ': ']),
            self.creator(removed_values)
         ])
      self.previous = new_values

def revision_field(website: Website, file: HtmlFile, field_id: str, change: RevisionChange) -> bs4.Tag:
   if change['from'] is not None:
      assert change['fromString'] is not None
      old_tag = historic_field(website, file, field_id, HistoricValue(change['from'], change['fromString']))
   else:
      old_tag = None
   if change['to'] is not None:
      assert change['toString'] is not None
      new_tag = historic_field(website, file, field_id, HistoricValue(change['to'], change['toString']))
   else:
      new_tag = None
   label = website.cache.fields[field_id].name
   link = new_content_tag(file.page.soup, 'a', label, attrs={'href': relative_link(website.root, file.path, website.field_pages[field_id].page.path)})
   return revision_change(file.page.soup, link, old_tag, new_tag)

def revision_text(soup: bs4.BeautifulSoup, label: str, revision: RevisionChange) -> bs4.Tag:
   assert revision['from'] is None
   assert revision['to'] is None
   old_val = revision['fromString']
   new_val = revision['toString']
   if old_val == '':
      old_val = None
   if new_val == '':
      new_val = None
   return revision_change(soup, label, old_val, new_val)

def revision_change(soup: bs4.BeautifulSoup, label: Tag, old_tag: Tag | None, new_tag: Tag | None) -> bs4.Tag:
   if old_tag is not None and new_tag is not None:
      return revision_from_to(soup, ['Changed ', label, ': '], old_tag, new_tag)
   # revision-change for style.css
   elif new_tag is None and old_tag is not None:
      return new_content_tag(soup, 'div', attrs={'class': 'revision-change'}, content=[
         revision_label(soup, ['Removed ', label, ': ']),
         old_tag
      ])
   elif old_tag is None and new_tag is not None:
      return new_content_tag(soup, 'div', attrs={'class': 'revision-change'}, content=[
         revision_label(soup, ['Added ', label, ': ']),
         new_tag
      ])
   raise ValueError()

def revision_from_to(soup: bs4.BeautifulSoup, label: Tag | list[Tag], old_tag: Tag, new_tag: Tag) -> bs4.Tag:
   # revision-change for style.css
   return new_content_tag(soup, 'div', attrs={'class': 'revision-change'}, content=[
      revision_label(soup, label),
      old_tag,
      revision_label(soup, ' → '),
      new_tag
   ])

def revision_label(soup: bs4.BeautifulSoup, content: Tag | list[Tag]) -> bs4.Tag:
   # history-label for style.css
   return new_content_tag(soup, 'span', content, attrs={'class': 'history-label'})

def revision_quoted(soup: bs4.BeautifulSoup, label: Tag | list[Tag], content: list[Tag]) -> bs4.Tag:
   # classes for style.css
   return new_content_tag(soup, 'div', attrs={'class': 'revision-change'}, content=[
      revision_label(soup, label),
      new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=content)
   ])

def revision_html_diff(soup: bs4.BeautifulSoup, label: str, revision: markup.RevisionData, process: typing.Callable[[bs4.Tag], bs4.Tag], panel_class: str) -> bs4.Tag:
   if revision.before is not None and revision.after is not None:
      assert revision.diff is not None
   if revision.diff is not None:
      has_insertions = revision.diff.find(class_='diff-insert') is not None
      has_deletions = revision.diff.find(class_='diff-delete') is not None
      if has_insertions and has_deletions:
         before_diff = copy.deepcopy(revision.diff)
         after_diff = copy.deepcopy(revision.diff)
         for tag in before_diff.find_all(class_='diff-insert'):
            tag.extract()
         for tag in after_diff.find_all(class_='diff-delete'):
            tag.extract()
         panel = new_content_tag(soup, 'div', attrs={'class': panel_class}, content=[process(before_diff), process(after_diff)])
         return revision_quoted(soup, f'Changed {label}:', [panel])
      return revision_quoted(soup, f'Changed {label}:', [process(revision.diff)])
   elif revision.before is not None and revision.after is None:
      return revision_quoted(soup, f'Removed {label}:', [process(revision.before)])
   elif revision.after is not None and revision.before is None:
      return revision_quoted(soup, f'Added {label}:', [process(revision.after)])
   raise ValueError()

def revision_large_diff(website: Website, file: HtmlFile, label: str, revision: markup.RevisionData) -> bs4.Tag:
   def process(tag: bs4.Tag) -> bs4.Tag:
      wiki =  embed_wiki(website, file, markup.parse_markup(tag))
      template = wiki.find('template')
      assert template is not None
      template.insert(0, file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('web/css/diff.css'))))
      return wiki
   # diff-panel-side for style.css
   return revision_html_diff(file.page.soup, label, revision, process, 'diff-panel-side')

@dataclasses.dataclass
class TrackedProjectRevision:
   id: str

UNKNOWN_COMMENT_RE = re.compile(r'A comment with security level \'[a-z]+\' was removed\.' + '\u00a0?$')

def merged_revision_changes(website: Website, file: HtmlFile, issue_id: str, revision: MergedRevision, project: TrackedProjectRevision, labels: TrackedMultiValueRevision, categories: TrackedMultiValueRevision) -> typing.Generator[Tag]:
   soup = file.page.soup
   def changed_attachments(attaches: typing.Iterable[HistoricValue]) -> bs4.Tag:
      # history-quote for style.css
      return new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=[
         new_content_tag(soup, 'div', attrs={'class': 'attachments'}, content=[historic_attachment(website, file, x) for x in attaches])
      ])
   def changed_linked(links: typing.Iterable[HistoricValue]) -> bs4.Tag:
      link_dict: dict[str, list[bs4.Tag]] = {}
      for link in links:
         link_dir = get_link_dir(link.name, link.id)
         if link_dir not in link_dict:
            link_dict[link_dir] = []
         link_dict[link_dir].append(historic_linked_issue(website, file, link.id))
      # history-quote for style.css
      result = soup.new_tag('blockquote', attrs={'class': 'history-quote'})
      for dir, tags in link_dict.items():
         result.append(new_content_tag(soup, 'p', dir))
         result.extend(tags)
      return result
   affected_versions = TrackedMultiSetProjectRevision('Affects Versions', None, lambda x: historic_version_list(website, file, x))
   fixed_versions = TrackedMultiSetProjectRevision('Fixed Versions', None, lambda x: historic_version_list(website, file, x))
   attachments = TrackedMultiSetRevision('Attachments', None, changed_attachments)
   links = TrackedMultiSetRevision('Linked Issues', None, changed_linked)
   components = TrackedMultiSetRevision('Components', 'components', lambda x: historic_field_list(website, file, 'components', x))
   sorted_changes = sorted(revision.changes, key=lambda x: revision_order_key(x.change))
   for entry in sorted_changes:
      rev_id = entry.id
      change = entry.change
      if entry.project_move is not None:
         before_proj = entry.project_move.before
         after_proj = entry.project_move.after
         project.id = after_proj
      else:
         before_proj = project.id
         after_proj = project.id
      match change['field']:
         # tracked changes
         case 'labels': # source always null, string always 'id id'
            yield from labels.handle(website, file, change)
         case 'Category': # source/string are either null or '[id, id]'/'Name,Name'
            yield from categories.handle(website, file, change)
         # special batched changes
         case 'Link': # source/string are either null or 'key'/'This issue ...'
            links.import_change(change)
         case 'Attachment': # source/string are either null or 'id'/'filename'
            attachments.import_change(change)
         # other batched changes
         # source/string are either null or 'id'/'Name'
         case 'Component':
            components.import_change(change)
         case 'Version':
            affected_versions.import_change(change, before_proj, after_proj)
         case 'Fix Version':
            fixed_versions.import_change(change, before_proj, after_proj)
         # custom enum field changes
         # source/string are either null/null, null/empty, or 'id'/'Name'
         case 'Confirmation Status':
            yield revision_field(website, file, 'customfield_10500', change)
         case 'Area':
            yield revision_field(website, file, 'customfield_12800', change)
         case 'Game Mode':
            yield revision_field(website, file, 'customfield_10501', change)
         case 'Platform' | 'Device': # field was renamed at some point, but old name persists in history
            yield revision_field(website, file, 'customfield_10402', change)
         case 'Realms Platform':
            yield revision_field(website, file, 'customfield_12301', change)
         case 'Dungeons Platform':
            yield revision_field(website, file, 'customfield_12400', change)
         case 'Legends Platform':
            yield revision_field(website, file, 'customfield_12900', change)
         case 'Mojang Priority':
            yield revision_field(website, file, 'customfield_12200', change)
         # builtin enum field changes
         # source/string are either null or 'id'/'Name'
         case 'priority':
            yield revision_field(website, file, 'priority', change)
         case 'security':
            yield revision_field(website, file, 'security', change)
         case 'resolution':
            old_tag = historic_meta(website, file, 'resolution', change['from'], change['fromString'])
            new_tag = historic_meta(website, file, 'resolution', change['to'], change['toString'])
            link = new_content_tag(soup, 'a', 'Resolution', attrs={'href': relative_link(website.root, file.path, website.meta_pages['resolution'].page.path)})
            yield revision_change(soup, link, old_tag, new_tag)
         case 'status':
            assert change['from'] is not None
            assert change['to'] is not None
            if change['from'] != change['to']:
               old_tag = historic_meta(website, file, 'status', change['from'], change['fromString'])
               new_tag = historic_meta(website, file, 'status', change['to'], change['toString'])
               link = new_content_tag(soup, 'a', 'Status', attrs={'href': relative_link(website.root, file.path, website.meta_pages['status'].page.path)})
               yield revision_change(soup, link, old_tag, new_tag)
         # text field changes
         # source always null, string either null or empty or text
         case 'ADO' | 'VSO': # field was renamed at some point, but old name persists in history
            yield revision_text(soup, 'ADO', change)
         case 'Impact':
            yield revision_text(soup, 'Impact', change)
         case 'Regression Builds':
            yield revision_text(soup, 'Regression Builds', change)
         case 'Partner Team Reporting':
            yield revision_text(soup, 'Partner Team', change)
         case 'Operating System Version':
            yield revision_text(soup, 'OS Version', change)
         # other simple changes
         case 'Triaged Time': # source/string are either null or 'date'/'Display'
            old_tag = None if change['from'] is None or change['from'] == '' else render_date(soup, datetime.datetime.fromisoformat(change['from']))
            new_tag = None if change['to'] is None or change['to'] == '' else render_date(soup, datetime.datetime.fromisoformat(change['to']))
            yield revision_change(soup, 'Triaged Time', old_tag, new_tag)
         case 'assignee': # source/string are either null or 'key'/'Name'
            if change['from'] is None:
               old_tag = None
            else:
               assert change['fromString'] is not None
               old_tag =  historic_user(website, file, HistoricValue(change['from'], change['fromString']))
            if change['to'] is None:
               new_tag = None
            else:
               assert change['toString'] is not None
               new_tag = None if change['to'] is None else historic_user(website, file, HistoricValue(change['to'], change['toString']))
            yield revision_change(soup, 'Assignee', old_tag, new_tag)
         case 'reporter': # source/string are always 'key'/'Name'
            assert change['from'] is not None
            assert change['fromString'] is not None
            assert change['to'] is not None
            assert change['toString'] is not None
            old_tag = historic_user(website, file, HistoricValue(change['from'], change['fromString']))
            new_tag = historic_user(website, file, HistoricValue(change['to'], change['toString']))
            yield revision_from_to(soup, 'Changed Reporter: ', old_tag, new_tag)
         case 'Key': # source always null, string always 'key'
            assert change['fromString'] is not None
            assert change['toString'] is not None
            assert entry.project_move is not None
            before_proj = try_project(website.cache, entry.project_move.before)
            after_proj = try_project(website.cache, entry.project_move.after)
            old_tag = issue_key(website, file, before_proj, change['fromString'], with_icon=True)
            new_tag = issue_key(website, file, after_proj, change['toString'], with_icon=True)
            yield revision_from_to(soup, 'Moved Issue: ', old_tag, new_tag)
         # html or markup changes
         case 'summary': # source always null, string always text
            assert change['fromString'] is not None
            assert change['toString'] is not None
            before = new_content_tag(soup, 'span', change['fromString'])
            after = new_content_tag(soup, 'span', change['toString'])
            diff = html_diff(soup, before, after)
            # diff-panel-top for style.css
            yield revision_html_diff(soup, 'Summary', markup.RevisionData(before, after, diff), lambda x: x, 'diff-panel-top')
         case 'description': # source always null, string either null or text
            revision_markup = website.markup_source.get_issue_description_revision(issue_id, rev_id)
            yield revision_large_diff(website, file, 'Description', revision_markup)
         case 'environment': # source always null, string either null or text
            revision_markup = website.markup_source.get_issue_environment_revision(issue_id, rev_id)
            yield revision_large_diff(website, file, 'Environment', revision_markup)
         case 'Comment': # from always text, all the rest always null
            assert change['from'] is not None
            assert change['to'] is None
            if UNKNOWN_COMMENT_RE.match(change['from']) is None and not website.perms.hidden_deleted_comments:
               comment = website.markup_source.get_deleted_comment_body(issue_id, rev_id)
               yield revision_quoted(soup, 'Deleted Comment:', [embed_wiki(website, file, markup.parse_markup(comment))])
         case (
            'RemoteIssueLink' # unfortunately these were not preserved in the archive
            | 'CHK' | 'Linked' | 'Pinned' # pointless fields
            | 'Workflow' # noise
            | 'Console' | 'Description' | 'Flagged' | 'Original story points' | 'Approvers' # only used in one test ticket
            | 'issuetype' # only relevant to MCAPI which sadly was not preserved
            | 'Affected Platforms' # old field that was only ever removed from tickets
            | 'project' | 'Project' # handled specially in advance
         ):
            pass
         case _:
            raise ValueError()
   yield from components.handle(website, file)
   yield from affected_versions.handle(website, file)
   yield from fixed_versions.handle(website, file)
   yield from attachments.handle(website, file)
   yield from links.handle(website, file)

# misc components
@dataclasses.dataclass
class UserReference:
   inner: bs4.Tag
   outer: bs4.Tag
   link: str
   display_name: str

def user_reference(website: Website, file: HtmlFile, user: User | UnknownUser) -> UserReference:
   display_name = user['displayName']
   img = user_avatar(website, file, user)
   link_url = relative_link(website.root, file.path, website.get_user_name_path(user['name']))
   # user-hover and rel for mojira.css
   # user-link for misode.css
   inner = new_content_tag(file.page.soup, 'span', attrs={'class':'user-hover user-link', 'rel': user['name']}, content=display_name)
   # aui-avatar for mojira.css
   # user-name-span for style.css
   outer = new_content_tag(file.page.soup, 'span', attrs={'class': 'user-name-span'}, content=[
      new_content_tag(file.page.soup, 'span', attrs={'class': 'aui-avatar'}, content=img),
      inner
   ])
   return UserReference(inner, outer, link_url, display_name)

def user_reference_key(website: Website, file: HtmlFile, user_key: str) -> UserReference:
   user_data = get_user(website.archive, user_key)
   return user_reference(website, file, user_data)

def user_link(website: Website, file: HtmlFile, user_key: str) -> bs4.Tag:
   ref = user_reference_key(website, file, user_key)
   ref.inner.name = 'a'
   ref.inner.attrs['href'] = ref.link
   return ref.outer

def historic_user(website: Website, file: HtmlFile, value: HistoricValue) -> bs4.Tag:
   user_data = website.archive.get_user_data(value.id)
   if user_data is None:
      user_data = website.archive.get_unknown_user_data(value.id)
      if user_data is None:
         return new_content_tag(file.page.soup, 'span', content=value.name, attrs={'class': 'missing-user'})
   return user_link(website, file, value.id)

def comment_author(website: Website, file: HtmlFile, user_key: str) -> bs4.Tag:
   ref = user_reference_key(website, file, user_key)
   ref.inner.name = 'a'
   ref.inner.attrs['href'] = ref.link
   # comment-author for misode.css
   append_class(ref.inner, 'comment-author')
   return ref.outer

def comment_author_or_dict(website: Website, file: HtmlFile, author: str | NewAuthor) -> bs4.Tag:
   if isinstance(author, str):
      return comment_author(website, file, author)
   # comment-author for misode.css
   return new_content_tag(file.page.soup, 'span', attrs={'class': 'comment-author'}, content=author['displayName'])

def user_head_issue(website: Website, file: HtmlFile, issue: Issue) -> typing.Generator[Tag]:
   soup = file.page.soup
   created_time = datetime.datetime.fromisoformat(issue['fields']['created'])
   if issue['fields']['reporter'] is not None:
      yield comment_author(website, file, issue['fields']['reporter'])
      yield ' '
   link = relative_link(website.root, file.path, website.get_issue_path(issue))
   # comment-link for misode.css
   # comment-on for misode.css
   link_part = soup.new_tag('a', attrs={'class': 'comment-link', 'href': link})
   yield new_content_tag(soup, 'span', 'on', attrs={'class': 'comment-on'})
   yield ' '
   # issue-key for misode.css
   issue_key = new_content_tag(soup, 'span', attrs={'class': 'issue-key'}, content=issue['key'])
   link_part.append(issue_key)
   link_part.append(' ')
   # comment-time for misode.css
   link_part.append(new_content_tag(soup, 'span', attrs={'class': 'comment-time'}, content=render_datetime(soup, created_time)))
   yield link_part

def user_head_comment(website: Website, file: HtmlFile, comment: Comment | NewComment, secret: bool, issue: Issue | None) -> typing.Generator[Tag]:
   soup = file.page.soup
   created_time = datetime.datetime.fromisoformat(comment['created'])
   updated_time = datetime.datetime.fromisoformat(comment['updated'])
   if 'author' in comment:
      yield comment_author_or_dict(website, file, comment['author'])
      yield ' '
   # apply the comment-time class to the entire span and the link specifically so they both turn gray
   if issue is None:
      link = f'#comment-id-{comment['id']}'
   else:
      link = relative_link(website.root, file.path, website.get_issue_path(issue)) + f'#comment-id-{comment['id']}'
   # comment-link for misode.css
   # comment-on for misode.css
   link_part = soup.new_tag('a', attrs={'class': 'comment-link', 'href': link})
   if issue is not None:
      yield new_content_tag(soup, 'span', 'on', attrs={'class': 'comment-on'})
      yield ' '
      # issue-key for misode.css
      issue_key = new_content_tag(soup, 'span', attrs={'class': 'issue-key'}, content=issue['key'])
      link_part.append(issue_key)
      link_part.append(' ')
   # comment-time for misode.css
   link_part.append(new_content_tag(soup, 'span', attrs={'class': 'comment-time'}, content=render_datetime(soup, created_time)))
   yield link_part
   more_info = soup.new_tag('span', attrs={'class': 'comment-time'})
   has_update_author = 'updateAuthor' in comment and ('author' not in comment or comment['updateAuthor'] != comment['author'])
   has_update = comment['updated'] != comment['created']
   if has_update_author or has_update:
      more_info.append(' • edited ')
   if has_update_author:
      assert 'updateAuthor' in comment
      more_info.append(comment_author_or_dict(website, file, comment['updateAuthor']))
      if has_update:
         more_info.append(' ')
   if has_update:
      if same_day(created_time, updated_time):
         inner_time = render_time(soup, updated_time)
      else:
         inner_time = render_datetime(soup, updated_time)
      more_info.append(inner_time)
   if 'visibility' in comment:
      if comment['visibility']['type'] == 'group':
         restriction = group_link(website, file, comment['visibility']['value'])
      else:
         # user-group-name for style.css
         restriction = new_content_tag(soup, 'span', attrs={'class': 'user-group-name'}, content=comment['visibility']['value'])
      more_info.extend([
         ' • ',
         soup.new_tag('img', attrs={'width': '16', 'height': '16', 'loading': 'lazy', 'alt': 'Restricted', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/ic_locked.png'))}),
         ' Restricted to ',
         restriction
      ])
   if secret:
      more_info.extend([
         ' • ',
         soup.new_tag('img', attrs={'width': '16', 'height': '16', 'loading': 'lazy', 'alt': 'Restricted', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/ic_locked.png'))}),
         ' Secret comment',
      ])
   yield more_info

def issue_key(website: Website, file: HtmlFile, project: Project | None, text: str, with_icon: bool) -> bs4.Tag:
   content: list[Tag] = []
   if with_icon:
      if project is not None:
         content.append(project_avatar(website, file, project))
      else:
         content.append(bug_icon(website, file))
   content.append(text)
   return new_content_tag(file.page.soup, 'span', content, attrs={'class': 'issue-key-span'})

def issue_key_issue(website: Website, file: HtmlFile, issue: Issue, with_icon: bool) -> bs4.Tag:
   project = try_project(website.cache, issue['fields']['project'])
   return issue_key(website, file, project, issue['key'], with_icon)

def issue_link(website: Website, file: HtmlFile, issue: Issue, with_icon: bool) -> bs4.Tag:
   link = relative_link(website.root, file.path, website.get_issue_path(issue))
   tag = issue_key_issue(website, file, issue, with_icon)
   tag.name = 'a'
   tag.attrs['href'] = link
   return tag

def project_key(website: Website, file: HtmlFile, project: Project, with_icon: bool) -> bs4.Tag:
   content: list[Tag] = []
   if with_icon:
      content.append(project_avatar(website, file, project))
   content.append(project['key'])
   return new_content_tag(file.page.soup, 'span', content, attrs={'class': 'project-key-span'})

def project_link(website: Website, file: HtmlFile, project: Project, with_icon: bool) -> bs4.Tag:
   tag = project_key(website, file, project, with_icon)
   tag.name = 'a'
   tag.attrs['href'] = relative_link(website.root, file.path, website.project_pages[project['id']].main.path)
   return tag

def group_name(website: Website, file: HtmlFile, group: str) -> bs4.Tag:
   assert group in website.cache.groups
   # user-group-name for style.css
   return new_content_tag(file.page.soup, 'span', attrs={'class': 'user-group-name'}, content=group)

def group_link(website: Website, file: HtmlFile, group: str) -> bs4.Tag:
   assert group in website.cache.groups
   link = relative_link(website.root, file.path, website.group_pages[group].users.path)
   # user-group-name for style.css
   return new_content_tag(file.page.soup, 'a', attrs={'class': 'user-group-name', 'href': link}, content=group)

def issue_attachments(website: Website, file: HtmlFile, attachments: list[str]) -> bs4.Tag:
   soup = file.page.soup
   attach_list: list[bs4.Tag] = []
   for entry in attachments:
      attach_info = website.cache.attachment_getter(entry)
      attach_div = render_attachment(website, file, attach_info, external_issue=None, include_author=True, include_time=True)
      attach_list.append(attach_div)
   return build_attachment_list(soup, attach_list)

def render_attachment(website: Website, file: HtmlFile, attachment: Attachment, external_issue: Issue | None, include_author: bool, include_time: bool) -> bs4.Tag:
   soup = file.page.soup
   preview = attachment_preview(website, file, attachment)
   attach_path = website.archive.get_attachment_content_path(attachment['id'], attachment['filename'])
   # attachment-details for style.css
   # attachment-block for style.css
   details_div = soup.new_tag('div', attrs={'class': 'attachment-details'})
   attach_div = soup.new_tag('div', attrs={'class': 'attachment-block'})
   attach_div.append(preview)
   attach_div.append(details_div)
   if external_issue is not None:
      issue_link = relative_link(website.root, file.path, website.get_issue_path(external_issue))
      details_div.append(new_content_tag(soup, 'a', attrs={'href': issue_link}, content=[
         issue_key_issue(website, file, external_issue, with_icon=True)
      ]))
   link = relative_link(website.root, file.path, attach_path)
   details_div.append(new_content_tag(soup, 'a', attrs={'href': link}, content=attachment['filename']))
   if include_author and 'author' in attachment:
         details_div.append(
            new_content_tag(soup, 'p', content=comment_author(website, file, attachment['author']))
         )
   if include_time:
      date_tag = render_datetime(soup, datetime.datetime.fromisoformat(attachment['created']))
      # comment-time for misode.css
      date_tag.attrs['class'] = 'comment-time'
      details_div.append(new_content_tag(soup, 'p', content=date_tag))
   return attach_div

def attachment_preview(website: Website, file: HtmlFile, attachment: Attachment) -> bs4.Tag:
   attach_path = website.archive.get_attachment_content_path(attachment['id'], attachment['filename'])
   link = relative_link(website.root, file.path, attach_path)
   mime = attachment['mimeType']
   # attachment-img for style.css
   if mime.startswith('image/'):
      img_tag = file.page.soup.new_tag('img', attrs={'class': 'attachment-img', 'src': link, 'alt': 'Attached image file', 'loading': 'lazy'})
      try:
         with PIL.Image.open(attach_path) as img:
            width, height = img.size
            img_tag.attrs['width'] = str(width)
            img_tag.attrs['height'] = str(height)
      except PIL.UnidentifiedImageError:
         pass
      return new_content_tag(file.page.soup, 'a', attrs={'href': link}, content=[
         img_tag
      ])
   if mime.startswith('video/'):
      return new_content_tag(file.page.soup, 'video', attrs={'class': 'attachment-img', 'alt': 'Attached video file', 'loading': 'lazy', 'controls': ''}, content=[file.page.soup.new_tag('source', attrs={'src': link})])
   if mime in ('application/zip', 'application/gzip'):
      icon = 'zip'
   elif mime == 'text/html':
      icon = 'html'
   elif mime == 'text/xml':
      icon = 'xml'
   elif mime.startswith('text/') or mime == 'application/json':
      icon = 'text'
   elif mime == 'application/msword':
      icon = 'word'
   elif mime == 'application/vnd.ms-excel':
      icon = 'excel'
   elif mime == 'application/vnd.ms-powerpoint':
      icon = 'powerpoint'
   elif mime == 'application/java-archive':
      icon = 'java'
   elif mime == 'application/pdf':
      icon = 'pdf'
   else:
      icon = 'file'
   # attachment-icon for style.css
   return new_content_tag(file.page.soup, 'a', attrs={'href': link}, content=[
      file.page.soup.new_tag('img', attrs={'class': 'attachment-icon', 'width': '16', 'height': '16', 'alt': f'Attached {icon} file', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/attach') / (icon + '.gif'))})
   ])

def historic_attachments(website: Website, file: HtmlFile, attachments: list[HistoricValue]) -> bs4.Tag:
   attach_list: list[bs4.Tag] = []
   for attach in attachments:
      attach_div = historic_attachment(website, file, attach)
      attach_list.append(attach_div)
   return build_attachment_list(file.page.soup, attach_list)

def historic_attachment(website: Website, file: HtmlFile, attach: HistoricValue) -> bs4.Tag:
   attachment = website.archive.get_attachment_data(attach.id)
   if attachment is not None:
      return render_attachment(website, file, attachment, external_issue=None, include_author=False, include_time=False)
   broken = file.page.soup.new_tag('img', attrs={'width': '32', 'height': '32', 'loading': 'lazy', 'alt': 'Unavailable attachment', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/attach/noimage.svg'))})
   # broken-attachment for style.css
   return new_content_tag(file.page.soup, 'div', attrs={'class': 'broken-attachment'}, content=[broken, attach.name])

def issue_links(website: Website, file: HtmlFile, links: dict[str, list[str]]) -> bs4.Tag | None:
   soup = file.page.soup
   link_types: dict[str, list[bs4.Tag]] = {}
   for identity, issues in links.items():
      link_types[identity] = [linked_issue(website, file, x) for x in website.cache.get_issues(issues)]
   if len(link_types) == 0:
      return None
   return build_link_section(soup, link_types)

def linked_issue(website: Website, file: HtmlFile, issue: Issue) -> bs4.Tag:
   # issue-link for misode.css
   # issue-resolved for misode.css
   status = merged_status(website, file, issue)
   cls = 'issue-link'
   if status.kind == 'resolved':
      cls += ' issue-resolved'
   elif status.kind == 'progress':
      cls += ' issue-progress'
   link = relative_link(website.root, file.path, website.get_issue_path(issue))
   key = issue_key_issue(website, file, issue, with_icon=True)
   # issue-link-key for misode.css
   append_class(key, 'issue-link-key')
   # issue-link-summary for misode.css
   summary = new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-link-summary', 'title': issue['fields']['summary']}, content=issue['fields']['summary'])
   return new_content_tag(file.page.soup, 'a', attrs={'class': cls, 'href': link}, content=[
      key,
      summary,
      status.badge.outer
   ])

def historic_links(website: Website, file: HtmlFile, links: typing.Iterable[HistoricValue]) -> bs4.Tag | None:
   link_types: dict[str, list[bs4.Tag]] = {}
   for link in links:
      identity = get_link_dir(link.name, link.id)
      if identity not in link_types:
         link_types[identity] = []
      link_types[identity].append(historic_linked_issue(website, file, link.id))
   if len(link_types) == 0:
      return None
   return build_link_section(file.page.soup, link_types)

def historic_linked_issue(website: Website, file: HtmlFile, ticket: str) -> bs4.Tag:
   if ticket in website.keys.issue_keys:
      issue_id = website.keys.issue_keys[ticket]
      if issue_id in website.cache.valid_issues:
         issue = website.cache.just_issue_getter(issue_id)
         # wrap in a div so misode.css includes the top border
         return new_content_tag(file.page.soup, 'div', linked_issue(website, file, issue))
   return new_content_tag(file.page.soup, 'div', issue_key(website, file, None, ticket, with_icon=True), attrs={'class': 'missing-value'})

def version_list(website: Website, file: HtmlFile, project: Project, versions: list[Version]) -> Tag:
   if len(versions) == 0:
      return ''
   if len(versions) == 1:
      return version_link(website, file, project, versions[0])
   span = inline_list(file.page.soup, map(lambda x: version_link(website, file, project, x), versions))
   if len(versions) <= 4:
      return span
   return new_content_tag(file.page.soup, 'details', [
      new_content_tag(file.page.soup, 'summary', [
         version_link(website, file, project, versions[0]),
         ' - ',
         version_link(website, file, project, versions[-1]),
      ]),
      span
   ])

def version_link(website: Website, file: HtmlFile, project: Project, version: Version) -> bs4.Tag:
   name = version['name']
   name = name.removeprefix('Minecraft ').removeprefix('Snapshot ')
   name = name.replace(' Pre-Release ', '-pre').replace(' Pre-release ', '-pre').replace(' Release Candidate ', '-rc')
   link = relative_link(website.root, file.path, website.project_pages[project['id']].get_version_path(version))
   return new_content_tag(file.page.soup, 'a', name, attrs={'class': 'status-badge', 'href': link})

def historic_version_list(website: Website, file: HtmlFile, versions: typing.Iterable[HistoricProjectValue]) -> bs4.Tag:
   return inline_list(file.page.soup, (historic_version(website, file, x) for x in versions))

def historic_version(website: Website, file: HtmlFile, version: HistoricProjectValue) -> bs4.Tag:
   if version.project in website.cache.projects:
      project = website.cache.projects[version.project]
      if version.id in project.versions:
         return version_link(website, file, project.project, project.versions[version.id].version)
   badge = status_badge(file.page.soup, version.name)
   append_class(badge, 'missing-value')
   return badge

@dataclasses.dataclass
class FieldBadge:
   outer: bs4.Tag
   link: str
   resolved: bool
   progress: bool

def meta_badge_display(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, display: ValueDisplay) -> FieldBadge:
   link = relative_link(website.root, file.path, website.meta_pages[meta_id].get_value_path(display.name))
   tag = status_badge(file.page.soup, display.name)
   append_class(tag, f'field-value-{meta_id}')
   if display.description is not None:
      tag.attrs['title'] = display.description
   resolved = (meta_id == 'resolution' and display.id is not None) or (meta_id == 'status' and display.id in ('5', '6'))
   progress = (meta_id == 'status' and display.id in ('3', '10200'))
   return FieldBadge(tag, link, resolved, progress)

def meta_badge(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, value_key: str | None) -> FieldBadge:
   display = website.cache.metas[meta_id].values[value_key].display
   return meta_badge_display(website, file, meta_id, display)

def meta_link_display(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, display: ValueDisplay) -> bs4.Tag:
   badge = meta_badge_display(website, file, meta_id, display)
   badge.outer.name = 'a'
   badge.outer.attrs['href'] = badge.link
   if badge.resolved:
      # issue-resolved for misode.css
      return new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-resolved'}, content=badge.outer)
   if badge.progress:
      return new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-progress'}, content=badge.outer)
   return badge.outer

def meta_link(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, value_key: str | None) -> bs4.Tag:
   display = website.cache.metas[meta_id].values[value_key].display
   return meta_link_display(website, file, meta_id, display)

def field_badge_display(website: Website, file: HtmlFile, field_id: str, display: ValueDisplay) -> FieldBadge:
   field_name_str = website.cache.fields[field_id].name.lower().replace(' ', '-').replace('/', '')
   link = relative_link(website.root, file.path, website.field_pages[field_id].get_value_path(display.name))
   content: list[Tag] = [display.name]
   if display.icon is not None:
      assert display.icon.startswith('https://bugs.mojang.com/')
      relative = pathlib.PurePath(display.icon[len('https://bugs.mojang.com/'):])
      img = file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'loading': 'lazy', 'alt': display.name, 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets') / relative)})
      content.insert(0, img)
   elif field_id == 'customfield_12200':
      content.insert(0, mojang_priority_icon(website, file, display.name))
   tag = status_badge(file.page.soup, content)
   append_class(tag, f'field-value-{field_name_str}')
   if display.description is not None:
      tag.attrs['title'] = display.description
   return FieldBadge(tag, link, False, False)

def field_badge(website: Website, file: HtmlFile, field_id: str, value_key: str) -> FieldBadge:
   display = website.cache.fields[field_id].values[value_key].display
   return field_badge_display(website, file, field_id, display)

def field_link_display(website: Website, file: HtmlFile, field_id: str, display: ValueDisplay) -> bs4.Tag:
   badge = field_badge_display(website, file, field_id, display)
   badge.outer.name = 'a'
   badge.outer.attrs['href'] = badge.link
   return badge.outer

def field_link(website: Website, file: HtmlFile, field_id: str, value_key: str) -> bs4.Tag:
   display = website.cache.fields[field_id].values[value_key].display
   return field_link_display(website, file, field_id, display)

def historic_meta(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, source: str | None, string: str | None) -> bs4.Tag:
   if source in website.cache.metas[meta_id].values:
      display = website.cache.metas[meta_id].values[source].display
      return meta_link_display(website, file, meta_id, display)
   assert string is not None
   badge = status_badge(file.page.soup, string)
   append_class(badge, 'missing-value')
   return badge

def historic_field(website: Website, file: HtmlFile, field_id: str, value: HistoricValue) -> bs4.Tag:
   if value.id in website.cache.fields[field_id].values:
      return field_link(website, file, field_id, value.id)
   badge = status_badge(file.page.soup, value.name)
   field_name_str = website.cache.fields[field_id].name.lower().replace(' ', '-').replace('/', '')
   append_class(badge, f'field-value-{field_name_str}')
   append_class(badge, 'missing-value')
   return badge

def historic_field_list(website: Website, file: HtmlFile, field_id: str, fields: typing.Iterable[HistoricValue]) -> bs4.Tag:
   return inline_list(file.page.soup, (historic_field(website, file, field_id, x) for x in fields))

@dataclasses.dataclass
class MergedStatus:
   kind: typing.Literal['resolved', 'progress', 'priority', 'confirmed', 'unresolved']
   badge: FieldBadge

def merged_status(website: Website, file: HtmlFile, issue: Issue) -> MergedStatus:
   fields = issue['fields']
   if (resolution := fields['resolution']) is not None:
      return MergedStatus('resolved', meta_badge(website, file, 'resolution', resolution))
   if (status := fields['status']) in ('3', '10200'):
      return MergedStatus('progress', meta_badge(website, file, 'status', status))
   if (priority := fields.get('customfield_12200')) is not None:
      return MergedStatus('priority', field_badge(website, file, 'customfield_12200', priority['id']))
   if (confirmation := fields.get('customfield_10500')) is not None:
      return MergedStatus('confirmed', field_badge(website, file, 'customfield_10500', confirmation['id']))
   return MergedStatus('unresolved', meta_badge(website, file, 'resolution', None))

def issue_detail_field_label(website: Website, file: HtmlFile, field_id: str) -> bs4.Tag:
   link = relative_link(website.root, file.path, website.field_pages[field_id].page.path)
   fname = website.cache.fields[field_id].name
   label = new_content_tag(file.page.soup, 'a', fname + ':', attrs={'href': link})
   return label

def issue_detail_meta_label(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE) -> bs4.Tag:
   link = relative_link(website.root, file.path, website.meta_pages[meta_id].page.path)
   fname = website.cache.metas[meta_id].name
   label = new_content_tag(file.page.soup, 'a', fname + ':', attrs={'href': link})
   return label

def issue_detail_field(website: Website, file: HtmlFile, field_id: str, value_key: str) -> tuple[bs4.Tag, bs4.Tag]:
   return (
      issue_detail_field_label(website, file, field_id),
      field_link(website, file, field_id, value_key)
   )

def issue_detail_meta(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, value_key: str | None) -> tuple[bs4.Tag, bs4.Tag]:
   return (
      issue_detail_meta_label(website, file, meta_id),
      meta_link(website, file, meta_id, value_key)
   )

def historic_detail_field(website: Website, file: HtmlFile, field_id: str, value: HistoricValue) -> tuple[bs4.Tag, bs4.Tag]:
   return (
      issue_detail_field_label(website, file, field_id),
      historic_field(website, file, field_id, value)
   )

def historic_detail_meta(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, value: HistoricValue | None) -> tuple[bs4.Tag, bs4.Tag]:
   id = None if value is None else value.id
   name = None if value is None else value.name
   return (
      issue_detail_meta_label(website, file, meta_id),
      historic_meta(website, file, meta_id, id, name)
   )

def issue_top(website: Website, file: HtmlFile, project: Project | None, key: str, summary: str) -> bs4.Tag:
   key_tag = issue_key(website, file, project, key, with_icon=True)
   if project is not None:
      key_tag.name = 'a'
      key_tag.attrs['href'] = relative_link(website.root, file.path, website.project_pages[project['id']].main.path)
   return build_info_top(
      file.page.soup,
      # issue-key for misode.css
      new_content_tag(file.page.soup, 'div', attrs={'class': 'issue-key'}, content=key_tag),
      summary
   )

def issue_body(soup: bs4.BeautifulSoup, desc: bs4.Tag | None, env: bs4.Tag | None, impact: str | None) -> typing.Generator[bs4.Tag]:
   # classes for style.css
   if desc is not None:
      yield new_content_tag(soup, 'div', attrs={'class': 'issue-description'}, content=desc)
   if env is not None:
      yield new_content_tag(soup, 'div', attrs={'class': 'issue-environment'}, content=[
         new_content_tag(soup, 'h2', 'Environment'),
         env
      ])
   if impact is not None:
      yield new_content_tag(soup, 'div', attrs={'class': 'issue-impact'}, content=[
         new_content_tag(soup, 'h2', 'Impact'),
         new_content_tag(soup, 'p', content=impact)
      ])

def issue_comments(website: Website, file: HtmlFile, comments: typing.Iterable[RenderableComment]) -> PageSection:
   return build_user_section(file.page.soup, 'comment', 200, (comment_to_user(website, file, x) for x in comments))

def issue_history(website: Website, file: HtmlFile, issue: CachedIssue, revisions: list[Revision]) -> PageSection:
   initial_content = historic_issue(website, file, issue, issue.initial)
   initial_tag: list[Tag] = [
      # classes for style.css
      new_content_tag(file.page.soup, 'details', attrs={'open': ''}, content=[
         new_content_tag(file.page.soup, 'summary', revision_label(file.page.soup, 'Created Issue:')),
         new_content_tag(file.page.soup, 'div', attrs={'class': 'revision-change'}, content=[
            new_content_tag(file.page.soup, 'blockquote', attrs={'class': 'history-quote'}, content=initial_content)
         ])
      ])
   ]
   initial_render = RenderableRevision('initial', issue.issue['fields'].get('creator'), issue.created, None, None, initial_tag)
   renderable = get_renderable_revisions(website, file, issue.issue['id'], None, issue.initial.fields['project'], revisions)
   renderable.insert(0, initial_render)
   return build_user_section(file.page.soup, 'history', 200, (revision_to_user(website, file, x) for x in renderable))

def issue_mentions(website: Website, file: HtmlFile, mentions: typing.Iterable[RenderableMention]) -> PageSection:
   return build_user_section(file.page.soup, 'mention', 200, (mention_to_user(website, file, x) for x in mentions))

def user_activity(website: Website, file: HtmlFile, revisions: dict[str, list[str]]) -> PageSection:
   revision_data: list[tuple[CachedIssue, list[Revision]]] = []
   for issue_id, revision_ids in revisions.items():
      issue = website.cache.issue_getter(issue_id)
      issue_revs: dict[str, Revision] = {}
      for entry in issue.issue['changelog']['histories']:
         issue_revs[entry['id']] = entry
      found_revs: list[Revision] = []
      for revision_id in revision_ids:
         revision = issue_revs[revision_id]
         found_revs.append(revision)
      revision_data.append((issue, found_revs))
   revision_data.sort(key=lambda x: datetime.datetime.fromisoformat(x[1][0]['created']))
   all_renderable: list[RenderableRevision] = []
   for issue, revs in revision_data:
      renderable = get_renderable_revisions(website, file, issue.issue['id'], issue.issue, issue.initial.fields['project'], revs)
      all_renderable.extend(renderable)
   return build_user_section(file.page.soup, 'history', 200, (revision_to_user(website, file, x) for x in all_renderable))

def user_attachments(website: Website, file: HtmlFile, attachments: dict[str, list[str]]) -> PageSection:
   attach_data: list[tuple[Issue, Attachment]] = []
   for issue_id, attach_ids in attachments.items():
      issue = website.cache.just_issue_getter(issue_id)
      for attach_id in attach_ids:
         attachment = website.cache.attachment_getter(attach_id)
         attach_data.append((issue, attachment))
   attach_data.sort(key=lambda x: datetime.datetime.fromisoformat(x[1]['created']))
   attach_tags: list[tuple[bs4.Tag, str | None]] = []
   for issue, attachment in attach_data:
      tag = render_attachment(website, file, attachment, external_issue=issue, include_author=False, include_time=True)
      tag.attrs['style'] = f'--order: {len(attach_tags)}'
      attach_tags.append((tag, None))
   section = build_page_section(file.page.soup, 'attachment', 60, attach_tags)
   append_class(section.section, 'attachments')
   return section

def count_badge(soup: bs4.BeautifulSoup, amount: int) -> bs4.Tag:
   # count-badge for misode.css
   return new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=format_number(amount))

def preserve_spaces(value: str) -> str:
   stripped = value.lstrip(' ')
   value = '\u00a0' * (len(value) - len(stripped)) + stripped
   stripped = value.rstrip(' ')
   value = stripped + '\u00a0' * (len(value) - len(stripped))
   return value

def status_badge(soup: bs4.BeautifulSoup, content: Tag | list[Tag]) -> bs4.Tag:
   if not isinstance(content, list):
      content = [content]
   for i, value in enumerate(content):
      if isinstance(value, str):
         content[i] = preserve_spaces(value)
   # status-badge for misode.css
   return new_content_tag(soup, 'span', attrs={'class': 'status-badge'}, content=content)

def bug_icon(website: Website, file: HtmlFile) -> bs4.Tag:
   link = relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/issuetypes/bug.svg'))
   return file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'loading': 'lazy', 'src': link, 'alt': 'Issue'})

def user_avatar_link(website: Website, file: HtmlFile, user: User | UnknownUser) -> str:
   gravatar_path1 = website.archive.folder / 'assets/gravatar' / (mojira.encode_user_string(user['key']) + '.png')
   gravatar_path2 = website.archive.folder / 'assets/gravatar' / (mojira.encode_user_string(user['key']) + '.jpeg')
   if gravatar_path1.exists():
      return str(relative_path(website.root, file.path, gravatar_path1))
   if gravatar_path2.exists():
      return str(relative_path(website.root, file.path, gravatar_path2))
   avatar_url = user['avatarUrls']['48x48']
   avatar_path = get_avatar_path(website.archive, website.archive.users_avatars_folder, avatar_url)
   assert avatar_path is not None
   return str(relative_path(website.root, file.path, avatar_path))

def user_avatar(website: Website, file: HtmlFile, user: User | UnknownUser) -> bs4.Tag:
   link = user_avatar_link(website, file, user)
   # avatar for misode.css
   return file.page.soup.new_tag('img', attrs={'class': 'avatar', 'width': '48', 'height': '48', 'loading': 'lazy', 'src': link, 'alt': user['displayName']})

def project_avatar(website: Website, file: HtmlFile, project: Project) -> bs4.Tag:
   avatar_url = project['avatarUrls']['48x48']
   avatar_path = get_avatar_path(website.archive, website.archive.project_avatars_folder, avatar_url)
   assert avatar_path is not None
   link = str(relative_path(website.root, file.path, avatar_path))
   return file.page.soup.new_tag('img', attrs={'width': '48', 'height': '48', 'loading': 'lazy', 'src': link, 'alt': project['name']})

def mojang_priority_icon(website: Website, file: HtmlFile, value: str) -> bs4.Tag:
   prio = {'Trivial': 'trivial', 'Low': 'low', 'Normal': 'medium', 'Important': 'high', 'Very Important': 'major'}[value]
   link = relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/priorities') / f'{prio}.svg')
   img = file.page.soup.new_tag('img', attrs={'width': '48', 'height': '48', 'loading': 'lazy', 'src': link, 'alt': value})
   return img

if __name__ == '__main__':
   main()
