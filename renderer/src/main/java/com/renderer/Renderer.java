package com.renderer;

import com.atlassian.jira.bc.issue.attachment.AttachmentService;
import com.atlassian.renderer.*;
import com.atlassian.renderer.attachments.RendererAttachment;
import com.atlassian.renderer.attachments.RendererAttachmentManager;
import com.atlassian.renderer.embedded.DefaultEmbeddedResourceRenderer;
import com.atlassian.renderer.embedded.EmbeddedImage;
import com.atlassian.renderer.embedded.EmbeddedResource;
import com.atlassian.renderer.links.GenericLinkParser;
import com.atlassian.renderer.links.Link;
import com.atlassian.renderer.links.LinkResolver;
import com.atlassian.renderer.links.UrlLink;
import com.atlassian.renderer.v2.*;
import com.atlassian.renderer.v2.components.*;
import com.atlassian.renderer.v2.components.block.*;
import com.atlassian.renderer.v2.components.list.ListBlockRenderer;
import com.atlassian.renderer.v2.components.phrase.DashRendererComponent;
import com.atlassian.renderer.v2.components.phrase.ForceNewLineRendererComponent;
import com.atlassian.renderer.v2.components.phrase.NewLineRendererComponent;
import com.atlassian.renderer.v2.components.phrase.PhraseRendererComponent;
import com.atlassian.renderer.v2.components.table.TableBlockRenderer;
//import ru.protei.portal.core.renderer.impl.markup.custom.userlink.UserLinkRendererComponent;
//import ru.protei.portal.core.renderer.impl.markup.jira.link.LinkRendererComponent;
//import ru.protei.portal.core.renderer.impl.markup.jira.macro.CustomMacroManager;
//import ru.protei.portal.core.renderer.impl.markup.jira.macro.MacroRendererComponent;
//import ru.protei.portal.core.renderer.impl.markup.jira.phrase.NewLineRendererComponent;
//import ru.protei.portal.core.service.AttachmentService;
import com.atlassian.renderer.v2.macro.DefaultMacroManager;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Renderer {

   public Renderer() {
      // Order does matter! Components will be executed one by one. Components may
      // conflict with each other.
      // special NewLineRendererComponent
      List<RendererComponent> renderComponents = new ArrayList<>();
      renderComponents.add(new BackslashEscapeRendererComponent());
      renderComponents.add(new LinkRendererComponent(makeLinkResolver()));
      renderComponents.add(new UrlRendererComponent(makeLinkResolver()));
      //renderComponents.add(new UserLinkRendererComponent());
      renderComponents.add(new EmbeddedImageRendererComponent());
      renderComponents.add(new EmbeddedUnembeddableRendererComponent());
      renderComponents.add(new EmbeddedObjectRendererComponent());
      renderComponents.add(PhraseRendererComponent.getDefaultRenderer("citation"));
      renderComponents.add(PhraseRendererComponent.getDefaultRenderer("strong"));
      renderComponents.add(PhraseRendererComponent.getDefaultRenderer("superscript"));
      renderComponents.add(PhraseRendererComponent.getDefaultRenderer("subscript"));
      renderComponents.add(PhraseRendererComponent.getDefaultRenderer("emphasis"));
      renderComponents.add(PhraseRendererComponent.getDefaultRenderer("deleted"));
      renderComponents.add(PhraseRendererComponent.getDefaultRenderer("inserted"));
      renderComponents.add(PhraseRendererComponent.getDefaultRenderer("monospaced"));
      renderComponents.add(new ForceNewLineRendererComponent());
      V2SubRenderer macroSubRenderer = new V2SubRenderer(new V2Renderer(renderComponents));
      MacroRendererComponent macroRendererComponent = new MacroRendererComponent(
            new DefaultMacroManager(macroSubRenderer), macroSubRenderer);

      List<RendererComponent> renderComponentsAfterMacro = new ArrayList<>(renderComponents);
      renderComponentsAfterMacro.add(macroRendererComponent);
      renderComponentsAfterMacro.add(new DashRendererComponent());
      //renderComponentsAfterMacro.add(new NewLineRendererComponent());

      List<BlockRenderer> blockRendererList = new ArrayList<>();
      blockRendererList.add(new TableBlockRenderer());
      blockRendererList.add(new HeadingBlockRenderer());
      blockRendererList.add(new BlockquoteBlockRenderer());
      blockRendererList.add(new ListBlockRenderer());
      blockRendererList.add(new HorizontalRuleBlockRenderer());
      BlockRendererComponent blockRendererComponent = new BlockRendererComponent(
            new V2SubRenderer(new V2Renderer(renderComponents)),
            blockRendererList);

      List<RendererComponent> renderComponentsAfterBlock = new ArrayList<>(renderComponentsAfterMacro);
      renderComponentsAfterBlock.add(blockRendererComponent);

      this.subRenderer = new V2SubRenderer(new V2Renderer(renderComponentsAfterBlock));
      this.iconManager = new JiraIconManager();
      this.renderContext = makeRenderContext(subRenderer, iconManager);

      V2RendererFacade rendererFacade = new V2RendererFacade();
      rendererFacade.setRenderer(new V2Renderer(renderComponentsAfterBlock));
      this.rendererFacade = rendererFacade;
   }

   public String plain2html(String text) {
      return plain2html(text, true);
   }

   public String plain2html(String text, boolean renderIcons) {
      if (text == null || text.trim().isEmpty()) {
         return text;
      }
      text = doConvert(text, renderIcons);
      return text;
   }

   private String doConvert(String text, boolean renderIcons) {
      RenderContext renderContext = getRenderContext(renderIcons);
      String content = rendererFacade.convertWikiToXHtml(renderContext, text);
      return restoreContentFromContentStore(renderContext, content);
   }

   private String restoreContentFromContentStore(RenderContext context, String content) {

      Map<String, String> replacementMap = new HashMap<>();
      for (TokenType tokenType : TokenType.values()) {
         Pattern p = Pattern.compile(tokenType.getTokenPatternString(), Pattern.CASE_INSENSITIVE);
         Matcher m = p.matcher(content);
         while (m.find()) {
            String token = m.group();
            String replacement = renderFromContentStore(context, token);
            replacementMap.put(token, replacement);
         }
      }

      if (replacementMap.isEmpty()) {
         return content;
      }

      for (Map.Entry<String, String> rep : replacementMap.entrySet()) {
         content = content.replace(rep.getKey(), rep.getValue());
      }

      return restoreContentFromContentStore(context, content);
   }

   private String renderFromContentStore(RenderContext context, String token) {
      RenderedContentStore store = context.getRenderedContentStore();
      Object obj = store.get(token);
      if (obj instanceof String) {
         return (String) obj;
      }
      if (obj instanceof Renderable) {
         StringBuffer sb = new StringBuffer();
         ((Renderable) obj).render(subRenderer, context, sb);
         return sb.toString();
      }
      return "";
   }

   private RenderContext getRenderContext(boolean renderIcons) {
      iconManager.setRenderIcons(renderIcons);
      return renderContext;
   }

   private RenderContext makeRenderContext(SubRenderer subRenderer, IconManager iconManager) {
      RenderContext renderContext = new RenderContext();
      renderContext.setSiteRoot("TEMP");
      renderContext.setImagePath(renderContext.getSiteRoot() + "images");
      renderContext.setLinkRenderer(new V2LinkRenderer(subRenderer, iconManager, makeRendererConfiguration()));
      renderContext
            .setEmbeddedResourceRenderer(new DefaultEmbeddedResourceRenderer(makeRendererAttachmentManager()));
      renderContext.setCharacterEncoding(CHARACTER_ENCODING);
      renderContext.setRenderingForWysiwyg(false);
      return renderContext;
   }

   private RendererAttachmentManager makeRendererAttachmentManager() {
      return new RendererAttachmentManager() {
         private final String DOWNLOAD_PATH = "TEMP";

         @Override
         public RendererAttachment getAttachment(RenderContext renderContext, EmbeddedResource embeddedResource) {
            return null;
         }

         @Override
         public RendererAttachment getThumbnail(RendererAttachment rendererAttachment, RenderContext renderContext,
               EmbeddedImage embeddedImage) {
            return null;
         }

         @Override
         public boolean systemSupportsThumbnailing() {
            return false;
         }
      };
   }

   private LinkResolver makeLinkResolver() {
      return new LinkResolver() {
         @Override
         public Link createLink(RenderContext renderContext, String s) {
            return new UrlLink(new GenericLinkParser(s));
         }

         /* UrlRendererComponent and LinkRendererComponent dont use following methods */
         @Override
         public List extractLinkTextList(String s) {
            return null;
         }

         @Override
         public List extractLinks(RenderContext renderContext, String s) {
            return null;
         }

         @Override
         public String removeLinkBrackets(String s) {
            return null;
         }
      };
   }

   static class JiraIconManager implements IconManager {
      private boolean renderIcons;

      public boolean isRenderIcons() {
         return renderIcons;
      }

      public void setRenderIcons(boolean renderIcons) {
         this.renderIcons = renderIcons;
      }

      @Override
      public Icon getLinkDecoration(String s) {
         int size = isRenderIcons() ? 10 : 0;
         switch (s) {
            case "mailto":
               return Icon.makeRenderIcon("mail_small.png", 1, size, size);
            case "external":
               return Icon.makeRenderIcon("link_small.png", 1, size, size);
         }
         return null;
      }

      /* Following methods dont matter without EmoticonRendererComponent */
      @Override
      public Icon getEmoticon(String s) {
         return null;
      }

      @Override
      public String[] getEmoticonSymbols() {
         return new String[0];
      }
   }

   private RendererConfiguration makeRendererConfiguration() {
      return new RendererConfiguration() {
         @Override
         public String getWebAppContextPath() {
            return "TEMP";
         }

         @Override
         public boolean isNofollowExternalLinks() {
            return true;
         }

         @Override
         public boolean isAllowCamelCase() {
            return false;
         }

         @Override
         public String getCharacterEncoding() {
            return CHARACTER_ENCODING;
         }
      };
   }

   private AttachmentService attachmentService;

   private final V2RendererFacade rendererFacade;
   private final V2SubRenderer subRenderer;
   private final JiraIconManager iconManager;
   private final RenderContext renderContext;

   private static final String CHARACTER_ENCODING = StandardCharsets.UTF_8.name();
}
