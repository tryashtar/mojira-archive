package com.renderer;

import com.atlassian.jira.util.JiraKeyUtils;
import com.atlassian.jira.util.JiraKeyUtils.KeyMatcher;
import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.util.TextUtils;
import com.atlassian.renderer.v2.RenderMode;
import com.atlassian.renderer.v2.components.AbstractRendererComponent;
import com.atlassian.renderer.v2.components.link.LinkDecorator;

import org.apache.oro.text.perl.Perl5Util;
import org.apache.oro.text.regex.MatchResult;

import com.atlassian.jira.issue.fields.renderer.wiki.links.JiraIssueLink;
import com.atlassian.renderer.links.Link;

public class FakeIssueLinkRendererComponent extends AbstractRendererComponent {
      private final KeyMatcher Matcher;

      public FakeIssueLinkRendererComponent(KeyMatcher matcher) {
         Matcher = matcher;
      }

      public boolean shouldRender(RenderMode renderMode) {
         return renderMode.renderLinks();
      }

      public String render(String wiki, RenderContext context) {
         return this.linkBugKeys(wiki, context);
      }

      private String linkBugKeys(String body, RenderContext context) {
         if (!TextUtils.stringSet(body)) {
            return "";
         } else {
            Perl5Util util = new Perl5Util();
            StringBuilder buff = new StringBuilder(body.length());

            MatchResult match;
            int matchGroups;
            for (String issueKeyRegex = Matcher.getIssueKeyRegex(); util.match(issueKeyRegex,
                  body); body = body.substring(match.endOffset(matchGroups - 1))) {
               match = util.getMatch();
               buff.append(body.substring(0, match.beginOffset(2)));
               StringBuilder sb = new StringBuilder();
               matchGroups = match.groups();

               for (int i = 2; i < matchGroups; ++i) {
                  sb.append(match.group(i));
               }

               String key = sb.toString();
               if (JiraKeyUtils.isPartOfUrl(body, match.beginOffset(2))) {
                  buff.append(key);
               } else {
                  try {
                     Link link = new JiraIssueLink(key);
                     buff.append(context.getRenderedContentStore().addInline(new LinkDecorator(link)));
                  } catch (Exception var11) {
                     buff.append(key);
                  }
               }
            }

            buff.append(body);
            return buff.toString();
         }
      }
   }
