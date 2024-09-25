package com.renderer;

import java.util.List;

import com.atlassian.jira.issue.IssueManager;
import com.atlassian.jira.issue.fields.renderer.wiki.resolvers.AnchorLinkResolver;
import com.atlassian.jira.issue.fields.renderer.wiki.resolvers.AttachmentLinkResolver;
import com.atlassian.jira.user.util.UserManager;
import com.atlassian.jira.util.JiraKeyUtils.KeyMatcher;
import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.links.ContentLinkResolver;
import com.atlassian.renderer.links.GenericLinkParser;
import com.atlassian.renderer.links.Link;
import com.atlassian.renderer.links.LinkResolver;
import com.atlassian.renderer.links.UnresolvedLink;
import com.atlassian.renderer.links.UrlLink;
import com.atlassian.renderer.util.UrlUtil;
import com.opensymphony.util.TextUtils;

public class FakeLinkResolver implements LinkResolver {
   private final List<ContentLinkResolver> Resolvers;
   public FakeLinkResolver(KeyMatcher matcher, IssueManager issueManager, UserManager userManager) {
      Resolvers = List.of(
         new AttachmentLinkResolver(),
         new AnchorLinkResolver(),
         new FakeIssueLinkResolver(matcher, issueManager),
         new FakeUserProfileLinkResolver(userManager)
      );
   }
   public Link createLink(RenderContext context, String linkText) {
      try {
         GenericLinkParser parser = new GenericLinkParser(linkText);
         if (TextUtils.stringSet((String) parser.getNotLinkBody())) {
            if (UrlUtil.startsWithUrl((String) parser.getNotLinkBody()) || parser.getNotLinkBody().startsWith("//")
                  || parser.getNotLinkBody().startsWith("\\\\")) {
               return new UrlLink(parser);
            }
            parser.parseAsContentLink();
            for (ContentLinkResolver resolver : this.Resolvers) {
               Link link = resolver.createContentLink(context, parser);
               if (link == null)
                  continue;
               return link;
            }
         }
      } catch (Exception e) {
      }
      return new UnresolvedLink(linkText);
   }

   @SuppressWarnings("rawtypes")
   public List extractLinkTextList(String pageContent) {
      return null;
   }

   @SuppressWarnings("rawtypes")
   public List extractLinks(RenderContext context, String text) {
      return null;
   }

   public String removeLinkBrackets(String linkText) {
      if (TextUtils.stringSet((String) linkText) && linkText.startsWith("[") && linkText.endsWith("]")) {
         return linkText.substring(1, linkText.length() - 1);
      }
      return linkText;
   }
}
