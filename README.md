## Mojira Archive
These are the scripts I wrote to download the content from [the Minecraft bug tracker](https://bugs.mojang.com) and generate [a static web view](https://tryashtar.dev/mojira/web/public/home.html).

## Steps to Run
1. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) to run scripts in this project, and [Maven](https://maven.apache.org/install.html) to run the Jira wiki HTML generator.
2. The runnable scripts load paths from `.env`. It contains the following values:
    * `ARCHIVE_DATA`: Folder for archive assets, attachments, avatars, issues, and users.
    * `ARCHIVE_METAS`: Folder for archive projects, resolutions, statuses, fields, and issue and link types.
    * `CACHE_RELATIONS`: Folder for generated lookup tables.
    * `CACHE_MARKUP`: Folder for generated Jira wiki HTML.
    * `CACHE_MARKUP_RELATIONS`: Folder for generated mentions found in Jira wiki HTML.
    * `WEB_ROOT`: Folder for the root of the web view. Should be outside `ARCHIVE_DATA` since the site will include relative links to assets in there.
    * `WEB_EXPORT`: Relative path to the web root where the generated HTML files live.
    * `JIRA_URL`: URL of the Jira instance to download data from, e.g. `https://bugs-legacy.mojang.com`.
    * `JIRA_KEY`: Your Jira API key used to authenticate you when downloading data.
    * `SECRET_COMMENTS`: Optional path to a secret comments file, which you probably don't have.
3. `uv run download.py` to download everything on Jira. This can be interrupted and run multiple times; it will continue downloading new changes until your archive is complete and up-to-date.
4. `uv run relations.py` to generate lookup tables. This creates mappings from issue key to ID, and username to user key. It creates lists of issues that have a particular field value. It creates lists of user activity and groups. These lookup tables are used by the following steps.
5. `uv run markup.py` to generate Jira wiki HTML. Every issue description and environment, revision of description or environment, comment, and deleted comment is rendered into HTML. This HTML is used by the following steps.
6. `uv run markup_relations.py` to generate lookup tables for issue and user mentions found in the generated HTML. These lookup tables are used by the following steps.
7. `uv run render.py` to build a static site. This will take a very long time and use a lot of memory.

## Archive Information
Issues are downloaded as JSON from the Jira API, then processed slightly. All references to other issues, users, or metadata fields that are present as partial objects are replaced with that item's string ID. This prevents stale or duplicate data from being spread across issue files.

The Jira API has no means of enumerating users, so possible users are scraped from these partial objects on issues, then downloaded fully from the API. User references that were found on issues but aren't found by the API are saved as "unknown" users.
