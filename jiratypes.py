import typing

Version = typing.TypedDict('Version', {
   'id': str,
   'name': str,
   'description': typing.NotRequired[str],
   'archived': bool,
   'released': bool,
   'startDate': typing.NotRequired[str],
   'releaseDate': typing.NotRequired[str]
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
   'id': str,
   'name': str,
   'description': str
})
Status = typing.TypedDict('Status', {
   'id': str,
   'name': str,
   'description': str
})
Field = typing.TypedDict('Field', {
   'id': str,
   'name': str
})
IssueType = typing.TypedDict('IssueType', {
   'id': str,
   'name': str,
   'description': str
})
LinkType = typing.TypedDict('LinkType', {
   'id': str,
   'name': str,
   'inward': str,
   'outward': str
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

CommentVisibility = typing.TypedDict('CommentVisibility', {
   'type': str,
   'value': str
})

NewAuthor = typing.TypedDict('NewAuthor', {
   'displayName': str
})

NewComment = typing.TypedDict('NewComment', {
   'id': str,
   'author': NewAuthor,
   'updateAuthor': NewAuthor,
   'body': str,
   'created': str,
   'updated': str
})

Comment = typing.TypedDict('Comment', {
   'id': str,
   'author': typing.NotRequired[str],
   'updateAuthor': typing.NotRequired[str],
   'body': str,
   'created': str,
   'updated': str,
   'visibility': typing.NotRequired[CommentVisibility]
})

CommentField = typing.TypedDict('CommentField', {
   'comments': list[Comment],
   'total': int
})

VotesField = typing.TypedDict('VotesField', {
   'votes': int,
   'hasVoted': bool
})

WatchesField = typing.TypedDict('WatchesField', {
   'watchCount': int,
   'isWatching': bool
})

IssueLink = typing.TypedDict('IssueLink', {
   'id': str,
   'type': str,
   'outwardIssue': typing.NotRequired[str],
   'inwardIssue': typing.NotRequired[str],
})

Security = typing.TypedDict('Security', {
   'id': str,
   'name': str,
   'description': str
})

Component = typing.TypedDict('Component', {
   'id': str,
   'name': str,
   'description': str
})

Priority = typing.TypedDict('Priority', {
   'id': str,
   'name': str,
   'iconUrl': str,
})

IssueFields = typing.TypedDict('IssueFields', {
   'summary': str,
   'description': str | None,
   'environment': typing.NotRequired[str | None],
   'issuetype': str,
   'project': str,
   'versions': typing.NotRequired[list[str]],
   'fixVersions': typing.NotRequired[list[str]],
   'resolution': str | None,
   'resolutiondate': str | None,
   'updated': str,
   'created': str,
   'labels': list[str],
   'status': str,
   'creator': str,
   'reporter': str,
   'assignee': typing.NotRequired[str | None],
   'attachment': list[str],
   'customfield_12800': typing.NotRequired[CustomField | None], # Area
   'customfield_12200': typing.NotRequired[CustomField | None], # Mojang Priority
   'customfield_11901': typing.NotRequired[list[CustomField] | None], # Category
   'customfield_10500': typing.NotRequired[CustomField | None], # Confirmation Status
   'customfield_10501': typing.NotRequired[CustomField | None], # Game Mode
   'customfield_11500': typing.NotRequired[str | None], # ADO
   'customfield_12201': typing.NotRequired[str | None], # Triaged Time
   'customfield_11800': typing.NotRequired[str | None], # Partner Team Reporting
   'customfield_11801': typing.NotRequired[str | None], # Impact
   'customfield_10402': typing.NotRequired[CustomField | None], # Platform
   'customfield_12301': typing.NotRequired[CustomField | None], # Realms Platform
   'customfield_12400': typing.NotRequired[CustomField | None], # Dungeons Platform
   'customfield_12900': typing.NotRequired[CustomField | None], # Legends Platform
   'comment': CommentField,
   'votes': VotesField,
   'watches': WatchesField,
   'issuelinks': list[IssueLink],
   'security': typing.NotRequired[Security],
   'priority': typing.NotRequired[Priority | None],
   'components': typing.NotRequired[list[Component]],
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
