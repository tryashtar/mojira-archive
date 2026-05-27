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

UserGroup = typing.TypedDict('UserGroup', {
   'name': str
})

UserGroups = typing.TypedDict('UserGroups', {
   'size': int,
   'items': list[UserGroup]
})

User = typing.TypedDict('User', {
   'key': str,
   'name': str,
   'displayName': str,
   'active': bool,
   'deleted': bool,
   'avatarUrls': AvatarUrls,
   'groups': UserGroups
})

Attachment = typing.TypedDict('Attachment', {
   'id': str,
   'filename': str,
   'author': typing.NotRequired[str],
   'created': str,
   'size': int,
   'mimeType': str
})

CustomField = typing.TypedDict('CustomField', {
   'id': str,
   'value': str
})

Comment = typing.TypedDict('Comment', {
   'id': str,
   'author': typing.NotRequired[str],
   'updateAuthor': typing.NotRequired[str],
   'body': str,
   'created': str,
   'updated': str
})

CommentField = typing.TypedDict('CommentField', {
   'comments': list[Comment],
   'total': int
})

IssueFields = typing.TypedDict('IssueFields', {
   'summary': str,
   'description': str,
   'issuetype': str,
   'project': str,
   'versions': typing.NotRequired[list[str]],
   'fixVersions': typing.NotRequired[list[str]],
   'resolution': str,
   'resolutiondate': str,
   'updated': str,
   'created': str,
   'labels': list[str],
   'status': str,
   'creator': str,
   'reporter': str,
   'attachment': list[str],
   'customfield_12800': typing.NotRequired[CustomField | None],
   'customfield_12200': typing.NotRequired[CustomField | None],
   'customfield_11901': typing.NotRequired[list[CustomField] | None],
   'customfield_10500': typing.NotRequired[CustomField | None],
   'comment': CommentField
})

RevisionChange = typing.TypedDict('RevisionChange', {
   'field': str,
   'from': str | None,
   'to': str | None,
   'fromString': str | None,
   'toString': str | None
})

Revision = typing.TypedDict('Revision', {
   'id': str,
   'author': str,
   'created': str,
   'items': list[RevisionChange]
})

Changelog = typing.TypedDict('Changelog', {
   'total': int,
   'histories': list[Revision]
})

Issue = typing.TypedDict('Issue', {
   'id': str,
   'key': str,
   'fields': IssueFields,
   'changelog': Changelog
})
