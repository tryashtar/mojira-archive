import typing

Version = typing.TypedDict('Version', {
   'id': str,
   'name': str,
   'projectId': int,
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
   'versions': list[Version],
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
FieldSchema = typing.TypedDict('FieldSchema', {
   'type': str,
   'items': typing.NotRequired[str],
   'system': typing.NotRequired[str]
})
Field = typing.TypedDict('Field', {
   'id': str,
   'name': str,
   'custom': bool,
   'schema': typing.NotRequired[FieldSchema]
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
   'timeZone': str,
   'avatarUrls': AvatarUrls,
   'groups': UserGroups
})

UnknownUser = typing.TypedDict('UnknownUser', {
   'key': str,
   'name': str,
   'displayName': str,
   'active': bool,
   'timeZone': str,
   'avatarUrls': AvatarUrls
})

Attachment = typing.TypedDict('Attachment', {
   'id': str,
   'filename': str,
   'author': typing.NotRequired[str],
   'created': str,
   'size': int,
   'mimeType': str,
   'content': str
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

OutwardIssueLink = typing.TypedDict('OutwardIssueLink', {
   'id': str,
   'type': str,
   'outwardIssue': str,
   'inwardIssue': typing.NotRequired[str],
})

InwardIssueLink = typing.TypedDict('InwardIssueLink', {
   'id': str,
   'type': str,
   'inwardIssue': str,
})

CustomValue = typing.TypedDict('CustomValue', {
   'id': str,
   'value': str
})

DescriptionValue = typing.TypedDict('DescriptionValue', {
   'id': str,
   'name': str,
   'description': typing.NotRequired[str]
})

IconValue = typing.TypedDict('IconValue', {
   'id': str,
   'name': str,
   'iconUrl': str,
})

IssueFields = typing.TypedDict('IssueFields', {
   'summary': str,
   'description': str | None,
   'environment': typing.NotRequired[str | None],
   'created': str,
   'updated': str,
   'resolutiondate': str | None,
   'attachment': list[str],
   'comment': CommentField,
   'votes': VotesField,
   'watches': WatchesField,
   'issuelinks': list[OutwardIssueLink | InwardIssueLink],
   # metas
   'resolution': str | None,
   'issuetype': str,
   'project': str,
   'versions': typing.NotRequired[list[str]],
   'fixVersions': typing.NotRequired[list[str]],
   'status': str,
   'creator': str | None,
   'reporter': str | None,
   'assignee': typing.NotRequired[str | None],
   # discrete
   'labels': list[str],
   'security': typing.NotRequired[DescriptionValue],
   'priority': typing.NotRequired[IconValue | None],
   'components': typing.NotRequired[list[DescriptionValue]],
   'customfield_12800': typing.NotRequired[CustomValue | None], # Area
   'customfield_12200': typing.NotRequired[CustomValue | None], # Mojang Priority
   'customfield_10402': typing.NotRequired[CustomValue | None], # Platform
   'customfield_12301': typing.NotRequired[CustomValue | None], # Realms Platform
   'customfield_12400': typing.NotRequired[CustomValue | None], # Dungeons Platform
   'customfield_12900': typing.NotRequired[CustomValue | None], # Legends Platform
   'customfield_10500': typing.NotRequired[CustomValue | None], # Confirmation Status
   'customfield_10501': typing.NotRequired[CustomValue | None], # Game Mode
   'customfield_11901': typing.NotRequired[list[CustomValue] | None], # Category
   'customfield_11500': typing.NotRequired[str | None], # ADO
   'customfield_12201': typing.NotRequired[str | None], # Triaged Time
   'customfield_11800': typing.NotRequired[str | None], # Partner Team Reporting
   'customfield_11801': typing.NotRequired[str | None], # Impact
   'customfield_11802': typing.NotRequired[str | None], # Regression Builds
   'customfield_11300': typing.NotRequired[str | None], # Operating System Version
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
