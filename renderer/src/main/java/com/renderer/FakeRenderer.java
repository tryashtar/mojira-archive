package com.renderer;

import java.util.ArrayList;
import java.util.Arrays;

import com.atlassian.jira.issue.fields.renderer.wiki.JiraIconManager;
import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.RendererConfiguration;
import com.atlassian.renderer.WikiStyleRenderer;
import com.atlassian.renderer.links.LinkRenderer;
import com.atlassian.renderer.links.LinkResolver;
import com.atlassian.renderer.v2.Renderer;
import com.atlassian.renderer.v2.V2LinkRenderer;
import com.atlassian.renderer.v2.V2Renderer;
import com.atlassian.renderer.v2.V2RendererFacade;
import com.atlassian.renderer.v2.V2SubRenderer;
import com.atlassian.renderer.v2.components.AbstractRendererComponent;
import com.atlassian.renderer.v2.components.BackslashEscapeRendererComponent;
import com.atlassian.renderer.v2.components.CamelCaseLinkRendererComponent;
import com.atlassian.renderer.v2.components.EmbeddedImageRendererComponent;
import com.atlassian.renderer.v2.components.EmbeddedObjectRendererComponent;
import com.atlassian.renderer.v2.components.HtmlEscapeRendererComponent;
import com.atlassian.renderer.v2.components.LinkRendererComponent;
import com.atlassian.renderer.v2.components.MacroRendererComponent;
import com.atlassian.renderer.v2.components.RendererComponent;
import com.atlassian.renderer.v2.components.TokenRendererComponent;
import com.atlassian.renderer.v2.components.UrlRendererComponent;
import com.atlassian.renderer.v2.components.block.BlankLineBlockRenderer;
import com.atlassian.renderer.v2.components.block.BlockRendererComponent;
import com.atlassian.renderer.v2.components.block.BlockquoteBlockRenderer;
import com.atlassian.renderer.v2.components.block.HeadingBlockRenderer;
import com.atlassian.renderer.v2.components.block.HorizontalRuleBlockRenderer;
import com.atlassian.renderer.v2.components.list.ListBlockRenderer;
import com.atlassian.renderer.v2.components.phrase.DashRendererComponent;
import com.atlassian.renderer.v2.components.phrase.EmoticonRendererComponent;
import com.atlassian.renderer.v2.components.phrase.ForceNewLineRendererComponent;
import com.atlassian.renderer.v2.components.phrase.NewLineRendererComponent;
import com.atlassian.renderer.v2.components.phrase.PhraseRendererComponent;
import com.atlassian.renderer.v2.components.table.TableBlockRenderer;
import com.atlassian.renderer.v2.macro.DefaultMacroManager;

import org.apache.commons.lang3.StringUtils;

public class FakeRenderer {
   public final WikiStyleRenderer Facade;
   public final Renderer Renderer;
   public final LinkRenderer LinkRenderer;

   public FakeRenderer(LinkResolver resolver, RendererConfiguration config, AbstractRendererComponent issue_link) {
      var icon_manager = new JiraIconManager();
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
      components.add(issue_link);
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
      var facade = new V2RendererFacade();
      facade.setRenderer(Renderer);
      Facade = facade;
   }

   public String render(String text, RenderContext context) {
      if (StringUtils.isBlank(text)) {
         return "&nbsp;";
      }
      return Facade.convertWikiToXHtml(context, text);
   }
}
