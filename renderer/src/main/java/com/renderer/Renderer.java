package com.renderer;

import com.atlassian.renderer.*;
import com.atlassian.renderer.v2.*;
import com.atlassian.renderer.v2.components.*;
import com.atlassian.renderer.v2.components.block.*;
import com.atlassian.renderer.v2.components.list.ListBlockRenderer;
import com.atlassian.renderer.v2.components.phrase.DashRendererComponent;
import com.atlassian.renderer.v2.components.phrase.ForceNewLineRendererComponent;
import com.atlassian.renderer.v2.components.phrase.NewLineRendererComponent;
import com.atlassian.renderer.v2.components.phrase.PhraseRendererComponent;
import com.atlassian.renderer.v2.components.table.TableBlockRenderer;
import com.atlassian.renderer.v2.macro.DefaultMacroManager;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Renderer {
   public static Random RNG = new Random();

   public Renderer() {
      var macroSubComponents1 = new ArrayList<RendererComponent>();
      macroSubComponents1.add(new ForceNewLineRendererComponent());
      macroSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("monospaced"));
      macroSubComponents1.add(new HtmlEntityRendererComponent());
      macroSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("strong"));
      macroSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("subscript"));
      macroSubComponents1.add(new NewLineRendererComponent());
      macroSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("deleted"));
      macroSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("superscript"));
      macroSubComponents1.add(new BackslashEscapeRendererComponent());

      var blockSubComponents1 = new ArrayList<RendererComponent>();
      blockSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("inserted"));
      blockSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("emphasis"));
      blockSubComponents1.add(new ForceNewLineRendererComponent());
      blockSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("deleted"));
      blockSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("strong"));
      blockSubComponents1.add(new HtmlEntityRendererComponent());
      blockSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("subscript"));
      blockSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("monospaced"));
      blockSubComponents1.add(new NewLineRendererComponent());
      blockSubComponents1.add(new BackslashEscapeRendererComponent());
      blockSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("citation"));
      blockSubComponents1.add(PhraseRendererComponent.getDefaultRenderer("superscript"));
      blockSubComponents1.add(new DashRendererComponent());
      var blockSubRenderers1 = new ArrayList<BlockRenderer>();
      blockSubRenderers1.add(new TableBlockRenderer());
      blockSubRenderers1.add(new ListBlockRenderer());
      blockSubRenderers1.add(new HeadingBlockRenderer());
      blockSubRenderers1.add(new BlockquoteBlockRenderer());
      blockSubRenderers1.add(new HorizontalRuleBlockRenderer());
      blockSubRenderers1.add(new BlankLineBlockRenderer());

      var macroSubRenderer1 = new V2SubRenderer(new V2Renderer(macroSubComponents1));
      var macroRendererComponent1 = new MacroRendererComponent(
            new DefaultMacroManager(macroSubRenderer1), macroSubRenderer1);

      var blockSubRenderer1 = new V2SubRenderer(new V2Renderer(blockSubComponents1));
      var blockRendererComponent1 = new BlockRendererComponent(blockSubRenderer1, blockSubRenderers1);

      var macroSubComponents2 = new ArrayList<RendererComponent>();
      macroSubComponents2.add(blockRendererComponent1);
      macroSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("subscript"));
      macroSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("deleted"));
      macroSubComponents2.add(new NewLineRendererComponent());
      macroSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("strong"));
      macroSubComponents2.add(new HtmlEntityRendererComponent());
      macroSubComponents2.add(new ForceNewLineRendererComponent());
      macroSubComponents2.add(macroRendererComponent1);
      macroSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("monospaced"));
      macroSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("superscript"));
      macroSubComponents2.add(new BackslashEscapeRendererComponent());

      var macroSubRenderer2 = new V2SubRenderer(new V2Renderer(macroSubComponents2));
      var macroRendererComponent2 = new MacroRendererComponent(
            new DefaultMacroManager(macroSubRenderer2), macroSubRenderer2);

      var blockSubComponents2 = new ArrayList<RendererComponent>();
      blockSubComponents2.add(blockRendererComponent1);
      blockSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("deleted"));
      blockSubComponents2.add(new ForceNewLineRendererComponent());
      blockSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("strong"));
      blockSubComponents2.add(new NewLineRendererComponent());
      blockSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("subscript"));
      blockSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("superscript"));
      blockSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("monospaced"));
      blockSubComponents2.add(macroRendererComponent1);
      blockSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("inserted"));
      blockSubComponents2.add(new DashRendererComponent());
      blockSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("citation"));
      blockSubComponents2.add(new BackslashEscapeRendererComponent());
      blockSubComponents2.add(PhraseRendererComponent.getDefaultRenderer("emphasis"));
      blockSubComponents2.add(new HtmlEntityRendererComponent());
      var blockSubRenderers2 = new ArrayList<BlockRenderer>();
      blockSubRenderers2.add(new TableBlockRenderer());
      blockSubRenderers2.add(new ListBlockRenderer());
      blockSubRenderers2.add(new HeadingBlockRenderer());
      blockSubRenderers2.add(new BlockquoteBlockRenderer());
      blockSubRenderers2.add(new HorizontalRuleBlockRenderer());
      blockSubRenderers2.add(new BlankLineBlockRenderer());

      var blockSubRenderer2 = new V2SubRenderer(new V2Renderer(blockSubComponents2));
      var blockRendererComponent2 = new BlockRendererComponent(blockSubRenderer2, blockSubRenderers2);

      var mainComponents = new ArrayList<RendererComponent>();
      mainComponents.add(new HtmlEntityRendererComponent());
      mainComponents.add(new HtmlEscapeRendererComponent());
      mainComponents.add(macroRendererComponent2);
      mainComponents.add(new DashRendererComponent());
      mainComponents.add(macroRendererComponent1);
      mainComponents.add(blockRendererComponent2);
      mainComponents.add(new ForceNewLineRendererComponent());

      this.subRenderer = new V2SubRenderer();
      this.renderContext = makeRenderContext(subRenderer);

      this.rendererFacade = new V2RendererFacade();
      this.rendererFacade.setRenderer(new V2Renderer(mainComponents));
   }

   static class TestComponent implements RendererComponent {
      public String p1;
      public String p2;

      public TestComponent(String p1, String p2) {
         this.p1 = p1;
         this.p2 = p2;
      }

      @Override
      public String render(String wiki, RenderContext context) {
         return p1 + wiki + p2;
      }

      @Override
      public boolean shouldRender(RenderMode renderMode) {
         return true;
      }

   }

   public String plain2html(String text) {
      if (text == null || text.trim().isEmpty()) {
         return text;
      }
      text = doConvert(text);
      return text;
   }

   private String doConvert(String text) {
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

   private RenderContext makeRenderContext(SubRenderer subRenderer) {
      RenderContext renderContext = new RenderContext();
      renderContext.setSiteRoot("TEMP");
      renderContext.setCharacterEncoding(CHARACTER_ENCODING);
      renderContext.setRenderingForWysiwyg(false);
      renderContext.pushRenderMode(RenderMode.ALL_WITH_NO_MACRO_ERRORS);
      return renderContext;
   }

   private final V2RendererFacade rendererFacade;
   private final V2SubRenderer subRenderer;
   private final RenderContext renderContext;

   private static final String CHARACTER_ENCODING = StandardCharsets.UTF_8.name();
}
