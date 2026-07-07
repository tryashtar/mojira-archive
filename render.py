import dataclasses
import os
import sys
import typing
import dotenv
from jiratypes import Attachment, Comment, Issue, IssueLink, NewAuthor, NewComment, Project, Revision, RevisionChange, User, Version
import markup_relations
import mojira
import relations
import pathlib
import datetime
import urllib.parse
import markup
import bs4
import re
import bisect
import copy
import natsort
import json
from web import HtmlFile, add_metadata, append_desc_item, append_row, html_diff, html_to_text, inline_list, make_file, make_table, new_content_tag, relative_link, relative_path, render_date, render_date_range, render_datetime, render_time, same_day, write_html

@dataclasses.dataclass
class FieldPage:
   page: HtmlFile
   values_folder: pathlib.PurePath

   def get_value_path(self, value_name: str) -> pathlib.PurePath:
      return self.values_folder / (value_name.replace('/', '_') + '.html')

@dataclasses.dataclass
class ProjectPage:
   main: HtmlFile
   versions: HtmlFile | None
   issues: HtmlFile
   versions_folder: pathlib.PurePath

   def get_version_path(self, version: Version) -> pathlib.PurePath:
      return self.versions_folder / (version['name'].replace('/', '_') + '.html')

@dataclasses.dataclass
class Website:
   root: pathlib.Path
   home: HtmlFile
   all_issues_list: HtmlFile
   all_users_list: HtmlFile
   issues_folder: pathlib.PurePath
   users_folder: pathlib.PurePath
   group_page: FieldPage
   project_pages: dict[str, ProjectPage]
   field_pages: dict[str, FieldPage]
   archive: mojira.Archive
   metas: mojira.ArchiveMetas
   relations: relations.RelationsBundle
   markup_source: markup.MarkupSource
   markup_rels: markup_relations.MarkupRelations
   secret_comments: mojira.SecretComments

   def get_issue_path(self, issue: Issue) -> pathlib.PurePath:
      return self.get_issue_key_path(issue['key'])

   def get_issue_key_path(self, issue_key: str) -> pathlib.PurePath:
      return self.issues_folder / (issue_key + '.html')

   def get_user_path(self, user: User) -> pathlib.PurePath:
      return self.get_user_name_path(user['name'])

   def get_user_name_path(self, username: str) -> pathlib.PurePath:
      return self.users_folder / (urllib.parse.quote_plus(username.lower())[:100] + '.html')

def make_jira_file(root: pathlib.Path, path: pathlib.PurePath, title: str) -> HtmlFile:
   file = make_file(path, title)
   file.page.head.append(file.page.soup.new_tag('link', rel='icon', type='image/x-icon', href=relative_link(root, file.path, pathlib.PurePath('data/assets/favicon.ico'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('web/css/misode-reset.css'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('web/css/misode-style.css'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('data/assets/mojira.css'))))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(root, file.path, pathlib.PurePath('web/css/style.css'))))
   return file

def save_file(website: Website, file: HtmlFile):
   write_html(website.root / file.path, file.page)

def main():
   print('Loading...')
   dotenv.load_dotenv()
   root = pathlib.Path(os.environ['ARCHIVE_ROOT'])
   archive = mojira.Archive(pathlib.Path(os.environ['ARCHIVE_DATA']))
   metas = mojira.ArchiveMetas()
   metas.load(archive.folder)
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
   meta_list: list[mojira.META_TYPE] = ['resolution', 'status']
   website = Website(
      root=root,
      home=make_jira_file(root, pathlib.PurePath('web/home.html'), 'Mojira Archive'),
      all_issues_list=make_jira_file(root, pathlib.PurePath('web/issues.html'), 'All Issues'),
      all_users_list=make_jira_file(root, pathlib.PurePath('web/users.html'), 'All Users'),
      issues_folder=pathlib.PurePath('web/issues'),
      users_folder=pathlib.PurePath('web/users'),
      group_page=FieldPage(
         make_jira_file(root, pathlib.PurePath('web/groups.html'), 'User Groups'),
         pathlib.PurePath('web/groups')
      ),
      project_pages={},
      field_pages={},
      archive=archive,
      metas=metas,
      relations=rels,
      markup_source=markup_source,
      markup_rels=markup_rels,
      secret_comments=secret_comments
   )
   for id, value in metas.projects.items():
      full_title = f'[{value['key']}] {value['name']}'
      website.project_pages[id] = ProjectPage(
         make_jira_file(root, pathlib.PurePath('web/projects') / (value['key'] + '.html'), full_title),
         make_jira_file(root, pathlib.PurePath('web/projects') / value['key'] / 'versions.html', full_title) if len(value['versions']) > 0 else None,
         make_jira_file(root, pathlib.PurePath('web/projects') / value['key'] / 'issues.html', full_title),
         pathlib.PurePath('web/projects') / value['key'] / 'versions'
      )
   for key in [*rels.fields.fields.keys(), *meta_list]:
      fname = field_name(metas, key)
      website.field_pages[key] = FieldPage(
         make_jira_file(root, pathlib.PurePath('web/fields') / (fname + '.html'), fname),
         pathlib.PurePath('web/fields') / fname
      )


   print('Rendering...')
   to_render = sys.argv
   if 'all' in to_render:
      to_render.extend(['home', 'fields', 'metas', 'project_main', 'project_versions', 'project_issues', 'project_version_issues', 'field_issues', 'meta_issues', 'issues_list', 'issues', 'users', 'users_list'])
   if 'issue_lists' in to_render:
      to_render.extend(['project_issues', 'project_version_issues', 'field_issues', 'meta_issues', 'issues_list'])
   if 'home' in to_render:
      print('Home...')
      make_home_page(website, website.home)
      save_file(website, website.home)
   if 'metas' in to_render:
      print('Metas...')
      for key in meta_list:
         print('\t' + key)
         field_page = website.field_pages[key]
         make_meta_page(website, field_page.page, key)
         save_file(website, field_page.page)
   if 'fields' in to_render:
      print('Fields...')
      for key in rels.fields.fields.keys():
         print('\t' + key)
         field_page = website.field_pages[key]
         make_field_page(website, field_page.page, key)
         save_file(website, field_page.page)
   if 'project_main' in to_render:
      print('Project main...')
      for project_id, project in metas.projects.items():
         print('\t' + project['key'])
         project_page = website.project_pages[project_id]
         make_project_main_page(website, project_page.main, project)
         save_file(website, project_page.main)
   if 'project_versions' in to_render:
      print('Project versions...')
      for project_id, project in metas.projects.items():
         print('\t' + project['key'])
         project_page = website.project_pages[project_id]
         if project_page.versions is not None:
            make_project_versions_page(website, project_page.versions, project)
            save_file(website, project_page.versions)
   if 'project_issues' in to_render:
      print('Project issues...')
      for project_id, project in metas.projects.items():
         print('\t' + project['key'])
         project_page = website.project_pages[project_id]
         make_project_issues_page(website, project_page.issues, project)
         save_file(website, project_page.issues)
   if 'project_version_issues' in to_render:
      print('Project versions issues...')
      for project_id, project in metas.projects.items():
         print('\t' + project['key'])
         project_page = website.project_pages[project_id]
         for version in project['versions'].values():
            print('\t\t' + version['name'])
            full_title = f'[{project['key']}] {version['name']}'
            file = make_jira_file(website.root, project_page.get_version_path(version), full_title)
            make_version_page(website, file, version)
            save_file(website, file)
   if 'meta_issues' in to_render:
      print('Meta issues...')
      for key in meta_list:
         print('\t' + key)
         field_page = website.field_pages[key]
         fname = field_name(metas, key)
         value_keys: list[str | None] = list(metas.metas[key].keys())
         if key == 'resolution':
            value_keys.insert(0, None)
         for value_key in value_keys:
            display = metas.display_value(key, value_key)
            assert display is not None
            print('\t\t' + display.name)
            full_title = f'[{fname}] {display.name}'
            file = make_jira_file(website.root, field_page.get_value_path(display.name), full_title)
            make_meta_value_page(website, file, key, value_key)
            save_file(website, file)
   if 'field_issues' in to_render:
      print('Field issues...')
      for key, values in rels.fields.fields.items():
         print('\t' + key)
         field_page = website.field_pages[key]
         fname = field_name(metas, key)
         for value_key in values.keys():
            display = website.relations.fields.display_value(key, value_key)
            assert display is not None
            print('\t\t' + display.name)
            full_title = f'[{fname}] {display.name}'
            file = make_jira_file(website.root, field_page.get_value_path(display.name), full_title)
            make_field_value_page(website, file, key, value_key)
            save_file(website, file)
   if 'issues_list' in to_render:
      print('All issues...')
      make_all_issues_page(website, website.all_issues_list)
      save_file(website, website.all_issues_list)
   if 'issues' in to_render:
      print('Issues...')
      written_issues: set[str] = set()
      for i, issue in enumerate(archive.issues()):
         print('\t' + issue['key'])
         if i % 1000 == 0:
            print(f'\t== {i} ==')
         path = website.get_issue_path(issue)
         full_title = f'[{issue['key']}] {issue['fields']['summary']}'
         file = make_jira_file(website.root, path, full_title)
         make_issue_page(website, file, issue)
         save_file(website, file)
         written_issues.add(issue['key'])
      print('Moved issues...')
      for issue_key, issue_id in rels.keys.issue_keys.items():
         if issue_key not in written_issues:
            print('\t' + issue_key)
            issue = archive.get_issue_data(issue_id)
            assert issue is not None
            from_path = website.get_issue_key_path(issue_key)
            to_path = website.get_issue_path(issue)
            relative = relative_path(website.root, from_path, website.root / to_path)
            from_full = website.root / from_path
            if from_full.is_symlink():
               if from_full.readlink() != relative:
                  from_full.unlink()
                  from_full.symlink_to(relative)
            else:
               from_full.symlink_to(relative)
   if 'users' in to_render:
      print('Users...')
      for i, user in enumerate(archive.users()):
         print('\t' + user['name'])
         if i % 1000 == 0:
            print(f'\t== {i} ==')
         path = website.get_user_path(user)
         file = make_jira_file(website.root, path, user['displayName'])
         make_user_page(website, file, user)
         save_file(website, file)

def fix_markup(website: Website, file: HtmlFile, html: bs4.BeautifulSoup):
   parsed = markup.parse_markup(html)
   for entry in parsed.issues:
      if entry.key not in website.relations.keys.issue_keys:
         del entry.tag.attrs[entry.attr]
      else:
         entry.tag.attrs[entry.attr] = relative_link(website.root, file.path, website.get_issue_key_path(entry.key))
   for entry in parsed.users:
      if entry.username not in website.relations.keys.user_keys:
         del entry.tag.attrs[entry.attr]
      else:
         entry.tag.attrs[entry.attr] = relative_link(website.root, file.path, website.get_user_name_path(entry.username))
   for entry in [*parsed.attachments, *parsed.thumbnails]:
      data = website.archive.get_attachment_data(entry.id)
      if data is None:
         del entry.tag.attrs[entry.attr]
      else:
         path = relative_path(website.root, file.path, website.archive.get_attachment_content_path(entry.id, entry.filename))
         entry.tag.attrs[entry.attr] = urllib.parse.quote(str(path))
   for entry in parsed.icons:
      path = relative_path(website.root, file.path, website.archive.folder / 'assets/images' / entry.path)
      entry.tag.attrs[entry.attr] = urllib.parse.quote(str(path))

def make_home_page(website: Website, file: HtmlFile):
   soup = file.page.soup

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   file.page.body.append(make_generic_footer(website, file))

   issue_count = sum(1 for _ in website.archive.issue_ids())
   user_count = sum(1 for _ in website.archive.user_keys())
   add_metadata(file, 'Mojira Archive', f'{issue_count} issues, {user_count} users', None)

   home_main = soup.new_tag('div', attrs={'class': 'home-main'})
   content.append(home_main)
   home_main.append(new_content_tag(soup, 'h2', 'Full Lists'))
   home_main.append(new_content_tag(soup, 'div', attrs={'class': 'home-grid'}, content=[
      new_content_tag(soup, 'div', content=[
         new_content_tag(soup, 'a', attrs={'class': 'home-grid-name', 'href': relative_link(website.root, file.path, website.all_issues_list.path)}, content='All Issues'),
         f'{issue_count} issues'
      ]),
      new_content_tag(soup, 'div', content=[
         new_content_tag(soup, 'a', attrs={'class': 'home-grid-name', 'href': relative_link(website.root, file.path, website.all_users_list.path)}, content='All Users'),
         f'{user_count} users'
      ])
   ]))
   home_main.append(new_content_tag(soup, 'h2', 'Projects'))
   table = render_projects_grid(website, file, sorted(website.metas.projects.values(), key=lambda x: len(website.relations.fields.metas['project'][x['id']]), reverse=True))
   home_main.append(table)
   home_main.append(new_content_tag(soup, 'h2', 'Fields'))
   def relevant_tickets(field_id: str) -> int:
      if field_id in website.relations.fields.fields:
         return sum(len(x['issues']) for x in website.relations.fields.fields[field_id].values())
      return sum(len(x) for x in website.relations.fields.metas[field_id].values())
   table = render_fields_grid(website, file, sorted(website.field_pages.keys(), key=relevant_tickets, reverse=True))
   home_main.append(table)
   home_main.append(new_content_tag(soup, 'h2', 'User Groups'))
   table = render_groups_grid(website, file, sorted(website.relations.user.groups.keys(), key=lambda x: len(website.relations.user.groups[x]), reverse=True))
   home_main.append(table)

def make_all_issues_page(website: Website, file: HtmlFile):
   soup = file.page.soup

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   list_main = soup.new_tag('div', attrs={'class': 'list-main'})
   content.append(list_main)
   file.page.body.append(make_generic_footer(website, file))

   list_main.append(new_content_tag(soup, 'h1', 'All Issues'))
   table = create_issue_list(website, file, 'issue', website.archive.issues())
   list_main.append(table.filters)
   list_main.append(table.table)
   add_table_scripts(website, file, [table.data])

def make_field_page(website: Website, file: HtmlFile, field_id: str):
   soup = file.page.soup

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   file.page.body.append(make_generic_footer(website, file))

   name = field_name(website.metas, field_id)
   values = website.relations.fields.fields[field_id].values()
   add_metadata(file, name, f'{len(values)} values', None)

   home_main = soup.new_tag('div', attrs={'class': 'home-main'})
   content.append(home_main)
   home_main.append(new_content_tag(soup, 'h2', name))
   table = render_field_values_grid(website, file, field_id, sorted(values, key=field_value_order_key))
   home_main.append(table)

def make_field_value_page(website: Website, file: HtmlFile, field_id: str, value_key: str):
   soup = file.page.soup

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   list_main = soup.new_tag('div', attrs={'class': 'list-main'})
   content.append(list_main)
   file.page.body.append(make_generic_footer(website, file))

   display = website.relations.fields.display_value(field_id, value_key)
   assert display is not None

   issue_ids = website.relations.fields.fields[field_id][value_key]['issues']
   add_metadata(file, display.name, display.description, display.icon)
   def issue_map(issue_id: str):
      issue = website.archive.get_issue_data(issue_id)
      assert issue is not None
      return issue

   fname = field_name(website.metas, field_id)
   flink = relative_link(website.root, file.path, website.field_pages[field_id].page.path)
   list_main.append(new_content_tag(soup, 'h1', [new_content_tag(soup, 'a', attrs={'href': flink}, content=fname)]))
   list_main.append(new_content_tag(soup, 'h2', [field_link(website, file, field_id, value_key), ' issues']))
   table = create_issue_list(website, file, 'issue', (issue_map(x) for x in issue_ids))
   list_main.append(table.filters)
   list_main.append(table.table)
   add_table_scripts(website, file, [table.data])

def make_meta_value_page(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, value_key: str | None):
   soup = file.page.soup

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   list_main = soup.new_tag('div', attrs={'class': 'list-main'})
   content.append(list_main)
   file.page.body.append(make_generic_footer(website, file))

   issue_ids = website.relations.fields.metas[meta_id]['' if value_key is None else value_key]
   def issue_map(issue_id: str):
      issue = website.archive.get_issue_data(issue_id)
      assert issue is not None
      return issue

   fname = field_name(website.metas, meta_id)
   flink = relative_link(website.root, file.path, website.field_pages[meta_id].page.path)
   list_main.append(new_content_tag(soup, 'h1', [new_content_tag(soup, 'a', attrs={'href': flink}, content=fname)]))
   list_main.append(new_content_tag(soup, 'h2', [meta_link(website, file, meta_id, value_key), ' issues']))
   table = create_issue_list(website, file, 'issue', (issue_map(x) for x in issue_ids))
   list_main.append(table.filters)
   list_main.append(table.table)
   add_table_scripts(website, file, [table.data])

def make_meta_page(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE):
   soup = file.page.soup

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   file.page.body.append(make_generic_footer(website, file))

   name = field_name(website.metas, meta_id)
   values: list[str | None] = [x['id'] for x in website.metas.metas[meta_id].values()]
   if meta_id == 'resolution':
      values.insert(0, None)
   add_metadata(file, name, f'{len(values)} values', None)

   home_main = soup.new_tag('div', attrs={'class': 'home-main'})
   content.append(home_main)
   home_main.append(new_content_tag(soup, 'h2', name))
   table = render_meta_values_grid(website, file, meta_id, sorted(values, key=lambda x: meta_value_order_key(website, meta_id, x)))
   home_main.append(table)

def make_project_main_page(website: Website, file: HtmlFile, project: Project):
   soup = file.page.soup
   project_page = website.project_pages[project['id']]

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   file.page.body.append(make_generic_footer(website, file))

   project_top = render_generic_top(soup, project_link(website, file, project, project['key']), project['name'])
   if len(project['description']) > 0:
      desc = bs4.BeautifulSoup(project['description'], 'html.parser')
      desc = new_content_tag(soup, 'div', desc, attrs={'class': 'project-desc'})
      desc_text = html_to_text(desc)
      project_body = new_content_tag(soup, 'main', attrs={'class': 'issue-body'}, content=desc)
   else:
      project_body = new_content_tag(soup, 'main', attrs={'class': 'issue-body'}, content=[])
      desc_text = None

   add_metadata(file, project['name'], desc_text, project['avatarUrls']['48x48'])

   project_details = soup.new_tag('dl', attrs={'class': 'issue-details'})
   append_desc_item(soup, project_details,
      'Project Lead:',
      user_link(website, file, project['lead'])
   )
   issues = website.relations.fields.metas['project'][project['id']]
   append_desc_item(soup, project_details,
      'Issues:',
      new_content_tag(soup, 'a', str(len(issues)), attrs={'href': relative_link(website.root, file.path, project_page.issues.path)})
   )
   versions = project['versions']
   if project_page.versions is not None:
      append_desc_item(soup, project_details,
         'Versions:',
         new_content_tag(soup, 'a', str(len(versions)), attrs={'href': relative_link(website.root, file.path, project_page.versions.path)})
      )
   data_link = relative_path(website.root, file.path, website.archive.folder / website.metas.projects_path)
   portal_num = portal_number(project['key'])
   link_content = [
      new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': urllib.parse.quote(str(data_link))}, content='JSON')),
      new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://bugs.mojang.com/browse/{project['key']}'}, content='bugs.mojang.com')),
   ]
   if portal_num is not None:
      link_content.append(new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://report.bugs.mojang.com/servicedesk/customer/portal/{portal_num}'}, content='report.bugs.mojang.com')))
   link_content.extend([
      new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://mojira.atlassian.net/browse/{project['key']}'}, content='mojira.atlassian.net')),
   ])
   append_desc_item(soup, project_details,
      'Links:',
      new_content_tag(soup, 'ul', content=link_content)
   )
   project_div = build_issue_content(soup, project_top, project_body, project_details, None, None)
   content.append(project_div)

def portal_number(project_key: str) -> int | None:
   return {'MCPE': 6, 'MC': 2, 'MCL': 7, 'REALMS': 9, 'WEB': 10, 'BDS': 4, 'MCM': 11}.get(project_key)

def make_project_versions_page(website: Website, file: HtmlFile, project: Project):
   soup = file.page.soup

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   list_main = soup.new_tag('div', attrs={'class': 'list-main'})
   content.append(list_main)
   file.page.body.append(make_generic_footer(website, file))

   add_metadata(file, project['name'], f'{len(project['versions'])} versions', project['avatarUrls']['48x48'])

   list_main.append(new_content_tag(soup, 'h1', [project_link(website, file, project, project['key']), ' versions']))
   table = render_versions_table(website, file, project, project['versions'].values())
   list_main.append(new_content_tag(soup, 'div', attrs={'class': 'issue-list'}, content=table))

def make_project_issues_page(website: Website, file: HtmlFile, project: Project):
   soup = file.page.soup

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   list_main = soup.new_tag('div', attrs={'class': 'list-main'})
   content.append(list_main)
   file.page.body.append(make_generic_footer(website, file))

   issue_ids = website.relations.fields.metas['project'][project['id']]
   add_metadata(file, project['name'], f'{len(issue_ids)} issues', project['avatarUrls']['48x48'])
   def issue_map(issue_id: str):
      issue = website.archive.get_issue_data(issue_id)
      assert issue is not None
      return issue
   list_main.append(new_content_tag(soup, 'h1', [project_link(website, file, project, project['key']), ' issues']))
   table = create_issue_list(website, file, 'issue', (issue_map(x) for x in issue_ids))
   list_main.append(table.filters)
   list_main.append(table.table)
   add_table_scripts(website, file, [table.data])

def make_version_page(website: Website, file: HtmlFile, version: Version):
   soup = file.page.soup

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   file.page.body.append(make_generic_footer(website, file))

   project = website.metas.projects[str(version['projectId'])]
   version_top = render_generic_top(soup, project_link(website, file, project, project['key']), version['name'])
   if 'description' in version and len(version['description']) > 0:
      desc = new_content_tag(soup, 'div', version['description'], attrs={'class': 'project-desc'})
      version_body = new_content_tag(soup, 'main', attrs={'class': 'issue-body'}, content=desc)
   else:
      version_body = new_content_tag(soup, 'main', attrs={'class': 'issue-body'}, content=[])
   version_details = soup.new_tag('dl', attrs={'class': 'issue-details'})
   if 'startDate' in version:
      append_desc_item(soup, version_details,
         'Start Date:',
         render_date(soup, datetime.datetime.fromisoformat(version['startDate']))
      )
   if 'releaseDate' in version:
      append_desc_item(soup, version_details,
         'Release Date:',
         render_date(soup, datetime.datetime.fromisoformat(version['releaseDate']))
      )
   append_desc_item(soup, version_details,
      'Released:',
      'Yes' if version['released'] else 'No'
   )
   append_desc_item(soup, version_details,
      'Archived:',
      'Yes' if version['archived'] else 'No'
   )
   version_div = build_issue_content(soup, version_top, version_body, version_details, None, None)
   content.append(version_div)

   add_metadata(file, version['name'], version['description'] if 'description' in version else None, project['avatarUrls']['48x48'])

   tabbed_content = soup.new_tag('div', attrs={'class': 'issue-tabs-content'})
   version_tabs: list[bs4.Tag] = []

   table_scripts: list[TableData] = []
   def issue_map(issue_id: str):
      issue = website.archive.get_issue_data(issue_id)
      assert issue is not None
      return issue
   affected_issues = website.relations.fields.metas['versions'].get(version['id'], [])
   if len(affected_issues) > 0:
      version_tabs.extend([
         soup.new_tag('input', attrs={'type': 'radio', 'name': 'version-tabs', 'id': 'version-tab-affected', 'checked': ''}),
         new_content_tag(soup, 'label', attrs={'for': 'version-tab-affected'}, content=[
            'Affected Issues',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(affected_issues)))
         ])
      ])
      affected_table = create_issue_list(website, file, 'affected', (issue_map(x) for x in affected_issues))
      tabbed_content.append(new_content_tag(soup, 'div', attrs={'id': 'version-tab-content-affected', 'class': 'issue-tab-content'}, content=[affected_table.filters, affected_table.table]))
      table_scripts.append(affected_table.data)
   fixed_issues = website.relations.fields.metas['fixVersions'].get(version['id'], [])
   if len(fixed_issues) > 0:
      input_tag = soup.new_tag('input', attrs={'type': 'radio', 'name': 'version-tabs', 'id': 'version-tab-fixed'})
      if len(affected_issues) == 0:
         input_tag.attrs['checked'] = ''
      version_tabs.extend([
         input_tag,
         new_content_tag(soup, 'label', attrs={'for': 'version-tab-fixed'}, content=[
            'Fixed Issues',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(fixed_issues)))
         ])
      ])
      fixed_table = create_issue_list(website, file, 'fixed', (issue_map(x) for x in fixed_issues))
      tabbed_content.append(new_content_tag(soup, 'div', attrs={'id': 'version-tab-content-fixed', 'class': 'issue-tab-content'}, content=[fixed_table.filters, fixed_table.table]))
      table_scripts.append(fixed_table.data)
   version_tabs.append(tabbed_content)
   version_div.append(
      new_content_tag(soup, 'div', attrs={'class': 'issue-tabs'}, content=version_tabs)
   )
   if len(table_scripts) > 0:
      add_table_scripts(website, file, table_scripts)

TableData = typing.TypedDict('TableData', {
   'rowHeight': int,
   'tableHeaderId': str,
   'tableBodyId': str,
   'scrollId': str,
   'searchId': str,
   'countId': str,
   'summaries': list[str],
   'sort': list[list[int]],
   'rows': list[bs4.Tag]
})

@dataclasses.dataclass
class VirtualTable:
   table: bs4.Tag
   filters: bs4.Tag
   data: TableData

def add_table_scripts(website: Website, file: HtmlFile, scripts: list[TableData]):
   result: list[dict[str, typing.Any]] = []
   for entry in scripts:
      result.append({
         'rowHeight': entry['rowHeight'],
         'tableHeaderId': entry['tableHeaderId'],
         'tableBodyId': entry['tableBodyId'],
         'scrollId': entry['scrollId'],
         'searchId': entry['searchId'],
         'countId': entry['countId'],
         'summaries': entry['summaries'],
         'sort': entry['sort'],
         'rows': [str(x) for x in entry['rows']],
      })
   json_str = json.dumps(result, separators=(',', ':'))
   escaped = json_str.replace('\\', '\\\\').replace('\'', '\\\'')
   script = f'window.tableData = JSON.parse(\'{escaped}\');'
   file.page.body.append(new_content_tag(file.page.soup, 'script', script))
   file.page.head.append(file.page.soup.new_tag('script', src=relative_link(website.root, file.path, pathlib.PurePath('web/js/table.js'))))

def create_issue_list(website: Website, file: HtmlFile, id_prefix: str, issues: typing.Iterable[Issue]) -> VirtualTable:
   soup = file.page.soup
   all_rows: list[bs4.Tag] = []
   summaries: list[str] = []
   sort_data: list[list[tuple[int, typing.Any]]] = [
      [],
      [],
      [],
      [],
      [],
      []
   ]
   issue_table = soup.new_tag('div', attrs={'class': 'issue-table'})
   issue_table.append(new_content_tag(soup, 'div', attrs={'class': 'issue-table-header', 'id': f'{id_prefix}-table-header'}, content=[
      new_content_tag(soup, 'div', 'Key', attrs={'class': 'issue-table-key'}),
      new_content_tag(soup, 'div', 'Summary', attrs={'class': 'issue-table-summary'}),
      new_content_tag(soup, 'div', 'Status', attrs={'class': 'issue-table-status'}),
      new_content_tag(soup, 'div', 'Reporter', attrs={'class': 'issue-table-username'}),
      new_content_tag(soup, 'div', 'Assignee', attrs={'class': 'issue-table-username'}),
      new_content_tag(soup, 'div', 'Created', attrs={'class': 'issue-table-time'}),
   ]))
   issue_body = soup.new_tag('div', attrs={'id': f'{id_prefix}-table-body', 'class': 'issue-table-body'})
   issue_table.append(issue_body)
   for i, issue in enumerate(issues):
      if issue['fields']['project'] in website.metas.projects:
         project = website.metas.projects[issue['fields']['project']]
         icon = project_avatar(website, file, project)
      else:
         icon = bug_icon(website, file)
      key = new_content_tag(soup, 'a', attrs={'class': 'issue-table-key', 'href': relative_link(website.root, file.path, website.get_issue_path(issue))}, content=[
         icon,
         issue['key']
      ])
      if issue['fields']['reporter'] is not None:
         reporter_ref = user_reference(website, file, 'a', issue['fields']['reporter'])
         reporter = [soup.new_tag('a', attrs={'class': 'overlay', 'href': reporter_ref.link}), reporter_ref.outer]
      else:
         reporter = []
      if 'assignee' in issue['fields'] and issue['fields']['assignee'] is not None:
         assignee_ref = user_reference(website, file, 'a', issue['fields']['assignee'])
         assignee = [soup.new_tag('a', attrs={'class': 'overlay', 'href': assignee_ref.link}), assignee_ref.outer]
      else:
         assignee = []
      status = merged_status(website, file, 'span', issue)
      status_cls = 'issue-table-status'
      if issue['fields']['resolution'] is not None:
         status_cls += ' issue-resolved'
      row_tags = [
         key,
         new_content_tag(soup, 'div', issue['fields']['summary'], attrs={'class': 'issue-table-summary', 'title': issue['fields']['summary']}),
         new_content_tag(soup, 'a', new_content_tag(soup, 'div', status.badge.outer), attrs={'class': status_cls, 'href':  status.badge.link}),
         new_content_tag(soup, 'div', reporter, attrs={'class': 'issue-table-username'}),
         new_content_tag(soup, 'div', assignee, attrs={'class': 'issue-table-username'}),
         new_content_tag(soup, 'div', render_datetime(soup, datetime.datetime.fromisoformat(issue['fields']['created'])), attrs={'class': 'issue-table-time'})
      ]
      def sorter_key(x: tuple[int, typing.Any]):
         key = natsort.natsort_keygen(alg=natsort.ns.IGNORECASE)
         return key(x[1])
      status_order = ['unresolved', 'confirmed', 'priority', 'resolved']
      for j in range(len(sort_data)):
         text = html_to_text(row_tags[j])
         val = (status_order.index(status.kind), text) if j == 2 else text
         bisect.insort_left(sort_data[j], (i, val), key=sorter_key)
      summaries.append(issue['fields']['summary'].lower())
      row = new_content_tag(soup, 'div', content=row_tags)
      if issue['fields']['resolution'] is not None:
         row.attrs['class'] = 'issue-table-row issue-resolved'
      else:
         row.attrs['class'] = 'issue-table-row'
      all_rows.append(row)
      if i < 30:
         issue_body.append(new_content_tag(soup, 'div', attrs={'class': 'issue-table-virtual-row', 'style': f'top: {i * 32}px;'}, content=row))
   issue_body.insert(0, soup.new_tag('div', attrs={'id': f'{id_prefix}-table-scroll', 'class': 'issue-table-scroll'}))
   filters = new_content_tag(soup, 'div', attrs={'class': 'filters'}, content=[
      soup.new_tag('input', attrs={'name': 'search', 'type': 'text', 'placeholder': 'Summary', 'id': f'{id_prefix}-table-search'})
   ])
   controls = new_content_tag(soup, 'div', attrs={'class': 'issue-controls'}, content=[
      new_content_tag(soup, 'div', attrs={'class': 'issue-count', 'id': f'{id_prefix}-table-count'}, content=[f'{len(all_rows)} issues'])
   ])
   table_data: TableData = {
      'rowHeight': 32,
      'tableHeaderId': f'{id_prefix}-table-header',
      'tableBodyId': f'{id_prefix}-table-body',
      'scrollId': f'{id_prefix}-table-scroll',
      'searchId': f'{id_prefix}-table-search',
      'countId': f'{id_prefix}-table-count',
      'summaries': summaries,
      'sort': [[x[0] for x in y] for y in sort_data],
      'rows':  all_rows,
   }
   result = new_content_tag(soup, 'div', attrs={'class': 'issue-list'}, content=[
      controls,
      issue_table
   ])
   return VirtualTable(result, filters, table_data)

def render_groups_grid(website: Website, file: HtmlFile, group_ids: typing.Iterable[str]) -> bs4.Tag:
   soup = file.page.soup
   entries: list[bs4.Tag] = []
   for group_id in group_ids:
      users = website.relations.user.groups[group_id]
      link = relative_link(website.root, file.path, website.group_page.get_value_path(group_id))
      content = [
         new_content_tag(soup, 'a', attrs={'class': 'home-grid-name', 'href': link}, content=group_id),
         f'{len(users)} users'
      ]
      entries.append(new_content_tag(soup, 'div', content=content))
   return new_content_tag(soup, 'div', attrs={'class': 'home-grid'}, content=entries)

def field_value_order_key(value: relations.FieldRelation):
   if isinstance(value['value'], str):
      name = value['value']
   elif 'name' in value['value']:
      name = value['value']['name']
   else:
      name = value['value']['value']
   return (-len(value['issues']), name)

def meta_value_order_key(website: Website, meta_id: mojira.META_TYPE, value: str | None):
   display = website.metas.display_value(meta_id, value)
   assert display is not None
   resolved = (meta_id == 'resolution' and value is not None) or (meta_id == 'status' and value in ('5', '6'))
   return (resolved, display.name)

def render_field_values_grid(website: Website, file: HtmlFile, field_id: str, field_values: typing.Iterable[relations.FieldRelation]) -> bs4.Tag:
   soup = file.page.soup
   entries: list[bs4.Tag] = []
   for value in field_values:
      issues = value['issues']
      value_key = value['value'] if isinstance(value['value'], str) else value['value']['id']
      content: list[bs4.Tag | str] = [
         new_content_tag(soup, 'span', attrs={'class': 'home-grid-name'}, content=field_link(website, file, field_id, value_key))
      ]
      if not isinstance(value['value'], str) and 'description' in value['value']:
         content.append(value['value']['description'])
         content.append(soup.new_tag('br'))
      content.append(f'{len(issues)} issues')
      entries.append(new_content_tag(soup, 'div', content=content))
   return new_content_tag(soup, 'div', attrs={'class': 'home-grid'}, content=entries)

def render_meta_values_grid(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, values: typing.Iterable[str | None]) -> bs4.Tag:
   soup = file.page.soup
   entries: list[bs4.Tag] = []
   for value in values:
      issues = website.relations.fields.metas[meta_id]['' if value is None else value]
      content: list[bs4.Tag | str] = [
         new_content_tag(soup, 'span', attrs={'class': 'home-grid-name'}, content=meta_link(website, file, meta_id, value))
      ]
      display = website.metas.display_value(meta_id, value)
      assert display is not None
      if display.description is not None:
         content.append(display.description)
         content.append(soup.new_tag('br'))
      content.append(f'{len(issues)} issues')
      entries.append(new_content_tag(soup, 'div', content=content))
   return new_content_tag(soup, 'div', attrs={'class': 'home-grid'}, content=entries)

def render_fields_grid(website: Website, file: HtmlFile, field_ids: typing.Iterable[str | mojira.META_TYPE]) -> bs4.Tag:
   soup = file.page.soup
   entries: list[bs4.Tag] = []
   for field_id in field_ids:
      name = field_name(website.metas, field_id)
      link = relative_link(website.root, file.path, website.field_pages[field_id].page.path)
      content: list[bs4.Tag | str] = [
         new_content_tag(soup, 'a', attrs={'class': 'home-grid-name', 'href': link}, content=name),
      ]
      if field_id in website.relations.fields.fields:
         field_values = website.relations.fields.fields[field_id].values()
         def transform_field(value: relations.FieldRelation):
            return field_link(website, file, field_id, value['value'] if isinstance(value['value'], str) else value['value']['id'])
         if len(field_values) > 15:
            content.append(f'{len(field_values)} values')
         else:
            tags = inline_list(soup, map(transform_field, sorted(field_values, key=field_value_order_key)))
            content.append(tags)
      else:
         meta_id = typing.cast(mojira.META_TYPE, field_id)
         meta_values: list[str | None] = [x['id'] for x in website.metas.metas[meta_id].values()]
         if meta_id == 'resolution':
            meta_values.insert(0, None)
         def transform_meta(value: str | None):
            meta_id = typing.cast(mojira.META_TYPE, field_id)
            return meta_link(website, file, meta_id, value)
         if len(meta_values) > 15:
            content.append(f'{len(meta_values)} values')
         else:
            tags = inline_list(soup, map(transform_meta, sorted(meta_values, key=lambda x: meta_value_order_key(website, typing.cast(mojira.META_TYPE, meta_id), x))))
            content.append(tags)
      entries.append(new_content_tag(soup, 'div', content=content))
   return new_content_tag(soup, 'div', attrs={'class': 'home-grid'}, content=entries)

def render_projects_grid(website: Website, file: HtmlFile, projects: typing.Iterable[Project]) -> bs4.Tag:
   soup = file.page.soup
   entries: list[bs4.Tag] = []
   for project in projects:
      issues = website.relations.fields.metas['project'][project['id']]
      versions = project['versions']
      project_key = project_link(website, file, project, project['key'])
      project_page = website.project_pages[project['id']]
      content = [
         project_key,
         new_content_tag(soup, 'span', attrs={'class': 'home-grid-name'}, content=project['name']),
         new_content_tag(file.page.soup, 'a', f'{len(issues)} issues', attrs={'href': relative_link(website.root, file.path, project_page.issues.path)}),
      ]
      if project_page.versions is not None:
         content.append(new_content_tag(file.page.soup, 'a', f'{len(versions)} versions', attrs={'href': relative_link(website.root, file.path, project_page.versions.path)}))
      entries.append(new_content_tag(soup, 'div', content=content))
   return new_content_tag(soup, 'div', attrs={'class': 'home-grid'}, content=entries)

def render_versions_table(website: Website, file: HtmlFile, project: Project, versions: typing.Iterable[Version]) -> bs4.Tag:
   soup = file.page.soup
   table = make_table(soup, [
      new_content_tag(soup, 'th', new_content_tag(soup, 'div', 'Name'), attrs={'class': 'version-table-name'}),
      new_content_tag(soup, 'th', new_content_tag(soup, 'div', 'Description'), attrs={'class': 'version-table-desc'}),
      new_content_tag(soup, 'th', new_content_tag(soup, 'div', 'Date'), attrs={'class': 'version-table-date'}),
      new_content_tag(soup, 'th', new_content_tag(soup, 'div', 'Affected'), attrs={'class': 'version-table-issues'}),
         new_content_tag(soup, 'th', new_content_tag(soup, 'div', 'Fixed'), attrs={'class': 'version-table-issues'}),
   ])
   table.attrs['class'] = 'version-table'
   for version in versions:
      affected_issues = website.relations.fields.metas['versions'].get(version['id'], [])
      fixed_issues = website.relations.fields.metas['fixVersions'].get(version['id'], [])
      link = relative_link(website.root, file.path, website.project_pages[project['id']].get_version_path(version))
      badge = new_content_tag(soup, 'span', version['name'], attrs={'class': 'status-badge'})
      append_row(soup, table, [
         new_content_tag(soup, 'td', attrs={'class': 'version-table-name'}, content=new_content_tag(soup, 'a', attrs={'href': link}, content=new_content_tag(soup, 'div', badge))),
         new_content_tag(soup, 'td', attrs={'class': 'version-table-desc'}, content=new_content_tag(soup, 'div', version['description'])) if 'description' in version else '',
         new_content_tag(soup, 'td', attrs={'class': 'version-table-date'}, content=new_content_tag(soup, 'div', render_date(soup, datetime.datetime.fromisoformat(version['releaseDate'])))) if 'releaseDate' in version else '',
         new_content_tag(soup, 'td', attrs={'class': 'version-table-issues'}, content=new_content_tag(soup, 'div', f'{len(affected_issues)} issues')) if len(affected_issues) > 0 else '',
         new_content_tag(soup, 'td', attrs={'class': 'version-table-issues'}, content=new_content_tag(soup, 'div', f'{len(fixed_issues)} issues')) if len(fixed_issues) > 0 else '',
      ])
   return table

def make_generic_header(website: Website, file: HtmlFile) -> bs4.Tag:
   header = new_content_tag(file.page.soup, 'header', [
      new_content_tag(file.page.soup, 'a', 'Mojira Archive', attrs={'class': 'header-main', 'href': relative_link(website.root, file.path, website.home.path)}),
      new_content_tag(file.page.soup, 'form', attrs={'id': 'jump', 'class': 'jump'}, content=[
         file.page.soup.new_tag('input', attrs={'id': 'jump-input', 'type': 'text', 'name': 'jump', 'placeholder': 'Issue or User'}),
         new_content_tag(file.page.soup, 'button', attrs={'id': 'jump-submit', 'type': 'submit'}, content='Go'),
         new_content_tag(file.page.soup, 'script', f'window.jumpStart = "{relative_path(website.root, file.path, website.root)}";')
      ])
   ])
   file.page.head.append(file.page.soup.new_tag('script', src=relative_link(website.root, file.path, pathlib.PurePath('web/js/jump.js'))))
   return header

def make_generic_footer(website: Website, file: HtmlFile) -> bs4.Tag:
   footer = new_content_tag(file.page.soup, 'footer', [
      new_content_tag(file.page.soup, 'p', [
         'Pre-migration archive of ',
         new_content_tag(file.page.soup, 'a', attrs={'href': 'https://bugs.mojang.com'}, content='bugs.mojang.com'),
         ' by ',
         new_content_tag(file.page.soup, 'a', attrs={'href': 'https://github.com/tryashtar'}, content='tryashtar'),
         '. For Mojira volunteer use only!'
      ])
   ])
   return footer

def bug_icon(website: Website, file: HtmlFile) -> bs4.Tag:
   return file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/issuetypes/bug.svg'))})

def make_user_page(website: Website, file: HtmlFile, user: User):
   soup = file.page.soup

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   file.page.body.append(make_generic_footer(website, file))

   ref = user_reference(website, file, 'span', user['key'])
   user_top = render_generic_top(soup, None, ref.outer)
   user_details = soup.new_tag('dl', attrs={'class': 'issue-details'})
   append_desc_item(soup, user_details,
      'Username:',
      user['name']
   )
   append_desc_item(soup, user_details,
      'User Key:',
      user['key']
   )
   append_desc_item(soup, user_details,
      'Time Zone:',
      user['timeZone']
   )
   append_desc_item(soup, user_details,
      'Active:',
      'Yes' if user['active'] else 'No'
   )
   append_desc_item(soup, user_details,
      'Deleted:',
      'Yes' if user['deleted'] else 'No'
   )
   group_content: list[bs4.Tag] = []
   for group in user['groups']['items']:
      link = relative_link(website.root, file.path, website.group_page.get_value_path(group['name']))
      tag = new_content_tag(soup, 'a', attrs={'class': 'comment-visibility-name', 'href': link}, content=group['name'])
      group_content.append(new_content_tag(soup, 'li', tag))
   append_desc_item(soup, user_details,
      'Groups:',
      new_content_tag(soup, 'ul', content=group_content)
   )
   data_link = relative_path(website.root, file.path, website.archive.get_user_path(user['key']))
   link_content = [
      new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': urllib.parse.quote(str(data_link))}, content='JSON')),
   ]
   append_desc_item(soup, user_details,
      'Links:',
      new_content_tag(soup, 'ul', content=link_content)
   )
   user_body = new_content_tag(soup, 'main', attrs={'class': 'issue-body'}, content=[])
   user_div = build_issue_content(soup, user_top, user_body, user_details, None, None)
   content.append(user_div)

def make_issue_page(website: Website, file: HtmlFile, issue: Issue):
   key = issue['key']
   fields = issue['fields']
   summary = fields['summary']
   if issue['fields']['project'] in website.metas.projects:
      project = website.metas.projects[issue['fields']['project']]
   else:
      project = None
   full_title = f'[{key}] {summary}'

   soup = file.page.soup
   file.page.head.append(file.page.soup.new_tag('link', attrs={'rel': 'preload', 'as': 'style', 'href': relative_link(website.root, file.path, pathlib.PurePath('web/css/jira-wiki.css'))}))
   file.page.head.append(file.page.soup.new_tag('link', attrs={'rel': 'preload', 'as': 'style', 'href': relative_link(website.root, file.path, pathlib.PurePath('web/css/wiki-tweaks.css'))}))
   file.page.head.append(file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('web/css/diff.css'))))

   file.page.body.append(make_generic_header(website, file))
   content = soup.new_tag('div', attrs={'class': 'content'})
   file.page.body.append(content)
   file.page.body.append(make_generic_footer(website, file))

   issue_top = render_issue_top(website, file, project, key, summary)
   if fields['description'] is not None:
      desc = website.markup_source.get_issue_description(issue['id'])
      fix_markup(website, file, desc)
      desc = embed_wiki(website, file, desc)
      desc_text = html_to_text(desc)
   else:
      desc = None
      desc_text = None
   if 'environment' in fields and fields['environment'] is not None:
      env = website.markup_source.get_issue_environment(issue['id'])
      fix_markup(website, file, env)
      env = embed_wiki(website, file, env)
   else:
      env = None
   if 'customfield_11801' in fields and fields['customfield_11801'] is not None:
      impact = fields['customfield_11801']
   else:
      impact = None
   issue_body = build_issue_body(soup, desc, env, impact)
   issue_details = render_issue_details(website, file, issue)
   issue_links = render_issue_links(website, file, issue['fields']['issuelinks'])
   image_url = project['avatarUrls']['48x48'] if project is not None else None
   if len(issue['fields']['attachment']) > 0:
      issue_attaches = render_issue_attachments(website, file, issue['fields']['attachment'])
      for entry in issue['fields']['attachment']:
         attach = website.archive.get_attachment_data(entry)
         assert attach is not None
         if attach['mimeType'].startswith('image/'):
            image_url = attach['content']
            break
   else:
      issue_attaches = None
   issue_div = build_issue_content(soup, issue_top, issue_body, issue_details, issue_links, issue_attaches)
   issue_div.attrs['id'] = 'issue'
   content.append(issue_div)

   add_metadata(file, full_title, desc_text, image_url)

   tabbed_content = soup.new_tag('div', attrs={'class': 'issue-tabs-content'})
   all_comments: list[RenderableComment] = []
   if len(issue['fields']['comment']['comments']) > 0:
      for comment in issue['fields']['comment']['comments']:
         body = website.markup_source.get_comment_body(issue['id'], comment['id'])
         fix_markup(website, file, body)
         all_comments.append(RenderableComment(comment, body, secret=False))
      for comment in website.secret_comments.get(issue['id']):
         body = website.markup_source.get_secret_comment_body(issue['id'], comment['id'])
         fix_markup(website, file, body)
         bisect.insort_left(all_comments, RenderableComment(comment, body, secret=True), key=lambda x: datetime.datetime.fromisoformat(x.comment['created']))
      comment_section = render_issue_comments(website, file, all_comments)
   else:
      comment_section = soup.new_tag('div')
   tabbed_content.append(new_content_tag(soup, 'div', attrs={'id': 'issue-tab-content-comments', 'class': 'issue-tab-content'}, content=comment_section))
   history_section = render_issue_revisions(website, file, issue, issue['changelog']['histories'])
   tabbed_content.append(new_content_tag(soup, 'div', attrs={'id': 'issue-tab-content-history', 'class': 'issue-tab-content'}, content=history_section))
   issue_div.append(
      new_content_tag(soup, 'div', attrs={'class': 'issue-tabs'}, content=[
         soup.new_tag('input', attrs={'type': 'radio', 'name': 'issue-tabs', 'id': 'issue-tab-comments', 'checked': ''}),
         new_content_tag(soup, 'label', attrs={'for': 'issue-tab-comments'}, content=[
            'Comments',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(all_comments)))
         ]),
         soup.new_tag('input', attrs={'type': 'radio', 'name': 'issue-tabs', 'id': 'issue-tab-history'}),
         new_content_tag(soup, 'label', attrs={'for': 'issue-tab-history'}, content=[
            'History',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(issue['changelog']['histories'])))
         ]),
         soup.new_tag('input', attrs={'type': 'checkbox', 'name': 'issue-order', 'id': 'issue-tab-order'}),
         new_content_tag(soup, 'label', attrs={'for': 'issue-tab-order'}, content=''),
         tabbed_content
      ])
   )

def render_issue_top(website: Website, file: HtmlFile, project: Project | None, key: str, summary: str) -> bs4.Tag:
   if project is None:
      key_part = [
         bug_icon(website, file),
         new_content_tag(file.page.soup, 'span', key)
      ]
   else:
      key_part = [
         project_link(website, file, project, key)
      ]
   return render_generic_top(
      file.page.soup,
      new_content_tag(file.page.soup, 'div', attrs={'class': 'issue-key'}, content=key_part),
      summary
   )

def render_generic_top(soup: bs4.BeautifulSoup, key: str | bs4.Tag | None, summary: str | bs4.Tag) -> bs4.Tag:
   title_content: list[bs4.Tag | str] = []
   if key is not None:
      title_content.append(key)
   title_content.append(new_content_tag(soup, 'h1', attrs={'class': 'issue-summary'}, content=summary))
   return new_content_tag(soup, 'div', attrs={'class': 'issue-top'}, content=[
      new_content_tag(soup, 'div', attrs={'class': 'issue-title'}, content=title_content)
   ])

def build_issue_content(soup: bs4.BeautifulSoup, top: bs4.Tag, body: bs4.Tag, details: bs4.Tag, links: bs4.Tag | None, attachments: bs4.Tag | None) -> bs4.Tag:
   issue_div = soup.new_tag('div', attrs={'class': 'issue'})
   issue_div.append(top)
   issue_div.append(new_content_tag(soup, 'div', attrs={'class': 'issue-split'}, content=[
      body,
      details
   ]))
   if links is not None:
      body.append(links)
   if attachments is not None:
      body.append(attachments)
   return issue_div

def build_issue_body(soup: bs4.BeautifulSoup, desc: bs4.Tag | None, env: bs4.Tag | None, impact: str | None) -> bs4.Tag:
   issue_body = soup.new_tag('main', attrs={'class': 'issue-body'})
   if desc is not None:
      issue_body.append(new_content_tag(soup, 'div', attrs={'class': 'issue-description'}, content=desc))
   if env is not None:
      issue_body.append(new_content_tag(soup, 'div', attrs={'class': 'issue-environment-section'}, content=[
         new_content_tag(soup, 'h2', 'Environment'),
         env
      ]))
   if impact is not None:
      issue_body.append(new_content_tag(soup, 'div', attrs={'class': 'issue-impact-section'}, content=[
         new_content_tag(soup, 'h2', 'Impact'),
         new_content_tag(soup, 'p', content=impact)
      ]))
   return issue_body

@dataclasses.dataclass
class HistoryChangeValue:
   id: str
   name: str

@dataclasses.dataclass
class ProjectHistoryValue:
   id: str
   name: str
   project: str

class TrackedMultiSetRevision:
   def __init__(self, name: str, field_id: str | None, creator: typing.Callable[[typing.Iterable[ProjectHistoryValue]], bs4.Tag], inline: bool):
      self.added: list[ProjectHistoryValue] = []
      self.removed: list[ProjectHistoryValue] = []
      self.name = name
      self.field_id = field_id
      self.creator = creator
      self.inline = inline

   def import_change(self, entry: RevisionChange, project_id: str):
      if entry['to'] is not None:
         assert entry['toString'] is not None
         self.added.append(ProjectHistoryValue(entry['to'], entry['toString'], project_id))
      if entry['from'] is not None:
         assert entry['fromString'] is not None
         self.removed.append(ProjectHistoryValue(entry['from'], entry['fromString'], project_id))

   def handle(self, website: Website, file: HtmlFile) -> typing.Generator[bs4.Tag]:
      soup = file.page.soup
      if len(self.added) > 0:
         link = new_content_tag(soup, 'a', self.name, attrs={'href': relative_link(website.root, file.path, website.field_pages[self.field_id].page.path)}) if self.field_id is not None else self.name
         label = new_content_tag(soup, 'span', ['Added ', link, ': '], attrs={'class': 'history-label'})
         contents = self.creator(self.added)
         if self.inline:
            yield new_content_tag(soup, 'p', [label, contents])
         else:
            yield new_content_tag(soup, 'p', label)
            yield contents
      if len(self.removed) > 0:
         link = new_content_tag(soup, 'a', self.name, attrs={'href': relative_link(website.root, file.path, website.field_pages[self.field_id].page.path)}) if self.field_id is not None else self.name
         label = new_content_tag(soup, 'span', ['Removed ', link, ': '], attrs={'class': 'history-label'})
         contents = self.creator(self.removed)
         if self.inline:
            yield new_content_tag(soup, 'p', [label, contents])
         else:
            yield new_content_tag(soup, 'p', label)
            yield contents

class TrackedMultiValueRevision:
   def __init__(self, name: str, field_id: str, splitter: typing.Callable[[str | None, str | None], list[HistoryChangeValue]], creator: typing.Callable[[list[HistoryChangeValue]], bs4.Tag]):
      self.previous: list[HistoryChangeValue] | None = None
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
      if len(added_values) > 0:
         link = new_content_tag(soup, 'a', self.name, attrs={'href': relative_link(website.root, file.path, website.field_pages[self.field_id].page.path)})
         yield new_content_tag(soup, 'p', [
            new_content_tag(soup, 'span', ['Added ', link, ': '], attrs={'class': 'history-label'}),
            self.creator(added_values)
         ])
      if len(removed_values) > 0:
         link = new_content_tag(soup, 'a', self.name, attrs={'href': relative_link(website.root, file.path, website.field_pages[self.field_id].page.path)})
         yield new_content_tag(soup, 'p', [
            new_content_tag(soup, 'span', ['Removed ', link, ': '], attrs={'class': 'history-label'}),
            self.creator(removed_values)
         ])
      self.previous = new_values

def revision_from_to(soup: bs4.BeautifulSoup, label: bs4.Tag | str, old_tag: bs4.Tag, new_tag: bs4.Tag) -> bs4.Tag:
   return new_content_tag(soup, 'p', [
      new_content_tag(soup, 'span', label, attrs={'class': 'history-label'}),
      old_tag,
      new_content_tag(soup, 'span', ' → ', attrs={'class': 'history-label'}),
      new_tag
   ])

def revision_change(soup: bs4.BeautifulSoup, label: str | bs4.Tag, old_tag: bs4.Tag | None, new_tag: bs4.Tag | None) -> typing.Generator[bs4.Tag]:
   if old_tag is not None and new_tag is not None:
      yield revision_from_to(soup, new_content_tag(soup, 'span', ['Changed ', label, ': ']), old_tag, new_tag)
   elif new_tag is None and old_tag is not None:
      yield new_content_tag(soup, 'p', [
         new_content_tag(soup, 'span', new_content_tag(soup, 'span', ['Removed ', label, ': ']), attrs={'class': 'history-label'}),
         old_tag
      ])
   elif old_tag is None and new_tag is not None:
      yield new_content_tag(soup, 'p', [
         new_content_tag(soup, 'span', new_content_tag(soup, 'span', ['Added ', label, ': ']), attrs={'class': 'history-label'}),
         new_tag
      ])

def revision_html_diff(soup: bs4.BeautifulSoup, label: str, before: bs4.Tag | None, after: bs4.Tag | None, process: typing.Callable[[bs4.Tag], bs4.Tag], panel_class: str) -> typing.Generator[bs4.Tag]:
   if before is not None and after is not None:
      diff = html_diff(soup, before, after)
      has_insertions = diff.find('diff:insert') is not None or diff.find(attrs={'diff:insert': True})
      has_deletions = diff.find('diff:delete') is not None or diff.find(attrs={'diff:delete': True})
      if has_insertions and has_deletions:
         before_diff = copy.deepcopy(diff)
         after_diff = copy.deepcopy(diff)
         for tag in before_diff.find_all('diff:insert'):
            tag.extract()
         for tag in before_diff.find_all(attrs={'diff:insert': True}):
            tag.extract()
         for tag in after_diff.find_all('diff:delete'):
            tag.extract()
         for tag in after_diff.find_all(attrs={'diff:delete': True}):
            tag.extract()
         yield new_content_tag(soup, 'p', f'Changed {label}: ', attrs={'class': 'history-label'})
         yield new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=[
            new_content_tag(soup, 'div', attrs={'class': panel_class}, content=[process(before_diff), process(after_diff)])
            ])
      elif has_insertions:
         yield new_content_tag(soup, 'p', f'Changed {label}: ', attrs={'class': 'history-label'})
         yield new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=process(diff))
      elif has_deletions:
         yield new_content_tag(soup, 'p', f'Changed {label}: ', attrs={'class': 'history-label'})
         yield new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=process(diff))
   elif before is not None and after is None:
      yield new_content_tag(soup, 'p', f'Removed {label}: ', attrs={'class': 'history-label'})
      yield new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=process(before))
   elif after is not None and before is None:
      yield new_content_tag(soup, 'p', f'Added {label}: ', attrs={'class': 'history-label'})
      yield new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=process(after))

@dataclasses.dataclass
class MergedRevision:
   user_key: str
   start_time: datetime.datetime
   end_time: datetime.datetime
   changes: list[tuple[str, RevisionChange]]

def merge_revisions(revisions: list[Revision]) -> list[MergedRevision]:
   merged_revisions: list[MergedRevision] = []
   current: MergedRevision | None = None
   for revision in revisions:
      time = datetime.datetime.fromisoformat(revision['created'])
      merged = MergedRevision(
         user_key=revision['author'],
         start_time=time,
         end_time=time,
         changes=[(revision['id'], x) for x in revision['items']]
      )
      if current is None:
         current = merged
      elif revision['author'] == current.user_key and time - current.end_time <= datetime.timedelta(minutes=10):
         current.end_time = time
         current.changes.extend((revision['id'], x) for x in revision['items'])
      else:
         merged_revisions.append(current)
         current = merged
   if current is not None:
      merged_revisions.append(current)
   return merged_revisions

UNKNOWN_COMMENT_RE = re.compile(r'A comment with security level \'[a-z]+\' was removed\.' + '\u00a0?$')

def render_issue_revisions(website: Website, file: HtmlFile, issue: Issue, revisions: list[Revision]) -> bs4.Tag:
   soup = file.page.soup

   # revisions can include references to versions, attachments, issues, or fields that no longer exist
   # we still display them, just without full data or links
   def render_version(version: ProjectHistoryValue) -> bs4.Tag:
      if version.project in website.metas.projects:
         project = website.metas.projects[version.project]
         if version.id in project['versions']:
            return version_link(website, file, project, project['versions'][version.id])
      return new_content_tag(file.page.soup, 'span', version.name, attrs={'class': 'status-badge'})

   def render_version_list(versions: typing.Iterable[ProjectHistoryValue]) -> bs4.Tag:
      return inline_list(file.page.soup, map(render_version, versions))

   def render_attach(attach: HistoryChangeValue) -> bs4.Tag:
      attachment = website.archive.get_attachment_data(attach.id)
      if attachment is not None:
         return render_attachment(website, file, attachment, include_upload=False)
      broken = soup.new_tag('img', attrs={'width': '32', 'height': '32', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/attach/noimage.svg'))})
      return new_content_tag(soup, 'div', attrs={'class': 'broken-attachment'}, content=[broken, attach.name])

   def render_attach_list(attaches: typing.Iterable[HistoryChangeValue]) -> bs4.Tag:
      return new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=[
         new_content_tag(soup, 'div', attrs={'class': 'attachments'}, content=list(
            map(render_attach, attaches)
         ))
      ])

   def render_link(ticket: str) -> bs4.Tag:
      if ticket in website.relations.keys.issue_keys:
         relevant_issue = website.archive.get_issue_data(website.relations.keys.issue_keys[ticket])
         assert relevant_issue is not None
         # wrap in a div so Misode's CSS includes the top border
         return new_content_tag(soup, 'div', big_issue_link(website, file, relevant_issue))
      else:
         return new_content_tag(soup, 'div', issue_key(website, file, ticket))

   def get_link_dir(full_str: str, issue_key: str) -> str:
      assert full_str.startswith('This issue ')
      assert full_str.endswith(issue_key)
      return full_str[len('This issue '):-(len(issue_key) + 1)]

   def render_link_list(links: typing.Iterable[HistoryChangeValue]) -> bs4.Tag:
      link_dict: dict[str, list[bs4.Tag]] = {}
      for link in links:
         link_dir = get_link_dir(link.name, link.id)
         if link_dir not in link_dict:
            link_dict[link_dir] = []
         link_dict[link_dir].append(render_link(link.id))
      result = soup.new_tag('blockquote', attrs={'class': 'history-quote'})
      for dir, tags in link_dict.items():
         result.append(new_content_tag(soup, 'p', dir))
         result.extend(tags)
      return result

   def render_user(value: HistoryChangeValue) -> bs4.Tag:
      user_data = website.archive.get_user_data(value.id)
      if user_data is None:
         user_data = website.archive.get_unknown_user_data(value.id)
         if user_data is None:
            return new_content_tag(soup, 'span', attrs={'class': 'username'}, content=value.name)
      return user_link(website, file, value.id)

   def render_field(field_id: str, value: HistoryChangeValue) -> bs4.Tag:
      if value.id in website.relations.fields.fields[field_id]:
         return field_link(website, file, field_id, value.id)
      else:
         return new_content_tag(file.page.soup, 'span', value.name, attrs={'class': 'status-badge'})

   def render_field_list(field_id: str, values: typing.Iterable[HistoryChangeValue]) -> bs4.Tag:
      return inline_list(file.page.soup, map(lambda x: render_field(field_id, x), values))

   def label_splitter(source: str | None, string: str | None) -> list[HistoryChangeValue]:
      assert source is None
      assert string is not None
      if string == '':
         return []
      return [HistoryChangeValue(x, x) for x in string.split(' ')]

   def category_splitter(source: str | None, string: str | None) -> list[HistoryChangeValue]:
      if source is None or string is None or source == '' or string == '':
         return []
      source = source.removeprefix('[').removesuffix(']')
      source_list = source.split(', ')
      string_list = string.split(',')
      assert len(source_list) == len(string_list)
      return list(map(lambda x: HistoryChangeValue(x[0], x[1]), zip(source_list, string_list)))

   def handle_field(revision: RevisionChange, label: str, field_id: str) -> typing.Iterator[bs4.Tag]:
      if revision['from'] is not None:
         assert revision['fromString'] is not None
         old_tag = render_field(field_id, HistoryChangeValue(revision['from'], revision['fromString']))
      else:
         old_tag = None
      if revision['to'] is not None:
         assert revision['toString'] is not None
         new_tag = render_field(field_id, HistoryChangeValue(revision['to'], revision['toString']))
      else:
         new_tag = None
      link = new_content_tag(soup, 'a', label, attrs={'href': relative_link(website.root, file.path, website.field_pages[field_id].page.path)})
      return revision_change(soup, link, old_tag, new_tag)

   def render_meta(meta_id: mojira.META_TYPE, source: str | None, string: str | None) -> bs4.Tag | None:
      display =  website.metas.display_value(meta_id, source)
      if display is not None:
         return meta_link(website, file, meta_id, source)
      if string is not None:
         return new_content_tag(file.page.soup, 'span', string, attrs={'class': 'status-badge'})
      return None

   def handle_text(revision: RevisionChange, label: str) -> typing.Iterator[bs4.Tag]:
      assert revision['from'] is None
      assert revision['to'] is None
      old_val = revision['fromString']
      new_val = revision['toString']
      if old_val == '':
         old_val = None
      if new_val == '':
         new_val = None
      old_tag = None if old_val is None else new_content_tag(soup, 'span', old_val)
      new_tag = None if new_val is None else new_content_tag(soup, 'span', new_val)
      return revision_change(soup, label, old_tag, new_tag)

   def handle_large_diff(before: bs4.BeautifulSoup | None, after: bs4.BeautifulSoup | None, label: str) -> typing.Iterator[bs4.Tag]:
      if before is not None:
         fix_markup(website, file, before)
         before_tag = before
      else:
         before_tag = None
      if after is not None:
         fix_markup(website, file, after)
         after_tag = after
      else:
         after_tag = None
      def process(tag: bs4.Tag) -> bs4.Tag:
         wiki =  embed_wiki(website, file, tag)
         template = wiki.find('template')
         assert template is not None
         template.insert(0, file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('web/css/diff.css'))))
         return wiki
      return revision_html_diff(soup, label, before_tag, after_tag, process, 'diff-panel-side')

   HistoricFields = typing.TypedDict('HistoricFields', {
      'labels': typing.NotRequired[list[HistoryChangeValue]],
      'customfield_11901': typing.NotRequired[list[HistoryChangeValue] | None],
      'issuelinks': list[HistoryChangeValue],
      'attachments': list[HistoryChangeValue],
      'components': list[HistoryChangeValue],
      'versions': list[ProjectHistoryValue],
      'fixVersions': list[ProjectHistoryValue],
      'customfield_10500': typing.NotRequired[HistoryChangeValue | None],
      'customfield_12800': typing.NotRequired[HistoryChangeValue | None],
      'customfield_10501': typing.NotRequired[HistoryChangeValue | None],
      'customfield_10402': typing.NotRequired[HistoryChangeValue | None],
      'customfield_12301': typing.NotRequired[HistoryChangeValue | None],
      'customfield_12400': typing.NotRequired[HistoryChangeValue | None],
      'customfield_12900': typing.NotRequired[HistoryChangeValue | None],
      'customfield_12200': typing.NotRequired[HistoryChangeValue | None],
      'priority': typing.NotRequired[HistoryChangeValue | None],
      'security': typing.NotRequired[HistoryChangeValue | None],
      'resolution': typing.NotRequired[HistoryChangeValue | None],
      'status': typing.NotRequired[HistoryChangeValue],
      'customfield_11500': typing.NotRequired[str | None],
      'customfield_11801': typing.NotRequired[str | None],
      'customfield_11802': typing.NotRequired[str | None],
      'customfield_11800': typing.NotRequired[str | None],
      'customfield_11300': typing.NotRequired[str | None],
      'customfield_12201': typing.NotRequired[str | None],
      'assignee': typing.NotRequired[HistoryChangeValue | None],
      'reporter': typing.NotRequired[HistoryChangeValue | None],
      'key': typing.NotRequired[str],
      'summary': typing.NotRequired[str],
      'project': str,
   })

   def to_historic_link(link: IssueLink) -> HistoryChangeValue:
      link_type = website.metas.link_types[link['type']]
      if 'inwardIssue' in link:
         dir = link_type['inward']
         issue_data = website.archive.get_issue_data(link['inwardIssue'])
      else:
         assert 'outwardIssue' in link
         dir = link_type['outward']
         issue_data = website.archive.get_issue_data(link['outwardIssue'])
      assert issue_data is not None
      return HistoryChangeValue(issue_data['key'], f'This issue {dir} {issue_data['key']}')

   def to_historic_attachment(attach_id: str) -> HistoryChangeValue:
      attach_data = website.archive.get_attachment_data(attach_id)
      assert attach_data is not None
      return HistoryChangeValue(attach_id, attach_data['filename'])

   def to_historic_version(project: Project, version_id: str) -> ProjectHistoryValue:
      version_data = project['versions'][version_id]
      return ProjectHistoryValue(version_id, version_data['name'], issue['fields']['project'])

   def backwards_revision_order_key(change: RevisionChange) -> int:
      if change['field'] == 'Key':
         return 0
      if change['field'] == 'status':
         return 1
      if change['field'] == 'resolution':
         return 2
      if change['field'] in ('Version', 'Fix Version'):
         return 3 if change['to'] is None else 5
      if change['field'] in ('project', 'Project'):
         return 4
      return 6

   def forwards_revision_order_key(change: RevisionChange) -> int:
      if change['field'] == 'Key':
         return 0
      if change['field'] == 'status':
         return 1
      if change['field'] == 'resolution':
         return 2
      if change['field'] in ('Version', 'Fix Version'):
         return 5 if change['to'] is None else 3
      if change['field'] in ('project', 'Project'):
         return 4
      return 6

   def render_initial_issue() -> bs4.Tag:
      if issue['fields']['project'] in website.metas.projects:
         final_project = website.metas.projects[issue['fields']['project']]
      else:
         final_project = None
      historic_fields: HistoricFields = {
         'issuelinks': [to_historic_link(x) for x in issue['fields']['issuelinks']],
         'attachments': [to_historic_attachment(x) for x in issue['fields']['attachment']],
         'components': [HistoryChangeValue(x['id'], x['name']) for x in issue['fields']['components']] if 'components' in issue['fields'] else [],
         'versions': [to_historic_version(final_project, x) for x in issue['fields']['versions']] if 'versions' in issue['fields'] and final_project is not None else [],
         'fixVersions': [to_historic_version(final_project, x) for x in issue['fields']['fixVersions']] if 'fixVersions' in issue['fields'] and final_project is not None else [],
         'project': issue['fields']['project']
      }
      description_revision: str | None = None
      environment_revision: str | None = None
      for revision in revisions:
         for change in revision['items']:
            match change['field']:
               case 'labels':
                  if 'labels' not in historic_fields:
                     historic_fields['labels'] = label_splitter(change['from'], change['fromString'])
               case 'Category':
                  if 'customfield_11901' not in historic_fields:
                     historic_fields['customfield_11901'] = category_splitter(change['from'], change['fromString'])
               case 'Confirmation Status':
                  if 'customfield_10500' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['customfield_10500'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['customfield_10500'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'Area':
                  if 'customfield_12800' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['customfield_12800'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['customfield_12800'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'Game Mode':
                  if 'customfield_10501' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['customfield_10501'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['customfield_10501'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'Platform' | 'Device':
                  if 'customfield_10402' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['customfield_10402'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['customfield_10402'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'Realms Platform':
                  if 'customfield_12301' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['customfield_12301'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['customfield_12301'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'Dungeons Platform':
                  if 'customfield_12400' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['customfield_12400'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['customfield_12400'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'Legends Platform':
                  if 'customfield_12900' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['customfield_12900'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['customfield_12900'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'Mojang Priority':
                  if 'customfield_12200' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['customfield_12200'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['customfield_12200'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'priority':
                  if 'priority' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['priority'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['priority'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'security':
                  if 'security' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['security'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['security'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'resolution':
                  if 'resolution' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['resolution'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['resolution'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'status':
                  if 'status' not in historic_fields:
                     assert change['from'] is not None
                     assert change['fromString'] is not None
                     historic_fields['status'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'ADO' | 'VSO':
                  if 'customfield_11500' not in historic_fields:
                     historic_fields['customfield_11500'] = change['fromString']
               case 'Impact':
                  if 'customfield_11801' not in historic_fields:
                     historic_fields['customfield_11801'] = change['fromString']
               case 'Regression Builds':
                  if 'customfield_11802' not in historic_fields:
                     historic_fields['customfield_11802'] = change['fromString']
               case 'Partner Team Reporting':
                  if 'customfield_11800' not in historic_fields:
                     historic_fields['customfield_11800'] = change['fromString']
               case 'Operating System Version':
                  if 'customfield_11300' not in historic_fields:
                     historic_fields['customfield_11300'] = change['fromString']
               case 'Triaged Time':
                  if 'customfield_12201' not in historic_fields:
                     if change['from'] == '':
                        historic_fields['customfield_12201'] = None
                     else:
                        historic_fields['customfield_12201'] = change['from']
               case 'assignee':
                  if 'assignee' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['assignee'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['assignee'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'reporter':
                  if 'reporter' not in historic_fields:
                     if change['from'] is None:
                        historic_fields['reporter'] = None
                     else:
                        assert change['fromString'] is not None
                        historic_fields['reporter'] = HistoryChangeValue(change['from'], change['fromString'])
               case 'Key':
                  if 'key' not in historic_fields:
                     assert change['fromString'] is not None
                     historic_fields['key'] = change['fromString']
               case 'summary':
                  if 'summary' not in historic_fields:
                     assert change['fromString'] is not None
                     historic_fields['summary'] = change['fromString']
               case 'description':
                  if description_revision is None:
                     description_revision = revision['id']
               case 'environment':
                  if environment_revision is None:
                     environment_revision = revision['id']
               case _:
                  pass
      for revision in reversed(revisions):
         for change in reversed(sorted(revision['items'], key=backwards_revision_order_key)):
            match change['field']:
               case 'project' | 'Project':
                  assert change['from'] is not None
                  historic_fields['project'] = change['from']
               case 'Link':
                  if change['to'] is not None:
                     assert change['from'] is None
                     assert change['toString'] is not None
                     historic_fields['issuelinks'][:] = [x for x in historic_fields['issuelinks'] if x.id != change['to'] and x.name != change['toString']]
                  elif change['from'] is not None:
                     assert change['to'] is None
                     assert change['fromString'] is not None
                     historic_fields['issuelinks'].append(HistoryChangeValue(change['from'], change['fromString']))
               case 'Attachment':
                  if change['to'] is not None:
                     assert change['from'] is None
                     assert change['toString'] is not None
                     historic_fields['attachments'][:] = [x for x in historic_fields['attachments'] if x.id != change['to']]
                  elif change['from'] is not None:
                     assert change['to'] is None
                     assert change['fromString'] is not None
                     historic_fields['attachments'].append(HistoryChangeValue(change['from'], change['fromString']))
               case 'Component':
                  if change['to'] is not None:
                     assert change['from'] is None
                     assert change['toString'] is not None
                     historic_fields['components'][:] = [x for x in historic_fields['components'] if x.id != change['to']]
                  elif change['from'] is not None:
                     assert change['to'] is None
                     assert change['fromString'] is not None
                     historic_fields['components'].append(HistoryChangeValue(change['from'], change['fromString']))
               case 'Version':
                  if change['to'] is not None:
                     assert change['from'] is None
                     assert change['toString'] is not None
                     historic_fields['versions'][:] = [x for x in historic_fields['versions'] if x.id != change['to']]
                  elif change['from'] is not None:
                     assert change['to'] is None
                     assert change['fromString'] is not None
                     historic_fields['versions'].append(ProjectHistoryValue(change['from'], change['fromString'], historic_fields['project']))
               case 'Fix Version':
                  if change['to'] is not None:
                     assert change['from'] is None
                     assert change['toString'] is not None
                     historic_fields['fixVersions'][:] = [x for x in historic_fields['fixVersions'] if x.id != change['to']]
                  elif change['from'] is not None:
                     assert change['to'] is None
                     assert change['fromString'] is not None
                     historic_fields['fixVersions'].append(ProjectHistoryValue(change['from'], change['fromString'], historic_fields['project']))
               case _:
                  pass
      if 'labels' not in historic_fields:
         historic_fields['labels'] = [HistoryChangeValue(x, x) for x in issue['fields']['labels']]
      if 'customfield_11901' not in historic_fields and 'customfield_11901' in issue['fields']:
         if issue['fields']['customfield_11901'] is None:
            historic_fields['customfield_11901'] = None
         else:
            historic_fields['customfield_11901'] = [HistoryChangeValue(x['id'], x['value']) for x in issue['fields']['customfield_11901']]
      if 'customfield_10500' not in historic_fields and 'customfield_10500' in issue['fields']:
         historic_fields['customfield_10500'] = None if issue['fields']['customfield_10500'] is None else HistoryChangeValue(issue['fields']['customfield_10500']['id'], issue['fields']['customfield_10500']['value'])
      if 'customfield_12800' not in historic_fields and 'customfield_12800' in issue['fields']:
         historic_fields['customfield_12800'] = None if issue['fields']['customfield_12800'] is None else HistoryChangeValue(issue['fields']['customfield_12800']['id'], issue['fields']['customfield_12800']['value'])
      if 'customfield_10501' not in historic_fields and 'customfield_10501' in issue['fields']:
         historic_fields['customfield_10501'] = None if issue['fields']['customfield_10501'] is None else HistoryChangeValue(issue['fields']['customfield_10501']['id'], issue['fields']['customfield_10501']['value'])
      if 'customfield_10402' not in historic_fields and 'customfield_10402' in issue['fields']:
         historic_fields['customfield_10402'] = None if issue['fields']['customfield_10402'] is None else HistoryChangeValue(issue['fields']['customfield_10402']['id'], issue['fields']['customfield_10402']['value'])
      if 'customfield_12301' not in historic_fields and 'customfield_12301' in issue['fields']:
         historic_fields['customfield_12301'] = None if issue['fields']['customfield_12301'] is None else HistoryChangeValue(issue['fields']['customfield_12301']['id'], issue['fields']['customfield_12301']['value'])
      if 'customfield_12400' not in historic_fields and 'customfield_12400' in issue['fields']:
         historic_fields['customfield_12400'] = None if issue['fields']['customfield_12400'] is None else HistoryChangeValue(issue['fields']['customfield_12400']['id'], issue['fields']['customfield_12400']['value'])
      if 'customfield_12900' not in historic_fields and 'customfield_12900' in issue['fields']:
         historic_fields['customfield_12900'] = None if issue['fields']['customfield_12900'] is None else HistoryChangeValue(issue['fields']['customfield_12900']['id'], issue['fields']['customfield_12900']['value'])
      if 'customfield_12200' not in historic_fields and 'customfield_12200' in issue['fields']:
         historic_fields['customfield_12200'] = None if issue['fields']['customfield_12200'] is None else HistoryChangeValue(issue['fields']['customfield_12200']['id'], issue['fields']['customfield_12200']['value'])
      if 'priority' not in historic_fields and 'priority' in issue['fields']:
         historic_fields['priority'] = None if issue['fields']['priority'] is None else HistoryChangeValue(issue['fields']['priority']['id'], issue['fields']['priority']['name'])
      if 'security' not in historic_fields and 'security' in issue['fields']:
         historic_fields['security'] = None if issue['fields']['security'] is None else HistoryChangeValue(issue['fields']['security']['id'], issue['fields']['security']['name'])
      if 'resolution' not in historic_fields:
         if issue['fields']['resolution'] is None:
            historic_fields['resolution'] = None
         else:
            resolution = website.metas.resolutions[issue['fields']['resolution']]
            historic_fields['resolution'] = HistoryChangeValue(issue['fields']['resolution'], resolution['name'])
      if 'status' not in historic_fields:
         status = website.metas.statuses[issue['fields']['status']]
         historic_fields['status']  = HistoryChangeValue(issue['fields']['status'], status['name'])
      if 'customfield_11500' not in historic_fields and 'customfield_11500' in issue['fields']:
         historic_fields['customfield_11500'] = issue['fields']['customfield_11500']
      if 'customfield_11801' not in historic_fields and 'customfield_11801' in issue['fields']:
         historic_fields['customfield_11801'] = issue['fields']['customfield_11801']
      if 'customfield_11802' not in historic_fields and 'customfield_11802' in issue['fields']:
         historic_fields['customfield_11802'] = issue['fields']['customfield_11802']
      if 'customfield_11800' not in historic_fields and 'customfield_11800' in issue['fields']:
         historic_fields['customfield_11800'] = issue['fields']['customfield_11800']
      if 'customfield_11300' not in historic_fields and 'customfield_11300' in issue['fields']:
         historic_fields['customfield_11300'] = issue['fields']['customfield_11300']
      if 'customfield_12201' not in historic_fields and 'customfield_12201' in issue['fields']:
         historic_fields['customfield_12201'] = issue['fields']['customfield_12201']
      if 'assignee' not in historic_fields and 'assignee' in issue['fields']:
         if issue['fields']['assignee'] is None:
            historic_fields['assignee'] = None
         else:
            user_data = website.archive.get_user_data(issue['fields']['assignee'])
            assert user_data is not None
            historic_fields['assignee'] = HistoryChangeValue(issue['fields']['assignee'], user_data['displayName'])
      if 'reporter' not in historic_fields:
         if issue['fields']['reporter'] is None:
            historic_fields['reporter'] = None
         else:
            user_data = website.archive.get_user_data(issue['fields']['reporter'])
            assert user_data is not None
            historic_fields['reporter'] = HistoryChangeValue(issue['fields']['reporter'], user_data['displayName'])
      if 'key' not in historic_fields:
         historic_fields['key'] = issue['key']
      if 'summary' not in historic_fields:
         historic_fields['summary'] = issue['fields']['summary']

      def render_historic_details(fields: HistoricFields) -> bs4.Tag:
         issue_details = soup.new_tag('dl', attrs={'class': 'issue-details'})
         resolution_tag = render_meta('resolution', None if historic_fields['resolution'] is None else historic_fields['resolution'].id, None if historic_fields['resolution'] is None else historic_fields['resolution'].name)
         assert resolution_tag is not None
         append_desc_item(soup, issue_details,
            issue_detail_field(website, file, 'Resolution', 'resolution'),
            resolution_tag
         )
         is_resolved = historic_fields['resolution'] is not None
         resolved_statuses = ('5',)
         unresolved_statuses = ('1', '4')
         if (is_resolved and historic_fields['status'] not in resolved_statuses) or (not is_resolved and historic_fields['status'] not in unresolved_statuses):
            status_tag = render_meta('status', historic_fields['status'].id, historic_fields['status'].name)
            assert status_tag is not None
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Status', 'status'),
               status_tag
            )
         if 'security' in fields and fields['security'] is not None:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Security Level', 'security'),
               render_field('security', fields['security'])
            )
         if 'customfield_11800' in fields and fields['customfield_11800'] is not None:
            append_desc_item(soup, issue_details,
               'Partner Team:',
               fields['customfield_11800']
            )
         if 'assignee' in fields and fields['assignee'] is not None:
            append_desc_item(soup, issue_details,
               'Assignee:',
               render_user(fields['assignee'])
            )
         if 'customfield_10500' in fields and fields['customfield_10500'] is not None:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Confirmation Status', 'customfield_10500'),
               render_field('customfield_10500', fields['customfield_10500'])
            )
         if 'priority' in fields and fields['priority'] is not None:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Priority', 'priority'),
               render_field('priority', fields['priority'])
            )
         if 'customfield_12200' in fields and fields['customfield_12200'] is not None:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Mojang Priority', 'customfield_12200'),
               render_field('customfield_12200', fields['customfield_12200'])
            )
         if 'customfield_11500' in fields and fields['customfield_11500'] is not None:
            append_desc_item(soup, issue_details,
               'ADO:',
               fields['customfield_11500']
            )
         if 'customfield_12800' in fields and fields['customfield_12800'] is not None:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Area', 'customfield_12800'),
               render_field('customfield_12800', fields['customfield_12800'])
            )
         if 'customfield_11901' in fields and fields['customfield_11901'] is not None and len(fields['customfield_11901']) > 0:
            category_list = render_field_list('customfield_11901', fields['customfield_11901'])
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Category', 'customfield_11901'),
               category_list
            )
         if 'components' in fields and len(fields['components']) > 0:
            component_list = render_field_list('components', fields['components'])
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Component', 'components'),
               component_list
            )
         if 'customfield_10501' in fields and fields['customfield_10501'] is not None:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Game Mode:', 'customfield_10501'),
               render_field('customfield_10501', fields['customfield_10501'])
            )
         if 'customfield_10402' in fields and fields['customfield_10402'] is not None:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Platform', 'customfield_10402'),
               render_field('customfield_10402', fields['customfield_10402'])
            )
         if 'customfield_12301' in fields and fields['customfield_12301'] is not None:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Platform', 'customfield_12301'),
               render_field('customfield_12301', fields['customfield_12301'])
            )
         if 'customfield_12400' in fields and fields['customfield_12400'] is not None:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Platform', 'customfield_12400'),
               render_field('customfield_12400', fields['customfield_12400'])
            )
         if 'customfield_12900' in fields and fields['customfield_12900'] is not None:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Platform', 'customfield_12900'),
               render_field('customfield_12400', fields['customfield_12900'])
            )
         if 'customfield_11300' in fields and fields['customfield_11300'] is not None:
            append_desc_item(soup, issue_details,
               'OS Version:',
               fields['customfield_11300']
            )
         if 'labels' in fields:
            append_desc_item(soup, issue_details,
               issue_detail_field(website, file, 'Labels', 'labels'),
               render_field_list('labels', fields['labels'])
            )
         if 'versions' in fields:
            append_desc_item(soup, issue_details,
               'Affects Versions:',
               render_version_list(fields['versions'])
            )
         if 'customfield_11802' in fields and fields['customfield_11802'] is not None:
            append_desc_item(soup, issue_details,
               'Regression Builds:',
               fields['customfield_11802']
            )
         if 'fixVersions' in fields and len(fields['fixVersions']) > 0:
            append_desc_item(soup, issue_details,
               'Fix Versions:',
               render_version_list(fields['fixVersions'])
            )
         return issue_details

      def render_historic_links(links: typing.Iterable[HistoryChangeValue]) -> bs4.Tag | None:
         link_types: dict[str, list[bs4.Tag]] = {}
         for link in links:
            identity = get_link_dir(link.name, link.id)
            if identity not in link_types:
               link_types[identity] = []
            link_types[identity].append(render_link(link.id))
         if len(link_types) == 0:
            return None
         return build_link_section(soup, link_types)

      def render_historic_attachments(attachments: list[HistoryChangeValue]) -> bs4.Tag:
         attach_list: list[bs4.Tag] = []
         for attach in attachments:
            attach_div = render_attach(attach)
            attach_list.append(attach_div)
         return build_attachment_list(soup, len(attachments), attach_list)

      if historic_fields['project'] in website.metas.projects:
         initial_project = website.metas.projects[historic_fields['project']]
      else:
         initial_project = None
      issue_top = render_issue_top(website, file, initial_project, historic_fields['key'], historic_fields['summary'])
      if description_revision is not None:
         desc = website.markup_source.get_issue_description_revision(issue['id'], description_revision)[0]
      elif issue['fields']['description'] is not None:
         desc = website.markup_source.get_issue_description(issue['id'])
      else:
         desc = None
      if desc is not None:
         fix_markup(website, file, desc)
         desc = embed_wiki(website, file, desc)
      if environment_revision is not None:
         env = website.markup_source.get_issue_environment_revision(issue['id'], environment_revision)[0]
      elif 'environment' in issue['fields'] and issue['fields']['environment'] is not None:
         env = website.markup_source.get_issue_environment(issue['id'])
      else:
         env = None
      if env is not None:
         fix_markup(website, file, env)
         env = embed_wiki(website, file, env)
      if 'customfield_11801' in historic_fields:
         impact = historic_fields['customfield_11801']
      else:
         impact = None
      issue_body = build_issue_body(soup, desc, env, impact)
      issue_details = render_historic_details(historic_fields)
      issue_links = render_historic_links(historic_fields['issuelinks'])
      if len(historic_fields['attachments']) > 0:
         issue_attaches = render_historic_attachments(historic_fields['attachments'])
      else:
         issue_attaches = None
      return build_issue_content(soup, issue_top, issue_body, issue_details, issue_links, issue_attaches)

   revisions_list: list[bs4.Tag] = []
   time_part = new_content_tag(soup, 'span', attrs={'class': 'comment-time'}, content=[
      new_content_tag(soup, 'a', attrs={'class': 'comment-time', 'href': '#history-initial'}, content=[
         render_datetime(soup, datetime.datetime.fromisoformat(issue['fields']['created']))
      ])
   ])
   head_content: list[bs4.Tag | str] = []
   if issue['fields']['creator'] is not None:
      head_content.extend([
         comment_author(website, file, issue['fields']['creator']),
         ' ',
      ])
   head_content.append(time_part)
   revisions_list.append(new_content_tag(soup, 'div', attrs={'class': 'comment'}, content=[
      soup.new_tag('div', attrs={'class': 'anchor', 'id': 'history-initial'}),
      new_content_tag(soup, 'div', attrs={'class': 'comment-head'}, content=head_content),
      new_content_tag(soup, 'div', attrs={'class': 'comment-body'}, content=[
         new_content_tag(soup, 'details', attrs={'open': ''}, content=[
            new_content_tag(soup, 'summary', 'Created Issue:', attrs={'class': 'history-label'}),
            new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=[
               render_initial_issue()
            ])
         ])
      ])
   ]))
   labels = TrackedMultiValueRevision('Labels', 'labels', label_splitter, lambda x: render_field_list('labels', x))
   categories = TrackedMultiValueRevision('Category', 'labels', category_splitter, lambda x: render_field_list('customfield_11901', x))
   merged = merge_revisions(revisions)
   issue_project = issue['fields']['project']
   for entry in merged:
      history_items: list[bs4.Tag] = []
      affected_versions = TrackedMultiSetRevision('Affects Versions', None, render_version_list, inline=True)
      fixed_versions = TrackedMultiSetRevision('Fixed Versions', None, render_version_list, inline=True)
      attachments = TrackedMultiSetRevision('Attachments', None, lambda x: render_attach_list([HistoryChangeValue(y.id, y.name) for y in x]), inline=False)
      links = TrackedMultiSetRevision('Linked Issues', None, lambda x: render_link_list([HistoryChangeValue(y.id, y.name) for y in x]), inline=False)
      components = TrackedMultiSetRevision('Components', 'components', lambda x: render_field_list('components', [HistoryChangeValue(y.id, y.name) for y in x]), inline=False)
      sorted_changes = sorted(entry.changes, key=lambda x: forwards_revision_order_key(x[1]))
      for rev_id, item in sorted_changes:
         new_tags: typing.Iterator[bs4.Tag] | None = None
         match item['field']:
            # tracked changes
            case 'labels': # source always null, string always 'id id'
               new_tags = labels.handle(website, file, item)
            case 'Category': # source/string are either null or '[id, id]'/'Name,Name'
               new_tags = categories.handle(website, file, item)
            # special batched changes
            case 'Link': # source/string are either null or 'key'/'This issue ...'
               links.import_change(item, issue_project)
            case 'Attachment': # source/string are either null or 'id'/'filename'
               attachments.import_change(item, issue_project)
            # other batched changes
            # source/string are either null or 'id'/'Name'
            case 'Component':
               components.import_change(item, issue_project)
            case 'Version':
               affected_versions.import_change(item, issue_project)
            case 'Fix Version':
               fixed_versions.import_change(item, issue_project)
            # custom enum field changes
            # source/string are either null/null, null/empty, or 'id'/'Name'
            case 'Confirmation Status':
               new_tags = handle_field(item, 'Confirmation Status', 'customfield_10500')
            case 'Area':
               new_tags = handle_field(item, 'Area', 'customfield_12800')
            case 'Game Mode':
               new_tags = handle_field(item, 'Game Mode', 'customfield_10501')
            case 'Platform' | 'Device': # field was renamed at some point, but old name persists in history
               new_tags = handle_field(item, 'Platform', 'customfield_10402')
            case 'Realms Platform':
               new_tags = handle_field(item, 'Platform', 'customfield_12301')
            case 'Dungeons Platform':
               new_tags = handle_field(item, 'Platform', 'customfield_12400')
            case 'Legends Platform':
               new_tags = handle_field(item, 'Platform', 'customfield_12900')
            case 'Mojang Priority':
               new_tags = handle_field(item, 'Mojang Priority', 'customfield_12200')
            # builtin enum field changes
            # source/string are either null or 'id'/'Name'
            case 'priority':
               new_tags = handle_field(item, 'Priority', 'priority')
            case 'security':
               new_tags = handle_field(item, 'Security Level', 'security')
            case 'resolution':
               old_tag = render_meta('resolution', item['from'], item['fromString'])
               new_tag = render_meta('resolution', item['to'], item['toString'])
               link = new_content_tag(soup, 'a', 'Resolution', attrs={'href': relative_link(website.root, file.path, website.field_pages['resolution'].page.path)})
               new_tags = revision_change(soup, link, old_tag, new_tag)
            case 'status':
               assert item['from'] is not None
               assert item['to'] is not None
               if item['from'] != item['to']:
                  old_tag = render_meta('status', item['from'], item['fromString'])
                  new_tag = render_meta('status', item['to'], item['toString'])
                  link = new_content_tag(soup, 'a', 'Status', attrs={'href': relative_link(website.root, file.path, website.field_pages['status'].page.path)})
                  new_tags = revision_change(soup, link, old_tag, new_tag)
            # text field changes
            # source always null, string either null or empty or text
            case 'ADO' | 'VSO': # field was renamed at some point, but old name persists in history
               new_tags = handle_text(item, 'ADO')
            case 'Impact':
               new_tags = handle_text(item, 'Impact')
            case 'Regression Builds':
               new_tags = handle_text(item, 'Regression Builds')
            case 'Partner Team Reporting':
               new_tags = handle_text(item, 'Partner Team')
            case 'Operating System Version':
               new_tags = handle_text(item, 'OS Version')
            # other simple changes
            case 'Triaged Time': # source/string are either null or 'date'/'Display'
               old_tag = None if item['from'] is None or item['from'] == '' else render_date(soup, datetime.datetime.fromisoformat(item['from']))
               new_tag = None if item['to'] is None or item['to'] == '' else render_date(soup, datetime.datetime.fromisoformat(item['to']))
               new_tags = revision_change(soup, 'Triaged Time', old_tag, new_tag)
            case 'assignee': # source/string are either null or 'key'/'Name'
               if item['from'] is None:
                  old_tag = None
               else:
                  assert item['fromString'] is not None
                  old_tag =  render_user(HistoryChangeValue(item['from'], item['fromString']))
               if item['to'] is None:
                  new_tag = None
               else:
                  assert item['toString'] is not None
                  new_tag = None if item['to'] is None else render_user(HistoryChangeValue(item['to'], item['toString']))
               new_tags = revision_change(soup, 'Assignee', old_tag, new_tag)
            case 'reporter': # source/string are always 'key'/'Name'
               assert item['from'] is not None
               assert item['fromString'] is not None
               assert item['to'] is not None
               assert item['toString'] is not None
               old_tag = render_user(HistoryChangeValue(item['from'], item['fromString']))
               new_tag = render_user(HistoryChangeValue(item['to'], item['toString']))
               new_tags = iter([revision_from_to(soup, 'Changed Reporter: ', old_tag, new_tag)])
            case 'Key': # source always null, string always 'key'
               assert item['fromString'] is not None
               assert item['toString'] is not None
               old_tag = issue_key(website, file, item['fromString'])
               new_tag = issue_key(website, file, item['toString'])
               new_tags = iter([
                  revision_from_to(soup, 'Moved Issue: ', old_tag, new_tag)
               ])
            # html or markup changes
            case 'summary': # source always null, string always text
               assert item['fromString'] is not None
               assert item['toString'] is not None
               before = new_content_tag(soup, 'span', item['fromString'])
               after = new_content_tag(soup, 'span', item['toString'])
               new_tags = revision_html_diff(soup, 'Summary', before, after, lambda x: x, 'diff-panel-top')
            case 'description': # source always null, string either null or text
               before, after = website.markup_source.get_issue_description_revision(issue['id'], rev_id)
               new_tags = handle_large_diff(before, after, 'Description')
            case 'environment': # source always null, string either null or text
               before, after = website.markup_source.get_issue_environment_revision(issue['id'], rev_id)
               new_tags = handle_large_diff(before, after, 'Environment')
            case 'Comment': # from always text, all the rest always null
               assert item['from'] is not None
               assert item['to'] is None
               if UNKNOWN_COMMENT_RE.match(item['from']) is None:
                  comment = website.markup_source.get_deleted_comment_body(issue['id'], rev_id)
                  fix_markup(website, file, comment)
                  new_tags = iter([
                     new_content_tag(soup, 'p', 'Deleted Comment: ', attrs={'class': 'history-label'}),
                     new_content_tag(soup, 'blockquote', attrs={'class': 'history-quote'}, content=[
                           embed_wiki(website, file, comment)
                        ])
                  ])
            case 'project' | 'Project':
               assert item['from'] is not None
               issue_project = item['from']
            case (
               'RemoteIssueLink' # unfortunately these were not preserved in the archive
               | 'CHK' | 'Linked' | 'Pinned' # pointless fields
               | 'Workflow' # noise
               | 'Console' | 'Description' | 'Flagged' | 'Original story points' | 'Approvers' # only used in one test ticket
               | 'issuetype' # only relevant to MCAPI which sadly was not preserved
               | 'Affected Platforms' # old field that was only ever removed from tickets
            ):
               pass
            case _:
               raise ValueError()
         if new_tags is not None:
            history_items.extend(new_tags)
      for tag in components.handle(website, file):
         history_items.append(tag)
      for tag in affected_versions.handle(website, file):
         history_items.append(tag)
      for tag in fixed_versions.handle(website, file):
         history_items.append(tag)
      for tag in attachments.handle(website, file):
         history_items.append(tag)
      for tag in links.handle(website, file):
         history_items.append(tag)
      if len(history_items) > 0:
         time_part = new_content_tag(soup, 'span', attrs={'class': 'comment-time'}, content=[
            new_content_tag(soup, 'a', attrs={'class': 'comment-time', 'href': f'#history-id-{entry.changes[0][0]}'}, content=[
               render_date_range(soup, entry.start_time, entry.end_time)
            ])
         ])
         revisions_list.append(new_content_tag(soup, 'div', attrs={'class': 'comment'}, content=[
            soup.new_tag('div', attrs={'class': 'anchor', 'id': f'history-id-{entry.changes[0][0]}'}),
            new_content_tag(soup, 'div', attrs={'class': 'comment-head'}, content=[
               comment_author(website, file, entry.user_key),
               ' ',
               time_part
            ]),
            new_content_tag(soup, 'div', attrs={'class': 'comment-body'}, content=history_items)
         ]))
   return new_content_tag(soup, 'div', attrs={'class': 'issue-history-section'}, content=revisions_list)

def comment_author(website: Website, file: HtmlFile, user_key: str) -> bs4.Tag:
   user_tag = user_link(website, file, user_key)
   user_text = user_tag if 'username' in user_tag.attrs['class'] else user_tag.find(class_='username')
   assert user_text is not None
   user_text.attrs['class'] = 'username comment-author'
   return user_tag

@dataclasses.dataclass
class RenderableComment:
   comment: Comment | NewComment
   rendered_body: bs4.BeautifulSoup
   secret: bool

def render_author_key_or_dict(website: Website, file: HtmlFile, author: str | NewAuthor) -> bs4.Tag:
   if isinstance(author, dict):
      return new_content_tag(file.page.soup, 'span', attrs={'class': 'username comment-author'}, content=author['displayName'])
   else:
      return comment_author(website, file, author)

def comment_authorship(website: Website, file: HtmlFile, comment: Comment | NewComment, secret: bool) -> bs4.Tag:
   soup = file.page.soup
   div = soup.new_tag('div', attrs={'class': 'comment-head'})
   created_time = datetime.datetime.fromisoformat(comment['created'])
   updated_time = datetime.datetime.fromisoformat(comment['updated'])
   if 'author' in comment:
      div.append(render_author_key_or_dict(website, file, comment['author']))
      div.append(' ')
   # apply the comment-time class to the entire span and the link specifically so they both turn gray
   time_part = new_content_tag(soup, 'span', attrs={'class': 'comment-time'}, content=[
      new_content_tag(soup, 'a', attrs={'class': 'comment-time', 'href': f'#comment-id-{comment['id']}'}, content=[
         render_datetime(soup, created_time)
      ])
   ])
   has_update_author = 'updateAuthor' in comment and ('author' not in comment or comment['updateAuthor'] != comment['author'])
   has_update = comment['updated'] != comment['created']
   if has_update_author or has_update:
      time_part.append(' • edited ')
   if has_update_author:
      assert 'updateAuthor' in comment
      time_part.append(render_author_key_or_dict(website, file, comment['updateAuthor']))
      if has_update:
         time_part.append(' ')
   if has_update:
      if same_day(created_time, updated_time):
         inner_time = render_time(soup, updated_time)
      else:
        inner_time = render_datetime(soup, updated_time)
      time_part.append(inner_time)
   if 'visibility' in comment:
      if comment['visibility']['type'] == 'group':
         assert comment['visibility']['value'] in website.relations.user.groups
         link = relative_link(website.root, file.path, website.group_page.get_value_path(comment['visibility']['value']))
         restriction = new_content_tag(soup, 'a', attrs={'class': 'comment-visibility-name', 'href': link}, content=comment['visibility']['value'])
      else:
         restriction = new_content_tag(soup, 'span', attrs={'class': 'comment-visibility-name'}, content=comment['visibility']['value'])
      time_part.extend([
         ' • ',
         soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/ic_locked.png'))}),
         ' Restricted to ',
         restriction
      ])
   if secret:
      time_part.extend([
         ' • ',
         soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/ic_locked.png'))}),
         ' Secret comment',
      ])
   div.append(time_part)
   return div

def render_issue_comments(website: Website, file: HtmlFile, comments: list[RenderableComment]) -> bs4.Tag:
   soup = file.page.soup
   comments_list: list[bs4.Tag] = []
   for entry in comments:
      comment_div = new_content_tag(soup, 'div', attrs={'class': 'comment'}, content=[
         soup.new_tag('div', attrs={'class': 'anchor', 'id': f'comment-id-{entry.comment['id']}'}),
         comment_authorship(website, file, entry.comment, entry.secret)
      ])
      comment_div.append(new_content_tag(soup, 'div', attrs={'class': 'comment-body'}, content=[
         embed_wiki(website, file, entry.rendered_body)
      ]))
      comments_list.append(comment_div)
   return new_content_tag(soup, 'div', attrs={'class': 'issue-comment-section'}, content=comments_list)

def embed_wiki(website: Website, file: HtmlFile, wiki: bs4.Tag) -> bs4.Tag:
   return new_content_tag(file.page.soup, 'div', attrs={'class': 'jira-wiki'}, content=[
      new_content_tag(file.page.soup, 'template', attrs={'shadowrootmode': 'open'}, content=[
         file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('web/css/jira-wiki.css'))),
         file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('data/assets/mojira.css'))),
         file.page.soup.new_tag('link', rel='stylesheet', href=relative_link(website.root, file.path, pathlib.PurePath('web/css/wiki-tweaks.css'))),
         new_content_tag(file.page.soup, 'div', wiki)
      ])
   ])

def render_attachment(website: Website, file: HtmlFile, attachment: Attachment, include_upload: bool) -> bs4.Tag:
   soup = file.page.soup
   preview = attachment_preview(website, file, attachment)
   attach_path = website.archive.get_attachment_content_path(attachment['id'], attachment['filename'])
   link = relative_link(website.root, file.path, attach_path)
   details_div = soup.new_tag('div', attrs={'class': 'attachment-details'})
   attach_div = soup.new_tag('div', attrs={'class': 'attachment-block'})
   attach_div.append(preview)
   attach_div.append(details_div)
   details_div.append(new_content_tag(soup, 'a', attrs={'href': link}, content=attachment['filename']))
   if include_upload:
      if 'author' in attachment:
         details_div.append(
            new_content_tag(soup, 'p', content=comment_author(website, file, attachment['author']))
         )
      date_tag = render_datetime(soup, datetime.datetime.fromisoformat(attachment['created']))
      date_tag.attrs['class'] = 'comment-time'
      details_div.append(
         new_content_tag(soup, 'p', content=date_tag)
      )
   return attach_div

def render_issue_attachments(website: Website, file: HtmlFile, attachments: list[str]) -> bs4.Tag:
   soup = file.page.soup
   attach_list: list[bs4.Tag] = []
   for entry in attachments:
      attach_info = website.archive.get_attachment_data(entry)
      assert attach_info is not None
      attach_div = render_attachment(website, file, attach_info, include_upload=True)
      attach_list.append(attach_div)
   return build_attachment_list(soup, len(attachments), attach_list)

def build_attachment_list(soup: bs4.BeautifulSoup, count: int, attachments: list[bs4.Tag]) -> bs4.Tag:
   return new_content_tag(soup, 'details', attrs={'open': '', 'class': 'issue-attachment-section'}, content=[
      new_content_tag(soup, 'summary', [
         new_content_tag(soup, 'h2', content=[
            'Attachments',
            new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(count))
         ])
      ]),
      new_content_tag(soup, 'div', attrs={'class': 'attachments'}, content=attachments)
   ])

def render_issue_links(website: Website, file: HtmlFile, links: list[IssueLink]) -> bs4.Tag | None:
   soup = file.page.soup
   link_types: dict[str, list[bs4.Tag]] = {}
   for link in links:
      if 'inwardIssue' in link:
         identity = website.metas.link_types[link['type']]['inward']
         linked_issue = link['inwardIssue']
      elif 'outwardIssue' in link:
         identity = website.metas.link_types[link['type']]['outward']
         linked_issue = link['outwardIssue']
      else:
         raise ValueError()
      if identity not in link_types:
         link_types[identity] = []
      linked_data = website.archive.get_issue_data(linked_issue)
      assert linked_data is not None
      link_types[identity].append(big_issue_link(website, file, linked_data))
   if len(link_types) == 0:
      return None
   return build_link_section(soup, link_types)

def build_link_section(soup: bs4.BeautifulSoup, link_types: dict[str, list[bs4.Tag]]) -> bs4.Tag:
   link_lists: list[bs4.Tag] = []
   for link_desc, issues in link_types.items():
      link_list: list[bs4.Tag] = []
      for linked_issue in issues:
         link_list.append(linked_issue)
      link_block = new_content_tag(soup, 'details', attrs={'open': '', 'class': 'issue-links-category'}, content=[
         new_content_tag(soup, 'summary', attrs={'class': 'issue-link-type'}, content=[
            new_content_tag(soup, 'h3', content=[
               link_desc,
               new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(len(issues)))
            ]),
         ]),
         new_content_tag(soup, 'div', content=link_list)
      ])
      link_lists.append(link_block)
   link_section = new_content_tag(soup, 'details', attrs={'open': '', 'class': 'issue-link-section'}, content=[
      new_content_tag(soup, 'summary', [
         new_content_tag(soup, 'h2', content=[
            'Linked Issues'
         ])
      ]),
      new_content_tag(soup, 'div', attrs={'class': 'issue-link-section'}, content=link_lists)
   ])
   return link_section

def issue_detail_field(website: Website, file: HtmlFile, name: str, field_id: str) -> bs4.Tag:
   link = relative_link(website.root, file.path, website.field_pages[field_id].page.path)
   return new_content_tag(file.page.soup, 'a', name + ':', attrs={'href': link})

def render_issue_details(website: Website, file: HtmlFile, issue: Issue) -> bs4.Tag:
   fields = issue['fields']
   soup = file.page.soup
   issue_details = soup.new_tag('dl', attrs={'class': 'issue-details'})
   append_desc_item(soup, issue_details,
      issue_detail_field(website, file, 'Resolution', 'resolution'),
      meta_link(website, file, 'resolution', fields['resolution'])
   )
   is_resolved = fields['resolution'] is not None
   resolved_statuses = ('5',)
   unresolved_statuses = ('1', '4')
   if (is_resolved and fields['status'] not in resolved_statuses) or (not is_resolved and fields['status'] not in unresolved_statuses):
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Status', 'status'),
         meta_link(website, file, 'status', fields['status'])
      )
   if 'security' in fields:
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Security Level', 'security'),
         field_link(website, file, 'security', fields['security']['id'])
      )
   if fields['reporter'] is not None:
      append_desc_item(soup, issue_details,
         'Reporter:',
         user_link(website, file, fields['reporter'])
      )
   if fields['creator'] is not None and fields['reporter'] != fields['creator']:
      append_desc_item(soup, issue_details,
         'Creator:',
         user_link(website, file, fields['creator'])
      )
   if 'customfield_11800' in fields and fields['customfield_11800'] is not None:
      append_desc_item(soup, issue_details,
         'Partner Team:',
         fields['customfield_11800']
      )
   if 'assignee' in fields and fields['assignee'] is not None:
      append_desc_item(soup, issue_details,
         'Assignee:',
         user_link(website, file, fields['assignee'])
      )
   append_desc_item(soup, issue_details,
      'Created:',
      render_datetime(soup, datetime.datetime.fromisoformat(fields['created']))
   )
   append_desc_item(soup, issue_details,
      'Updated:',
      render_datetime(soup, datetime.datetime.fromisoformat(fields['updated']))
   )
   if 'customfield_12201'in fields and fields['customfield_12201'] is not None:
      append_desc_item(soup, issue_details,
         'Triaged:',
         render_datetime(soup, datetime.datetime.fromisoformat(fields['customfield_12201']))
      )
   if fields['resolutiondate'] is not None:
      append_desc_item(soup, issue_details,
         'Resolved:',
         render_datetime(soup, datetime.datetime.fromisoformat(fields['resolutiondate']))
      )
   append_desc_item(soup, issue_details,
      'Votes:',
      new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(fields['votes']['votes']))
   )
   append_desc_item(soup, issue_details,
      'Watchers:',
      new_content_tag(soup, 'span', attrs={'class': 'count-badge'}, content=str(fields['watches']['watchCount']))
   )
   if 'customfield_10500' in fields and fields['customfield_10500'] is not None:
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Confirmation Status', 'customfield_10500'),
         field_link(website, file, 'customfield_10500', fields['customfield_10500']['id'])
      )
   if 'priority' in fields and fields['priority'] is not None:
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Priority', 'priority'),
         field_link(website, file, 'priority', fields['priority']['id'])
      )
   if 'customfield_12200' in fields and fields['customfield_12200'] is not None:
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Mojang Priority', 'customfield_12200'),
         field_link(website, file, 'customfield_12200', fields['customfield_12200']['id'])
      )
   if 'customfield_11500' in fields and fields['customfield_11500'] is not None:
      append_desc_item(soup, issue_details,
         'ADO:',
         fields['customfield_11500']
      )
   if 'customfield_12800' in fields and fields['customfield_12800'] is not None:
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Area', 'customfield_12800'),
         field_link(website, file, 'customfield_12800', fields['customfield_12800']['id'])
      )
   if 'customfield_11901' in fields and fields['customfield_11901'] is not None:
      category_list = inline_list(soup, map(lambda x: field_link(website, file, 'customfield_11901', x['id']), fields['customfield_11901']))
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Category', 'customfield_11901'),
         category_list
      )
   if 'components' in fields and len(fields['components']) > 0:
      component_list = inline_list(soup, map(lambda x: field_link(website, file, 'components', x['id']), fields['components']))
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Component', 'components'),
         component_list
      )
   if 'customfield_10501' in fields and fields['customfield_10501'] is not None:
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Game Mode', 'customfield_10501'),
         field_link(website, file, 'customfield_10501', fields['customfield_10501']['id'])
      )
   if 'customfield_10402' in fields and fields['customfield_10402'] is not None:
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Platform', 'customfield_10402'),
         field_link(website, file, 'customfield_10402', fields['customfield_10402']['id'])
      )
   if 'customfield_12301' in fields and fields['customfield_12301'] is not None:
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Platform', 'customfield_12301'),
         field_link(website, file, 'customfield_12301', fields['customfield_12301']['id'])
      )
   if 'customfield_12400' in fields and fields['customfield_12400'] is not None:
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Platform', 'customfield_12400'),
         field_link(website, file, 'customfield_12400', fields['customfield_12400']['id'])
      )
   if 'customfield_12900' in fields and fields['customfield_12900'] is not None:
      append_desc_item(soup, issue_details,
         issue_detail_field(website, file, 'Platform', 'customfield_12900'),
         field_link(website, file, 'customfield_12900', fields['customfield_12900']['id'])
      )
   if 'customfield_11300' in fields and fields['customfield_11300'] is not None:
      append_desc_item(soup, issue_details,
         'OS Version:',
         fields['customfield_11300']
      )
   append_desc_item(soup, issue_details,
      issue_detail_field(website, file, 'Labels', 'labels'),
      inline_list(soup, map(lambda x: field_link(website, file, 'labels', x), fields['labels']))
   )
   if fields['project'] in website.metas.projects:
      project = website.metas.projects[fields['project']]
   else:
      project = None
   if 'versions' in fields:
      if project is not None:
         versions = list(map(lambda x: project['versions'][x], fields['versions']))
         append_desc_item(soup, issue_details,
            'Affects Versions:',
            render_version_list(website, file, project, versions)
         )
   if 'customfield_11802' in fields and fields['customfield_11802'] is not None:
      append_desc_item(soup, issue_details,
         'Regression Builds:',
         fields['customfield_11802']
      )
   if 'fixVersions' in fields:
      if project is not None:
         versions = list(map(lambda x: project['versions'][x], fields['fixVersions']))
         append_desc_item(soup, issue_details,
            'Fix Versions:',
            render_version_list(website, file, project, versions)
         )
   data_link = relative_path(website.root, file.path, website.archive.get_issue_path(issue['id']))
   portal_num = portal_number(project['key']) if project is not None else None
   link_content = [
      new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': urllib.parse.quote(str(data_link))}, content='JSON')),
      new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://mojira.dev/{issue['key']}'}, content='mojira.dev')),
      new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://bugs.mojang.com/browse/{issue['key']}'}, content='bugs.mojang.com')),
   ]
   if portal_num is not None:
      link_content.append(new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://report.bugs.mojang.com/servicedesk/customer/portal/{portal_num}/{issue['key']}'}, content='report.bugs.mojang.com')))
   link_content.extend([
      new_content_tag(soup, 'li', new_content_tag(soup, 'a', attrs={'href': f'https://mojira.atlassian.net/browse/{issue['key']}'}, content='mojira.atlassian.net')),
   ])
   append_desc_item(soup, issue_details,
      'Links:',
      new_content_tag(soup, 'ul', content=link_content)
   )
   return issue_details

def attachment_preview(website: Website, file: HtmlFile, attachment: Attachment) -> bs4.Tag:
   attach_path = website.archive.get_attachment_content_path(attachment['id'], attachment['filename'])
   link = relative_link(website.root, file.path, attach_path)
   mime = attachment['mimeType']
   if mime.startswith('image/'):
      return file.page.soup.new_tag('img', attrs={'class': 'attachment-img', 'src': link, 'alt': attachment['filename'], 'loading': 'lazy'})
   if mime.startswith('video/'):
      return new_content_tag(file.page.soup, 'video', attrs={'class': 'attachment-img', 'alt': attachment['filename'], 'loading': 'lazy', 'controls': ''}, content=[file.page.soup.new_tag('source', attrs={'src': link})])
   if mime in ('application/zip', 'application/gzip'):
      icon = 'zip.gif'
   elif mime == 'text/html':
      icon = 'html.gif'
   elif mime == 'text/xml':
      icon = 'xml.gif'
   elif mime.startswith('text/') or mime == 'application/json':
      icon = 'text.gif'
   elif mime == 'application/msword':
      icon = 'word.gif'
   elif mime == 'application/vnd.ms-excel':
      icon = 'excel.gif'
   elif mime == 'application/vnd.ms-powerpoint':
      icon = 'powerpoint.gif'
   elif mime == 'application/java-archive':
      icon = 'java.gif'
   elif mime == 'application/pdf':
      icon = 'pdf.gif'
   else:
      icon = 'file.gif'
   return file.page.soup.new_tag('img', attrs={'class': 'attachment-icon', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/attach') / icon)})

def get_avatar_path(archive: mojira.Archive, folder: pathlib.Path, url: str) -> pathlib.Path | None:
   avatar_id = archive.get_avatar_id(url)
   avatar_file = folder / (avatar_id + '.png')
   if avatar_file.exists():
      return avatar_file
   avatar_file = folder / (avatar_id + '.svg')
   if avatar_file.exists():
      return avatar_file
   return None

def project_avatar(website: Website, file: HtmlFile, project: Project) -> bs4.Tag:
   avatar_url = project['avatarUrls']['48x48']
   avatar_path = get_avatar_path(website.archive, website.archive.project_avatars_folder, avatar_url)
   assert avatar_path is not None
   img = file.page.soup.new_tag('img', attrs={'class': 'project-avatar', 'width': '32', 'height': '32', 'src': str(relative_path(website.root, file.path, avatar_path))})
   return img

def project_link(website: Website, file: HtmlFile, project: Project, text: str) -> bs4.Tag:
   img = project_avatar(website, file, project)
   link = relative_link(website.root, file.path, website.project_pages[project['id']].main.path)
   return new_content_tag(file.page.soup, 'a', [img, text], attrs={'class': 'project-key', 'href': link})

def big_issue_link(website: Website, file: HtmlFile, issue: Issue) -> bs4.Tag:
   cls = 'issue-link' if issue['fields']['resolution'] is None else 'issue-link issue-resolved'
   link = relative_link(website.root, file.path, website.get_issue_path(issue))
   status = merged_status(website, file, 'span', issue)
   if issue['fields']['project'] in website.metas.projects:
      project = website.metas.projects[issue['fields']['project']]
      icon = project_avatar(website, file, project)
   else:
      icon = bug_icon(website, file)
   return new_content_tag(file.page.soup, 'a', attrs={'class': cls, 'href': link}, content=[
      icon,
      new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-link-key'}, content=issue['key']),
      new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-link-summary', 'title': issue['fields']['summary']}, content=issue['fields']['summary']),
      status.badge.outer
   ])

def issue_key(website: Website, file: HtmlFile, issue_key: str) -> bs4.Tag:
   linkpart = new_content_tag(file.page.soup, 'span', issue_key, attrs={'class': 'issue-link-key'})
   tag = new_content_tag(file.page.soup, 'span', [bug_icon(website, file), linkpart], attrs={'class': 'small-issue-link'})
   return tag

@dataclasses.dataclass
class UserReference:
   inner: bs4.Tag
   outer: bs4.Tag
   link: str

def user_reference(website: Website, file: HtmlFile, tag_type: str, user_key: str) -> UserReference:
   user_data = website.archive.get_user_data(user_key)
   if user_data is None:
      user_data = website.archive.get_unknown_user_data(user_key)
      assert user_data is not None
      display_name = user_data['name']
   else:
      display_name = user_data['displayName']
   avatar_url = user_data['avatarUrls']['48x48']
   avatar_path = get_avatar_path(website.archive, website.archive.users_avatars_folder, avatar_url)
   img = file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'loading': 'lazy', 'class': 'avatar'})
   if avatar_path is not None:
      img['src'] = str(relative_path(website.root, file.path, avatar_path))
   link_url = relative_link(website.root, file.path, website.get_user_name_path(user_data['name']))
   inner = new_content_tag(file.page.soup, tag_type, attrs={'class':'user-hover user-link', 'rel': user_data['name']}, content=[
      new_content_tag(file.page.soup, 'span', attrs={'class': 'username'}, content=display_name),
   ])
   outer = new_content_tag(file.page.soup, 'span', attrs={'class': 'user-reference'}, content=[
      new_content_tag(file.page.soup, 'span', attrs={'class': 'aui-avatar aui-avatar-small'}, content=img),
      ' ',
      inner
   ])
   return UserReference(inner, outer, link_url)

def user_link(website: Website, file: HtmlFile, user_key: str) -> bs4.Tag:
   ref = user_reference(website, file, 'a', user_key)
   ref.inner.attrs['href'] = ref.link
   return ref.outer

def mojang_priority_icon(website: Website, file: HtmlFile, value: str) -> bs4.Tag:
   prio = {'Trivial': 'trivial', 'Low': 'low', 'Normal': 'medium', 'Important': 'high', 'Very Important': 'major'}[value]
   img = file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets/images/icons/priorities') / f'{prio}.svg')})
   return img

@dataclasses.dataclass
class FieldBadge:
   outer: bs4.Tag
   link: str
   resolved: bool

def meta_badge(website: Website, file: HtmlFile, tag_type: str, meta_id: mojira.META_TYPE, value_key: str | None) -> FieldBadge:
   display = website.metas.display_value(meta_id, value_key)
   assert display is not None
   link = relative_link(website.root, file.path, website.field_pages[meta_id].get_value_path(display.name))
   cls = f'status-badge field-value-{meta_id}'
   tag = new_content_tag(file.page.soup, tag_type, display.name, attrs={'class': cls})
   if display.description is not None:
      tag.attrs['title'] = display.description
   resolved = (meta_id == 'resolution' and value_key is not None) or (meta_id == 'status' and value_key in ('5', '6'))
   return FieldBadge(tag, link, resolved)

def meta_link(website: Website, file: HtmlFile, meta_id: mojira.META_TYPE, value_key: str | None) -> bs4.Tag:
   badge = meta_badge(website, file, 'a', meta_id, value_key)
   badge.outer.attrs['href'] = badge.link
   if badge.resolved:
      return new_content_tag(file.page.soup, 'span', attrs={'class': 'issue-resolved'}, content=badge.outer)
   return badge.outer

def field_name(metas: mojira.ArchiveMetas, field_id: str) -> str:
   extras = {'customfield_12400': 'Dungeons Platform', 'customfield_12900': 'Legends Platform', 'components': 'Component'}
   if field_id in extras:
      return extras[field_id]
   return metas.fields[field_id]['name']

def field_badge(website: Website, file: HtmlFile, tag_type: str, field_id: str, value_key: str) -> FieldBadge:
   field_name_str = field_name(website.metas, field_id).lower().replace(' ', '-').replace('/', '')
   display = website.relations.fields.display_value(field_id, value_key)
   assert display is not None
   link = relative_link(website.root, file.path, website.field_pages[field_id].get_value_path(display.name))
   content: list[bs4.Tag | str] = [display.name]
   cls = f'status-badge field-value-{field_name_str}'
   if display.icon is not None:
      assert display.icon.startswith('https://bugs.mojang.com/')
      relative = pathlib.PurePath(display.icon[len('https://bugs.mojang.com/'):])
      img = file.page.soup.new_tag('img', attrs={'width': '16', 'height': '16', 'src': relative_link(website.root, file.path, pathlib.PurePath('data/assets') / relative)})
      content.insert(0, img)
   elif field_id == 'customfield_12200':
      content.insert(0, mojang_priority_icon(website, file, display.name))
   tag = new_content_tag(file.page.soup, tag_type, content, attrs={'class': cls})
   if display.description is not None:
      tag.attrs['title'] = display.description
   return FieldBadge(tag, link, False)

def field_link(website: Website, file: HtmlFile, field_id: str, value_key: str) -> bs4.Tag:
   badge = field_badge(website, file, 'a', field_id, value_key)
   badge.outer.attrs['href'] = badge.link
   return badge.outer

@dataclasses.dataclass
class MergedStatus:
   badge: FieldBadge
   kind: typing.Literal['resolved', 'priority', 'confirmed', 'unresolved']

def merged_status(website: Website, file: HtmlFile, tag_type: str, issue: Issue) -> MergedStatus:
   if issue['fields']['resolution'] is not None:
      return MergedStatus(
         meta_badge(website, file, tag_type, 'resolution', issue['fields']['resolution']),
         'resolved'
      )
   if 'customfield_12200' in issue['fields'] and issue['fields']['customfield_12200'] is not None:
      return MergedStatus(
         field_badge(website, file, tag_type, 'customfield_12200', issue['fields']['customfield_12200']['id']),
         'priority'
      )
   if 'customfield_10500' in issue['fields'] and issue['fields']['customfield_10500'] is not None:
      return MergedStatus(
         field_badge(website, file, tag_type, 'customfield_10500', issue['fields']['customfield_10500']['id']),
         'confirmed'
      )
   return MergedStatus(
      meta_badge(website, file, tag_type, 'resolution', None),
      'unresolved'
   )

def render_version_list(website: Website, file: HtmlFile, project: Project, versions: list[Version]) -> bs4.Tag | str:
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

if __name__ == '__main__':
   main()
