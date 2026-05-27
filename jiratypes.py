import typing

Version = typing.TypedDict('Version', {
   'id': str,
   'name': str,
   'description': str,
   'archived': bool,
   'released': bool,
   'startDate': str,
   'releaseDate': str
})

AvatarUrls = typing.TypedDict('AvatarUrls', {'48x48': str})

Project = typing.TypedDict('Project', {
   'id': str,
   'key': str,
   'name': str,
   'description': str,
   'lead': str,
   'versions': dict[str, Version],
   'avatarUrls': AvatarUrls
})

Resolution = typing.TypedDict('Resolution', {
   'id': str
})
Status = typing.TypedDict('Status', {
   'id': str
})
Field = typing.TypedDict('Field', {
   'id': str
})
IssueType = typing.TypedDict('IssueType', {
   'id': str
})
LinkType = typing.TypedDict('LinkType', {
   'id': str
})

IdsCache = typing.TypedDict('IdsCache', {
   'issues': dict[str, str],
   'users': dict[str, str]
})

UserRelations = typing.TypedDict('UserRelations', {
   'created': list[str],
   'reported': list[str],
   'assigned': list[str],
   'comments': list[str],
   'edits': list[str],
   'changes': list[str]
})

VersionRelations = typing.TypedDict('VersionRelations', {
   'affected': list[str],
   'fixed': list[str]
})

RelationsCache = typing.TypedDict('RelationsCache', {
   'groups': dict[str, list[str]],
   'projects': dict[str, list[str]],
   'resolutions': dict[str, list[str]],
   'users': dict[str, UserRelations],
   'versions': dict[str, VersionRelations],
   'labels': dict[str, list[str]],
   'categories': dict[str, list[str]],
   'confirmation': dict[str, list[str]],
   'priority': dict[str, list[str]],
   'area': dict[str, list[str]]
})

User = typing.TypedDict('User', {
   'key': str,
   'name': str,
   'displayName': str,
   'active': bool,
   'deleted': bool,
   'avatarUrls': AvatarUrls
})

IssueFields = typing.TypedDict('IssueFields', {
   'summary': str,
   'description': str,
   'issuetype': str,
   'project': str,
   'fixVersions': list[str],
   'resolution': str,
   'resolutiondate': str,
   'updated': str,
   'created': str,
   'labels': list[str],
   'status': str,
   'creator': str,
   'reporter': str
})

Issue = typing.TypedDict('Issue', {
   'id': str,
   'key': str,
   'fields': IssueFields,
})
