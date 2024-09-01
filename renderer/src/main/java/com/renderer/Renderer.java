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
      var formatComponents = List.of(
            PhraseRendererComponent.getDefaultRenderer("citation"),
            PhraseRendererComponent.getDefaultRenderer("strong"),
            PhraseRendererComponent.getDefaultRenderer("superscript"),
            PhraseRendererComponent.getDefaultRenderer("subscript"),
            PhraseRendererComponent.getDefaultRenderer("emphasis"),
            PhraseRendererComponent.getDefaultRenderer("deleted"),
            PhraseRendererComponent.getDefaultRenderer("inserted"),
            PhraseRendererComponent.getDefaultRenderer("monospaced")
            );
      var otherComponents = List.of(
            new BackslashEscapeRendererComponent(),
            new HtmlEntityRendererComponent(),
            new HtmlEscapeRendererComponent(),
            new ForceNewLineRendererComponent(),
            new DashRendererComponent(),
            new NewLineRendererComponent());
      var blockRenderers = List.of(
            new TableBlockRenderer(),
            new ListBlockRenderer(),
            new HeadingBlockRenderer(),
            new BlockquoteBlockRenderer(),
            new HorizontalRuleBlockRenderer(),
            new BlankLineBlockRenderer()
            );

      var macroSubComponents = new ArrayList<RendererComponent>();
      macroSubComponents.addAll(otherComponents);
      macroSubComponents.addAll(formatComponents);
      Collections.shuffle(macroSubComponents, RNG);
      macroSubComponents.subList(0, RNG.nextInt(macroSubComponents.size()) + 1).clear();

      var blockSubComponents = new ArrayList<RendererComponent>();
      blockSubComponents.addAll(otherComponents);
      blockSubComponents.addAll(formatComponents);
      Collections.shuffle(blockSubComponents, RNG);
      blockSubComponents.subList(0, RNG.nextInt(blockSubComponents.size()) + 1).clear();
      var blockSubRenderers = new ArrayList<BlockRenderer>();
      blockSubRenderers.addAll(blockRenderers);
      Collections.shuffle(blockSubRenderers, RNG);
      blockSubRenderers.subList(0, RNG.nextInt(blockSubRenderers.size()) + 1).clear();

      var macroSubRenderer1 = new V2SubRenderer(new V2Renderer(macroSubComponents));
      var macroRendererComponent1 = new MacroRendererComponent(
            new DefaultMacroManager(macroSubRenderer1), macroSubRenderer1);

      // blockSubComponents.add(new TestComponent("(", ")"));
      var blockSubRenderer1 = new V2SubRenderer(new V2Renderer(blockSubComponents));
      var blockRendererComponent1 = new BlockRendererComponent(blockSubRenderer1, blockRenderers);

      macroSubComponents.add(blockRendererComponent1);
      macroSubComponents.add(macroRendererComponent1);
      Collections.shuffle(macroSubComponents, RNG);
      var macroSubRenderer2 = new V2SubRenderer(new V2Renderer(macroSubComponents));
      var macroRendererComponent2 = new MacroRendererComponent(
            new DefaultMacroManager(macroSubRenderer2), macroSubRenderer2);

      blockSubComponents.add(blockRendererComponent1);
      blockSubComponents.add(macroRendererComponent1);
      Collections.shuffle(blockSubComponents, RNG);
      var blockSubRenderer2 = new V2SubRenderer(new V2Renderer(blockSubComponents));
      var blockRendererComponent2 = new BlockRendererComponent(blockSubRenderer2, blockRenderers);

      var mainComponents = new ArrayList<RendererComponent>();
      // mainComponents.add(new TestComponent("[","]"));
      mainComponents.addAll(otherComponents);
      mainComponents.addAll(formatComponents);
      mainComponents.add(blockRendererComponent1);
      mainComponents.add(blockRendererComponent2);
      mainComponents.add(macroRendererComponent1);
      mainComponents.add(macroRendererComponent2);
      Collections.shuffle(mainComponents, RNG);
      mainComponents.subList(0, RNG.nextInt(mainComponents.size()) + 1).clear();

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
