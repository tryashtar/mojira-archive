package com.renderer;

import com.atlassian.jira.issue.IssueManager;
import com.atlassian.jira.util.JiraKeyUtils.KeyMatcher;
import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.links.ContentLinkResolver;
import com.atlassian.renderer.links.GenericLinkParser;
import com.atlassian.renderer.links.Link;

import java.text.ParseException;

public class FakeIssueLinkResolver implements ContentLinkResolver {
    private final KeyMatcher Matcher;
    private final IssueManager Manager;

    public FakeIssueLinkResolver(KeyMatcher matcher, IssueManager manager) {
        Matcher = matcher;
        Manager = manager;
    }

    public Link createContentLink(RenderContext context, GenericLinkParser parser) throws ParseException {
        return Matcher.isValidIssueKey(parser.getNotLinkBody())
                ? new FakeIssueLink(parser.getNotLinkBody(), parser.getLinkBody(), Manager, context)
                : null;
    }
}
