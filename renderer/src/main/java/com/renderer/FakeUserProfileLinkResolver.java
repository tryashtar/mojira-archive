package com.renderer;

import java.text.ParseException;

import com.atlassian.jira.user.util.UserManager;
import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.links.ContentLinkResolver;
import com.atlassian.renderer.links.GenericLinkParser;
import com.atlassian.renderer.links.Link;
import com.atlassian.renderer.links.UnresolvedLink;

public class FakeUserProfileLinkResolver implements ContentLinkResolver {
    private final UserManager Manager;

    public FakeUserProfileLinkResolver(UserManager manager) {
        this.Manager = manager;
    }

    public Link createContentLink(RenderContext context, GenericLinkParser parser) throws ParseException {
        if (parser.getNotLinkBody().startsWith("~")) {
            FakeUserProfileLink profileLink = new FakeUserProfileLink(parser, context, Manager);
            return (Link) (profileLink.getUser() == null ? new UnresolvedLink(parser.getOriginalLinkText()) : profileLink);
        } else {
            return null;
        }
    }
}
