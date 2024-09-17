package com.renderer;

import com.atlassian.jira.issue.fields.renderer.IssueRenderContext;
import com.atlassian.jira.issue.fields.renderer.wiki.links.JiraIssueLink;
import com.atlassian.jira.util.JiraKeyUtils;
import com.atlassian.jira.util.JiraKeyUtils.KeyMatcher;
import com.atlassian.renderer.*;
import com.atlassian.renderer.attachments.RendererAttachment;
import com.atlassian.renderer.attachments.RendererAttachmentManager;
import com.atlassian.renderer.embedded.DefaultEmbeddedResourceRenderer;
import com.atlassian.renderer.embedded.EmbeddedImage;
import com.atlassian.renderer.embedded.EmbeddedResource;
import com.atlassian.renderer.embedded.EmbeddedResourceRenderer;
import com.atlassian.renderer.links.Link;
import com.atlassian.renderer.links.LinkRenderer;
import com.atlassian.renderer.links.LinkResolver;
import com.atlassian.renderer.util.DefaultUnicodeEscapingTool;
import com.atlassian.renderer.util.TextUtils;
import com.atlassian.renderer.util.UnicodeEscapingTool;
import com.atlassian.renderer.v2.*;
import com.atlassian.renderer.v2.components.*;
import com.atlassian.renderer.v2.components.block.*;
import com.atlassian.renderer.v2.components.link.LinkDecorator;
import com.atlassian.renderer.v2.components.list.ListBlockRenderer;
import com.atlassian.renderer.v2.components.phrase.DashRendererComponent;
import com.atlassian.renderer.v2.components.phrase.EmoticonRendererComponent;
import com.atlassian.renderer.v2.components.phrase.ForceNewLineRendererComponent;
import com.atlassian.renderer.v2.components.phrase.NewLineRendererComponent;
import com.atlassian.renderer.v2.components.phrase.PhraseRendererComponent;
import com.atlassian.renderer.v2.components.table.TableBlockRenderer;
import com.atlassian.renderer.v2.macro.DefaultMacroManager;
import java.util.*;

import org.apache.commons.lang3.StringUtils;
import org.apache.oro.text.perl.Perl5Util;
import org.apache.oro.text.regex.MatchResult;

public class FakeRenderer {
   private final Renderer Renderer;
   private final LinkRenderer LinkRenderer;
   private final RendererConfiguration RendererConfig;
   private final EmbeddedResourceRenderer ResourceRenderer;
   private final UnicodeEscapingTool EscapingTool;

   private static class FakeLinkResolver implements LinkResolver {
      public Link createLink(RenderContext context, String linkText) {
         throw new UnsupportedOperationException("Unimplemented method 'createLink'");
      }

      public List extractLinkTextList(String pageContent) {
         throw new UnsupportedOperationException("Unimplemented method 'extractLinkTextList'");
      }

      public List extractLinks(RenderContext context, String text) {
         throw new UnsupportedOperationException("Unimplemented method 'extractLinks'");
      }

      public String removeLinkBrackets(String linkText) {
         throw new UnsupportedOperationException("Unimplemented method 'removeLinkBrackets'");
      }
   }

   private static class FakeRendererConfiguration implements RendererConfiguration {
      public String getCharacterEncoding() {
         return "UTF-8";
      }

      public String getWebAppContextPath() {
         return "";
      }

      public boolean isAllowCamelCase() {
         return false;
      }

      public boolean isNofollowExternalLinks() {
         return true;
      }
   }

   private static class FakeAttachmentManager implements RendererAttachmentManager {
      public RendererAttachment getAttachment(RenderContext context, EmbeddedResource resource) {
         throw new UnsupportedOperationException("Unimplemented method 'getAttachment'");
      }

      public RendererAttachment getThumbnail(RendererAttachment attachment, RenderContext context,
            EmbeddedImage resource) {
         throw new UnsupportedOperationException("Unimplemented method 'getThumbnail'");
      }

      public boolean systemSupportsThumbnailing() {
         throw new UnsupportedOperationException("Unimplemented method 'systemSupportsThumbnailing'");
      }
   }

   private static class FakeKeyMatcher implements KeyMatcher {
      private final Perl5Util perlUtil = new Perl5Util();
      private final String projectKeyRegex;
      private final String issueKeyRegex;

      public FakeKeyMatcher(String projectRegexp) {
         if (StringUtils.isNotBlank((CharSequence) projectRegexp)) {
            this.projectKeyRegex = "/^" + projectRegexp + "$/";
            this.issueKeyRegex = "/(^|[^a-zA-Z]|\n)" + projectRegexp + "(-[0-9]+)/";
         } else {
            this.projectKeyRegex = "/^[A-Z][A-Z]+$/";
            this.issueKeyRegex = "/(^|[^a-zA-Z]|\n)([A-Z][A-Z]+-[0-9]+)/";
         }
      }

      @Override
      public boolean isKeyInString(String s) {
         return this.perlUtil.match(this.getIssueKeyRegex(), s);
      }

      @Override
      public String getProjectKeyRegex() {
         return this.projectKeyRegex;
      }

      @Override
      public String getIssueKeyRegex() {
         return this.issueKeyRegex;
      }

      @Override
      public boolean isValidIssueKey(String issueKey) {
         if (issueKey == null) {
            return false;
         }
         int hyphenLocation = issueKey.lastIndexOf(45);
         if (hyphenLocation > 0) {
            String projectKey = issueKey.substring(0, hyphenLocation);
            String issueNumber = issueKey.substring(hyphenLocation + 1);
            if (JiraKeyUtils.validProjectKey(projectKey)) {
               char[] chars;
               if (issueNumber.length() == 0) {
                  return false;
               }
               for (char c : chars = issueNumber.toCharArray()) {
                  if (Character.isDigit(c))
                     continue;
                  return false;
               }
               return true;
            }
            return false;
         }
         return false;
      }

      @Override
      public boolean isValidProjectKey(String projectKey) {
         if (StringUtils.isBlank((CharSequence) projectKey)) {
            return false;
         }
         return this.perlUtil.match(this.getProjectKeyRegex(), projectKey);
      }

      @Override
      public boolean isIgnoreUrlWithKey() {
         return true;
      }

      @Override
      public boolean isKeyDetectionBackwardsCompatible() {
         return false;
      }

      @Override
      public String getLink(String key) {
         return key;
      }

      //@Override
      //public String getLink(String key) {
      //   StringBuilder buff = new StringBuilder();
      //   try {
      //      MutableIssue issue = this.getIssueManager().getIssueObject(key);
      //      if (issue != null && this.canCurrentUserSeeIssue(issue)) {
      //         String title = TextUtils.htmlEncode((String) issue.getSummary());
      //         VelocityRequestContext velocityRequestContext = ComponentAccessor
      //               .getComponent(VelocityRequestContextFactory.class).getJiraVelocityRequestContext();
      //         buff.append("<a href=\"").append(velocityRequestContext.getBaseUrl()).append("/browse/")
      //               .append(issue.getKey()).append("\" title=\"").append(title).append("\"")
      //               .append(" class=\"issue-link\" data-issue-key=\"").append(issue.getKey()).append("\">");
      //         if (issue.getResolutionObject() != null) {
      //            buff.append("<strike>");
      //            buff.append(key);
      //            buff.append("</strike>");
      //         } else {
      //            buff.append(key);
      //         }
      //         buff.append("</a>");
      //      } else {
      //         buff.append(key);
      //      }
      //   } catch (Exception e) {
      //      buff.append(key);
      //   }
      //   return buff.toString();
      //}
   }

   private static class JiraIssueLinkRendererComponent extends AbstractRendererComponent {
      private final KeyMatcher Matcher;

      public JiraIssueLinkRendererComponent() {
         Matcher = new FakeKeyMatcher("");
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

   public FakeRenderer() {
      var resolver = new FakeLinkResolver();
      var config = new FakeRendererConfiguration();
      var icon_manager = new DefaultIconManager();
      var renderer = new V2Renderer();
      var subrenderer = new V2SubRenderer(renderer);
      var components = new ArrayList<RendererComponent>();
      var macros = new DefaultMacroManager(subrenderer);
      macros.unregisterMacro("html");
      components.add(new MacroRendererComponent(macros, subrenderer));
      components.add(new BlockRendererComponent(subrenderer,
            Arrays.asList(new BlankLineBlockRenderer(), new HeadingBlockRenderer(), new BlockquoteBlockRenderer(),
                  new HorizontalRuleBlockRenderer(), new ListBlockRenderer(), new TableBlockRenderer())));
      components.add(new LinkRendererComponent(resolver));
      components.add(new UrlRendererComponent(resolver));
      components.add(new CamelCaseLinkRendererComponent(resolver, config));
      components.add(new EmbeddedImageRendererComponent());
      components.add(new JiraIssueLinkRendererComponent());
      components.add(new BackslashEscapeRendererComponent());
      components.add(new HtmlEscapeRendererComponent());
      components.add(new DashRendererComponent());
      components.add(new EmoticonRendererComponent(icon_manager));
      components.add(new EmbeddedObjectRendererComponent());
      components.add(PhraseRendererComponent.getDefaultRenderer("strong"));
      components.add(PhraseRendererComponent.getDefaultRenderer("superscript"));
      components.add(PhraseRendererComponent.getDefaultRenderer("subscript"));
      components.add(PhraseRendererComponent.getDefaultRenderer("emphasis"));
      components.add(PhraseRendererComponent.getDefaultRenderer("deleted"));
      components.add(PhraseRendererComponent.getDefaultRenderer("citation"));
      components.add(PhraseRendererComponent.getDefaultRenderer("inserted"));
      components.add(PhraseRendererComponent.getDefaultRenderer("monospaced"));
      components.add(new ForceNewLineRendererComponent());
      components.add(new NewLineRendererComponent());
      components.add(new TokenRendererComponent(subrenderer));

      renderer.setComponents(components);
      Renderer = renderer;
      LinkRenderer = new V2LinkRenderer(subrenderer, icon_manager, config);
      RendererConfig = config;
      ResourceRenderer = new DefaultEmbeddedResourceRenderer(new FakeAttachmentManager());
      EscapingTool = new DefaultUnicodeEscapingTool(() -> "");
   }

   public String render(String text, IssueRenderContext context) {
      if (StringUtils.isBlank(text)) {
         return "&nbsp;";
      }
      var renderContext = getRenderContext(context);
      return Renderer.render(text, renderContext);
   }

   private RenderContext getRenderContext(IssueRenderContext context) {
      RenderContext renderContext = new RenderContext();
      if (context != null) {
         renderContext.getParams().putAll(context.getParams());
         if (context.getIssue() != null) {
            renderContext.addParam("jira.issue", context.getIssue());
         }
      }
      renderContext.setSiteRoot("");
      renderContext.setImagePath(renderContext.getSiteRoot() + "/images");
      renderContext.setLinkRenderer(LinkRenderer);
      renderContext.setEmbeddedResourceRenderer(ResourceRenderer);
      renderContext.setCharacterEncoding(RendererConfig.getCharacterEncoding());
      renderContext.setUnicodeEscapingTool(EscapingTool);
      renderContext.setBaseUrl("https://bugs.mojang.com");
      renderContext.pushRenderMode(RenderMode.ALL_WITH_NO_MACRO_ERRORS);
      renderContext.addParam("com.atlassian.renderer.v2.components.macro.render.consider.variable.format", true);
      return renderContext;
   }
}
